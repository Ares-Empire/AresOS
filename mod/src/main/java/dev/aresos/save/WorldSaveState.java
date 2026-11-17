package dev.aresos.save;

import dev.aresos.AresOs;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;

import java.nio.file.Path;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.function.Supplier;

/** Associates off-thread storage errors with the world that owns the file, never the currently displayed world. */
public final class WorldSaveState {
    private static final Map<MinecraftServer, WorldSaveState> WORLDS = new IdentityHashMap<>();
    private record Encoding(WorldSaveState state, String chunk, String part, boolean retained) { }
    private static final ThreadLocal<Encoding> ENCODING = new ThreadLocal<>();
    public final SaveFailures failures = new SaveFailures(part -> AresOs.LOGGER.error("World save failed: {}", part));
    private final Path root;

    private WorldSaveState(MinecraftServer server) {
        root = server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
    }

    public static void register() {
        ServerLifecycleEvents.SERVER_STARTING.register(WorldSaveState::of);
        ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
            synchronized (WORLDS) { WORLDS.remove(server); }
        });
    }

    public static WorldSaveState of(MinecraftServer server) {
        synchronized (WORLDS) { return WORLDS.computeIfAbsent(server, WorldSaveState::new); }
    }

    public static WorldSaveState at(Path path) {
        Path absolute = path.toAbsolutePath().normalize();
        synchronized (WORLDS) {
            return WORLDS.values().stream().filter(state -> absolute.startsWith(state.root)).findFirst().orElse(null);
        }
    }

    public static void failure(Path path, String part) {
        var state = at(path);
        if (state != null) state.failures.failure(part);
    }

    public <T> T encoding(String chunk, String part, boolean retained, Supplier<T> action) {
        var previous = ENCODING.get();
        ENCODING.set(new Encoding(this, chunk, part, retained));
        try { return action.get(); }
        finally {
            if (previous == null) ENCODING.remove(); else ENCODING.set(previous);
        }
    }

    public static void encodingProblem(String problem) {
        var current = ENCODING.get();
        if (current == null) return;
        String detail = current.part() + ": " + problem;
        if (current.chunk() != null) {
            current.state().failures.chunkFailure(current.chunk());
            AresOs.LOGGER.error("World save serialization failed: {}", detail);
        } else if (current.retained()) current.state().failures.failure(detail);
        else current.state().failures.lost(detail + "; retention cannot be proved");
    }

    public static String chunk(String dimension, ChunkPos pos) { return dimension + " " + pos; }
}
