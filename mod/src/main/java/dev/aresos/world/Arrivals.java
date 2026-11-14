package dev.aresos.world;

import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.util.Mth;
import net.minecraft.world.level.ChunkPos;
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

/**
 * Where {@code /go} puts him when his arrival is not loaded yet (package 37, review fixes 1, point 4). The spots are
 * checked before he is moved (his build is never teleported into), but reading a block of a chunk that is not loaded
 * loads it on the server thread: 416 ms for new ground in a server test. So where a spot's chunk is not loaded, nothing
 * is read: the game's own ticket for teleports ({@link TicketType#PORTAL}) loads the chunks the spots' boxes touch (at
 * most four) away from the server thread, a later tick checks the spots, and he is moved then, or one line says why
 * not. The tickets go when he arrives, when it gives up, and when another move of the mod comes first.
 */
public final class Arrivals {
    /** How long a {@code /go} waits for its arrival to load: this many ticks and this long on the clock, both. */
    private static final int WAIT_TICKS = 200;
    private static final long WAIT_NANOS = TimeUnit.SECONDS.toNanos(10);
    /** A ticket of this radius loads its own chunk only. */
    private static final int RADIUS = 0;

    /** What a {@link #go} did: he arrived, no spot is free, or the spots are loading and a later tick moves him. */
    public enum Result { ARRIVED, BLOCKED, LOADING }

    /** One {@code /go} on its way: the spots in order, the facing, its lines, the chunks it loads, and since when. */
    private record Pending(ServerLevel level, List<Vec3> spots, float yaw, float pitch, String arrived, String blocked, String late,
                           Set<Long> chunks, int tick, long started) { }

    // Server thread only, like the servers themselves.
    private static final Map<MinecraftServer, Map<UUID, Pending>> PENDING = new WeakHashMap<>();

    private Arrivals() { }

    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(Arrivals::tick);
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> drop(server, handler.player.getUUID()));
        ServerLifecycleEvents.SERVER_STOPPED.register(PENDING::remove);
    }

    /**
     * Moves him to the first of the spots where he can stand ({@link HomeSites#isSafe}), looking this way: now, when
     * the chunks of every spot are loaded; otherwise once they are, from a later tick, which then says the line of
     * {@code arrived} (may be null), {@code blocked} or {@code late} itself. Now, the caller says them.
     */
    public static Result go(ServerPlayer player, ServerLevel level, List<Vec3> spots, float yaw, float pitch,
                            String arrived, String blocked, String late) {
        var server = level.getServer();
        drop(server, player.getUUID());
        var chunks = chunks(spots);
        if (loaded(level, chunks)) return land(player, level, spots, yaw, pitch) ? Result.ARRIVED : Result.BLOCKED;
        for (long chunk : chunks) level.getChunkSource().addTicketWithRadius(TicketType.PORTAL, ChunkPos.unpack(chunk), RADIUS);
        PENDING.computeIfAbsent(server, ignored -> new HashMap<>()).put(player.getUUID(),
                new Pending(level, List.copyOf(spots), yaw, pitch, arrived, blocked, late, chunks, server.getTickCount(), System.nanoTime()));
        return Result.LOADING;
    }

    /** Another move of the mod came first ({@code HomeCommands.teleport}): a {@code /go} still loading is dropped. */
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
            if (player == null) {
                drop(server, entry.getKey());
            } else if (loaded(pending.level(), pending.chunks())) {
                drop(server, entry.getKey());
                if (!land(player, pending.level(), pending.spots(), pending.yaw(), pending.pitch()))
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
