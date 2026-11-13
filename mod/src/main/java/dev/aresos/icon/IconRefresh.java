package dev.aresos.icon;

import dev.aresos.config.AppDefinition;

import java.io.IOException;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Consumer;
import java.util.function.Supplier;

/**
 * Keeps the icon pack in step with the app list while the game runs. One background thread makes the pictures.
 * When a file of the pack changed, the game loads its resource packs again, at most once per {@code gap}; lists
 * that arrive in between share the next reload. Only after the reload are the new pictures handed out
 * ({@code publish}), so an item never points at a picture the game has not loaded. When nothing changed, nothing
 * is reloaded and nothing is handed out.
 */
public final class IconRefresh {
    /** Loads the game's resource packs again. The future completes when the new pictures can be drawn. */
    public interface Reloader { CompletableFuture<Void> reload(); }

    private static final Duration RELOAD_WAIT = Duration.ofMinutes(5);
    private final Supplier<Path> pack;
    private final IconConverter converter;
    private final Duration gap;
    private final Supplier<Set<String>> current;
    private final Consumer<Set<String>> publish;
    private volatile Reloader reloader;
    private final Object lock = new Object();
    private List<AppDefinition> waiting;
    private boolean working;
    // The three below belong to the worker thread.
    private long lastReload;
    private boolean reloaded;
    private boolean reloadOwed;

    /**
     * @param current the apps whose pictures the game shows now
     * @param publish takes the new set once the game can draw it
     */
    public IconRefresh(Supplier<Path> pack, IconConverter converter, Duration gap,
                       Supplier<Set<String>> current, Consumer<Set<String>> publish) {
        this.pack = pack;
        this.converter = converter;
        this.gap = gap;
        this.current = current;
        this.publish = publish;
    }

    /** Without a reloader (a server, a test) new pictures are handed out at once. */
    public void reloader(Reloader reloader) { this.reloader = reloader; }

    /** Any thread. Only the latest list counts; this never waits for the pictures. */
    public void request(List<AppDefinition> apps) {
        synchronized (lock) {
            waiting = List.copyOf(apps);
            if (working) return;
            working = true;
        }
        Thread.ofPlatform().daemon().name("aresos-icons").start(this::work);
    }

    private void work() {
        while (true) {
            try {
                Reloader reload = reloader;
                if (reload != null && reloaded) {
                    // Lists that arrive while the last reload is still fresh collect here and share the next one.
                    long wait = gap.toNanos() - (System.nanoTime() - lastReload);
                    if (wait > 0) TimeUnit.NANOSECONDS.sleep(wait);
                }
                List<AppDefinition> apps;
                synchronized (lock) {
                    apps = waiting;
                    waiting = null;
                    if (apps == null) {
                        working = false;
                        return;
                    }
                }
                var result = IconPack.generate(pack.get(), apps, converter);
                reloadOwed |= result.changed();
                if (!reloadOwed && result.generated().equals(current.get())) continue;
                if (reloadOwed && reload != null) {
                    // A reload that failed is still owed: the files changed, and the game has not read them.
                    try { reload.reload().get(RELOAD_WAIT.toMillis(), TimeUnit.MILLISECONDS); }
                    finally {
                        lastReload = System.nanoTime();
                        reloaded = true;
                    }
                }
                reloadOwed = false;
                publish.accept(result.generated());
            } catch (InterruptedException stopped) {
                synchronized (lock) { working = false; }
                Thread.currentThread().interrupt();
                return;
            } catch (IOException | RuntimeException | ExecutionException | TimeoutException error) {
                System.getLogger("aresos").log(System.Logger.Level.ERROR, "Could not refresh the app icons; the old ones stay", error);
            }
        }
    }
}
