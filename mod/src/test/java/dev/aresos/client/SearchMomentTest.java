package dev.aresos.client;

import static dev.aresos.client.SearchMoment.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** Package 53d: when Super's shell_search opens the search over the world, and when it is ignored. */
class SearchMomentTest {
    @Test void opensOverTheWorldAndOverAnyOtherScreen() {
        assertEquals(OPEN, of(true, false, false, false));
        assertTrue(OPEN.opens());
    }

    @Test void anOpenContainerClosesFirst() {
        assertEquals(CLOSE_CONTAINER_THEN_OPEN, of(true, false, false, true));
        assertTrue(CLOSE_CONTAINER_THEN_OPEN.opens());
    }

    @Test void ignoredWithoutAReadyDesktopWorldWhateverIsOpen() {
        for (boolean open : new boolean[] {false, true})
            for (boolean typing : new boolean[] {false, true})
                for (boolean container : new boolean[] {false, true}) {
                    assertEquals(NO_WORLD, of(false, open, typing, container));
                }
        assertFalse(NO_WORLD.opens());
    }

    @Test void ignoredWhileHeTypes() {
        assertEquals(TYPING, of(true, false, true, false));
        // An anvil is a container he types in: his typing wins, nothing closes.
        assertEquals(TYPING, of(true, false, true, true));
        assertFalse(TYPING.opens());
    }

    @Test void ignoredWhileTheSearchIsOpenAlready() {
        // The search's own box has the focus: it counts as open, not as typing elsewhere.
        assertEquals(ALREADY_OPEN, of(true, true, true, false));
        assertFalse(ALREADY_OPEN.opens());
    }
}
