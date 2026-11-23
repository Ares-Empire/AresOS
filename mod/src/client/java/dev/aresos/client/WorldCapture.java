package dev.aresos.client;

import com.mojang.blaze3d.platform.Window;
import dev.aresos.AresOs;
import dev.aresos.focus.PointerRules;
import net.minecraft.client.Minecraft;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWNativeX11;
import org.lwjgl.system.APIUtil;
import org.lwjgl.system.JNI;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.system.SharedLibrary;

/**
 * Package 328a: how the world takes the mouse in the AresOS session, where the game is an X11 window under Xwayland in
 * labwc. The traces behind this are in reviews/328-look-around/PROGRESS.md.
 *
 * <p><b>The leak.</b> Minecraft's capture warps the X pointer to the window's centre while the cursor is still visible,
 * and GLFW 3.5 warps it there again before it hides the cursor. Xwayland answers each such warp with a pointer lock
 * whose position hint is that centre, and drops the lock at once because the cursor is visible. labwc moves its real
 * cursor to the hint of every active lock that is dropped. The lock that stays then holds the hidden cursor at the world
 * window's centre: relative motion still turns the camera, but a click or a scroll goes to whatever window stands there,
 * the app in front of the world. GLFW's own hidden cursor does not help: Xwayland takes its transparent image for a
 * visible cursor.
 *
 * <p><b>The fix.</b> In the session the cursor is hidden through XFixes before Minecraft's capture starts, so every warp
 * is made with a cursor X does not draw at all. Xwayland then keeps its first lock, labwc never moves the cursor, and it
 * stays where the world was clicked. Letting go puts the X pointer back there before the cursor shows again, so the
 * pointer reappears where the capture began. And in a desktop world the world takes the mouse
 * only where the lock works: the compositor has given it the focus and the pointer is over its window
 * ({@link PointerRules#mayCapture}, the brief's safe fallback).
 *
 * <p><b>Letting go.</b> GLFW 3.5 on X11 undoes a capture in two places. {@code glfwSetInputMode} does it only if the X
 * server says, at that instant, that the window has the focus; otherwise it records the normal mode but keeps its grab,
 * its raw motion and its disabled-cursor window, and then warps the pointer to the window's centre after every poll. Its
 * handling of a FocusOut does it always. No question to the server can make the first way safe: the focus can move
 * between the question and GLFW's own. So every release takes the second way, whatever asked for it and wherever the
 * focus is: at the next event poll the mod puts a FocusOut of its own at the head of Xlib's queue, GLFW lets go
 * completely, and inside that same event the mode turns normal. If Minecraft still records the window as focused, a
 * FocusIn restores GLFW's input context. Minecraft sees neither event (rig/GlfwProbe.java shows the steps with GLFW alone).
 */
public final class WorldCapture {
    /** {@code InputConstants.grabOrReleaseMouse}: a cursor position first, then GLFW's cursor mode. */
    @FunctionalInterface
    public interface CursorMode {
        void set(Window window, int mode, double x, double y);
    }

    // Client thread only. What the compositor last said about the world's focus: the helper's shell_focus, or a press
    // that reached the world (labwc focuses a window before it hands it the press).
    private static boolean worldFocused = true;
    // Client thread only: this game's XFixesHideCursor is in force (X counts hides per client; each needs its show).
    private static boolean hiddenInX;
    // Client thread only: where the pointer was when the capture began, in window coordinates.
    private static double startX, startY;
    // Client thread only: the window whose capture is being let go; the next event poll does it. Null: nothing to do.
    private static Window letGo;
    // Client thread only: the mod's own X focus event that GLFW reads next (0: none). The numbers are X's event types.
    private static final int FOCUS_IN = 9, FOCUS_OUT = 10;
    private static int own;
    private static Boolean pointerOverWorldForTests;
    private static boolean directForTests;

    private WorldCapture() { }

    /** The helper's focus changed, or a press on the world showed the compositor gave the world the focus. */
    static void worldFocused(boolean focused) {
        worldFocused = focused;
    }

    /** The helper went away: its next connection reports the focus again. What the mod hid is let go at once. */
    static void helperLost(Minecraft client) {
        worldFocused = true;
        if (!ownsCapture()) return;
        client.mouseHandler.releaseMouse();
        // Whatever Minecraft believed about the mouse, what the mod hid comes back at the next event poll.
        if (letGo == null) letGo = client.getWindow();
    }

    public static boolean ownsCapture() {
        return hiddenInX;
    }

    /** Whether the world may take the mouse now (Minecraft's own check for its window's focus follows). */
    public static boolean allowed(Minecraft client) {
        if (letGo != null) return false;
        boolean desktop = HomeScreen.active(client);
        return PointerRules.mayCapture(desktop, worldFocused, desktop && worldFocused && pointerOverWorld(client));
    }

