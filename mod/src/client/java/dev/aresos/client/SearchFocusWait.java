package dev.aresos.client;

/**
 * Package 53d, review 1: Super's {@code shell_search} can come a moment before the game's window has the keyboard (the
 * helper sends it once the compositor reports the world active, which can reach the mod before the window's own focus
 * event). The bar never opens without the keyboard, or his typing would go to the window that still has it: the
 * request waits for the focus, at most ten client ticks (500 ms at the game's 20 a second), and is dropped after that.
 * Counted in ticks so the rule can be held exactly in tests.
 */
final class SearchFocusWait {
    static final int TICKS = 10;

    enum Step { NOTHING, OPEN, DROP }

    // Ticks left to wait; 0 while nothing waits.
    private int left;

    /** A request came without the focus: wait for it. A newer request starts the wait again. */
    void start() { left = TICKS; }

    void cancel() { left = 0; }

    boolean waiting() { return left > 0; }

    /** One client tick: {@code OPEN} once the window has the keyboard, {@code DROP} when the wait ran out. */
    Step tick(boolean focused) {
        if (left == 0) return Step.NOTHING;
        if (focused) {
            left = 0;
            return Step.OPEN;
        }
        return --left == 0 ? Step.DROP : Step.NOTHING;
    }
}
