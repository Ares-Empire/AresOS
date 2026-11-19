package dev.aresos.client;

/**
 * Package 53d: what Super's {@code shell_search} does at this moment (briefs/53d-world-search.md, step 2). The rule
 * alone, so a unit test can hold it; {@link WorldSearchScreen#requested} reads the moment from the game.
 */
public enum SearchMoment {
    /** No desktop world to search over: a home switch, loading, or not his AresOS world. Ignored. */
    NO_WORLD,
    /** The search is open already: what he typed stays. Ignored. */
    ALREADY_OPEN,
    /**
     * A screen he types in is open (chat, a sign, a book or its signing, an anvil, a command, structure or test block, or
     * any screen whose focus is in a text box): his draft is never lost. Ignored.
     */
    TYPING,
    /**
     * The game's window does not have the keyboard yet: the search waits for it ({@link SearchFocusWait}), so what he
     * types never goes to the window that still has it (review 1).
     */
    NO_FOCUS,
    /** A container is open: it closes the normal way first (the server hears of it, a carried item goes back). */
    CLOSE_CONTAINER_THEN_OPEN,
    /** Opens the search; any other screen is left for it, and Escape then goes to the world. */
    OPEN;

    public static SearchMoment of(boolean worldReady, boolean searchOpen, boolean typing, boolean container, boolean focused) {
        if (!worldReady) return NO_WORLD;
        if (searchOpen) return ALREADY_OPEN;
        if (typing) return TYPING;
        if (!focused) return NO_FOCUS;
        return container ? CLOSE_CONTAINER_THEN_OPEN : OPEN;
    }

    public boolean opens() { return this == OPEN || this == CLOSE_CONTAINER_THEN_OPEN; }
}
