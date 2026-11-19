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
     * A screen that is not on the list of those Super may replace ({@link Open#OTHER}): it stays as it is, with
     * whatever he typed or chose in it. Ignored.
     */
    OTHER_SCREEN,
    /**
     * The game's window does not have the keyboard yet: the search waits for it ({@link SearchFocusWait}), so what he
     * types never goes to the window that still has it (review 1).
     */
    NO_FOCUS,
    /** A container is open: it closes the normal way first (the server hears of it, a carried item goes back). */
    CLOSE_CONTAINER_THEN_OPEN,
    /** Opens the search; Escape then goes to the world. */
    OPEN;

    /**
     * What is open when Super comes. Review 2: an allowlist. The search replaces only what is known to hold nothing
     * typed, {@link #NOTHING}, {@link #CONTAINER}, {@link #MENU} and {@link #APPS}; everything else is {@link #OTHER}
     * and stays. {@link WorldSearchScreen#opened} says which one a screen is.
     */
    public enum Open {
        /** No screen: he is in the world. */
        NOTHING,
        /** The inventory or another container, with no text in any text box of it. */
        CONTAINER,
        /** The game menu, the game's own or AresOS's. */
        MENU,
        /** The Apps screen while its search box is empty. */
        APPS,
        /** The search over the world itself. */
        SEARCH,
        /** Any other screen, the game's, another mod's or AresOS's own, and a listed one while it holds text. */
        OTHER
    }

    public static SearchMoment of(boolean worldReady, Open open, boolean focused) {
        if (!worldReady) return NO_WORLD;
        // Every kind is named: a new one cannot be replaced by default.
        return switch (open) {
            case SEARCH -> ALREADY_OPEN;
            case OTHER -> OTHER_SCREEN;
            case CONTAINER -> focused ? CLOSE_CONTAINER_THEN_OPEN : NO_FOCUS;
            case NOTHING, MENU, APPS -> focused ? OPEN : NO_FOCUS;
        };
    }

    public boolean opens() { return this == OPEN || this == CLOSE_CONTAINER_THEN_OPEN; }
}
