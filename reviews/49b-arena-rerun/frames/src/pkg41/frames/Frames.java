// DEVELOPMENT AID of package 49b (copied from package 41) (measurement only, never shipped): records when each frame starts.
package pkg41.frames;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;

/**
 * Minecraft.runTick runs once per frame; its start time (System.nanoTime, the JVM's CLOCK_MONOTONIC) goes into a
 * small ring that a daemon thread writes out every 250 ms as one number per line. The frame time is the gap between
 * two lines. The ring is 512 KB, allocated once, so the recorder adds no garbage on the render thread.
 */
public final class Frames {
    private static final int SIZE = 1 << 16;
    private static final long[] RING = new long[SIZE];
    private static volatile long written;
    private static long read;

    static {
        String path = System.getProperty("pkg41.frames");
        if (path != null) {
            Thread thread = new Thread(() -> drain(path), "pkg41-frames");
            thread.setDaemon(true);
            thread.start();
        }
    }

    private Frames() {}

    public static void mark() {
        long n = written;
        RING[(int) (n & (SIZE - 1))] = System.nanoTime();
        written = n + 1;
    }

    private static void drain(String path) {
        try (BufferedWriter out = new BufferedWriter(new FileWriter(path, true))) {
            while (true) {
                long until = written;
                if (until - read > SIZE) {
                    out.write("lost " + (until - read - SIZE) + "\n");
                    read = until - SIZE;
                }
                for (; read < until; read++) {
                    out.write(Long.toString(RING[(int) (read & (SIZE - 1))]));
                    out.write('\n');
                }
                out.flush();
                Thread.sleep(250);
            }
        } catch (IOException | InterruptedException error) {
            System.err.println("pkg41-frames stopped: " + error);
        }
    }
}
