package dev.aresos.zone;

import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import static java.util.concurrent.TimeUnit.SECONDS;
import static org.junit.jupiter.api.Assertions.*;

/** Pictures read away from the server thread, and dropped when the server stops (review fixes 1, step B, points 3 and 7). */
class PictureReaderTest {
    private static AppDefinition app(String id) { return new AppDefinition(id, id, List.of(id), "minecraft:ender_pearl", false); }

    @Test
    void readsEachAppInOrderOffTheCallingThread() throws Exception {
        var executor = Executors.newSingleThreadExecutor();
        try {
            var reader = new PictureReader(executor);
            var caller = Thread.currentThread();
            var read = reader.read(List.of(app("a"), app("b")), app -> app.id() + (Thread.currentThread() != caller));
            assertEquals(Map.of("a", "atrue", "b", "btrue"), read.get(5, SECONDS));
            assertEquals(0, reader.waiting());
        } finally {
            executor.shutdownNow();
        }
    }

    @Test
    void aStoppedServerLeavesNoWork() throws Exception {
        var executor = Executors.newSingleThreadExecutor();
        try {
            var reader = new PictureReader(executor);
            var started = new CountDownLatch(1);
            var release = new CountDownLatch(1);
            var reads = new AtomicInteger();
            var slow = reader.read(List.of(app("slow"), app("next")), app -> {
                reads.incrementAndGet();
                started.countDown();
                try {
                    assertTrue(release.await(5, SECONDS));
                } catch (InterruptedException interrupted) {
                    throw new IllegalStateException(interrupted);
                }
                return app.id();
            });
            assertTrue(started.await(5, SECONDS));
            var queued = reader.read(List.of(app("queued")), app -> reads.incrementAndGet());
            assertEquals(2, reader.waiting());

            reader.drop();
            release.countDown();
            // The thread finishes the app at hand and reads nothing more: not the next app, not the queued read.
            executor.submit(() -> { }).get(5, SECONDS);
            assertTrue(slow.isCancelled() && queued.isCancelled());
            assertEquals(1, reads.get());
            assertEquals(0, reader.waiting());
            // Nothing starts after the stop.
            assertTrue(reader.read(List.of(app("late")), app -> reads.incrementAndGet()).isCancelled());
            executor.submit(() -> { }).get(5, SECONDS);
            assertEquals(1, reads.get());
        } finally {
            executor.shutdownNow();
        }
    }
}
