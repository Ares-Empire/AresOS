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
    /** A screen he types in is open (chat, a sign, a book, an anvil, a command block): his typing is never lost. Ignored. */
    TYPING,
    /** A container is open: it closes the normal way first (the server hears of it, a carried item goes back). */
    CLOSE_CONTAINER_THEN_OPEN,
    /** Opens the search; any other screen is left for it, and Escape then goes to the world. */
    OPEN;

    public static SearchMoment of(boolean worldReady, boolean searchOpen, boolean typing, boolean container) {
        if (!worldReady) return NO_WORLD;
        if (searchOpen) return ALREADY_OPEN;
        if (typing) return TYPING;
        return container ? CLOSE_CONTAINER_THEN_OPEN : OPEN;
    }

    public boolean opens() { return this == OPEN || this == CLOSE_CONTAINER_THEN_OPEN; }
}
