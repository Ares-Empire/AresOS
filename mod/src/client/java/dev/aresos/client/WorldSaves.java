package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.shell.LifecycleClient;
import dev.aresos.shell.LifecycleClient.Saved;
import dev.aresos.world.DesktopWorld;
import dev.aresos.save.SaveRepair;
import dev.aresos.save.WorldSaveState;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.server.MinecraftServer;

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;

/**
 * Package 46: the game's side of the lifecycle channel's {@code save_world}. A save runs on the integrated server's
 * thread as {@code save-all flush} does ({@code saveEverything} with flush, so the chunk IO is on disk before the
 * answer), without a pause, a screen or leaving the world. The server thread keeps taking tasks while the game is
 * paused (covered, or the Esc menu open), so a save runs then too.
 *
 * <p>A save that has not started when the server begins to stop is refused as {@code server_stopping}: the server's own
 * stop saves the world, and this mod never claims a save it did not make.
 */
public final class WorldSaves implements LifecycleClient.Game {
    public static final WorldSaves INSTANCE = new WorldSaves();

    private final Object lock = new Object();
    // Guarded by lock: the integrated server from its start until it stopped, whether it began to stop, and the saves
    // asked of a server that have not started yet (refused when that server begins to stop).
    private MinecraftServer open;
    private boolean stopping;
    private final Map<CompletableFuture<Saved>, MinecraftServer> queued = new IdentityHashMap<>();

    private WorldSaves() { }

    /** Once, from the client's initializer. */
    public void register() {
        ServerLifecycleEvents.SERVER_STARTED.register(this::started);
        ServerLifecycleEvents.SERVER_STOPPING.register(this::stopping);
        ServerLifecycleEvents.SERVER_STOPPED.register(this::stopped);
    }

    /** The server is ready: saves can be asked of it. Public, like the two below, for the client test. */
    public void started(MinecraftServer server) {
        synchronized (lock) {
            open = server;
            stopping = false;
        }
    }

    /**
     * On the server thread, before it saves and closes the world: a save queued behind this would never run as asked,
     * so it is refused, and so is every request until the server stopped.
     */
    public void stopping(MinecraftServer server) {
        var refused = new ArrayList<CompletableFuture<Saved>>();
        synchronized (lock) {
            if (open == server) stopping = true;
            queued.entrySet().removeIf(entry -> entry.getValue() == server && refused.add(entry.getKey()));
        }
        refused.forEach(save -> save.complete(Saved.refused("server_stopping")));
    }

    /** No world any more: requests are answered {@code no_world}. */
    public void stopped(MinecraftServer server) {
        synchronized (lock) {
            if (open != server) return;
            open = null;
            stopping = false;
        }
    }

    @Override public CompletionStage<Saved> save(Runnable starting) {
        var result = new CompletableFuture<Saved>();
        MinecraftServer server;
        synchronized (lock) {
            server = open;
            if (server == null) return CompletableFuture.completedFuture(Saved.refused("no_world"));
            if (stopping) return CompletableFuture.completedFuture(Saved.refused("server_stopping"));
            queued.put(result, server);
        }
        try {
            server.executeIfPossible(() -> {
                Saved saved;
                try {
                    saved = run(server, starting, result);
                } catch (RuntimeException error) {
                    // Every request gets its answer, whatever went wrong before the save.
                    AresOs.LOGGER.error("The save the AresOS supervisor asked for failed before it began", error);
                    saved = Saved.refused("error");
                }
                if (saved != null) result.complete(saved);
            });
        } catch (RejectedExecutionException stopped) {
            synchronized (lock) { queued.remove(result); }
            result.complete(Saved.refused("server_stopping"));
        }
        return result;
    }

    /** On the server thread. Null when the server's stop refused this save already. */
    private Saved run(MinecraftServer server, Runnable starting, CompletableFuture<Saved> result) {
        synchronized (lock) {
            if (queued.remove(result) == null) return null;
            // A server that stopped in between runs the task in place, on the asking thread: never save from there.
            if (open != server || stopping || !server.isSameThread()) return Saved.refused("server_stopping");
        }
        if (!DesktopWorld.isEnabled(server)) return Saved.refused("not_desktop_world");
        starting.run();
        long began = System.nanoTime();
        var state = WorldSaveState.of(server);
        // Earlier autosaves may still be completing. Account for them before deciding what needs rewriting.
        state.failures.awaitWrites();
        var attempt = state.failures.begin();
        boolean saved = false;
        try {
            if (attempt.rewrite()) {
                ((SaveRepair) server.getDataStorage()).aresos$rewrite();
                for (var level : server.getAllLevels()) {
                    ((SaveRepair) level.getChunkSource().getDataStorage()).aresos$rewrite();
                    ((SaveRepair) level.getChunkSource().getPoiManager()).aresos$rewrite();
                    ((SaveRepair) level.getChunkSource().chunkMap).aresos$rewrite();
                }
            }
            // save-all flush: quiet logs, flush, and saved even if saving was turned off.
            saved = server.saveEverything(true, true, true);
            // Vanilla's POI flush only queues writes; its own synchronization also forces the region files.
            for (var level : server.getAllLevels())
                ((SaveRepair) level.getChunkSource().getPoiManager()).aresos$flush();
        } catch (RuntimeException error) {
            saved = false;
            AresOs.LOGGER.error("The save the AresOS supervisor asked for failed", error);
        } finally {
            state.failures.awaitWrites();
        }
        if (state.failures.finish(attempt, saved))
            return Saved.done(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - began), DesktopWorld.saveName(server));
        return Saved.refused("error");
    }

    /** The saves asked of a server and not yet started; for tests. */
    public List<MinecraftServer> queued() {
        synchronized (lock) { return List.copyOf(queued.values()); }
    }
}
