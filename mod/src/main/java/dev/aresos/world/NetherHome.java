package dev.aresos.world;

import com.mojang.serialization.Codec;
import com.mojang.datafixers.util.Pair;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
import dev.aresos.mixin.GameModeAccess;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RespawnAnchorBlock;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import net.minecraft.world.level.storage.LevelData;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import static java.nio.file.StandardOpenOption.CREATE_NEW;

/**
 * Explicitly provisioned homes only; enabling the ordinary desktop marker never builds a hub.
 * Despite the name this holds every AresHub home: the Nether one and, since package 32, the flat one
 * ({@link FlatHome}), which shares the save folder, the manifest, the provisioning promises and the home data.
 */
public final class NetherHome extends SavedData {
    /** Which home a new AresHub gets. The manifest names it; a manifest without the key is a Nether home. */
    public enum Kind { NETHER, FLAT }
    /** What a starting server may do with a save: see {@link #startPlan}. */
    public enum Start { NOTHING, MISSING_DATA, PROVISION }
    private static final String KIND_KEY = "home";
    private static final String KIND_FLAT = "flat";
    public static final String SAVE_FOLDER = "AresHub";
    public static final String MANIFEST = "aresos-home.properties";
    public static final String PROVISIONED = "aresos-home.provisioned";
    private static final Set<Path> NEW_WORLDS = ConcurrentHashMap.newKeySet();
    private static final Set<MinecraftServer> NEW_SERVERS = ConcurrentHashMap.newKeySet();
    private static final String MISSING_HOME_MESSAGE = "AresOS home data is missing or unreadable. The world was opened unchanged; "
            + "automatic hub setup and home arrival are disabled. Restore the complete world backup to recover.";
    // Survey and alternate seeds: reviews/04-nether-home/seeds/README.md.
    public static final Site DEFAULT_SITE = new Site(49, -64, 56, 32, 0);
    public static final int RADIUS = 7;
    public static final int SHELL_RADIUS = RADIUS + 1;
    public static final int CEILING = 10;

