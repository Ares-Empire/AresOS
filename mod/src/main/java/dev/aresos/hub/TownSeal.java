package dev.aresos.hub;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.mixin.ServerStorageAccess;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.storage.LevelStorageSource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collections;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.WeakHashMap;

/**
 * The seal on the town's records (review fixes 1, point 1): {@code data/aresos/town-seal.dat}, written right after
 * each {@code level.dat} the game writes while this mod runs. It holds the {@code LastPlayed} just written into
 * {@code level.dat}, the world's seed and the fingerprint of the town's records ({@code town.dat}) as they are saved
 * with it. The town is sealed when the seal is there and all three still fit the world it opens.
 *
 * <p>So a world copied or renamed as a whole stays sealed (its files move together), while a world that an older mod
 * or plain Minecraft saved since (a new {@code LastPlayed} and no seal for it), a {@code town.dat} restored from a
 * backup or copied from another world (another fingerprint), and a crash between {@code level.dat} and the seal come
 * out unsealed. The last is a false alarm on the safe side.
 *
 * <p>The game writes {@code level.dat} in two kinds of places: the server's saves, where the town is in memory and
 * the seal is written from it (unless the town is frozen or refused: then the seal is not renewed), and before a
 * server runs on the world (the game writes {@code level.dat} as it opens a world, and when it optimizes one), where
 * a seal that holds just before the write is carried over to the new {@code LastPlayed}.
 */
public final class TownSeal {
    /** The seal as saved: the {@code LastPlayed} it was written for, the seed, the town's fingerprint. */
    public record Seal(long lastPlayed, long seed, String town) {
        static final Codec<Seal> CODEC = RecordCodecBuilder.create(i -> i.group(
                Codec.LONG.fieldOf("last_played").forGetter(Seal::lastPlayed),
                Codec.LONG.fieldOf("seed").forGetter(Seal::seed),
                Codec.STRING.fieldOf("town").forGetter(Seal::town)).apply(i, Seal::new));
    }

    /** Where the seal lies, beside {@code hub.dat} and {@code town.dat}. */
    public static Path file(Path world) { return world.resolve(LevelResource.DATA.id()).resolve(AresOs.id("town-seal").getNamespace()).resolve("town-seal.dat"); }

    /** The world's level storage each running server writes through, so a save knows whose town to seal. */
    private static final Map<LevelStorageSource.LevelStorageAccess, MinecraftServer> SERVERS = Collections.synchronizedMap(new WeakHashMap<>());
    /** The {@code LastPlayed} of the level data being written on this thread. */
    private static final ThreadLocal<Long> WRITTEN = new ThreadLocal<>();
    /** A seal that held just before {@code level.dat} is written without a server: carried over to the new one. */
    private static final ThreadLocal<Seal> CARRIED = new ThreadLocal<>();

    private TownSeal() { }

    public static void register() {
        ServerLifecycleEvents.SERVER_STARTING.register(server -> SERVERS.put(((ServerStorageAccess)server).aresos$storageSource(), server));
        ServerLifecycleEvents.SERVER_STOPPED.register(server -> SERVERS.remove(((ServerStorageAccess)server).aresos$storageSource()));
    }

    /** Mixin, {@code PrimaryLevelData.writeLastPlayed}: the level data about to be written holds this {@code LastPlayed}. */
    public static void lastPlayed(long value) { WRITTEN.set(value); }

    /** Mixin, the start of {@code saveDataTag}: {@code level.dat} is about to be written. */
    public static void before(LevelStorageSource.LevelStorageAccess access) {
        WRITTEN.remove();
        CARRIED.remove();
        try {
            var server = SERVERS.get(access);
            // The server reads the town's records, and checks them against the seal, before its save changes level.dat.
            if (server != null) HubData.get(server);
            else holding(access.getLevelPath(LevelResource.ROOT)).ifPresent(CARRIED::set);
        } catch (RuntimeException error) {
            AresOs.LOGGER.error("Could not read the town's seal before a save", error);
        }
    }

