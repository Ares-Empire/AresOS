package dev.aresos.test;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Package 46, owner fix 1: what {@link SaveNowClientGameTest} needs to see of vanilla's "Saving world" corner text.
 * {@code SavingTextTestMixin} counts every frame that draws it and gives the HUD's tick every save that began since its
 * last tick.
 *
 * <p>Why the second: the text rises only while a client tick finds the server saving. The test's client and server tick
 * in lockstep, both within the same step, so whether a client tick catches a save depends on their order there, not on
 * how long the save takes (the report's JUDGMENT-CALL saw a 81 ms save never caught). In play the client ticks every
 * 50 ms on its own, so a save of 50 ms or more always shows. While this is on, a save that began since the client's last
 * tick counts as running at its next one; the text then rises for every save, as the test needs to show where it is
 * drawn and where not. Off, the HUD sees exactly what Minecraft sees.
 */
public final class SavingText {
    private static volatile boolean on;
    // Saves begun on the server (Fabric's BEFORE_SAVE, inside the save while the server's saving flag is up), and the
    // count the client's last tick of the text saw.
    private static final AtomicInteger BEGUN = new AtomicInteger();
    private static volatile int seen;
    private static final AtomicInteger DRAWN = new AtomicInteger();

    private SavingText() { }

    /** From the test thread, before the world opens. */
    public static void start() {
        BEGUN.set(0);
        seen = 0;
        DRAWN.set(0);
        on = true;
    }

    public static void stop() {
        on = false;
    }

    /** Server thread: a save began. */
    public static void began() {
        if (on) BEGUN.incrementAndGet();
    }

    /** Client thread, in the HUD's tick of the text: whether it counts the server as saving. */
    public static boolean saving(boolean saving) {
        if (!on) return saving;
        int begun = BEGUN.get();
        boolean missed = begun != seen;
        seen = begun;
        return saving || missed;
    }

    /** Client thread: a frame drew the text. */
    public static void drawn() {
        if (on) DRAWN.incrementAndGet();
    }

    public static int begun() {
        return BEGUN.get();
    }

    /** The frames that drew the text since {@link #start}. */
    public static int frames() {
        return DRAWN.get();
    }
}