    public record Site(long seed, int x, int y, int z, float yaw) {
        public static final MapCodec<Site> MAP_CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
                Codec.LONG.fieldOf("seed").forGetter(Site::seed),
                Codec.INT.fieldOf("x").forGetter(Site::x),
                Codec.INT.fieldOf("y").forGetter(Site::y),
                Codec.INT.fieldOf("z").forGetter(Site::z),
                Codec.FLOAT.fieldOf("yaw").forGetter(Site::yaw)).apply(i, Site::new));
        public static final Codec<Site> CODEC = MAP_CODEC.codec();

        public BlockPos floor() { return new BlockPos(x, y, z); }
        public BlockPos anchor() { return floor().offset(-4, 1, 3); }
        public Vec3 arrival() {
            double radians = Math.toRadians(yaw);
            return new Vec3(x + 0.5 - Math.sin(radians) * 5, y + 1, z + 0.5 + Math.cos(radians) * 5);
        }
    }

    public record Home(ResourceKey<Level> dimension, Vec3 position, float yaw, float pitch) {
        public static final Codec<Home> CODEC = RecordCodecBuilder.create(i -> i.group(
                Level.RESOURCE_KEY_CODEC.fieldOf("dimension").forGetter(Home::dimension),
                Vec3.CODEC.fieldOf("position").forGetter(Home::position),
                Codec.FLOAT.fieldOf("yaw").forGetter(Home::yaw),
                Codec.FLOAT.fieldOf("pitch").forGetter(Home::pitch)).apply(i, Home::new));
    }

    // Old saves retain their anchor behavior; an optional exact home adds no migration writes or block edits.
    private static final Codec<NetherHome> CODEC = RecordCodecBuilder.<NetherHome>create(i -> i.group(
            Site.MAP_CODEC.forGetter(home -> home.site),
            Home.CODEC.optionalFieldOf("home").forGetter(home -> Optional.ofNullable(home.home)))
            .apply(i, (site, home) -> new NetherHome(site, home.orElse(null))))
            .mapResult(new Codec.ResultFunction<>() {
                @Override
                public <T> DataResult<Pair<NetherHome, T>> apply(DynamicOps<T> ops, T input,
                                                                 DataResult<Pair<NetherHome, T>> result) {
                    // SavedDataStorage accepts partial results. A damaged home must never become an arrival.
                    return result.error().isPresent() ? DataResult.error(() -> result.error().orElseThrow().message()) : result;
                }

                @Override
                public <T> DataResult<T> coApply(DynamicOps<T> ops, NetherHome home, DataResult<T> result) {
                    return result;
                }
            });
    private static final SavedDataType<NetherHome> TYPE = new SavedDataType<>(AresOs.id("nether_home"),
            () -> new NetherHome(DEFAULT_SITE, null), CODEC, null);
    private final Site site;
    private Home home;

    private NetherHome(Site site, Home home) { this.site = site; this.home = home; }

    public static NetherHome get(MinecraftServer server) {
        var data = server.getDataStorage().get(TYPE);
        if (data == null || data.hasExactHome()) return data;
        Path directory = server.getWorldPath(LevelResource.ROOT);
        try {
            // Only pre-exact-home Nether saves may use the old anchor arrival.
            if (Files.exists(directory.resolve(MANIFEST)) && readKind(directory) != Kind.NETHER) return null;
        } catch (IOException error) {
            return null;
        }
        return data;
    }
    public Site site() { return site; }
    public Home home() { return home != null ? home : new Home(Level.NETHER, site.arrival(), site.yaw, 20); }
    public boolean hasExactHome() { return home != null; }
    public void setHome(Home home) { this.home = home; setDirty(); }

    /** A newly provisioned home that arrives at an exact spot from the start (the flat home). */
    static void store(MinecraftServer server, Site site, Home home) {
        server.getDataStorage().set(TYPE, new NetherHome(site, home));
    }

    public static NetherHome recordHome(MinecraftServer server, Home target) {
        var data = get(server);
        if (data == null) {
            data = new NetherHome(new Site(server.overworld().getSeed(), 0, 64, 0, 0), target);
            server.getDataStorage().set(TYPE, data);
        } else data.setHome(target);
        return data;
    }

    /** The manifest is written only into a newly reserved directory, never into an existing save. */
    public static void writeManifest(Path directory, Site site) throws IOException {
        writeManifest(directory, site, true);
    }

    public static void writeManifest(Path directory, Site site, boolean placeholder) throws IOException {
        var properties = siteProperties(site);
        properties.setProperty("placeholder", Boolean.toString(placeholder));
        storeManifest(directory, properties, "AresOS Nether home provisioning v1; keep with this save");
    }

    /** The manifest of a flat home: the same file and version, with the home kind named. */
    public static void writeFlatManifest(Path directory) throws IOException {
        var properties = siteProperties(FlatHome.SITE);
        properties.setProperty(KIND_KEY, KIND_FLAT);
        storeManifest(directory, properties, "AresOS flat home provisioning v1; keep with this save");
    }

    private static Properties siteProperties(Site site) {
        var properties = new Properties();
        properties.setProperty("version", "1");
        properties.setProperty("seed", Long.toString(site.seed));
        properties.setProperty("x", Integer.toString(site.x));
        properties.setProperty("y", Integer.toString(site.y));
        properties.setProperty("z", Integer.toString(site.z));
        properties.setProperty("yaw", Float.toString(site.yaw));
        return properties;
    }

    private static void storeManifest(Path directory, Properties properties, String comment) throws IOException {
        try (var output = Files.newOutputStream(directory.resolve(MANIFEST), CREATE_NEW)) {
            properties.store(output, comment);
        }
    }

    /** The home kind a manifest asks for. An unknown kind is refused, never guessed. */
    public static Kind readKind(Path directory) throws IOException {
        var properties = new Properties();
        try (var input = Files.newInputStream(directory.resolve(MANIFEST))) { properties.load(input); }
        String value = properties.getProperty(KIND_KEY);
        if (value == null) return Kind.NETHER;
        if (value.equals(KIND_FLAT)) return Kind.FLAT;
        throw new IOException("Invalid AresOS home manifest: unknown home kind");
    }

    private static boolean placeholderRequested(Path directory) throws IOException {
        var properties = new Properties();
        try (var input = Files.newInputStream(directory.resolve(MANIFEST))) { properties.load(input); }
        String value = properties.getProperty("placeholder", "true");
        if (!value.equals("true") && !value.equals("false")) throw new IOException("Invalid placeholder setting");
        return Boolean.parseBoolean(value);
    }

    public static Site readManifest(Path directory) throws IOException {
        var properties = new Properties();
        try {
            try (var input = Files.newInputStream(directory.resolve(MANIFEST))) { properties.load(input); }
            if (!"1".equals(properties.getProperty("version"))) throw new IllegalArgumentException("Unknown version");
            var site = new Site(Long.parseLong(properties.getProperty("seed", "")), Integer.parseInt(properties.getProperty("x", "")),
                    Integer.parseInt(properties.getProperty("y", "")), Integer.parseInt(properties.getProperty("z", "")),
                    Float.parseFloat(properties.getProperty("yaw", "")));
            if (Math.abs((long) site.x) > 1000000 || Math.abs((long) site.z) > 1000000
                    || site.y < 33 || site.y > 100 || !Float.isFinite(site.yaw)) throw new IllegalArgumentException("Invalid site");
            return site;
        } catch (IllegalArgumentException error) { throw new IOException("Invalid AresOS home manifest", error); }
    }

    /** Creation can defer server startup; hand permission to that server before it initializes level data. */
    public static void createNewWorld(Path directory, Runnable create) throws IOException {
        Path key = directory.toAbsolutePath().normalize();
        if (Files.exists(key.resolve("level.dat")) || Files.exists(key.resolve("level.dat_old"))
                || Files.exists(key.resolve(PROVISIONED)) || !NEW_WORLDS.add(key)) {
            throw new IOException("Existing worlds cannot be provisioned automatically");
        }
        try { create.run(); }
        catch (RuntimeException | Error error) {
            NEW_WORLDS.remove(key);
            throw error;
        }
    }

    public static void cancelPendingCreation() { NEW_WORLDS.clear(); }

    public static void register() {
        ServerLifecycleEvents.SERVER_STARTING.register(server -> {
            Path key = server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
            if (NEW_WORLDS.remove(key) && !server.getWorldData().overworldData().isInitialized()) NEW_SERVERS.add(server);
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(NEW_SERVERS::remove);
        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            Path directory = server.getWorldPath(LevelResource.ROOT);
            boolean newWorld = NEW_SERVERS.remove(server);
            try {
                switch (startPlan(directory, get(server) != null, newWorld)) {
                    case NOTHING -> { }
                    case MISSING_DATA -> AresOs.LOGGER.warn(MISSING_HOME_MESSAGE);
                    case PROVISION -> provision(server, directory);
                }
            } catch (IOException error) { AresOs.LOGGER.error("Cannot provision AresOS home; automatic recovery refused", error); }
        });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            if (get(server) == null && Files.exists(server.getWorldPath(LevelResource.ROOT).resolve(MANIFEST))) {
                handler.player.sendSystemMessage(Component.literal(MISSING_HOME_MESSAGE));
            }
        });
    }

    /**
     * The promises every AresHub home keeps, Nether or flat. A home is built only in a world this session created
     * ({@code newWorld}) that carries a manifest and no trace of an earlier provisioning. A save whose home data is
     * missing or unreadable is opened unchanged with a message, and a leftover claim or data file is refused.
     */
    public static Start startPlan(Path directory, boolean hasHomeData, boolean newWorld) throws IOException {
        if (hasHomeData || !Files.exists(directory.resolve(MANIFEST))) return Start.NOTHING;
        if (!newWorld) return Start.MISSING_DATA;
        if (Files.exists(directory.resolve("data/aresos/nether_home.dat")) || Files.exists(directory.resolve(PROVISIONED))) {
            throw new IOException("Previous provisioning detected; restore the save instead of rebuilding the hub");
        }
        return Start.PROVISION;
    }

    private static void provision(MinecraftServer server, Path directory) throws IOException {
        Site site = readManifest(directory);
        Kind kind = readKind(directory);
        if (server.overworld().getSeed() != site.seed) throw new IOException("Home manifest seed differs from world seed");
        // Claim before touching blocks: a crash or partial restore must never authorize a second build.
        Files.writeString(directory.resolve(PROVISIONED), "started\n", CREATE_NEW);
        if (kind == Kind.FLAT) FlatHome.initialize(server, site);
        else {
            boolean placeholder = placeholderRequested(directory);
            if (site.seed != 49 || !placeholder) site = HomeSites.find(java.util.Objects.requireNonNull(server.getLevel(Level.NETHER)));
            initialize(server, site, placeholder);
        }
        server.saveEverything(false, true, true);
        Files.writeString(directory.resolve(PROVISIONED), "complete\n");
    }

    private static void initialize(MinecraftServer server, Site site, boolean placeholder) {
        if (get(server) != null) return;
        ServerLevel nether = java.util.Objects.requireNonNull(server.getLevel(Level.NETHER));
        applyRules(server.getGameRules(), server);
        server.setDifficulty(net.minecraft.world.Difficulty.NORMAL, true);
        if (placeholder) build(nether, site);
        DesktopWorld.setEnabled(server, true);
        Home arrival = placeholder ? null : new Home(Level.NETHER, Vec3.atBottomCenterOf(site.floor().above()), site.yaw, 20);
        server.getDataStorage().set(TYPE, new NetherHome(site, arrival));
    }

    public static void applyRules(GameRules rules, MinecraftServer server) {
        rules.set(GameRules.SPAWN_MOBS, false, server);
        rules.set(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER, 0, server);
        rules.set(GameRules.MOB_GRIEFING, false, server);
        rules.set(GameRules.KEEP_INVENTORY, true, server);
        rules.set(GameRules.SPAWN_PHANTOMS, false, server);
        rules.set(GameRules.SPAWN_PATROLS, false, server);
        rules.set(GameRules.SPAWN_WANDERING_TRADERS, false, server);
    }

    public static boolean isPool(int x, int z) { return x >= 4 && x <= 5 && z >= 3 && z <= 4; }

    public static void build(ServerLevel level, Site site) {
        // A complete nonflammable shell stops both hillside lava and ceiling drips, while glass keeps the view.
        for (int x = -SHELL_RADIUS; x <= SHELL_RADIUS; x++) for (int z = -SHELL_RADIUS; z <= SHELL_RADIUS; z++) {
            boolean edge = Math.abs(x) == SHELL_RADIUS || Math.abs(z) == SHELL_RADIUS;
            for (int y = -1; y <= CEILING; y++) {
                var block = y <= 0 ? Blocks.POLISHED_BLACKSTONE : Blocks.AIR;
                if (y == -1 || (y == 0 && edge)) block = Blocks.BLACKSTONE;
                if (y > 0 && (edge || y == CEILING)) block = Blocks.GLASS;
                if (y > 0 && Math.abs(x) == SHELL_RADIUS && Math.abs(z) == SHELL_RADIUS) block = Blocks.POLISHED_BLACKSTONE_BRICKS;
                if (y == 0 && (Math.abs(x) == 6 && Math.abs(z) == 6)) block = Blocks.GOLD_BLOCK;
                if (y == 0 && (Math.abs(x) == RADIUS || Math.abs(z) == RADIUS)) block = Blocks.GILDED_BLACKSTONE;
                if (y == 0 && x >= 3 && x <= 6 && z >= 2 && z <= 5) block = Blocks.POLISHED_BLACKSTONE_BRICKS;
                // Avoid breaking attached vegetation into item drops while its supports are being replaced.
                level.setBlock(site.floor().offset(x, y, z), block.defaultBlockState(), 2);
            }
        }
        level.setBlockAndUpdate(site.anchor(), Blocks.RESPAWN_ANCHOR.defaultBlockState().setValue(RespawnAnchorBlock.CHARGE, 4));
        for (int x : new int[]{-6, 6}) for (int z : new int[]{-6, 6}) {
            level.setBlockAndUpdate(site.floor().offset(x, 1, z), Blocks.LANTERN.defaultBlockState());
        }
        for (int x = 4; x <= 5; x++) for (int z = 3; z <= 4; z++) {
            level.setBlockAndUpdate(site.floor().offset(x, 0, z), Blocks.LAVA.defaultBlockState());
        }
    }

    /** Called before vanilla captures the login dimension or sends any play packets. */
    public static void arrive(ServerPlayer player) {
        var server = player.level().getServer();
        var home = get(server);
        if (home == null || !DesktopWorld.isEnabled(server)) return;
        Home target = home.home();
        ServerLevel level = server.getLevel(target.dimension);
        if (level == null) {
            AresOs.LOGGER.warn("AresOS home dimension is unavailable; keeping saved player position");
            return;
        }
        if (!dev.aresos.mode.ModeInventories.of(player).enterLiveBeforeLogin(player)) return;
        player.setServerLevel(level);
        ((GameModeAccess) player.gameMode).aresos$setMode(GameType.SURVIVAL, player.gameMode.getGameModeForPlayer());
        player.getAbilities().flying = false;
        player.snapTo(target.position.x, target.position.y, target.position.z, target.yaw, target.pitch);
        player.setDeltaMovement(Vec3.ZERO);
        player.fallDistance = 0;
        player.clearFire();
        dev.aresos.zone.WalkInZones.arrived(player);
        setRespawn(player, home);
        if (!dev.aresos.mode.ModeInventories.of(player).hasStoredInventories()) AppItems.placePinned(player, AresOs.apps());
        dev.aresos.mode.LiveMode.protect(player);
    }

    public static void setRespawn(ServerPlayer player, NetherHome home) {
        Home target = home.home();
        player.setRespawnPosition(new ServerPlayer.RespawnConfig(LevelData.RespawnData.of(target.dimension,
                home.hasExactHome() ? BlockPos.containing(target.position) : home.site.anchor(), target.yaw, target.pitch),
                home.hasExactHome()), false);
    }

    /** Vanilla restores this tree after placeNewPlayer, when our player is already in the Nether. */
    public static boolean restoreVehicleWithoutMount(ServerPlayer player, ValueInput input) {
        var server = player.level().getServer();
        if (get(server) == null || !DesktopWorld.isEnabled(server)) return false;
        input.child("RootVehicle").ifPresent(root -> {
            var source = input.read(ServerPlayer.SavedPosition.MAP_CODEC)
                    .flatMap(ServerPlayer.SavedPosition::dimension).map(server::getLevel);
            if (source.isEmpty()) {
                AresOs.LOGGER.warn("Cannot restore saved home vehicle: original dimension is unavailable");
                return;
            }
            var level = source.get();
            EntityType.loadEntityRecursive(root.childOrEmpty("Entity"), level, EntitySpawnReason.LOAD,
                    entity -> level.addWithUUID(entity) ? entity : null);
        });
        return true;
    }
}
