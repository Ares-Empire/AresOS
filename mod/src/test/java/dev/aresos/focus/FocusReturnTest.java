package dev.aresos.focus;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class FocusReturnTest {
    @Test
    void onlyClosesTheCapturedFocusLossScreen() {
        var tracker = new FocusReturn();
        var pause = new Object();
        tracker.arm(1);
        assertTrue(tracker.beforeFocusPause(2, null));
        tracker.recordPause(pause);
        assertFalse(tracker.beforeFocusPause(3, pause));
        assertTrue(tracker.regainedFocus(pause));
        assertFalse(tracker.regainedFocus(pause));
    }

    @Test
    void preservesEscMenuAndReplacementScreen() {
        var tracker = new FocusReturn();
        var escPause = new Object();
        tracker.arm(1);
        assertFalse(tracker.beforeFocusPause(2, escPause));
        assertFalse(tracker.regainedFocus(escPause));
        tracker.arm(3);
        assertTrue(tracker.beforeFocusPause(4, null));
        tracker.recordPause(new Object());
        assertFalse(tracker.regainedFocus(escPause));
    }

    @Test
    void unrelatedFocusLossAndFailedOrExpiredLaunchDoNotCloseMenus() {
        var tracker = new FocusReturn();
        assertFalse(tracker.beforeFocusPause(1, null));
        tracker.arm(2);
        tracker.reset();
        assertFalse(tracker.beforeFocusPause(3, null));
        tracker.arm(4);
        assertFalse(tracker.beforeFocusPause(4 + FocusReturn.FOCUS_WINDOW_NANOS + 1, null));
    }

    @Test
    void focusLossIsAcceptedThroughThirtySecondsOnly() {
        var tracker = new FocusReturn();
        tracker.arm(1);
        assertTrue(tracker.beforeFocusPause(1 + FocusReturn.FOCUS_WINDOW_NANOS, null));
        tracker.arm(2);
        assertFalse(tracker.beforeFocusPause(3 + FocusReturn.FOCUS_WINDOW_NANOS, null));
    }

    @Test
    void failureCanOnlyCancelItsOwnLaunch() {
        var tracker = new FocusReturn();
        long earlier = tracker.arm(1);
        long newer = tracker.arm(2);
        assertNotEquals(earlier, newer);
        var pause = new Object();
        assertTrue(tracker.beforeFocusPause(3, null));
        tracker.recordPause(pause);
        tracker.cancel(earlier);
        assertTrue(tracker.regainedFocus(pause));
        long failed = tracker.arm(4);
        tracker.cancel(failed);
        assertFalse(tracker.beforeFocusPause(5, null));
    }

    @Test
    void returnBeforeMenuExistsDoesNotCloseAnything() {
        var tracker = new FocusReturn();
        tracker.arm(1);
        tracker.focusLost(2, null);
        assertFalse(tracker.regainedFocus(null));
        assertFalse(tracker.beforeFocusPause(3, null));
    }

    @Test
    void returnTokenWorksWithoutPauseAndOnlyOnce() {
        var tracker = new FocusReturn();
        long token = tracker.arm(1);
        tracker.focusLost(2, null);
        assertFalse(tracker.regainedFocus(null));
        assertEquals(token, tracker.takeReturnedToken());
        assertEquals(0, tracker.takeReturnedToken());
    }

    @Test
    void returnTokenSurvivesAScreenOpenedBeforeFocusLoss() {
        var tracker = new FocusReturn();
        long token = tracker.arm(3);
        var inventory = new Object();
        assertFalse(tracker.beforeFocusPause(4, inventory));
        assertFalse(tracker.regainedFocus(inventory));
        assertEquals(token, tracker.takeReturnedToken());
        assertEquals(0, tracker.takeReturnedToken());
    }

    @Test
    void expiredOrCancelledLaunchCannotReturnThroughAnOpenScreen() {
        var tracker = new FocusReturn();
        long token = tracker.arm(3);
        tracker.cancel(token);
        tracker.focusLost(4, new Object());
        tracker.regainedFocus(null);
        assertEquals(0, tracker.takeReturnedToken());
        tracker.arm(5);
        tracker.focusLost(6 + FocusReturn.FOCUS_WINDOW_NANOS, new Object());
        tracker.regainedFocus(null);
        assertEquals(0, tracker.takeReturnedToken());
    }
}
