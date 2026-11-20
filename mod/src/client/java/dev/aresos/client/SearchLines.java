package dev.aresos.client;

/**
 * Package 53d: which of the search's lines stand in which of the bar's slots. The arithmetic alone, so a unit test can
 * hold it ({@link WorldSearchScreen} draws and clicks by it).
 *
 * <p>The best hit and the heading over it stay at the top while the rest scrolls under them, so the program Enter opens
 * is always in view (review 1). Only where the bar has at least {@link #PIN_FROM} slots: in a smaller one the pinned
 * lines would fill it and no other hit could be reached (review 2, finding 6), so there the whole list scrolls.
 *
 * @param lines  how many lines the list has
 * @param pinned how many of the first lines stay at the top
 * @param slots  how many lines the bar has room for
 */
record SearchLines(int lines, int pinned, int slots) {
    static final int PIN_FROM = 4;

    /** {@code bestLine}: the best hit's place in the list, or -1 when there is none. */
    static SearchLines of(int lines, int bestLine, int slots) {
        boolean pin = bestLine >= 0 && slots >= PIN_FROM && bestLine + 1 < slots;
        return new SearchLines(lines, pin ? bestLine + 1 : 0, slots);
    }

    /** How many lines are shown. */
    int shown() { return Math.min(lines, slots); }

    /** How far the lines under the pinned ones can be scrolled. */
    int maxScroll() { return Math.max(0, lines - slots); }

    /** The line in slot {@code slot} when {@code scroll} lines are scrolled past: the pinned ones first. */
    int line(int slot, int scroll) { return slot < pinned ? slot : slot + scroll; }
}
