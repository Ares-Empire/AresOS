package dev.aresos.focus;

import org.junit.jupiter.api.Test;

import static dev.aresos.focus.ClickLook.LOOK_RELEASE_MS;
import static dev.aresos.focus.ClickLook.START_GRACE_MS;
import static org.junit.jupiter.api.Assertions.*;

class ClickLookTest {
    @Test void lookModeIsTheCaptureAndEndsAfterStillness() {
        var look = new ClickLook();
        look.frame(false, 0);
        assertFalse(look.looking());
        assertFalse(look.due(10_000), "no look mode, nothing to end");
        look.frame(true, 1_000);
        assertTrue(look.looking());
        assertFalse(look.due(1_000 + LOOK_RELEASE_MS - 1));
        assertTrue(look.due(1_000 + LOOK_RELEASE_MS));
        // Later frames of the same capture do not restart the count.
        look.frame(true, 1_500);
        assertTrue(look.due(1_000 + LOOK_RELEASE_MS));
    }

    @Test void anyMotionStartsTheStillnessAgain() {
        var look = new ClickLook();
        look.frame(true, 0);
        look.moved(700);
        assertFalse(look.due(LOOK_RELEASE_MS), "the mouse moved 100 ms before");
        assertFalse(look.due(700 + LOOK_RELEASE_MS - 1));
        assertTrue(look.due(700 + LOOK_RELEASE_MS));
    }

    @Test void motionOutsideLookModeCountsForNothing() {
        var look = new ClickLook();
        look.moved(5_000);
        look.frame(true, 6_000);
        assertTrue(look.due(6_000 + LOOK_RELEASE_MS));
    }

    @Test void anyReleaseEndsLookModeAndTheNextCaptureCountsFresh() {
        var look = new ClickLook();
        look.frame(true, 0);
        look.frame(false, 300);  // Esc, an app taking the focus, or the stillness release itself
        assertFalse(look.looking());
        assertFalse(look.due(5_000));
        look.frame(true, 5_000);
        assertFalse(look.due(5_000 + LOOK_RELEASE_MS - 1));
        assertTrue(look.due(5_000 + LOOK_RELEASE_MS));
        look.reset();
        assertFalse(look.looking() || look.due(99_000));
    }

    @Test void aClickBeforeTheFocusWaitsOnlyForTheGrace() {
        var look = new ClickLook();
        assertFalse(look.clickWaiting(0));
        look.clickWaits(100);
        assertTrue(look.clickWaiting(100 + START_GRACE_MS));
        assertFalse(look.clickWaiting(101 + START_GRACE_MS));
        assertFalse(look.clickWaiting(100), "an expired click never comes back");
        look.clickWaits(200);
        look.clickDone();
        assertFalse(look.clickWaiting(200));
        look.clickWaits(300);
        look.reset();
        assertFalse(look.clickWaiting(300));
    }

    @Test void thePointerIsFreeOnlyOutsideLookModeInTheClickSetting() {
        for (int bits = 0; bits < 8; bits++) {
            boolean click = (bits & 1) != 0, starting = (bits & 2) != 0, captured = (bits & 4) != 0;
            assertEquals(click && !starting && !captured, ClickLook.idle(click, starting, captured), "bits " + bits);
        }
    }

    @Test void onlyAFirstMovementKeyPressInTheFreeWorldStartsLookMode() {
        for (int bits = 0; bits < 32; bits++) {
            boolean idle = (bits & 1) != 0, app = (bits & 2) != 0, screen = (bits & 4) != 0, press = (bits & 8) != 0,
                    movement = (bits & 16) != 0;
            assertEquals(bits == 25, ClickLook.keyStarts(idle, app, screen, press, movement), "bits " + bits);
        }
    }

    @Test void package56StillDecidesAPressOnTheFreeWorld() {
        // Outside look mode the click setting makes the pointer free, so the hotbar rules of package 56 apply.
        boolean free = PointerRules.free(true, true, true, ClickLook.idle(true, false, false));
        assertEquals(PointerRules.Click.OPEN_APP, PointerRules.click(free, true, true));
        assertEquals(PointerRules.Click.ENTER_WORLD, PointerRules.click(free, true, false), "an empty slot or open world");
        assertEquals(PointerRules.Click.ENTER_WORLD, PointerRules.click(free, false, true), "a right click on an app");
        // In look mode it is not free: clicks are Minecraft's, as in classic.
        assertFalse(PointerRules.free(true, true, true, ClickLook.idle(true, false, true)));
        // Classic never frees the pointer in front of the world.
        assertFalse(PointerRules.free(true, true, true, ClickLook.idle(false, false, false)));
    }
}
