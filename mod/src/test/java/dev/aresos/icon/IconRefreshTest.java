package dev.aresos.icon;

import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BooleanSupplier;

import static org.junit.jupiter.api.Assertions.*;

/** While the game runs: reload once when a picture changed, never when nothing did, and not in quick succession. */
class IconRefreshTest {
    private static final Duration GAP = Duration.ofMillis(500);
    @TempDir Path directory;
    private final AtomicReference<Set<String>> shown = new AtomicReference<>(Set.of());
    private final List<Set<String>> handedOut = new CopyOnWriteArrayList<>();
    private final LinkedBlockingQueue<CompletableFuture<Void>> reloads = new LinkedBlockingQueue<>();

    private IconRefresh refresh() {
        return new IconRefresh(() -> directory.resolve("pack"), new PixelIconConverter(), GAP, shown::get, pictures -> {
            shown.set(pictures);
            handedOut.add(pictures);
        });
    }

    private AppDefinition app(String id, int colour) throws IOException {
        var image = new BufferedImage(32, 32, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 32; y++) for (int x = 0; x < 32; x++) image.setRGB(x, y, colour);
        Path file = directory.resolve(id + ".png");
        assertTrue(ImageIO.write(image, "PNG", file.toFile()));
        return new AppDefinition(id, id, List.of(id), "minecraft:paper", false, "command", null, file.toString());
    }

    private static void await(BooleanSupplier done, String what) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while (!done.getAsBoolean()) {
            assertTrue(System.nanoTime() < end, what);
            Thread.sleep(10);
        }
    }

    @Test void picturesAreHandedOutOnlyAfterTheirReloadAndChangesInBetweenShareOne() throws Exception {
        var refresh = refresh();
        refresh.reloader(() -> {
            var reload = new CompletableFuture<Void>();
            reloads.add(reload);
            return reload;
        });

        var red = app("a", 0xffcc0000);
        refresh.request(List.of(red));
        var first = reloads.poll(10, TimeUnit.SECONDS);
        assertNotNull(first, "A new picture asked for no reload");
        Thread.sleep(100);
        assertTrue(handedOut.isEmpty(), "A picture was handed out before the game had loaded it");
        first.complete(null);
        await(() -> shown.get().equals(Set.of("a")), "The picture was never handed out");

        // The same list again: nothing changed, so no reload and nothing handed out.
        refresh.request(List.of(red));
        assertNull(reloads.poll(GAP.toMillis() + 500, TimeUnit.MILLISECONDS), "An unchanged list reloaded the game");
        assertEquals(1, handedOut.size());

        // A change, and three more while its reload runs: those three share the next reload, which keeps its distance.
        refresh.request(List.of(app("a", 0xff0000cc)));
        var second = reloads.poll(10, TimeUnit.SECONDS);
        assertNotNull(second, "A changed picture asked for no reload");
        refresh.request(List.of(app("a", 0xff00cc00)));
        refresh.request(List.of(app("a", 0xffcccc00)));
        refresh.request(List.of(app("a", 0xffcc00cc), app("b", 0xff00cccc)));
        long released = System.nanoTime();
        second.complete(null);
        var third = reloads.poll(10, TimeUnit.SECONDS);
        long waited = System.nanoTime() - released;
        assertNotNull(third, "Changes during a reload were lost");
        assertTrue(waited >= GAP.toNanos() - TimeUnit.MILLISECONDS.toNanos(20),
                "The next reload came after " + TimeUnit.NANOSECONDS.toMillis(waited) + " ms");
        assertEquals(Set.of("a"), shown.get(), "A picture was handed out before the game had loaded it");
        third.complete(null);
        await(() -> shown.get().equals(Set.of("a", "b")), "The last list was never handed out");
        assertNull(reloads.poll(GAP.toMillis() + 500, TimeUnit.MILLISECONDS), "Three changes did not share one reload");
    }

    @Test void aReloadThatFailedIsStillOwed() throws Exception {
        var refresh = refresh();
        refresh.reloader(() -> {
            var reload = new CompletableFuture<Void>();
            reloads.add(reload);
            return reload;
        });
        var app = app("a", 0xffcc0000);
        refresh.request(List.of(app));
        reloads.poll(10, TimeUnit.SECONDS).completeExceptionally(new IllegalStateException("fixture: reload failed"));
        Thread.sleep(200);
        assertTrue(handedOut.isEmpty(), "A picture the game never loaded was handed out");
        // The files are up to date now, but the game has not read them: the next list must still reload.
        refresh.request(List.of(app));
        var again = reloads.poll(10, TimeUnit.SECONDS);
        assertNotNull(again, "The failed reload was forgotten");
        again.complete(null);
        await(() -> shown.get().equals(Set.of("a")), "The picture was never handed out");
    }

    @Test void withoutAGameToReloadPicturesAreHandedOutAtOnce() throws Exception {
        refresh().request(List.of(app("a", 0xffcc0000)));
        await(() -> shown.get().equals(Set.of("a")), "The picture was never handed out");
    }

    @Test void aClientAttachedDuringStartupGenerationLoadsPicturesBeforeTheyAreHandedOut() throws Exception {
        var generating = new CountDownLatch(1);
        var finish = new CountDownLatch(1);
        var pixels = new PixelIconConverter();
        var converter = new IconConverter() {
            @Override public String version() { return "startup-barrier"; }
            @Override public BufferedImage convert(BufferedImage image) {
                generating.countDown();
                try {
                    if (!finish.await(10, TimeUnit.SECONDS)) throw new AssertionError("Startup generation barrier timed out");
                } catch (InterruptedException error) { throw new AssertionError(error); }
                return pixels.convert(image);
            }
        };
        var refresh = new IconRefresh(() -> directory.resolve("pack"), converter, GAP, shown::get, shown::set);
        refresh.request(List.of(app("startup", 0xffcc0000)));
        try {
            assertTrue(generating.await(10, TimeUnit.SECONDS));
            refresh.reloader(() -> {
                var reload = new CompletableFuture<Void>();
                reloads.add(reload);
                return reload;
            });
        } finally { finish.countDown(); }
        var reload = reloads.poll(10, TimeUnit.SECONDS);
        assertNotNull(reload, "The client attached during generation was ignored");
        assertTrue(shown.get().isEmpty(), "Startup published a picture before the attached client loaded it");
        reload.complete(null);
        await(() -> shown.get().equals(Set.of("startup")), "The startup picture was never handed out");
    }
}
