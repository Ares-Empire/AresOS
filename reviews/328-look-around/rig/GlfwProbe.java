// Package 328 rig: GLFW 3.5 alone (LWJGL 3.4.1, the game's own libraries), as an X11 window with the desktop's identity
// under the rig's Xwayland, driven line by line from stdin. It shows what GLFW itself does with the pointer when its cursor
// mode changes while another window has the focus, without Minecraft or the mod. Run it through in-rig.sh:
//
//   java -cp <lwjgl, lwjgl-glfw and their natives-linux jars> GlfwProbe.java
//
// Commands: capture (Minecraft's grab: a warp to the centre, then GLFW_CURSOR_DISABLED) | release (Minecraft's release:
// GLFW_CURSOR_NORMAL) | xfhide | xfshow | ungrab | focusout (sent to the window) | state
// Release matrix: away (PointerRoot) | root | back | normal (set the mode only) | lever [away|root|back].
// Join commands with semicolons to run them without an intervening poll. Each line answers "done" on stdout.
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWNativeX11;
import org.lwjgl.system.APIUtil;
import org.lwjgl.system.JNI;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.system.MemoryUtil;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.concurrent.LinkedBlockingQueue;

public class GlfwProbe {
    static long window, display, xwindow;
    static final org.lwjgl.system.SharedLibrary X11 = APIUtil.apiCreateLibrary("libX11.so.6");
    static final org.lwjgl.system.SharedLibrary XFIXES = APIUtil.apiCreateLibrary("libXfixes.so.3");
    static long moves;
    static String leverFocus;

    public static void main(String[] args) throws Exception {
        if (System.getenv().getOrDefault("DISPLAY", ":0").equals(":0")) throw new IllegalStateException("refusing :0");
        GLFW.glfwInitHint(GLFW.GLFW_PLATFORM, GLFW.GLFW_PLATFORM_X11);
        if (!GLFW.glfwInit()) throw new IllegalStateException("glfwInit");
        GLFW.glfwWindowHint(GLFW.GLFW_CLIENT_API, GLFW.GLFW_NO_API);
        GLFW.glfwWindowHintString(GLFW.GLFW_X11_CLASS_NAME, "aresos-desktop");
        GLFW.glfwWindowHintString(GLFW.GLFW_X11_INSTANCE_NAME, "aresos-desktop");
        window = GLFW.glfwCreateWindow(1280, 720, "GlfwProbe", 0, 0);
        display = GLFWNativeX11.glfwGetX11Display();
        xwindow = GLFWNativeX11.glfwGetX11Window(window);
        // No GL here: an X background gives Xwayland something to show, so labwc maps the window.
        JNI.invokePPPI(display, xwindow, 0x204060L, X11.getFunctionAddress("XSetWindowBackground"));
        JNI.invokePJI(display, xwindow, X11.getFunctionAddress("XClearWindow"));
        JNI.invokePI(display, X11.getFunctionAddress("XFlush"));
        if (GLFW.glfwRawMouseMotionSupported()) GLFW.glfwSetInputMode(window, GLFW.GLFW_RAW_MOUSE_MOTION, GLFW.GLFW_TRUE);
        GLFW.glfwSetWindowFocusCallback(window, (w, focused) -> {
            say("FOCUS " + focused);
            if (!focused && leverFocus != null) {
                String move = leverFocus;
                leverFocus = null;
                if (!move.isEmpty()) focus(move);
                normal();
            }
        });
        GLFW.glfwSetCursorEnterCallback(window, (w, entered) -> say("ENTER " + entered));
        GLFW.glfwSetCursorPosCallback(window, (w, x, y) -> moves++);
        GLFW.glfwSetKeyCallback(window, (w, key, scan, action, mods) -> {
            if (key == GLFW.GLFW_KEY_ESCAPE) say("ESC " + action);
        });
        var commands = new LinkedBlockingQueue<String>();
        var reader = new Thread(() -> {
            try (var in = new BufferedReader(new InputStreamReader(System.in))) {
                for (String line; (line = in.readLine()) != null; ) commands.add(line.trim());
            } catch (Exception ignored) { }
            commands.add("quit");
        });
        reader.setDaemon(true);
        reader.start();
        say("ready");
        while (!GLFW.glfwWindowShouldClose(window)) {
            GLFW.glfwPollEvents();
            String command = commands.poll(16, java.util.concurrent.TimeUnit.MILLISECONDS);
            if (command == null || command.isEmpty()) continue;
            if (command.equals("quit")) break;
            for (String part : command.split(";")) run(part.trim());
            say("done " + command);
        }
        GLFW.glfwDestroyWindow(window);
        GLFW.glfwTerminate();
    }

