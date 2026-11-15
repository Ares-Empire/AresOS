package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.shell.ShellClient;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;

import java.util.Locale;

/**
 * Package 40: the world is the home screen. Two things follow, each with its own condition.
 *
 * <p><b>The window</b> ({@link #session}): a game the AresOS session started is the desktop window. labwc keeps it
 * maximized without a frame and below every app (rc.xml), so the game never makes it fullscreen and never lets
 * GLFW minimize it. That holds from the title screen on, whatever world is open.
 *
 * <p><b>The focus</b> ({@link #active}): in a desktop world with the app helper connected, another window having the
 * focus never opens the pause menu. Where the focus is comes from the helper's {@code shell_focus}, because GLFW
 * cannot say: when a Wayland window takes the focus, the X server hands the game a pointer focus that GLFW reports as
 * the real one (measured in package 40), so {@code Window.isFocused()} stays true behind an app.
 */
public final class HomeScreen {
    private static final boolean SESSION = System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("linux")
            && ShellClient.configured(System.getenv());
    private static Boolean sessionForTests, activeForTests;
    // Client thread only: what the helper last said, and what GLFW said at the last frame.
    private static boolean appInFront;
    private static boolean wasFocused = true;

    private HomeScreen() { }

    /** The AresOS session started this game (its supervisor, or run-hub.sh): its window is the desktop. */
    public static boolean session() {
        return sessionForTests != null ? sessionForTests : SESSION;
    }

    /** A desktop world with the app helper connected. Outside it the game treats focus as Minecraft always does. */
    public static boolean active(Minecraft client) {
        if (!AresOsClient.acceptsAppCommands(client)) return false;
        if (activeForTests != null) return activeForTests;
        var shell = AresOs.shell();
        return session() && shell != null && shell.status().state() == ShellClient.State.CONNECTED;
    }

    /** The helper said an app took the foreground (true) or the world got the focus back (false). */
    static void appInFront(boolean inFront) {
        appInFront = inFront;
    }

    /**
     * Once a frame, before Minecraft looks at the focus. If GLFW does notice the focus leaving (the pointer was
     * outside the window), keys and the mouse are let go as they are for the helper's message; when it comes back
     * the mouse is captured again, unless the helper says an app is still in front.
     */
    public static void frame(Minecraft client) {
        boolean focused = client.getWindow().isFocused();
        if (!active(client)) {
            wasFocused = true;
            appInFront = false;
            return;
        }
        if (wasFocused && !focused) {
            KeyMapping.releaseAll();
            AppInput.reset();
            client.mouseHandler.releaseMouse();
        } else if (!wasFocused && focused && !appInFront && client.gui.screen() == null) {
            client.mouseHandler.grabMouse();
        }
        wasFocused = focused;
    }

    /** Client game tests have no session and no helper: they say what {@link #session} and {@link #active} answer. */
    public static void forTests(Boolean session, Boolean active) {
        sessionForTests = session;
        activeForTests = active;
        wasFocused = true;
        appInFront = false;
    }
}
