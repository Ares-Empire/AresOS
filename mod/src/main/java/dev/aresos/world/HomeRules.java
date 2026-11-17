package dev.aresos.world;

/**
 * Package 48: the two decisions that make the home screen stop behaving like a game. Pure, so unit tests reach them;
 * the client asks them with what it knows.
 */
public final class HomeRules {
    private HomeRules() { }

    /**
     * Whether every way the game opens its menu (Esc, F3+Esc, focus loss, another mod) opens the AresOS menu instead:
     * in a game the AresOS session started ({@code session}) and in a desktop world. The app helper's connection is
     * not asked: a helper that dropped must not bring Save and Quit back. A normal world, the plain development
     * client and a game the session did not start keep Minecraft's own menu.
     */
    public static boolean menuReplacesGameMenu(boolean session, boolean desktopWorld) {
        return session && desktopWorld;
    }

    /** What a title screen does: make the flat home at once, or show as it always has. */
    public enum FirstStart { CREATE_FLAT, TITLE_SCREEN }

    /**
     * The first start: the first title screen of a game the session started makes the flat home when no AresHub
     * folder exists at all. Decided once per game start ({@code decidedBefore}: an earlier title screen of this game
     * start already decided), so a failed creation's error screen leads to the title screen with the AresOS button,
     * and an existing AresHub, damaged or not, is never touched. Never while the AresOS menu switches homes.
     */
    public static FirstStart firstStart(boolean session, boolean decidedBefore, boolean hubFolderExists,
                                        boolean switchingHomes) {
        return session && !decidedBefore && !hubFolderExists && !switchingHomes
                ? FirstStart.CREATE_FLAT : FirstStart.TITLE_SCREEN;
    }
}
