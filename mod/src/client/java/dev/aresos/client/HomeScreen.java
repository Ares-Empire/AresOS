package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.shell.ShellClient;
import dev.aresos.world.HomeRules;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.sounds.SoundSource;

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
 *
 * <p><b>Covered</b> ({@link #covered}): while a maximized or fullscreen window hides the world on its screen, the helper
 * says so ({@code shell_covered}) and the world pauses without a screen and draws at most {@link #COVERED_FRAME_LIMIT}
 * frames a second. A smaller window leaves it moving (owner, 2026-11-15). Heartbeats and {@code world_ready} do not
 * change: they come from the shell client's own threads and from {@link ShellFocusClient#readyWorld}, which a pause
 * without a screen leaves as it is. While covered the home screen is silent, music included, and every sound goes on
 * where it was when the cover ends (orchestrator, 2026-11-15); with a smaller window in front the sound goes on.
 *
 * <p><b>The home</b> ({@link #home}): a desktop world in a game the session started, whether or not the helper is
 * connected right now. It shows no game notices: no "Saving world" text in the corner, for any save (package 46, the
 * owner on 2026-11-16: "Hide it").
 */
public final class HomeScreen {
    private static final boolean SESSION = System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("linux")
            && ShellClient.configured(System.getenv());
    /** Minecraft's own limit for a minimized window. It is also the longest wait before the world shows again. */
    public static final int COVERED_FRAME_LIMIT = 10;
    private static Boolean sessionForTests, activeForTests;
    // Client thread only: what the helper last said, and what GLFW said at the last frame.
    private static boolean appInFront;
    private static boolean wasFocused = true;
    private static boolean covered;
    // Client thread only: the sounds were paused for the cover at the last frame, so its end must start them again.
    private static boolean silenced;

    private HomeScreen() { }

    /** The AresOS session started this game (its supervisor, or run-hub.sh): its window is the desktop. */
    public static boolean session() {
        return sessionForTests != null ? sessionForTests : SESSION;
    }

    /**
     * A desktop world in a game the session started. Unlike {@link #active} it does not need the helper: a helper that
     * dropped must not bring the game's notices or Save and Quit back. The menu shares this gate.
     */
    public static boolean home(Minecraft client) {
        return HomeRules.home(session(), AresOsClient.acceptsAppCommands(client));
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

    static boolean appInFront() {
        return appInFront;
    }

    /**
     * Package 56: the pointer is free while an app is in front, and the world refuses every grab; with {@code look = click}
     * also outside look mode, and with {@code look = edge} always (package 328).
     */
    public static boolean freePointer(Minecraft client) {
        return dev.aresos.focus.PointerRules.free(session(), AresOsClient.acceptsAppCommands(client),
                active(client), appInFront || ClickToLook.idle(client) || EdgeLook.setting());
    }

    /**
     * Package 56: the world ignores the free pointer's clicks (no attack, no use): while an app is in front, and with
     * {@code look = click} outside look mode. With {@code look = edge} and the world in front they act (package 328c).
     */
    public static boolean ignoresMouse(Minecraft client) {
        return dev.aresos.focus.PointerRules.free(session(), AresOsClient.acceptsAppCommands(client),
                active(client), appInFront || ClickToLook.idle(client));
    }

    /** The helper said a window hides the world on its screen, or no longer does (false also when it went away). */
    static void covered(boolean now) {
        covered = now;
    }

    /** Covered in an active home screen: the world pauses and draws slowly. Outside it the helper's word changes nothing. */
    public static boolean covered(Minecraft client) {
        return covered && active(client);
    }

    /**
     * What {@code Minecraft.runTick} uses to decide the pause, given what the open screen says; once a frame. It also
     * keeps a covered home screen silent. Minecraft's own pause stops every sound but the music and the interface's,
     * and starts them again only when a screen closes. So while covered every sound is paused, at every frame: a screen
     * closing starts them all again, and a sound that begins meanwhile (a toast) is caught at the next frame. The music
     * starts no new song meanwhile ({@code MusicCoveredMixin}). When the cover ends each sound goes on where it was,
     * and under a pausing screen Minecraft's own pause stays as it was: its music and its buttons' sounds play.
     */
    public static boolean pausing(Minecraft client, boolean screenPauses) {
        boolean cover = covered(client);
        var sounds = client.getSoundManager();
        if (cover) {
            sounds.pauseAllExcept();
        } else if (silenced) {
            sounds.resume();
            if (screenPauses) sounds.pauseAllExcept(SoundSource.MUSIC, SoundSource.UI);
        }
        silenced = cover;
        return screenPauses || cover;
    }

    /** The frame rate cap {@code FramerateLimitTracker} answers, given its own. */
    public static int framerateLimit(Minecraft client, int limit) {
        return covered(client) ? Math.min(limit, COVERED_FRAME_LIMIT) : limit;
    }

    /**
     * Once a frame, before Minecraft looks at the focus. If GLFW does notice the focus leaving (the pointer was
     * outside the window), keys and the mouse are let go as they are for the helper's message; when it comes back
     * the mouse is captured again, unless the helper says an app is still in front.
     */
    public static void frame(Minecraft client) {
        boolean focused = client.getWindow().isFocused();
        HomePointer.frame(client);
        ClickToLook.frame(client);
        EdgeLook.frame(client);
        if (!active(client)) {
            wasFocused = true;
            // A helper event can precede the player/world while joining or switching homes. Keep its focus until
            // the helper changes it; clearing it here used to capture the mouse behind the still-focused app.
            var shell = dev.aresos.AresOs.shell();
            var state = shell == null ? ShellClient.State.CLOSED : shell.status().state();
            if (!session() || (state != ShellClient.State.CONNECTED && state != ShellClient.State.STARTING)) appInFront = false;
            return;
        }
        // With look = edge the world never holds the mouse: a capture from before the world was active is let go too.
        if ((appInFront || EdgeLook.on(client)) && client.mouseHandler.isMouseGrabbed()) client.mouseHandler.releaseMouse();
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
        covered = false;
        HomePointer.reset();
        // Tests that stand for a session run in classic unless they ask for another look (package 328).
        LookSetting.forTests(session == null && active == null ? null : dev.aresos.config.LookMode.CLASSIC);
        // Callback-driven tests have no real pointer over the window: they stand for one that is (package 328a).
        WorldCapture.forTests(session == null && active == null ? null : Boolean.TRUE, false);
    }
}
