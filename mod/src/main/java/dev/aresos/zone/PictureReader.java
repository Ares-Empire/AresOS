package dev.aresos.zone;

import dev.aresos.config.AppDefinition;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.server.MinecraftServer;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Function;

/**
 * Pictures read away from the server thread, one reader a server (review fixes 1, step B, points 3 and 7): an icon may
 * take seconds to read, and turning it into blocks is work too. The server keeps the future it got and uses the
 * pictures in a later tick. When the server stops, everything it still waits for is dropped: a read in progress stops
 * after the app at hand, one that has not started never starts, and nothing is delivered.
 */
public final class PictureReader {
    private static final ExecutorService THREAD = Executors.newSingleThreadExecutor(task -> {
        var thread = new Thread(task, "AresOS pictures");
        thread.setDaemon(true);
        return thread;
    });
    // Server thread only, like the servers themselves.
    private static final Map<MinecraftServer, PictureReader> READERS = new WeakHashMap<>();

    private final Executor executor;
    private final Set<CompletableFuture<?>> waiting = ConcurrentHashMap.newKeySet();
    private volatile boolean dropped;

    PictureReader(Executor executor) { this.executor = executor; }

    public static void register() {
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            var reader = READERS.remove(server);
            if (reader != null) reader.drop();
        });
    }

    /** Server thread: the reader of this server. */
    public static PictureReader of(MinecraftServer server) { return READERS.computeIfAbsent(server, ignored -> new PictureReader(THREAD)); }

    /**
     * Reads something for each app, in order, on the reader thread. The future holds what was read by app ID; it is
     * cancelled when the server stops first, and fails when reading throws.
     */
    public <T> CompletableFuture<Map<String, T>> read(List<AppDefinition> apps, Function<AppDefinition, T> how) {
        var result = new CompletableFuture<Map<String, T>>();
        if (dropped) {
            result.cancel(false);
            return result;
        }
        waiting.add(result);
        result.whenComplete((done, error) -> waiting.remove(result));
        var list = List.copyOf(apps);
        executor.execute(() -> {
            var read = new HashMap<String, T>();
            try {
                for (var app : list) {
                    // Dropped (the server stopped): nothing more is read.
                    if (result.isDone()) return;
                    read.put(app.id(), how.apply(app));
                }
                result.complete(read);
            } catch (RuntimeException error) {
                result.completeExceptionally(error);
            }
        });
        return result;
    }

    /** Drops everything this reader waits for; it reads nothing more. */
    void drop() {
        dropped = true;
        for (var future : List.copyOf(waiting)) future.cancel(false);
    }

    /** How many reads wait for their result. */
    int waiting() { return waiting.size(); }
}
