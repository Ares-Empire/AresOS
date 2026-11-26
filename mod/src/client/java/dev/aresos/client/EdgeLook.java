package dev.aresos.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.config.LookMode;
import dev.aresos.focus.EdgeTurn;
import net.minecraft.client.Minecraft;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.system.MemoryStack;

import java.util.ArrayList;
import java.util.List;

/**
 * Package 328c, prototype B ("edge turning"), with {@code look = edge} in {@link LookMode#FILE}. In a session's connected
 * desktop world the cursor is always free: the world never takes the mouse, so the pointer crosses to the other output
 * like any other. The view turns while the cursor rests near the world's left, right or top edge. Left and Right
 * turn the view, and Up and Down tilt it ({@link EdgeTurn} holds the rules and the tunables). Movement keys walk and
 * fly as in classic, in the direction the camera faces.
 *
 * <p>Nothing here captures or lets go. Every grab finds the pointer free ({@link HomeScreen#freePointer}) and is refused
 * at the head of {@code grabMouse}, as behind an app in package 56. A click on the world goes on through vanilla's own
 * button handling after that refused grab, so it acts on what the crosshair aims at ({@link #clicksAct}). App slot
 * shortcuts take priority. A primary click opens or brings back the app, and a secondary click opens a new window
 * when the helper offers {@code activate_app}. While an app is in front, other presses only bring the world forward.
 */
public final class EdgeLook {
    /** {@code Entity.turn} counts in the mouse's units of 0.15 degrees. */
    private static final double DEGREES_PER_TURN_UNIT = 0.15;
    /** How often the window's place and the outputs are read again, so an output plugged in or moved counts soon. */
    private static final long LAYOUT_REFRESH_NS = 500_000_000L;

    // Client thread only.
    private static long lastFrame, layoutRead;
    private static boolean layoutKnown, positionSeen;
    private static EdgeTurn.Box window;
    private static EdgeTurn.Shared shared = EdgeTurn.Shared.NONE;
    private static EdgeTurn.Box windowForTests;
    private static List<EdgeTurn.Box> outputsForTests;

    private EdgeLook() { }

    /** The edge setting in a session's connected desktop world. */
    public static boolean on(Minecraft client) {
        return setting() && HomeScreen.active(client);
    }

    /** The edge setting alone: {@link HomeScreen#freePointer} adds the session's gates. */
    static boolean setting() {
        return LookSetting.mode() == LookMode.EDGE;
    }

    /**
     * With the edge setting and the world in front, the free pointer's clicks act on what the crosshair aims at: attack,
     * use and a held attack that breaks a block, all without the capture vanilla asks for first.
     */
    public static boolean clicksAct(Minecraft client) {
        return HomeScreen.freePointer(client) && !HomeScreen.ignoresMouse(client);
    }

    /** A cursor position reached Minecraft (before it, the position it holds is only its starting value). */
    public static void moved() {
        positionSeen = true;
    }

    /** Once a frame, from {@link HomeScreen#frame}: turns the view by what the edges and the arrow keys say. */
    static void frame(Minecraft client) {
        long now = System.nanoTime();
        double seconds = lastFrame == 0 ? 0 : (now - lastFrame) / 1e9;
        lastFrame = now;
        if (!on(client)) {
            positionSeen = false;
            layoutKnown = false;
            return;
        }
        var player = client.player;
        // The world ignores the mouse and the keys while an app is in front, and a screen or overlay has them.
        if (player == null || client.gui.screen() != null || client.gui.overlay() != null || HomeScreen.appInFront()) return;
        var window = client.getWindow();
        var turn = EdgeTurn.keys(edges(client, now),
                InputConstants.isKeyDown(window, EdgeTurn.LEFT_ARROW), InputConstants.isKeyDown(window, EdgeTurn.RIGHT_ARROW),
                InputConstants.isKeyDown(window, EdgeTurn.UP_ARROW), InputConstants.isKeyDown(window, EdgeTurn.DOWN_ARROW))
                .over(seconds);
        if (!turn.still()) player.turn(turn.yaw() / DEGREES_PER_TURN_UNIT, turn.pitch() / DEGREES_PER_TURN_UNIT);
    }

    private static EdgeTurn.Rate edges(Minecraft client, long now) {
        if (!positionSeen) return EdgeTurn.Rate.STILL;
        readLayout(client, now);
        var screen = client.getWindow();
        if (window == null || window.width() <= 0 || window.height() <= 0 || screen.getScreenWidth() <= 0
                || screen.getScreenHeight() <= 0) return EdgeTurn.Rate.STILL;
        // Minecraft counts the cursor in its own screen size, which outside tests is the window's real size.
        double x = client.mouseHandler.xpos() * window.width() / screen.getScreenWidth();
        double y = client.mouseHandler.ypos() * window.height() / screen.getScreenHeight();
        if (!EdgeTurn.turns(x, y, window.width(), window.height(), shared)) return EdgeTurn.Rate.STILL;
        // The pointer's leave: once it has left the world (onto the other output, or onto an app over the world), the
        // last position Minecraft has stays at the edge. X's leave event clears GLFW's hover test, asked only in a band.
        if (!WorldCapture.pointerOverWorld(client)) return EdgeTurn.Rate.STILL;
        return EdgeTurn.edges(x, y, window.width(), window.height(), shared);
    }

    /** The world's window and every output, from GLFW (under Xwayland the X server's view of labwc's layout). */
    private static void readLayout(Minecraft client, long now) {
        if (layoutKnown && now - layoutRead < LAYOUT_REFRESH_NS) return;
        layoutKnown = true;
        layoutRead = now;
        EdgeTurn.Box box;
        var outputs = new ArrayList<EdgeTurn.Box>();
        if (windowForTests != null) {
            box = windowForTests;
            outputs.addAll(outputsForTests);
        } else {
            long handle = client.getWindow().handle();
            try (var stack = MemoryStack.stackPush()) {
                var x = stack.mallocInt(1);
                var y = stack.mallocInt(1);
                var width = stack.mallocInt(1);
                var height = stack.mallocInt(1);
                GLFW.glfwGetWindowPos(handle, x, y);
                GLFW.glfwGetWindowSize(handle, width, height);
                box = new EdgeTurn.Box(x.get(0), y.get(0), width.get(0), height.get(0));
                var monitors = GLFW.glfwGetMonitors();
                for (int i = 0; monitors != null && i < monitors.limit(); i++) {
                    long monitor = monitors.get(i);
                    var mode = GLFW.glfwGetVideoMode(monitor);
                    if (mode == null) continue;
                    GLFW.glfwGetMonitorPos(monitor, x, y);
                    outputs.add(new EdgeTurn.Box(x.get(0), y.get(0), mode.width(), mode.height()));
                }
            }
        }
        var next = EdgeTurn.Shared.of(box, outputs);
        if (!box.equals(window) || !next.equals(shared))
            AresOs.LOGGER.info("AresOS: edge turning: window {}, outputs {}, shared {}", box, outputs, next);
        window = box;
        shared = next;
    }

    /** Starts over ({@link LookSetting#forTests}); a layout given for tests is dropped. */
    static void reset() {
        lastFrame = 0;
        layoutKnown = false;
        positionSeen = false;
        window = null;
        shared = EdgeTurn.Shared.NONE;
        windowForTests = null;
        outputsForTests = null;
    }

    /** Client game tests: the window and the outputs to use instead of GLFW's, in Minecraft's screen units. */
    public static void layoutForTests(EdgeTurn.Box window, List<EdgeTurn.Box> outputs) {
        windowForTests = window;
        outputsForTests = List.copyOf(outputs);
        layoutKnown = false;
    }
}
