package dev.aresos.world;

import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.util.Mth;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * Where {@code /go} puts him when his arrival is not loaded yet (package 37, review fixes 1, point 4). The spots are
 * checked before he is moved (his build is never teleported into), but reading a block of a chunk that is not loaded
 * loads it within the command: 416 ms for new ground in a server test. So where a spot's chunk is not loaded, the
 * command reads nothing: the chunks the spots' boxes touch (at most four) are requested through the game's ticket
 * system, with its own ticket for teleports ({@link TicketType#PORTAL}), and checked in a later tick; the game loads
 * them in its own server ticks (new ground took one tick of about 400 ms in that test). Once they are loaded the spots
 * are checked, and he is moved then, or one line says why not.
 *
 * <p>A waiting {@code /go} is his wish only while it is still his (review fixes 2, point 2). It belongs to his
 * connection and to the dimension he typed it in, and it is dropped, its tickets released and nothing said, when he
 * leaves the game, changes dimension, dies or respawns, or is moved by void recovery or any other teleport of the mod.
 * Before it lands it checks its target again ({@code still}): otherwise it says one line and he stays. The tickets
 * also go when he arrives and when it gives up.
 */
public final class Arrivals {
    /** How long a {@code /go} waits for its arrival to load: this many ticks and this long on the clock, both. */
    private static final int WAIT_TICKS = 200;
    private static final long WAIT_NANOS = TimeUnit.SECONDS.toNanos(10);
    /** A ticket of this radius loads its own chunk only. */
    private static final int RADIUS = 0;

    /** What a {@link #go} did: he arrived, no spot is free, or the spots are loading and a later tick moves him. */
    public enum Result { ARRIVED, BLOCKED, LOADING }

    /**
     * One {@code /go} on its way: the spots in order, the facing, its lines, the check of its target, the chunks it
     * loads, since when, and the connection and dimension it was typed in.
     */
    private record Pending(ServerLevel level, List<Vec3> spots, float yaw, float pitch, String arrived, String blocked, String late,
                           Supplier<Optional<String>> still, Set<Long> chunks, int tick, long started,
                           ServerGamePacketListenerImpl connection, ResourceKey<Level> from) { }

    // Server thread only, like the servers themselves.
    private static final Map<MinecraftServer, Map<UUID, Pending>> PENDING = new WeakHashMap<>();

    private Arrivals() { }

    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(Arrivals::tick);
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> drop(server, handler.player.getUUID()));
        ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
            if (entity instanceof ServerPlayer player) cancel(player);
        });
        ServerPlayerEvents.AFTER_RESPAWN.register((before, after, alive) -> cancel(after));
        ServerLifecycleEvents.SERVER_STOPPED.register(PENDING::remove);
    }

    /**
     * Moves him to the first of the spots where he can stand ({@link HomeSites#isSafe}), looking this way: now, when
     * the chunks of every spot are loaded; otherwise once they are, from a later tick, which then says the line of
     * {@code arrived} (may be null), {@code blocked} or {@code late} itself. Now, the caller says them.
     *
     * @param still asked in that later tick before he is moved: empty while the target is still his, otherwise the
     *              one line why he stays
     */
    public static Result go(ServerPlayer player, ServerLevel level, List<Vec3> spots, float yaw, float pitch,
                            String arrived, String blocked, String late, Supplier<Optional<String>> still) {
        var server = level.getServer();
        drop(server, player.getUUID());
        var chunks = chunks(spots);
        if (loaded(level, chunks)) return land(player, level, spots, yaw, pitch) ? Result.ARRIVED : Result.BLOCKED;
        for (long chunk : chunks) level.getChunkSource().addTicketWithRadius(TicketType.PORTAL, ChunkPos.unpack(chunk), RADIUS);
        PENDING.computeIfAbsent(server, ignored -> new HashMap<>()).put(player.getUUID(),
                new Pending(level, List.copyOf(spots), yaw, pitch, arrived, blocked, late, still, chunks, server.getTickCount(), System.nanoTime(),
                        player.connection, player.level().dimension()));
        return Result.LOADING;
    }

    /**
     * He died, respawned or was moved by the mod (the shared teleport {@code HomeCommands.teleport}, void recovery, the
     * spawn on joining): a {@code /go} still loading is dropped, with its tickets, and nothing is said.
     */
    public static void cancel(ServerPlayer player) {
        drop(player.level().getServer(), player.getUUID());
    }

    /** Whether a {@code /go} of his is loading. */
    public static boolean loading(ServerPlayer player) {
        var waiting = PENDING.get(player.level().getServer());
        return waiting != null && waiting.containsKey(player.getUUID());
    }

    private static void tick(MinecraftServer server) {
        var waiting = PENDING.get(server);
        if (waiting == null || waiting.isEmpty()) return;
        for (var entry : List.copyOf(waiting.entrySet())) {
            var pending = entry.getValue();
            var player = server.getPlayerList().getPlayer(entry.getKey());
            // His wish only on the connection and in the dimension he typed it in: otherwise dropped, nothing said.
            if (player == null || player.connection != pending.connection() || !player.level().dimension().equals(pending.from())) {
                drop(server, entry.getKey());
            } else if (loaded(pending.level(), pending.chunks())) {
                drop(server, entry.getKey());
                var gone = pending.still().get();
                if (gone.isPresent()) player.sendSystemMessage(Component.literal(gone.get()).withStyle(ChatFormatting.RED));
                else if (!land(player, pending.level(), pending.spots(), pending.yaw(), pending.pitch()))
                    player.sendSystemMessage(Component.literal(pending.blocked()).withStyle(ChatFormatting.RED));
                else if (pending.arrived() != null) player.sendSystemMessage(Component.literal(pending.arrived()));
            } else if (server.getTickCount() - pending.tick() >= WAIT_TICKS && System.nanoTime() - pending.started() >= WAIT_NANOS) {
                drop(server, entry.getKey());
                player.sendSystemMessage(Component.literal(pending.late()).withStyle(ChatFormatting.RED));
            }
        }
    }

    /** To the first free spot; false, and he stays, when none is free. Reads loaded chunks only. */
    private static boolean land(ServerPlayer player, ServerLevel level, List<Vec3> spots, float yaw, float pitch) {
        Optional<Vec3> spot = spots.stream().filter(candidate -> HomeSites.isSafe(level, candidate)).findFirst();
        spot.ifPresent(at -> HomeCommands.teleport(player, level, at, yaw, pitch));
        return spot.isPresent();
    }

    /** Takes a waiting {@code /go} away with its tickets. */
    private static void drop(MinecraftServer server, UUID player) {
        var waiting = PENDING.get(server);
        var pending = waiting == null ? null : waiting.remove(player);
        if (pending == null) return;
        for (long chunk : pending.chunks())
            pending.level().getChunkSource().removeTicketWithRadius(TicketType.PORTAL, ChunkPos.unpack(chunk), RADIUS);
    }

    /** The chunks the boxes of a player standing on these spots touch, and the blocks under them: at most four here. */
    static Set<Long> chunks(List<Vec3> spots) {
        var chunks = new LinkedHashSet<Long>();
        for (var spot : spots) for (double dx : new double[] {-0.3, 0.3}) for (double dz : new double[] {-0.3, 0.3})
            chunks.add(ChunkPos.pack(Mth.floor(spot.x + dx) >> 4, Mth.floor(spot.z + dz) >> 4));
        return chunks;
    }

    private static boolean loaded(ServerLevel level, Set<Long> chunks) {
        return chunks.stream().allMatch(chunk -> level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)));
    }
}
