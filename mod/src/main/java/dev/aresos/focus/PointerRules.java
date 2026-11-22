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
        if (!free) return Click.VANILLA;
        return primary && appSlot ? Click.OPEN_APP : Click.ENTER_WORLD;
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