    /** GLFW's hover test: the X pointer is in the window, which Xwayland reports only over its visible part. */
    public static boolean pointerOverWorld(Minecraft client) {
        if (pointerOverWorldForTests != null) return pointerOverWorldForTests;
        return GLFW.glfwGetWindowAttrib(client.getWindow().handle(), GLFW.GLFW_HOVERED) == GLFW.GLFW_TRUE;
    }

    /** Replaces Minecraft's capture call in {@code MouseHandler.grabMouse}. */
    public static void grab(Window window, double x, double y, CursorMode minecraft) {
        if (HomeScreen.active(Minecraft.getInstance()) && !hiddenInX
                && (pointerOverWorldForTests == null || directForTests) && Xlib.ready()) {
            double[] here = new double[1], there = new double[1];
            GLFW.glfwGetCursorPos(window.handle(), here, there);
            startX = here[0];
            startY = there[0];
            long display = GLFWNativeX11.glfwGetX11Display();
            JNI.invokePJV(display, GLFWNativeX11.glfwGetX11Window(window.handle()), Xlib.HIDE_CURSOR);
            JNI.invokePI(display, Xlib.FLUSH);
            hiddenInX = true;
        }
        (directForTests ? (CursorMode) WorldCapture::direct : minecraft).set(window, GLFW.GLFW_CURSOR_DISABLED, x, y);
    }

    /**
     * Package 328b: look mode started by a key gives the pointer back at the centre of the world's window, which labwc
     * keeps maximized on its output, instead of where it rested. Only the point changes; the release stays the same.
     */
    static void returnToCentre(Window window) {
        if (!hiddenInX) return;
        int[] width = new int[1], height = new int[1];
        GLFW.glfwGetWindowSize(window.handle(), width, height);
        startX = width[0] / 2.0;
        startY = height[0] / 2.0;
    }

    /** Replaces Minecraft's release call in {@code MouseHandler.releaseMouse}. */
    public static void release(Window window, double x, double y, CursorMode minecraft) {
        if (letGo != null) return;
        if (!ownsCapture() && !capturedInX(window)) {
            (directForTests ? (CursorMode) WorldCapture::direct : minecraft).set(window, GLFW.GLFW_CURSOR_NORMAL, x, y);
            return;
        }
        // Minecraft has already cleared mouseGrabbed. The next event poll lets go, the same way whatever asked for it.
        letGo = window;
    }

    /** A session's game on X11 with GLFW's cursor disabled, also when Minecraft did it before the helper was there. */
    private static boolean capturedInX(Window window) {
        return HomeScreen.session() && Xlib.ready()
                && GLFW.glfwGetInputMode(window.handle(), GLFW.GLFW_CURSOR) == GLFW.GLFW_CURSOR_DISABLED;
    }

    /** Head of {@code RenderSystem.pollEvents}, outside every GLFW callback: GLFW's next event is the mod's FocusOut. */
    public static void beforePollEvents() {
        if (letGo == null) return;
        long handle = letGo.handle();
        // GLFW's FocusOut handling lets go only in the disabled mode. It is that mode here unless something changed it
        // behind the mod; then this puts it back first, so that what follows ends the same from any state.
        if (GLFW.glfwGetInputMode(handle, GLFW.GLFW_CURSOR) != GLFW.GLFW_CURSOR_DISABLED)
            GLFW.glfwSetInputMode(handle, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_DISABLED);
        own = FOCUS_OUT;
        Xlib.putBack(handle, FOCUS_OUT);
    }

