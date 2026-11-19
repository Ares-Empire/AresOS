package dev.aresos.client;

import static dev.aresos.client.SearchMoment.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** Package 53d: when Super's shell_search opens the search over the world, and when it is ignored. */
class SearchMomentTest {
    @Test void opensOverTheWorldAndOverAnyOtherScreen() {
        assertEquals(OPEN, of(true, false, false, false, true));
        assertTrue(OPEN.opens());
    }

    @Test void anOpenContainerClosesFirst() {
        assertEquals(CLOSE_CONTAINER_THEN_OPEN, of(true, false, false, true, true));
        assertTrue(CLOSE_CONTAINER_THEN_OPEN.opens());
    }

    @Test void ignoredWithoutAReadyDesktopWorldWhateverIsOpen() {
        for (boolean open : new boolean[] {false, true})
            for (boolean typing : new boolean[] {false, true})
                for (boolean container : new boolean[] {false, true}) {
                    assertEquals(NO_WORLD, of(false, open, typing, container, true));
                }
        assertFalse(NO_WORLD.opens());
    }

    @Test void ignoredWhileHeTypes() {
        assertEquals(TYPING, of(true, false, true, false, true));
        // An anvil is a container he types in: his typing wins, nothing closes.
        assertEquals(TYPING, of(true, false, true, true, true));
        assertFalse(TYPING.opens());
    }

    @Test void ignoredWhileTheSearchIsOpenAlready() {
        // The search's own box has the focus: it counts as open, not as typing elsewhere.
        assertEquals(ALREADY_OPEN, of(true, true, true, false, true));
        assertFalse(ALREADY_OPEN.opens());
    }

    @Test void withoutTheWindowsFocusItWaitsInsteadOfOpening() {
        assertEquals(NO_FOCUS, of(true, false, false, false, false));
        assertEquals(NO_FOCUS, of(true, false, false, true, false));
        assertFalse(NO_FOCUS.opens());
        // The other reasons not to open come first: nothing waits for them.
        assertEquals(NO_WORLD, of(false, false, false, false, false));
        assertEquals(ALREADY_OPEN, of(true, true, false, false, false));
        assertEquals(TYPING, of(true, false, true, false, false));
    }

    @Test void theWaitOpensOnceTheWindowHasTheKeyboard() {
        var wait = new SearchFocusWait();
        assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(true), "nothing waits");
        wait.start();
        for (int tick = 1; tick < SearchFocusWait.TICKS; tick++) assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(false));
        assertEquals(SearchFocusWait.Step.OPEN, wait.tick(true));
        assertFalse(wait.waiting());
        assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(true), "once");
    }

    @Test void theWaitIsDroppedAfterHalfASecond() {
        assertEquals(10, SearchFocusWait.TICKS, "500 ms at 20 ticks a second");
        var wait = new SearchFocusWait();
        wait.start();
        for (int tick = 1; tick < SearchFocusWait.TICKS; tick++) assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(false));
        assertEquals(SearchFocusWait.Step.DROP, wait.tick(false));
        assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(true), "focus after the wait opens nothing");
        // A newer request starts the wait again; cancelling ends it.
        wait.start();
        wait.cancel();
        assertEquals(SearchFocusWait.Step.NOTHING, wait.tick(true));
    }
}
