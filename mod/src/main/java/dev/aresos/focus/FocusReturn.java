package dev.aresos.focus;

/** Tracks a launch's return token separately from its permission to close a focus-loss pause screen. */
public final class FocusReturn {
    public static final long FOCUS_WINDOW_NANOS = 30_000_000_000L;
    private long nextToken;
    private long activeToken;
    private long armedUntil;
    private boolean lostFocus;
    private boolean mayCapturePause;
    private boolean attemptedPause;
    private Object ownedPause;
    private long returnedToken;

    public long arm(long now) {
        reset();
        activeToken = ++nextToken;
        armedUntil = now + FOCUS_WINDOW_NANOS;
        return activeToken;
    }

    public void cancel(long token) {
        if (token == activeToken) reset();
    }

    public boolean beforeFocusPause(long now, Object currentScreen) {
        focusLost(now, currentScreen);
        if (mayCapturePause && !attemptedPause && currentScreen == null) {
            attemptedPause = true;
            return true;
        }
        return false;
    }

    public void focusLost(long now, Object currentScreen) {
        if (!lostFocus && armedUntil != 0 && now <= armedUntil) {
            lostFocus = true;
            mayCapturePause = currentScreen == null;
        }
    }

    public void recordPause(Object screen) {
        ownedPause = screen;
    }

    public boolean regainedFocus(Object currentScreen) {
        if (!lostFocus) return false;
        boolean close = ownedPause != null && ownedPause == currentScreen;
        long returned = activeToken;
        reset();
        returnedToken = returned;
        return close;
    }

    /** A return can happen with pause-on-focus-loss disabled, so it is separate from closing a menu. */
    public long takeReturnedToken() {
        long token = returnedToken;
        returnedToken = 0;
        return token;
    }

    public void reset() {
        activeToken = 0;
        armedUntil = 0;
        lostFocus = false;
        mayCapturePause = false;
        attemptedPause = false;
        ownedPause = null;
        returnedToken = 0;
    }
}
