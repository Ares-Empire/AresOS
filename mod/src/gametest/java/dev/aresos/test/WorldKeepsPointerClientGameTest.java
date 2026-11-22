package dev.aresos.test;

import com.google.gson.Gson;
import dev.aresos.AresOs;
import dev.aresos.client.AresOsMenuScreen;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldCapture;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.KeyboardTestAccess;
import dev.aresos.test.mixin.MouseTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.input.MouseButtonInfo;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWNativeX11;
import org.lwjgl.system.APIUtil;
import org.lwjgl.system.JNI;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.system.MemoryUtil;

import java.io.*;
import java.lang.foreign.Arena;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.Linker;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.net.StandardProtocolFamily;
import java.net.UnixDomainSocketAddress;
import java.nio.channels.Channels;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Package 328a, last in the suite: the world keeps the pointer while it steers the camera. Every run checks the capture
 * rule through the game's own callbacks. With {@code client-test.sh --session} it also captures for real (Fabric
 * switches Minecraft's GLFW call off; {@link WorldCapture#forTests} puts the same calls back for this test), with the
 * rig's inert probe app over the window's centre and the rig's virtual pointer, and the probe must count nothing.
 */
public final class WorldKeepsPointerClientGameTest implements FabricClientGameTest {
    // Client thread only: what runs once at a named point of a release (WorldCaptureReleaseTestMixin).
    private static String seamName;
    private static Runnable seamRun;

    public static void seam(String name) {
        if (seamRun == null || !name.equals(seamName)) return;
        var run = seamRun;
        seamRun = null;
        run.run();
    }

