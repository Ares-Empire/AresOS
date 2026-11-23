package dev.aresos.client;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

import java.util.TreeSet;

/** Package 53d: which line of the search stands in which slot of the bar, and when the best hit is pinned. */
class SearchLinesTest {
    /** A heading, the best hit under it, and five more lines. */
    private static final int LINES = 7, BEST = 1;

    /** Every line some scrolling brings into view. */
    private static TreeSet<Integer> reachable(SearchLines view) {
        var seen = new TreeSet<Integer>();
        for (int scroll = 0; scroll <= view.maxScroll(); scroll++)
            for (int slot = 0; slot < view.shown(); slot++) seen.add(view.line(slot, scroll));
        return seen;
    }

    private static TreeSet<Integer> all(int lines) {
        var every = new TreeSet<Integer>();
        for (int line = 0; line < lines; line++) every.add(line);
        return every;
    }

    @Test void aTwoSlotBarPinsNothingAndScrollsToEveryHit() {
        // Review 2, finding 6: pinned, the heading and the best hit filled both slots and no other hit could be reached.
        var view = SearchLines.of(LINES, BEST, 2);
        assertEquals(0, view.pinned());
        assertEquals(2, view.shown());
        assertEquals(LINES - 2, view.maxScroll());
        assertEquals(all(LINES), reachable(view));
        // It scrolls as a plain list: the best hit leaves the view.
        assertEquals(0, view.line(0, 0));
        assertEquals(BEST, view.line(1, 0));
        assertEquals(2, view.line(0, 2));
    }

    @Test void belowFourSlotsNothingIsPinned() {
        for (int slots = 1; slots < SearchLines.PIN_FROM; slots++) {
            var view = SearchLines.of(LINES, BEST, slots);
            assertEquals(0, view.pinned(), slots + " slots");
            assertEquals(all(LINES), reachable(view), slots + " slots");
        }
        assertEquals(4, SearchLines.PIN_FROM);
    }

    @Test void fromFourSlotsTheBestHitStaysAtTheTopAndEveryHitIsReached() {
        for (int slots = SearchLines.PIN_FROM; slots <= 9; slots++) {
            var view = SearchLines.of(LINES, BEST, slots);
            assertEquals(BEST + 1, view.pinned(), slots + " slots");
            assertEquals(Math.max(0, LINES - slots), view.maxScroll());
            for (int scroll = 0; scroll <= view.maxScroll(); scroll++) {
                assertEquals(0, view.line(0, scroll), "the heading stays");
                assertEquals(BEST, view.line(1, scroll), "the best hit stays");
            }
            assertEquals(all(LINES), reachable(view), slots + " slots");
            // Scrolled to the end, the last slot shows the last line.
            assertEquals(LINES - 1, view.line(view.shown() - 1, view.maxScroll()));
        }
    }

    @Test void withoutABestHitNothingIsPinned() {
        // "No program matches": one line, no hit.
        var view = SearchLines.of(1, -1, 8);
        assertEquals(0, view.pinned());
        assertEquals(1, view.shown());
        assertEquals(0, view.maxScroll());
        assertEquals(0, SearchLines.of(0, -1, 8).shown());
    }
}
