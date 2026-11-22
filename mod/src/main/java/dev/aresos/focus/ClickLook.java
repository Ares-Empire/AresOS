package dev.aresos.focus;

/**
 * Package 328b, prototype A ("click to look"), the part that needs no game. In a session's connected desktop world the
 * cursor is free; look mode is the world holding the mouse, started by a click on the world or a movement key, and it
 * ends after the mouse and every movement key have been still for {@link #LOOK_RELEASE_MS}. The client
 * ({@code ClickToLook}) feeds it what the game says once a frame. Capture and release themselves stay package 328a's
 * ({@code WorldCapture}).
 */
public final class ClickLook {
    /** Look mode ends after the mouse and every movement key have been still this long (brief 328b: start at 800 ms). */
    public static final long LOOK_RELEASE_MS = 800;
    /**
     * A click on the world can reach the game a moment before GLFW has seen the focus, and Minecraft does not capture
     * without it (328a's diagnostics). The click still starts look mode if the focus follows within this time.
     */
    public static final long START_GRACE_MS = 250;

    private boolean looking;
    private long stillSince;
    private long clickWaitsUntil = -1;

    /** Once a frame: whether the world holds the mouse in look mode now. A new capture starts the stillness count. */
    public void frame(boolean captured, long now) {
        if (captured && !looking) stillSince = now;
        looking = captured;
    }

    /** The mouse moved, a button or the wheel was used, or a movement key is held. */
    public void moved(long now) {
        if (looking) stillSince = now;
    }

    public boolean looking() {
        return looking;
    }

    /** Look mode has been still long enough to end. */
    public boolean due(long now) {
        return looking && now - stillSince >= LOOK_RELEASE_MS;
    }

    /** A click on the world found the window without GLFW's focus: it may start look mode until the grace ends. */
    public void clickWaits(long now) {
        clickWaitsUntil = now + START_GRACE_MS;
    }

    /** Whether such a click still waits; once the grace is over it never starts look mode. */
    public boolean clickWaiting(long now) {
        if (clickWaitsUntil >= 0 && now > clickWaitsUntil) clickWaitsUntil = -1;
        return clickWaitsUntil >= 0;
    }

    public void clickDone() {
        clickWaitsUntil = -1;
    }

    public void reset() {
        looking = false;
        clickWaitsUntil = -1;
    }

    /**
     * Outside look mode in the click setting the pointer is free over the world too, as it is over an app (package 56),
     * so package 56's click rules decide a press: an app slot opens its app, anything else starts look mode. While a
     * start is under way it is not free, or the capture it asks for would be refused.
     */
    public static boolean idle(boolean click, boolean starting, boolean captured) {
        return click && !starting && !captured;
    }

    /**
     * A movement key starts look mode when it is first pressed (not a repeat) while the world is free and in front: an
     * active desktop world in the click setting, no app in front, no screen or overlay. The key still walks.
     */
    public static boolean keyStarts(boolean idleInDesktop, boolean appInFront, boolean screenOrOverlay, boolean press,
                                    boolean movementKey) {
        return idleInDesktop && !appInFront && !screenOrOverlay && press && movementKey;
    }
}
