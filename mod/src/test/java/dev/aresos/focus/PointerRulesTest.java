package dev.aresos.focus;

import org.junit.jupiter.api.Test;
import static dev.aresos.focus.PointerRules.Click.*;
import static org.junit.jupiter.api.Assertions.*;

class PointerRulesTest {
    @Test void onlyAnAppInASessionsConnectedDesktopGetsTheFreePointer() {
        for (int bits = 0; bits < 16; bits++) {
            boolean free = PointerRules.free((bits & 1) != 0, (bits & 2) != 0, (bits & 4) != 0, (bits & 8) != 0);
            assertEquals(bits == 15, free, "session/desktop/connection/app bits: " + bits);
            assertEquals(bits == 15 ? OPEN_APP : VANILLA, PointerRules.click(free, true, true));
            assertEquals(bits == 15 ? ENTER_WORLD : VANILLA, PointerRules.click(free, true, false));
        }
    }

    @Test void onlyPrimaryClicksOnAppsOpenThemAndEveryOtherPressEntersTheWorld() {
        assertEquals(OPEN_APP, PointerRules.click(true, true, true));
        assertEquals(ENTER_WORLD, PointerRules.click(true, true, false));
        assertEquals(ENTER_WORLD, PointerRules.click(true, false, true));
        assertEquals(ENTER_WORLD, PointerRules.click(true, false, false));
    }

    @Test void theHitBoxesFollowAllNineSlotsAtDifferentGuiScales() {
        for (int width : new int[]{320, 427, 640, 1280}) for (int height : new int[]{240, 360, 720}) {
            int left = width / 2 - 90;
            for (int slot = 0; slot < 9; slot++) {
                assertEquals(slot, PointerRules.slot(left + slot * 20, height - 21, width, height));
                assertEquals(slot, PointerRules.slot(left + slot * 20 + 19.99, height - 1.01, width, height));
            }
            assertEquals(-1, PointerRules.slot(left - .01, height - 10, width, height));
            assertEquals(-1, PointerRules.slot(left + 180, height - 10, width, height));
            assertEquals(-1, PointerRules.slot(left + 10, height - 21.01, width, height));
            assertEquals(-1, PointerRules.slot(left + 10, height - 1, width, height));
            assertEquals(-1, PointerRules.slot(width / 2, height / 2, width, height));
        }
    }
}