    @Override public void runTest(ClientGameTestContext context) {
        var previousShell = AresOs.shell();
        Path sockets = null;
        try {
            sockets = Files.createDirectories(Path.of("p328"));
            try (var helper = new HelperProcess(sockets);
                 var shell = new ShellClient(sockets.resolve("s.sock"), FakeHelper.INSTANCE, FakeHelper.NONCE,
                         FakeHelper.fast());
                 var rig = new Rig(context)) {
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setShell(shell);
                    HomeScreen.forTests(true, null);
                });
                shell.start();
                shell.awaitApps(Duration.ofSeconds(10));
                context.runOnClient(client -> ShellFocusClient.register(shell));
                try (var world = context.worldBuilder().create()) {
                    world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
                    context.waitFor(HomeScreen::active);
                    rules(context, helper);
                    if (rig.enabled) {
                        nativeCapture(context, helper, shell, rig);
                        rig.prepareWorldExit();
                    } else AresOs.LOGGER.info("328a: no --session, so the native capture checks did not run");
                }
                if (rig.enabled) {
                    context.waitFor(client -> client.gui.screen() instanceof TitleScreen && client.level == null);
                    rig.clean("world exit");
                    check(!Files.readString(Path.of("logs/latest.log")).contains("did not hand back"),
                            "GLFW missed a put-back focus event");
                    AresOs.LOGGER.info("328a: world exit released the session's vanilla capture on the title screen");
                }
                // Its listeners reach Minecraft, which only the client thread may do.
                context.runOnClient(client -> shell.close());
            }
            AresOs.LOGGER.info("328a world-keeps-pointer checks passed");
        } catch (IOException error) { throw new UncheckedIOException(error); }
        finally {
            context.runOnClient(client -> {
                seamRun = null;
                client.mouseHandler.releaseMouse();
                HomeScreen.forTests(null, null);
                AppsTestAccess.aresos$setShell(previousShell);
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
            if (sockets != null) try { Files.deleteIfExists(sockets.resolve("s.sock")); Files.deleteIfExists(sockets); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    /** The safe fallback, through the game's callbacks: the world takes the mouse only with the focus and the pointer. */
    private static void rules(ClientGameTestContext context, HelperProcess helper) {
        helper.focus(true);
        context.waitTicks(2);
        context.runOnClient(client -> {
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            client.mouseHandler.releaseMouse();
            WorldCapture.forTests(false, false);
            client.mouseHandler.grabMouse();
            check(!client.mouseHandler.isMouseGrabbed(), "The world took the mouse with the pointer on another window");
            WorldCapture.forTests(true, false);
            client.mouseHandler.grabMouse();
            check(client.mouseHandler.isMouseGrabbed(), "The world refused the mouse with the focus and the pointer on it");
            client.options.keyUp.setDown(true);
            client.options.keyAttack.setDown(true);
        });
        helper.focus(false);
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(!client.mouseHandler.isMouseGrabbed(), "An app took the focus and the world kept the mouse");
            check(!client.options.keyUp.isDown() && !client.options.keyAttack.isDown(), "Walking or attacking stayed held");
            client.mouseHandler.grabMouse();
            check(!client.mouseHandler.isMouseGrabbed(), "The world took the mouse behind the app in front");
            // A click on the world: labwc gives the world the focus before the press, so it captures at once.
            mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(GLFW.GLFW_MOUSE_BUTTON_LEFT, 0),
                    GLFW.GLFW_PRESS);
            mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(GLFW.GLFW_MOUSE_BUTTON_LEFT, 0),
                    GLFW.GLFW_RELEASE);
            check(client.mouseHandler.isMouseGrabbed(), "A click on the world did not enter it");
            client.options.keyUp.setDown(true);
            client.mouseHandler.releaseMouse();
            check(!client.options.keyUp.isDown(), "Letting go of the mouse left walking held");
            KeyMapping.releaseAll();
        });
        helper.focus(true);
        context.waitTicks(2);
    }

    /** The real capture under Xwayland and labwc, with the probe app over the window's centre. */
    private static void nativeCapture(ClientGameTestContext context, HelperProcess helper, ShellClient shell, Rig rig)
            throws IOException {
        context.runOnClient(client -> {
            client.mouseHandler.releaseMouse();
            WorldCapture.forTests(null, true);
        });
        rig.start();
        rig.tool("max", "aresos-desktop");
        rig.openProbe();
        helper.focus(false);  // what the helper says when an app opens over the world
        context.waitFor(client -> !client.mouseHandler.isMouseGrabbed());
        int[] box = rig.windowBox();
        int cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2;

        // The instrument: the probe stands over the centre and counts a click that is really its own.
        rig.input("abs " + cx + " " + cy);
        context.waitTicks(3);
        check(rig.probe().contains("\"pointer_inside\": true"), "The probe does not stand over the window's centre: " + rig.probe());
        check(!context.computeOnClient(WorldCapture::pointerOverWorld), "GLFW says the pointer is on the world over the probe");
        long presses = rig.count("button_press");
        rig.input("click left");
        context.waitTicks(3);
        check(rig.count("button_press") == presses + 1, "The probe did not count a click on it: " + rig.probe());

        // The safe fallback: focused world, pointer on the probe: no capture, the pointer stays a normal one.
        rig.tool("activate", "aresos-desktop");
        helper.focus(true);
        context.waitTicks(4);
        context.runOnClient(client -> {
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            client.mouseHandler.grabMouse();
            check(!client.mouseHandler.isMouseGrabbed(), "The world took the mouse with the pointer resting on the probe");
            check(GLFW.glfwGetInputMode(client.getWindow().handle(), GLFW.GLFW_CURSOR) == GLFW.GLFW_CURSOR_NORMAL,
                    "The pointer is not a normal pointer over the probe");
        });

        // The owner's report: the probe in front, a click on the world beside it, then the world steers the camera.
        rig.tool("activate", "aresos.pkg328.probe");
        helper.focus(false);
        context.waitTicks(4);
        rig.input("abs " + (box[0] + 60) + " " + (box[1] + 60));
        context.waitTicks(3);
        check(context.computeOnClient(WorldCapture::pointerOverWorld), "GLFW does not see the pointer on the world");
        long[] before = rig.counts();
        rig.input("click left");
        helper.focus(true);  // the helper's desktop_activated follows labwc's activation
        context.waitFor(WorldKeepsPointerClientGameTest::captured);
        float yaw = context.computeOnClient(client -> client.player.getYRot());
        for (int step = 0; step < 40; step++) rig.input("rel 12 8");
        rig.input("button left down");
        context.waitTicks(2);
        check(context.computeOnClient(client -> client.mouseHandler.isLeftPressed()),
                "Minecraft did not receive the captured click");
        rig.input("button left up");
        int slot = context.computeOnClient(client -> client.player.getInventory().getSelectedSlot());
        rig.input("scroll 15");
        context.waitTicks(5);
        check(context.computeOnClient(client -> client.player.getInventory().getSelectedSlot()) != slot,
                "Minecraft did not receive the captured scroll");
        long[] after = rig.counts();
        float turned = context.computeOnClient(client -> client.player.getYRot()) - yaw;
        AresOs.LOGGER.info("328a native capture: probe {} -> {}, camera turned {} degrees", java.util.Arrays.toString(before),
                java.util.Arrays.toString(after), turned);
        check(java.util.Arrays.equals(before, after), "The hidden pointer reached the probe: " + rig.probe());
        check(Math.abs(turned) > 1, "The world did not get the pointer's motion (camera turned " + turned + ")");
        check(context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()), "The world let go of the mouse");

        // An app takes the focus while the world steers: labwc moves the X focus before the mod lets go.
        rig.tool("activate", "aresos.pkg328.probe");
        helper.focus(false);
        context.waitFor(WorldKeepsPointerClientGameTest::released);
        // Super or Alt+Tab while the pointer rests on the probe: the world gets the focus but not the mouse.
        rig.input("abs " + cx + " " + cy);
        rig.tool("activate", "aresos-desktop");
        helper.focus(true);
        context.waitTicks(5);
        check(!context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()),
                "The world took the mouse with the pointer resting on the probe");
        // The pointer then moves onto the world as a normal pointer: never pulled back to the window's centre.
        long enters = rig.count("enter");
        rig.input("abs " + (box[0] + 60) + " " + (box[1] + 60));
        for (int step = 0; step < 12; step++) {
            rig.input("rel 5 3");
            context.waitTick();
        }
        context.waitTicks(3);
        check(rig.count("enter") == enters && !rig.probe().contains("\"pointer_inside\": true"),
                "The free pointer jumped back onto the probe: " + rig.probe());
        check(context.computeOnClient(WorldCapture::pointerOverWorld), "The free pointer is not on the world");
        // A click on the world takes the mouse, and Esc (the AresOS menu) lets go: a normal pointer that reaches the probe.
        rig.input("click left");
        context.waitFor(WorldKeepsPointerClientGameTest::captured);
        check(rig.count("button_press") == presses + 1, "The click on the world reached the probe: " + rig.probe());
        rig.escDuringHandoff(false);
        rig.restoreFocus();
        rig.closeMenuOverProbe();
        context.waitTicks(3);
        check(!context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()),
                "Closing the menu took the mouse with the pointer on the probe");
        rig.clean("Escape before NORMAL");

        // Queue a real FocusIn just before the synthetic FocusOut. It must leave Minecraft ready for the next click.
        rig.captureAt(box[0] + 60, box[1] + 60);
        rig.escDuringHandoff(true);
        check(context.computeOnClient(client -> client.isWindowActive() && xFocused(client)),
                "The synthetic FocusOut overwrote the real FocusIn");
        rig.closeMenuOverProbe();
        check(context.computeOnClient(WorldKeepsPointerClientGameTest::released),
                "Closing the menu over the probe captured the pointer");
        rig.captureAt(box[0] + 60, box[1] + 60);
        AresOs.LOGGER.info("328a: real Escape released after its GLFW callback and a racing FocusIn allowed recapture");

        // The matrix starts with a fresh click on every cycle, including the first one.
        context.runOnClient(client -> client.mouseHandler.releaseMouse());
        context.waitFor(client -> released(client) && WorldCapture.settled());
        rig.checkPosition(60, 60, "focused release restored the original pointer position");
        rig.clean("focused release before the matrix");
        rig.races();

        rig.captureAt(box[0] + 60, box[1] + 60);
        rig.leaveAtNormal("helper background");
        helper.focus(false);
        rig.clean("helper background");
        // SIGKILL the fake helper while the world holds the mouse and has no screen to release it.
        rig.captureAt(box[0] + 60, box[1] + 60);
        context.runOnClient(client -> {
            check(xFocused(client) && captured(client), "The game was not focused and captured before helper death");
            client.options.keyUp.setDown(true);
        });
        rig.leaveAtNormal("helper death");
        helper.kill();
        context.waitFor(client -> shell.status().state() != ShellClient.State.CONNECTED && released(client));
        rig.clean("helper death");
        context.runOnClient(client -> {
            check(!HomeScreen.active(client) && client.gui.screen() == null && xFocused(client),
                    "The connected-world gate, a menu or lost focus interfered with helper-loss cleanup");
            check(!client.options.keyUp.isDown(), "Helper death left walking held");
        });
        rig.input("abs " + cx + " " + cy);
        rig.await(() -> rig.probe().contains("\"pointer_inside\": true"), "free pointer on the probe after helper death");
        AresOs.LOGGER.info("328a: helper background and SIGKILL freed the cursor with X focus leaving before NORMAL");
    }

    static boolean captured(Minecraft client) {
        return client.mouseHandler.isMouseGrabbed() && cursorMode(client) == GLFW.GLFW_CURSOR_DISABLED;
    }

    static boolean released(Minecraft client) {
        return !client.mouseHandler.isMouseGrabbed() && cursorMode(client) == GLFW.GLFW_CURSOR_NORMAL;
    }

    private static int cursorMode(Minecraft client) {
        return GLFW.glfwGetInputMode(client.getWindow().handle(), GLFW.GLFW_CURSOR);
    }

    static boolean xFocused(Minecraft client) {
        return GLFW.glfwGetWindowAttrib(client.getWindow().handle(), GLFW.GLFW_FOCUSED) == GLFW.GLFW_TRUE;
    }

    static MouseTestAccess mouse(Minecraft client) { return (MouseTestAccess)(Object)client.mouseHandler; }

    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }

    private enum Start { FOCUSED, AWAY_QUEUED, AWAY_HANDLED }

    private enum Focus { AWAY, ROOT, BACK }

    /** The shared fake helper in its own process, so SIGKILL exercises the client's real socket-loss path. */
    public static final class HelperProcess implements AutoCloseable {
        private final Process process;
        private final BufferedWriter input;

        HelperProcess(Path sockets) throws IOException {
            var classes = java.util.stream.Stream.of(HelperProcess.class, FakeHelper.class, Gson.class)
                    .map(type -> Path.of(java.net.URI.create(
                            type.getProtectionDomain().getCodeSource().getLocation().toString())).toString())
                    .distinct().collect(java.util.stream.Collectors.joining(File.pathSeparator));
            process = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(), "-cp",
                    classes, HelperProcess.class.getName(), sockets.toString())
                    .redirectError(ProcessBuilder.Redirect.INHERIT).start();
            input = process.outputWriter();
            check("ready".equals(process.inputReader().readLine()), "The fake helper process failed to start");
        }

        public static void main(String[] args) throws IOException {
            try (var helper = new FakeHelper(Path.of(args[0]));
                 var commands = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
                System.out.println("ready");
                String command;
                while ((command = commands.readLine()) != null) {
                    if (Boolean.parseBoolean(command)) {
                        helper.event("shell_focus", Map.of("focus", "foreground", "reason", "desktop_activated"));
                    } else {
                        helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated",
                                "app_id", "probe"));
                    }
                }
            }
        }

        void focus(boolean world) {
            try {
                input.write(Boolean.toString(world));
                input.newLine();
                input.flush();
            } catch (IOException error) { throw new UncheckedIOException(error); }
        }

        void kill() {
            process.destroyForcibly().onExit().orTimeout(10, java.util.concurrent.TimeUnit.SECONDS).join();
        }

        @Override public void close() {
            if (process.isAlive()) kill();
        }
    }

    private static final class X11 {
        private static final org.lwjgl.system.SharedLibrary X11 = APIUtil.apiCreateLibrary("libX11.so.6");
        private static final org.lwjgl.system.SharedLibrary XFIXES = APIUtil.apiCreateLibrary("libXfixes.so.3");
        private static int xError;

        static long target(long handle, Focus focus) {
            long display = GLFWNativeX11.glfwGetX11Display();
            return switch (focus) {
                case AWAY -> 1L; // PointerRoot
                case ROOT -> JNI.invokePP(display, X11.getFunctionAddress("XDefaultRootWindow"));
                case BACK -> GLFWNativeX11.glfwGetX11Window(handle);
            };
        }

        static void focus(long handle, Focus focus) {
            long display = GLFWNativeX11.glfwGetX11Display();
            long target = target(handle, focus);
            JNI.invokePPPI(display, target, 0 /* RevertToNone */, 0L /* CurrentTime */,
                    X11.getFunctionAddress("XSetInputFocus"));
            sync(display);
            checkFocus(handle, focus, "after XSetInputFocus");
        }

        static void checkFocus(long handle, Focus expected, String where) {
            try (var stack = MemoryStack.stackPush()) {
                var actual = stack.callocLong(1);
                var revert = stack.callocInt(1);
                JNI.invokePPPI(GLFWNativeX11.glfwGetX11Display(), MemoryUtil.memAddress(actual),
                        MemoryUtil.memAddress(revert), X11.getFunctionAddress("XGetInputFocus"));
                check(actual.get(0) == target(handle, expected),
                        where + ": expected X focus " + expected + ", got 0x" + Long.toHexString(actual.get(0)));
            }
        }

        static void checkCursorShown(long handle) {
            long display = GLFWNativeX11.glfwGetX11Display();
            sync(display);
            // XFixes returns BadMatch for ShowCursor when this X client has no outstanding HideCursor.
            // Check the real server state using GLFW's connection, with the error handler scoped to this request.
            long setHandler = X11.getFunctionAddress("XSetErrorHandler");
            try (var arena = Arena.ofConfined()) {
                var handler = MethodHandles.lookup().findStatic(X11.class, "recordError",
                        MethodType.methodType(int.class, MemorySegment.class, MemorySegment.class));
                var callback = Linker.nativeLinker().upcallStub(handler,
                        FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS, ValueLayout.ADDRESS), arena);
                long previous = JNI.invokePP(callback.address(), setHandler);
                try {
                    xError = 0;
                    JNI.invokePJV(display, GLFWNativeX11.glfwGetX11Window(handle),
                            XFIXES.getFunctionAddress("XFixesShowCursor"));
                    sync(display);
                    check(xError == 8 /* BadMatch */, "XFixes cursor hide was still outstanding (X error " + xError + ")");
                } finally {
                    JNI.invokePP(previous, setHandler);
                }
            } catch (ReflectiveOperationException error) { throw new AssertionError(error); }
        }

        private static int recordError(MemorySegment display, MemorySegment event) {
            xError = Byte.toUnsignedInt(event.reinterpret(40).get(ValueLayout.JAVA_BYTE, 32)); // XErrorEvent.error_code
            return 0;
        }

        private static void sync(long display) {
            JNI.invokePI(display, 0, X11.getFunctionAddress("XSync"));
        }
    }

    /** The rig of reviews/328-look-around/rig on the session's own headless compositor: probe, virtual input, tl.py. */
    static final class Rig implements AutoCloseable {
        final boolean enabled = Boolean.getBoolean("aresos.pointerSession");
        final ClientGameTestContext context;
        Path root, repo;
        Process probe, vinput, sideWindow;
        int sideOutputX;
        org.lwjgl.glfw.GLFWCursorPosCallback previousMove;
        org.lwjgl.glfw.GLFWMouseButtonCallback previousButton;
        org.lwjgl.glfw.GLFWScrollCallback previousScroll;
        org.lwjgl.glfw.GLFWWindowFocusCallback previousFocus;
        int focusIn, focusOut;
        boolean installed;

        Rig(ClientGameTestContext context) { this.context = context; }

        void start() {
            check(!System.getenv().getOrDefault("WAYLAND_DISPLAY", "wayland-0").equals("wayland-0")
                    && !System.getenv().getOrDefault("DISPLAY", ":0").equals(":0"), "Refusing the owner's display");
            try {
                root = Files.createDirectories(Path.of("p328-rig").toAbsolutePath());
                repo = Path.of(System.getProperty("aresos.repoDir"));
                String[] layout = System.getenv().getOrDefault("ARESOS_POINTER_LAYOUT", "1280x720").split("x");
                sideOutputX = Integer.parseInt(layout[0]) / 2;
                Files.writeString(root.resolve("env"), "WAYLAND_DISPLAY=" + System.getenv("WAYLAND_DISPLAY")
                        + "\nDISPLAY=" + System.getenv("DISPLAY") + "\nLAYOUT_W=" + layout[0] + "\nLAYOUT_H=" + layout[1] + "\n");
                Files.deleteIfExists(root.resolve("vinput.sock"));
                Files.deleteIfExists(root.resolve("probe.json"));
                vinput = new ProcessBuilder("python3", "-I", rigFile("vinput.py"), root.toString())
                        .redirectErrorStream(true).redirectOutput(root.resolve("vinput.log").toFile()).start();
                await(() -> Files.exists(root.resolve("vinput.sock")), "the virtual input");
                sideWindow = new ProcessBuilder("python3", "-I", rigFile("xside.py"), Integer.toString(sideOutputX))
                        .redirectErrorStream(true).start();
                check("ready".equals(sideWindow.inputReader().readLine()), "The second-output X11 fixture did not start");
            } catch (IOException error) { throw new UncheckedIOException(error); }
            // Fabric attaches no native input callbacks and renders at a virtual size: map real coordinates to it.
            context.runOnClient(client -> {
                long handle = client.getWindow().handle();
                previousMove = GLFW.glfwSetCursorPosCallback(handle, (window, x, y) -> {
                    int[] size = realSize(window);
                    mouse(client).aresos$onMove(window, x * client.getWindow().getScreenWidth() / size[0],
                            y * client.getWindow().getScreenHeight() / size[1]);
                });
                previousButton = GLFW.glfwSetMouseButtonCallback(handle, (window, button, action, modifiers) ->
                        mouse(client).aresos$onButton(window, new MouseButtonInfo(button, modifiers), action));
                previousScroll = GLFW.glfwSetScrollCallback(handle, (window, dx, dy) ->
                        mouse(client).aresos$onScroll(window, dx, dy));
                previousFocus = GLFW.glfwSetWindowFocusCallback(handle, null);
                check(previousFocus != null, "Minecraft's native focus callback is missing");
                GLFW.glfwSetWindowFocusCallback(handle, (window, focused) -> {
                    if (focused) focusIn++;
                    else focusOut++;
                    previousFocus.invoke(window, focused);
                });
                NativeFocusTestPlugin.nativeFocus(true);
                installed = true;
            });
        }

        void openProbe() {
            try {
                probe = new ProcessBuilder("python3", "-I", rigFile("probe.py"), root.toString(), "640", "400")
                        .redirectErrorStream(true).redirectOutput(root.resolve("probe.out").toFile()).start();
            } catch (IOException error) { throw new UncheckedIOException(error); }
            await(() -> probe().contains("\"keyboard_focus\": true"), "the probe window");
            context.waitTicks(3);
        }

        void captureAt(int x, int y) {
            int[] box = windowBox();
            input("abs " + x + " " + y);
            context.waitFor(client -> WorldCapture.pointerOverWorld(client)
                    && atPosition(cursorPosition(client), x - box[0], y - box[1]));
            input("click left");
            context.waitFor(WorldKeepsPointerClientGameTest::captured);
        }

        void closeMenuOverProbe() {
            int[] box = windowBox();
            // Record a native X motion outside the game before entering the Wayland-only probe.
            moveOffWorld(box, "Escape over the probe");
            int cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2;
            for (int offset = 0; offset <= 30 && !probe().contains("\"pointer_inside\": true"); offset += 10) {
                input("abs " + (cx + offset) + " " + (cy + offset));
                context.waitTicks(3);
            }
            check(probe().contains("\"pointer_inside\": true"), "The released pointer did not reach the probe: " + probe());
            context.runOnClient(client -> {
                check(client.gui.screen() instanceof AresOsMenuScreen, "The Escape menu closed before the test could close it");
                check(client.isWindowActive() && !WorldCapture.pointerOverWorld(client),
                        "The test needs a focused game with the X pointer outside its window");
                client.gui.setScreen(null);
            });
        }

        void restoreFocus() {
            context.runOnClient(client -> X11.focus(client.getWindow().handle(), Focus.BACK));
        }

        void moveOffWorld(int[] box, String label) {
            moveTo(box, sideOutputX + 90 - box[0], 70 - box[1], label);
            check(!context.computeOnClient(WorldCapture::pointerOverWorld), label + ": X still reports the pointer on the world");
        }

        void races() {
            int[] box = windowBox();
            var moves = List.of(List.of(Focus.AWAY), List.of(Focus.ROOT),
                    List.of(Focus.BACK), List.of(Focus.AWAY, Focus.BACK), List.of(Focus.BACK, Focus.AWAY));
            int cycles = 0;
            for (Start start : Start.values()) {
                for (String point : List.of("asked", "queued", "normal", "show", "polled")) {
                    for (var move : moves) {
                        String label = start + " / " + point + " / " + move;
                        captureAt(box[0] + 90, box[1] + 70);
                        var events = context.computeOnClient(client -> {
                            long handle = client.getWindow().handle();
                            X11.checkFocus(handle, Focus.BACK, label + " before setup");
                            if (start == Start.AWAY_HANDLED) X11.focus(handle, Focus.AWAY);
                            return new int[] {focusOut, focusIn};
                        });
                        if (start == Start.AWAY_HANDLED) context.waitTicks(2);
                        context.runOnClient(client -> {
                            long handle = client.getWindow().handle();
                            check(captured(client) && WorldCapture.ownsCapture(), label + ": capture lost before release");
                            if (start == Start.AWAY_HANDLED) {
                                check(focusOut > events[0] && focusIn > events[1] && client.isWindowActive(),
                                        label + ": GLFW did not consume the real FocusOut and pointer FocusIn");
                            } else if (start == Start.AWAY_QUEUED) {
                                int out = focusOut, in = focusIn;
                                X11.focus(handle, Focus.AWAY);
                                check(focusOut == out && focusIn == in && client.isWindowActive(),
                                        label + ": GLFW handled the X focus events before release");
                            }
                            Focus expected = start == Start.FOCUSED ? Focus.BACK : Focus.AWAY;
                            arm(point, () -> {
                                X11.checkFocus(handle, expected, label + " before seam");
                                for (Focus destination : move) X11.focus(handle, destination);
                            });
                            client.mouseHandler.releaseMouse();
                            check(!WorldCapture.settled() && cursorMode(client) == GLFW.GLFW_CURSOR_DISABLED,
                                    label + ": release did not wait for the next poll");
                            client.mouseHandler.grabMouse();
                            check(!client.mouseHandler.isMouseGrabbed(), label + ": captured while release was pending");
                        });
                        clean(label);
                        cycles++;
                    }
                }
                AresOs.LOGGER.info("328a: {} passed all 25 focus races", start);
            }
            // Prove recapture for the final cycle too.
            captureAt(box[0] + 90, box[1] + 70);
            context.runOnClient(client -> client.mouseHandler.releaseMouse());
            clean("final race recapture");
            AresOs.LOGGER.info("328a: {} race cycles passed and every next click recaptured", cycles);
        }

        void clean(String label) {
            context.waitFor(client -> released(client) && WorldCapture.settled());
            int[] box = windowBox();
            // Restore focus with the pointer off the game to avoid HomeScreen's separate capture-on-return path.
            if (!context.computeOnClient(WorldKeepsPointerClientGameTest::xFocused)) moveOffWorld(box, label);
            context.runOnClient(client -> {
                check(seamRun == null, label + ": the release never reached its seam");
                X11.focus(client.getWindow().handle(), Focus.BACK);
            });
            context.waitTicks(3);
            context.runOnClient(client -> {
                check(released(client) && WorldCapture.settled(), label + ": release did not settle");
                check(client.isWindowActive(), label + ": Minecraft lost focus after X focus returned");
                X11.checkCursorShown(client.getWindow().handle());
            });
            // labwc may already be at the capture's starting point (90,70) while X still has its last warp there.
            // Use a distinct point first so the observations require two actual pointer moves.
            moveTo(box, 70, 50, label);
            for (int[] point : new int[][] {{90, 70}, {140, 110}}) {
                moveTo(box, point[0], point[1], label);
                context.waitTicks(3);
                checkPosition(point[0], point[1], label);
            }
            // Probing with another client's XGrabPointer can change routing, so do it after the motion checks.
            check(command("bash", rigFile("state.sh"), root.toString()).contains("X pointer grab: free"),
                    label + ": an X client still holds the pointer");
        }

        void moveTo(int[] box, int x, int y, String label) {
            int screenX = box[0] + x, screenY = box[1] + y;
            for (int attempt = 0; attempt < 4; attempt++) {
                // If labwc consumed the first motion while dropping a lock, a repeated destination may be a no-op.
                if (attempt > 0) input("abs " + (screenX - 8) + " " + (screenY - 8));
                input("abs " + screenX + " " + screenY);
                context.waitTicks(2);
                if (context.computeOnClient(client -> atPosition(cursorPosition(client), x, y))) return;
            }
            checkPosition(x, y, label + " (after delivering virtual motion)");
        }

        void checkPosition(int x, int y, String label) {
            context.runOnClient(client -> {
                var actual = cursorPosition(client);
                check(atPosition(actual, x, y), label + ": expected the free pointer at " + x + "," + y
                        + ", got " + actual[0] + "," + actual[1]);
            });
        }

        private static double[] cursorPosition(Minecraft client) {
            try (var stack = MemoryStack.stackPush()) {
                var x = stack.mallocDouble(1);
                var y = stack.mallocDouble(1);
                GLFW.glfwGetCursorPos(client.getWindow().handle(), x, y);
                return new double[] {x.get(0), y.get(0)};
            }
        }

        private static boolean atPosition(double[] actual, int x, int y) {
            return Math.abs(actual[0] - x) <= 2 && Math.abs(actual[1] - y) <= 2;
        }

        void prepareWorldExit() {
            int[] box = windowBox();
            captureAt(box[0] + 90, box[1] + 70);
            context.runOnClient(client -> check(HomeScreen.session() && !WorldCapture.ownsCapture(),
                    "World exit needs a Minecraft capture in the session without a helper"));
            leaveAtNormal("world exit");
        }

        void leaveAtNormal(String label) {
            context.runOnClient(client -> {
                long handle = client.getWindow().handle();
                arm("normal", () -> {
                    X11.checkFocus(handle, Focus.BACK, label + " before NORMAL");
                    X11.focus(handle, Focus.AWAY);
                });
            });
        }

        private static void arm(String point, Runnable run) {
            check(seamRun == null, "Previous release never reached " + seamName);
            seamName = point;
            seamRun = run;
        }

        void escDuringHandoff(boolean race) {
            var previous = context.computeOnClient(client -> {
                long handle = client.getWindow().handle();
                if (race) {
                    arm("queued", () -> {
                        X11.checkFocus(handle, Focus.ROOT, "Escape before queueing");
                        X11.focus(handle, Focus.BACK);
                    });
                } else {
                    arm("normal", () -> {
                        X11.checkFocus(handle, Focus.BACK, "Escape before NORMAL");
                        X11.focus(handle, Focus.ROOT);
                    });
                }
                var keyboard = (KeyboardTestAccess) (Object) client.keyboardHandler;
                return GLFW.glfwSetKeyCallback(handle, (window, key, scancode, action, mods) -> {
                    if (key == GLFW.GLFW_KEY_ESCAPE && action == GLFW.GLFW_PRESS) {
                        check(captured(client), "Escape did not arrive while captured");
                        if (race) {
                            // The key reached Minecraft before X focus left, and focus returns just before queuing.
                            X11.focus(window, Focus.ROOT);
                            check(!xFocused(client), "Escape did not run during an X focus handoff");
                        }
                        keyboard.aresos$nativeKey(window, key, scancode, action, mods);
                        check(client.gui.screen() instanceof AresOsMenuScreen, "Escape did not open the AresOS menu inline");
                        check(!client.mouseHandler.isMouseGrabbed() && cursorMode(client) == GLFW.GLFW_CURSOR_DISABLED,
                                "Native release ran inside the GLFW key callback");
                    } else {
                        keyboard.aresos$nativeKey(window, key, scancode, action, mods);
                    }
                });
            });
            try {
                input("key esc");
                context.waitFor(client -> client.gui.screen() instanceof AresOsMenuScreen && released(client)
                        && WorldCapture.settled());
                context.runOnClient(client -> check(seamRun == null, "Escape never reached its release seam"));
            } finally {
                context.runOnClient(client -> {
                    seamRun = null;
                    GLFW.glfwSetKeyCallback(client.getWindow().handle(), previous).free();
                });
            }
        }

        String rigFile(String name) { return repo.resolve("reviews/328-look-around/rig").resolve(name).toString(); }

        static int[] realSize(long window) {
            try (var stack = org.lwjgl.system.MemoryStack.stackPush()) {
                var width = stack.mallocInt(1); var height = stack.mallocInt(1);
                GLFW.glfwGetWindowSize(window, width, height);
                return new int[]{width.get(0), height.get(0)};
            }
        }

        /** The world window's position and size in compositor coordinates. */
        int[] windowBox() {
            return context.computeOnClient(client -> {
                try (var stack = org.lwjgl.system.MemoryStack.stackPush()) {
                    var x = stack.mallocInt(1); var y = stack.mallocInt(1);
                    GLFW.glfwGetWindowPos(client.getWindow().handle(), x, y);
                    int[] size = realSize(client.getWindow().handle());
                    return new int[]{x.get(0), y.get(0), size[0], size[1]};
                }
            });
        }

        void input(String command) {
            try (var channel = SocketChannel.open(StandardProtocolFamily.UNIX)) {
                channel.connect(UnixDomainSocketAddress.of(root.resolve("vinput.sock")));
                var out = Channels.newWriter(channel, StandardCharsets.UTF_8);
                out.write(command + "\n");
                out.flush();
                String reply = new BufferedReader(Channels.newReader(channel, StandardCharsets.UTF_8)).readLine();
                check("done".equals(reply), "Virtual input failed: " + command + " -> " + reply);
            } catch (IOException error) { throw new UncheckedIOException(error); }
        }

        String probe() {
            try { return Files.exists(root.resolve("probe.json")) ? Files.readString(root.resolve("probe.json")) : ""; }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }

        long count(String key) {
            var matcher = java.util.regex.Pattern.compile("\"" + key + "\": (\\d+)").matcher(probe());
            return matcher.find() ? Long.parseLong(matcher.group(1)) : -1;
        }

        long[] counts() {
            return new long[]{count("enter"), count("motion"), count("button"), count("axis")};
        }

        void tool(String action, String app) {
            String output = command("python3", repo.resolve("reviews/40-real-home/rig/tl.py").toString(),
                    root.toString(), action, app);
            if (action.equals("activate")) check(output.lines().anyMatch(line -> line.contains("'" + app + "'")
                    && line.contains("activated")), "Did not take the focus: " + output);
            context.waitTicks(3);
        }

        String command(String... args) {
            try {
                var process = new ProcessBuilder(args).redirectErrorStream(true).start();
                String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                check(process.waitFor() == 0, "Rig command failed: " + output);
                return output;
            } catch (IOException error) { throw new UncheckedIOException(error); }
            catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new RuntimeException(error); }
        }

        void await(java.util.function.BooleanSupplier condition, String what) {
            long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
            while (!condition.getAsBoolean()) {
                check(System.nanoTime() < deadline, "Timed out waiting for " + what);
                try { Thread.sleep(50); } catch (InterruptedException error) { Thread.currentThread().interrupt(); return; }
            }
        }

        @Override public void close() {
            if (installed) context.runOnClient(client -> {
                NativeFocusTestPlugin.nativeFocus(false);
                long handle = client.getWindow().handle();
                var move = GLFW.glfwSetCursorPosCallback(handle, previousMove);
                var button = GLFW.glfwSetMouseButtonCallback(handle, previousButton);
                var scroll = GLFW.glfwSetScrollCallback(handle, previousScroll);
                var focus = GLFW.glfwSetWindowFocusCallback(handle, previousFocus);
                if (move != null) move.free();
                if (button != null) button.free();
                if (scroll != null) scroll.free();
                if (focus != null) focus.free();
            });
            if (probe != null) probe.destroy();
            if (sideWindow != null) sideWindow.destroy();
            if (vinput != null) vinput.destroy();
        }
    }
}