    /** Return of {@code RenderSystem.pollEvents}. GLFW has handed the event back by now; if it ever has not, say so. */
    public static void afterPollEvents() {
        if (own == 0) return;
        AresOs.LOGGER.error("AresOS: GLFW did not hand back the release's own focus event ({}); forcing the normal cursor", own);
        own = 0;
        if (letGo == null) return;
        GLFW.glfwSetInputMode(letGo.handle(), GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
        finish();
    }

    /**
     * GLFW's focus callback ({@code Window.onFocus}), inside GLFW's event handling. True: the event was the mod's own
     * and Minecraft must not see it, so its record of the focus holds only what the real events said.
     *
     * <p>At the mod's FocusOut, GLFW has just let go completely: its handling of a FocusOut in the disabled mode asks
     * the server nothing. The mode turns normal here, inside the same event, so nothing can come between. A FocusIn
     * after it finds the normal mode and captures nothing, and whichever way GLFW's own focus test falls in
     * {@code glfwSetInputMode}, there is nothing left for it to skip.
     */
    public static boolean ownFocusEvent(long handle, boolean focused) {
        if (own == FOCUS_OUT && !focused && letGo != null && letGo.handle() == handle) {
            GLFW.glfwSetInputMode(handle, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
            finish();
            // GLFW also took the focus from its input context (dead keys). Where the real events say the window has
            // the focus, it gets a FocusIn the same way, as the very next event.
            own = Minecraft.getInstance().getWindow().isFocused() ? FOCUS_IN : 0;
            if (own == FOCUS_IN) Xlib.putBack(handle, FOCUS_IN);
            return true;
        }
        if (own == FOCUS_IN && focused) {
            own = 0;
            return true;
        }
        return false;
    }

    private static void finish() {
        long handle = letGo.handle();
        long display = GLFWNativeX11.glfwGetX11Display();
        // Give Xwayland the original pointer position before showing the cursor drops its lock. GLFW moves the pointer
        // only for a window with the X focus; without it the pointer shows where labwc left it.
        if (hiddenInX) GLFW.glfwSetCursorPos(handle, startX, startY);
        JNI.invokePJI(display, 0L /* CurrentTime */, Xlib.UNGRAB_POINTER);
        if (hiddenInX) JNI.invokePJV(display, GLFWNativeX11.glfwGetX11Window(handle), Xlib.SHOW_CURSOR);
        JNI.invokePI(display, Xlib.FLUSH);
        hiddenInX = false;
        letGo = null;
    }

    /** Client game tests: no release is under way and none of the mod's own events waits in Xlib's queue. */
    public static boolean settled() {
        return letGo == null && own == 0;
    }

    private static void direct(Window window, int mode, double x, double y) {
        GLFW.glfwSetCursorPos(window.handle(), x, y);
        GLFW.glfwSetInputMode(window.handle(), GLFW.GLFW_CURSOR, mode);
    }

    /** The few Xlib and XFixes calls, on GLFW's own X connection (client thread, as GLFW's). */
    private static final class Xlib {
        private static final SharedLibrary X11 = load("libX11.so.6"), XFIXES = load("libXfixes.so.3");
        static final long HIDE_CURSOR = address(XFIXES, "XFixesHideCursor"), SHOW_CURSOR = address(XFIXES, "XFixesShowCursor"),
                UNGRAB_POINTER = address(X11, "XUngrabPointer"), PUT_BACK_EVENT = address(X11, "XPutBackEvent"),
                FLUSH = address(X11, "XFlush");

        static boolean ready() {
            return HIDE_CURSOR != 0 && SHOW_CURSOR != 0 && UNGRAB_POINTER != 0 && PUT_BACK_EVENT != 0 && FLUSH != 0
                    && GLFW.glfwGetPlatform() == GLFW.GLFW_PLATFORM_X11 && GLFWNativeX11.glfwGetX11Display() != 0;
        }

        /**
         * Puts a focus event for the window (NotifyNormal, NotifyNonlinear, as X sends one) at the head of Xlib's event
         * queue: XPutBackEvent. It is the next event GLFW reads, ahead of everything the server has sent. Nothing goes to
         * the server and nothing is waited for, so no real focus change can get between this and GLFW's handling of it.
         */
        static void putBack(long handle, int type) {
            long display = GLFWNativeX11.glfwGetX11Display();
            try (var stack = MemoryStack.stackPush()) {
                // XFocusChangeEvent on x86-64: type, serial, send_event, display, window, mode, detail; XEvent is 192 bytes.
                var event = stack.calloc(192);
                event.putInt(0, type);
                event.putInt(16, 1 /* send_event: not from the server */);
                event.putLong(24, display);
                event.putLong(32, GLFWNativeX11.glfwGetX11Window(handle));
                event.putInt(40, 0 /* NotifyNormal */);
                event.putInt(44, 3 /* NotifyNonlinear */);
                JNI.invokePPI(display, MemoryUtil.memAddress(event), PUT_BACK_EVENT);
            }
        }

        private static SharedLibrary load(String name) {
            try {
                return APIUtil.apiCreateLibrary(name);
            } catch (Throwable error) {
                AresOs.LOGGER.warn("AresOS: {} is missing; the world captures the pointer as Minecraft does", name, error);
                return null;
            }
        }

        private static long address(SharedLibrary library, String function) {
            return library == null ? 0 : library.getFunctionAddress(function);
        }
    }

    /**
     * Client game tests: whether the pointer is over the world (null asks GLFW), and whether the cursor calls reach GLFW
     * although Fabric's test framework switches Minecraft's own call off (the native capture test needs the real one).
     */
    public static void forTests(Boolean pointerOverWorld, boolean direct) {
        pointerOverWorldForTests = pointerOverWorld;
        directForTests = direct;
        worldFocused = true;
    }
}
