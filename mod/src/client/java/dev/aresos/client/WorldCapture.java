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
 * <p><b>Letting go after an app took the focus.</b> GLFW 3.5 changes its X state for a cursor mode only while its window
 * has the X focus. When an app takes the focus with a click, X first takes the focus away from the game and then hands it
 * a pointer focus, on which GLFW captures once more; the mod's release comes after that, without the X focus, and GLFW
 * skips it. GLFW then keeps its X grab and warps the pointer to the window's centre after every move over the world, and
 * once the world is clicked again labwc follows one of those warps before the capture starts (rig/GlfwProbe.java shows
 * it with GLFW alone). So such a release first gives GLFW a focus-out event of its own: GLFW's handling of it lets go
 * completely, as it does when the focus leaves for good.
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
    private static Boolean pointerOverWorldForTests;
    private static boolean directForTests;

    private WorldCapture() { }

    /** The helper's focus changed, or a press on the world showed the compositor gave the world the focus. */
    static void worldFocused(boolean focused) {
        worldFocused = focused;
    }

    /** The helper went away: its next connection reports the focus again. */
    static void reset() {
        worldFocused = true;
    }

    /** Whether the world may take the mouse now (Minecraft's own check for its window's focus follows). */
    public static boolean allowed(Minecraft client) {
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
        if (HomeScreen.session() && !hiddenInX && Xlib.ready()) {
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

    /** Replaces Minecraft's release call in {@code MouseHandler.releaseMouse}. */
    public static void release(Window window, double x, double y, CursorMode minecraft) {
        // Fabric's client tests switch the capture off, so only a real one has X state to let go of.
        boolean captured = GLFW.glfwGetInputMode(window.handle(), GLFW.GLFW_CURSOR) == GLFW.GLFW_CURSOR_DISABLED;
        boolean x11 = HomeScreen.session() && Xlib.ready();
        long display = x11 ? GLFWNativeX11.glfwGetX11Display() : 0;
        long xwindow = x11 ? GLFWNativeX11.glfwGetX11Window(window.handle()) : 0;
        if (x11 && captured && !Xlib.focused(display, xwindow)) {
            // GLFW would skip this release (see above). Its own focus-out handling lets go of everything: give it one
            // and let it run now, before Minecraft's mode change. This is never inside a GLFW callback: without the X
            // focus a release comes from the helper's focus event or the frame's focus check, both queued work.
            Xlib.focusOut(display, xwindow);
            GLFW.glfwPollEvents();
        }
        (directForTests ? (CursorMode) WorldCapture::direct : minecraft).set(window, GLFW.GLFW_CURSOR_NORMAL, x, y);
        if (x11) {
            // GLFW put the X pointer back to the window's centre. Before the cursor shows, it goes to where the capture
            // began: Xwayland's last lock then has its hint there, and labwc leaves the pointer where it is. Otherwise
            // showing the cursor drops the lock and labwc parks the pointer at the centre, over whatever stands there,
            // also when Minecraft lets go and takes the mouse again within a frame.
            if (captured && hiddenInX) GLFW.glfwSetCursorPos(window.handle(), startX, startY);
            JNI.invokePJI(display, 0L /* CurrentTime */, Xlib.UNGRAB_POINTER);
            if (hiddenInX) JNI.invokePJV(display, xwindow, Xlib.SHOW_CURSOR);
            JNI.invokePI(display, Xlib.FLUSH);
        }
        hiddenInX = false;
    }

    private static void direct(Window window, int mode, double x, double y) {
        GLFW.glfwSetCursorPos(window.handle(), x, y);
        GLFW.glfwSetInputMode(window.handle(), GLFW.GLFW_CURSOR, mode);
    }

    /** The few Xlib and XFixes calls, on GLFW's own X connection (client thread, as GLFW's). */
    private static final class Xlib {
        private static final SharedLibrary X11 = load("libX11.so.6"), XFIXES = load("libXfixes.so.3");
        static final long HIDE_CURSOR = address(XFIXES, "XFixesHideCursor"), SHOW_CURSOR = address(XFIXES, "XFixesShowCursor"),
                UNGRAB_POINTER = address(X11, "XUngrabPointer"), GET_INPUT_FOCUS = address(X11, "XGetInputFocus"),
                SEND_EVENT = address(X11, "XSendEvent"), FLUSH = address(X11, "XFlush");

        static boolean ready() {
            return HIDE_CURSOR != 0 && SHOW_CURSOR != 0 && UNGRAB_POINTER != 0 && GET_INPUT_FOCUS != 0
                    && SEND_EVENT != 0 && FLUSH != 0
                    && GLFW.glfwGetPlatform() == GLFW.GLFW_PLATFORM_X11 && GLFWNativeX11.glfwGetX11Display() != 0;
        }

        /** Sends the window the FocusOut X sends when the focus leaves it (NotifyNormal, NotifyNonlinear). */
        static void focusOut(long display, long xwindow) {
            try (var stack = MemoryStack.stackPush()) {
                // XFocusChangeEvent on x86-64: type, serial, send_event, display, window, mode, detail; XEvent is 192 bytes.
                var event = stack.calloc(192);
                event.putInt(0, 10 /* FocusOut */);
                event.putInt(16, 1 /* send_event */);
                event.putLong(24, display);
                event.putLong(32, xwindow);
                event.putInt(40, 0 /* NotifyNormal */);
                event.putInt(44, 3 /* NotifyNonlinear */);
                // XSendEvent(display, window, propagate False, FocusChangeMask, event)
                JNI.invokePPPPI(display, xwindow, 0, 1L << 21, MemoryUtil.memAddress(event), SEND_EVENT);
                JNI.invokePI(display, FLUSH);
            }
        }

        /** GLFW's own test for its window's focus: the X input focus is that window. */
        static boolean focused(long display, long xwindow) {
            try (var stack = MemoryStack.stackPush()) {
                var focus = stack.callocLong(1);
                var revert = stack.callocInt(1);
                JNI.invokePPPI(display, MemoryUtil.memAddress(focus), MemoryUtil.memAddress(revert), GET_INPUT_FOCUS);
                return focus.get(0) == xwindow;
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
