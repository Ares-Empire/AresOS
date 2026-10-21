package dev.aresos.focus;

/** Tracks ownership of one focus-loss pause screen by object identity. */
public final class FocusReturn {
    public static final long FOCUS_WINDOW_NANOS = 30_000_000_000L;
    private long nextToken;
    private long activeToken;
    private long armedUntil;
    private boolean lostFocus;
    private boolean eligible;
    private boolean attemptedPause;
    private Object ownedPause;

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
        if (eligible && !attemptedPause && currentScreen == null) {
            attemptedPause = true;
            return true;
        }
        return false;
    }

    public void focusLost(long now, Object currentScreen) {
        if (!lostFocus && armedUntil != 0 && now <= armedUntil) {
            lostFocus = true;
            eligible = currentScreen == null;
        }
    }

    public void recordPause(Object screen) {
        ownedPause = screen;
    }

    public boolean regainedFocus(Object currentScreen) {
        if (!lostFocus) return false;
        boolean close = ownedPause != null && ownedPause == currentScreen;
        reset();
        return close;
    }

    public void reset() {
        activeToken = 0;
        armedUntil = 0;
        lostFocus = false;
        eligible = false;
        attemptedPause = false;
        ownedPause = null;
    }
}
