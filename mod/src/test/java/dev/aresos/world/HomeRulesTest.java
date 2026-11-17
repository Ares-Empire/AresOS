package dev.aresos.world;

import org.junit.jupiter.api.Test;

import static dev.aresos.world.HomeRules.FirstStart.CREATE_FLAT;
import static dev.aresos.world.HomeRules.FirstStart.TITLE_SCREEN;
import static org.junit.jupiter.api.Assertions.*;

class HomeRulesTest {
    @Test
    void theAresOsMenuOnlyInASessionsDesktopWorld() {
        assertTrue(HomeRules.menuReplacesGameMenu(true, true));
        assertFalse(HomeRules.menuReplacesGameMenu(true, false), "a normal world keeps the game menu");
        assertFalse(HomeRules.menuReplacesGameMenu(false, true), "the development client keeps the game menu");
        assertFalse(HomeRules.menuReplacesGameMenu(false, false));
    }

    @Test
    void theFirstStartMakesTheFlatHomeOnlyWhenNothingIsThere() {
        assertEquals(CREATE_FLAT, HomeRules.firstStart(true, false, false, false));
        assertEquals(TITLE_SCREEN, HomeRules.firstStart(false, false, false, false), "outside a session");
        assertEquals(TITLE_SCREEN, HomeRules.firstStart(true, false, true, false), "an AresHub is never touched");
        assertEquals(TITLE_SCREEN, HomeRules.firstStart(true, true, false, false), "once per game start");
        assertEquals(TITLE_SCREEN, HomeRules.firstStart(true, false, false, true), "never during a home switch");
    }
}
