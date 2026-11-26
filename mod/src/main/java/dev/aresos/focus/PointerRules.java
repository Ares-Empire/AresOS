package dev.aresos.focus;

/** The desktop's free pointer uses GUI coordinates, just as the game's hotbar does. */
public final class PointerRules {
    private PointerRules() { }

    public enum Click { VANILLA, OPEN_APP, NEW_WINDOW, ENTER_WORLD }

    public static boolean free(boolean session, boolean desktop, boolean connected, boolean appInFront) {
        return session && desktop && connected && appInFront;
    }

    /** The nine 20-pixel slots inside the 182 by 22 hotbar; its outside border is still the world. */
    public static int slot(double x, double y, int width, int height) {
        double left = width / 2 - 90;
        return x >= left && x < left + 180 && y >= height - 21 && y < height - 1
                ? (int) ((x - left) / 20) : -1;
    }

    public static Click click(boolean free, boolean primary, boolean appSlot) {
        return click(free, primary, false, appSlot, false, false);
    }

    public static Click click(boolean free, boolean primary, boolean appSlot, boolean worldActs) {
        return click(free, primary, false, appSlot, false, worldActs);
    }

    /** Package 333: a secondary click on an app slot opens a new window when the helper offers {@code activate_app}. */
    public static Click click(boolean free, boolean primary, boolean secondary, boolean appSlot, boolean canActivate) {
        return click(free, primary, secondary, appSlot, canActivate, false);
    }

    /**
     * App slot shortcuts take priority when the pointer is free. A primary click opens or brings back the app, and a
     * secondary click opens a new window when the helper offers {@code activate_app}. With {@code worldActs} (edge
     * turning and the world in front), other clicks act on what the crosshair aims at.
     */
    public static Click click(boolean free, boolean primary, boolean secondary, boolean appSlot, boolean canActivate,
                              boolean worldActs) {
        if (!free) return Click.VANILLA;
        if (appSlot && primary) return Click.OPEN_APP;
        if (appSlot && secondary && canActivate) return Click.NEW_WINDOW;
        return worldActs ? Click.VANILLA : Click.ENTER_WORLD;
    }

    /**
     * Package 328a, the safe fallback: in a session's connected desktop world the world takes the mouse only while the
     * compositor has given it the focus and the pointer is over its window. Otherwise labwc either never grants the pointer
     * lock (another window has the keyboard) or Xwayland only confines the pointer (it rests on another window), and the
     * hidden pointer then reaches the windows above the world. Outside such a world capture stays Minecraft's own.
     */
    public static boolean mayCapture(boolean desktop, boolean worldFocused, boolean pointerOverWorld) {
        return !desktop || worldFocused && pointerOverWorld;
    }
}