    /** Mixin, the end of {@code saveDataTag}: {@code level.dat} was just written. Writes the seal for it, if any. */
    public static void after(LevelStorageSource.LevelStorageAccess access) {
        Long written = WRITTEN.get();
        Seal carried = CARRIED.get();
        WRITTEN.remove();
        CARRIED.remove();
        if (written == null) return;
        try {
            var world = access.getLevelPath(LevelResource.ROOT);
            var server = SERVERS.get(access);
            if (server != null) {
                var hub = HubData.get(server);
                var town = hub == null ? Optional.<HubData.TownFile>empty() : hub.sealable();
                if (town.isPresent()) write(world, new Seal(written, seed(server), fingerprint(town.get())));
            } else if (carried != null) write(world, new Seal(written, carried.seed(), carried.town()));
        } catch (IOException | RuntimeException error) {
            AresOs.LOGGER.error("Could not write the town's seal", error);
        }
    }

    /** The world's seed, as the seal holds it. */
    public static long seed(MinecraftServer server) { return server.getWorldGenSettings().options().seed(); }

    /**
     * Whether a world's town records are sealed: the seal is there, it was written for the {@code LastPlayed} that
     * {@code level.dat} holds now, for this seed, and for exactly these records.
     */
    static boolean sealed(Path world, long seed, HubData.TownFile town) {
        return holding(world).filter(seal -> seal.seed() == seed && seal.town().equals(fingerprint(town))).isPresent();
    }

    /** The seal, while it was written for the {@code LastPlayed} that {@code level.dat} holds now. */
    public static Optional<Seal> holding(Path world) {
        var lastPlayed = lastPlayed(world);
        return read(world).filter(seal -> lastPlayed.isPresent() && seal.lastPlayed() == lastPlayed.getAsLong());
    }

    /** The {@code LastPlayed} in a world's {@code level.dat}; empty when there is none or it cannot be read. */
    public static OptionalLong lastPlayed(Path world) {
        var file = world.resolve(LevelResource.LEVEL_DATA_FILE.id());
        if (!Files.isRegularFile(file)) return OptionalLong.empty();
        try {
            var data = NbtIo.readCompressed(file, NbtAccounter.uncompressedQuota()).getCompoundOrEmpty("Data");
            return data.getLong("LastPlayed").map(OptionalLong::of).orElse(OptionalLong.empty());
        } catch (IOException | RuntimeException error) {
            AresOs.LOGGER.warn("Could not read {}", file, error);
            return OptionalLong.empty();
        }
    }

    /** The seal of a world; empty when there is none or it cannot be read. */
    public static Optional<Seal> read(Path world) {
        var file = file(world);
        if (!Files.isRegularFile(file)) return Optional.empty();
        try {
            return Seal.CODEC.parse(NbtOps.INSTANCE, NbtIo.readCompressed(file, NbtAccounter.uncompressedQuota())).result();
        } catch (IOException | RuntimeException error) {
            AresOs.LOGGER.warn("Could not read {}", file, error);
            return Optional.empty();
        }
    }

    /** Writes a world's seal whole or not at all, as the game writes {@code level.dat}. */
    public static void write(Path world, Seal seal) throws IOException {
        var file = file(world);
        Files.createDirectories(file.getParent());
        var temporary = Files.createTempFile(file.getParent(), "town-seal", ".dat");
        try {
            NbtIo.writeCompressed((CompoundTag)Seal.CODEC.encodeStart(NbtOps.INSTANCE, seal).getOrThrow(), temporary);
            Files.move(temporary, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(temporary);
        }
    }

    /**
     * The fingerprint of the town's records: SHA-256 of the town file as it is saved, in the game's text form of it,
     * whose keys are in a fixed order. The same records give the same fingerprint however often they are read and
     * saved again; one block more or less, or another home, gives another.
     */
    static String fingerprint(HubData.TownFile town) {
        var text = HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, town).getOrThrow().toString();
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