    static void run(String command) {
        if (command.equals("lever") || command.startsWith("lever ")) {
            lever(command.substring("lever".length()).trim());
            return;
        }
        int[] w = new int[1], h = new int[1];
        GLFW.glfwGetWindowSize(window, w, h);
        switch (command) {
            case "capture" -> {
                GLFW.glfwSetCursorPos(window, w[0] / 2.0, h[0] / 2.0);
                GLFW.glfwSetInputMode(window, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_DISABLED);
            }
            case "release" -> {
                GLFW.glfwSetCursorPos(window, w[0] / 2.0, h[0] / 2.0);
                normal();
            }
            case "normal" -> normal();
            case "away", "root", "back" -> focus(command);
            case "xfhide" -> JNI.invokePJV(display, xwindow, XFIXES.getFunctionAddress("XFixesHideCursor"));
            case "xfshow" -> JNI.invokePJV(display, xwindow, XFIXES.getFunctionAddress("XFixesShowCursor"));
            case "ungrab" -> JNI.invokePJI(display, 0L, X11.getFunctionAddress("XUngrabPointer"));
            case "focusout" -> focusOut(false);
            case "state" -> {
                double[] x = new double[1], y = new double[1];
                GLFW.glfwGetCursorPos(window, x, y);
                say("STATE mode=" + Integer.toHexString(GLFW.glfwGetInputMode(window, GLFW.GLFW_CURSOR))
                        + " xfocus=" + Long.toHexString(xFocus()) + " window=" + Long.toHexString(xwindow)
                        + " glfwFocused=" + GLFW.glfwGetWindowAttrib(window, GLFW.GLFW_FOCUSED)
                        + " hovered=" + GLFW.glfwGetWindowAttrib(window, GLFW.GLFW_HOVERED)
                        + " cursor=" + x[0] + "," + y[0] + " moves=" + moves);
            }
            default -> say("unknown " + command);
        }
        JNI.invokePI(display, X11.getFunctionAddress("XFlush"));
    }

    static long xFocus() {
        try (var stack = MemoryStack.stackPush()) {
            var focus = stack.callocLong(1);
            var revert = stack.callocInt(1);
            JNI.invokePPPI(display, MemoryUtil.memAddress(focus), MemoryUtil.memAddress(revert),
                    X11.getFunctionAddress("XGetInputFocus"));
            return focus.get(0);
        }
    }

    static void focus(String move) {
        long target = switch (move) {
            case "away" -> 1L; // PointerRoot
            case "root" -> JNI.invokePP(display, X11.getFunctionAddress("XDefaultRootWindow"));
            case "back" -> xwindow;
            default -> throw new IllegalArgumentException(move);
        };
        JNI.invokePPPI(display, target, 0 /* RevertToNone */, 0L /* CurrentTime */,
                X11.getFunctionAddress("XSetInputFocus"));
        JNI.invokePI(display, 0 /* keep queued events */, X11.getFunctionAddress("XSync"));
        if (xFocus() != target) throw new IllegalStateException("X focus did not move " + move);
    }

    static void normal() {
        GLFW.glfwSetInputMode(window, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
    }

    static void lever(String move) {
        if (GLFW.glfwGetInputMode(window, GLFW.GLFW_CURSOR) != GLFW.GLFW_CURSOR_DISABLED)
            GLFW.glfwSetInputMode(window, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_DISABLED);
        leverFocus = move;
        focusOut(true);
        GLFW.glfwPollEvents();
        if (leverFocus != null) throw new IllegalStateException("GLFW did not hand back the put-back FocusOut");
    }

    static void focusOut(boolean putBack) {
        // XFocusChangeEvent on x86-64: type, serial, send_event, display, window, mode, detail. XEvent is 192 bytes.
        try (var stack = MemoryStack.stackPush()) {
            var event = stack.calloc(192);
            event.putInt(0, 10); // FocusOut
            event.putInt(16, 1); // send_event
            event.putLong(24, display);
            event.putLong(32, xwindow);
            event.putInt(40, 0); // NotifyNormal
            event.putInt(44, 3); // NotifyNonlinear
            long address = MemoryUtil.memAddress(event);
            if (putBack) {
                JNI.invokePPI(display, address, X11.getFunctionAddress("XPutBackEvent"));
            } else {
                JNI.invokePPPPI(display, xwindow, 0, 1L << 21, address, X11.getFunctionAddress("XSendEvent"));
            }
        }
    }

    static void say(String text) {
        System.out.println(text);
        System.out.flush();
    }
}
