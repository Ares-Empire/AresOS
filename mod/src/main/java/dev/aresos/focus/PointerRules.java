package dev.aresos.focus;

/** The desktop's free pointer uses GUI coordinates, just as the game's hotbar does. */
public final class PointerRules {
    private PointerRules() { }

    public enum Click { VANILLA, OPEN_APP, ENTER_WORLD }

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
        return click(free, primary, appSlot, false);
    }

    /**
     * {@code worldActs}: package 328c's edge turning with the world in front, where the free pointer's clicks act on what
     * the crosshair aims at. A primary click on an app slot still opens the app; any other click is Minecraft's.
     */
    public static Click click(boolean free, boolean primary, boolean appSlot, boolean worldActs) {
        if (!free) return Click.VANILLA;
        if (primary && appSlot) return Click.OPEN_APP;
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
