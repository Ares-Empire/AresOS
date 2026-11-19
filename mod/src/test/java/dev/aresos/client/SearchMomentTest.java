package dev.aresos.client;

import static dev.aresos.client.SearchMoment.*;
import static org.junit.jupiter.api.Assertions.*;

import dev.aresos.client.SearchMoment.Open;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;

/** Package 53d: when Super's shell_search opens the search over the world, and when it is ignored. */
class SearchMomentTest {
    @Test void opensOverTheWorldTheMenuAndTheEmptyAppsScreen() {
        for (Open open : new Open[] {Open.NOTHING, Open.MENU, Open.APPS}) assertEquals(OPEN, of(true, open, true), open.name());
        assertTrue(OPEN.opens());
    }

    @Test void anOpenContainerClosesFirst() {
        assertEquals(CLOSE_CONTAINER_THEN_OPEN, of(true, Open.CONTAINER, true));
        assertTrue(CLOSE_CONTAINER_THEN_OPEN.opens());
    }

    @Test void onlyTheListedKindsAreReplaced() {
        // Review 2: an allowlist. Whatever is not one of these four stays, with or without the window's focus.
        var replaced = EnumSet.of(Open.NOTHING, Open.CONTAINER, Open.MENU, Open.APPS);
        for (Open open : Open.values())
            for (boolean focused : new boolean[] {true, false}) {
                var moment = of(true, open, focused);
                assertEquals(focused && replaced.contains(open), moment.opens(), open + " focused " + focused);
                if (!replaced.contains(open)) assertNotEquals(NO_FOCUS, moment, open + " must not wait to be replaced");
            }
        assertEquals(OTHER_SCREEN, of(true, Open.OTHER, true));
        assertFalse(OTHER_SCREEN.opens());
    }

    @Test void ignoredWithoutAReadyDesktopWorldWhateverIsOpen() {
        for (Open open : Open.values())
            for (boolean focused : new boolean[] {true, false}) assertEquals(NO_WORLD, of(false, open, focused));
        assertFalse(NO_WORLD.opens());
    }

    @Test void ignoredWhileTheSearchIsOpenAlready() {
        assertEquals(ALREADY_OPEN, of(true, Open.SEARCH, true));
        assertFalse(ALREADY_OPEN.opens());
    }

    @Test void withoutTheWindowsFocusItWaitsInsteadOfOpening() {
        for (Open open : new Open[] {Open.NOTHING, Open.CONTAINER, Open.MENU, Open.APPS})
            assertEquals(NO_FOCUS, of(true, open, false), open.name());
        assertFalse(NO_FOCUS.opens());
        // The other reasons not to open come first: nothing waits for them.
        assertEquals(NO_WORLD, of(false, Open.NOTHING, false));
        assertEquals(ALREADY_OPEN, of(true, Open.SEARCH, false));
        assertEquals(OTHER_SCREEN, of(true, Open.OTHER, false));
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
