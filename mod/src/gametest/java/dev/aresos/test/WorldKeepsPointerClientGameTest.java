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
import net.minecraft.client.input.MouseButtonInfo;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWNativeX11;
import org.lwjgl.system.APIUtil;
import org.lwjgl.system.JNI;

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
import java.util.Map;

/**
 * Package 328a, last in the suite: the world keeps the pointer while it steers the camera. Every run checks the capture
 * rule through the game's own callbacks. With {@code client-test.sh --session} it also captures for real (Fabric
 * switches Minecraft's GLFW call off; {@link WorldCapture#forTests} puts the same calls back for this test), with the
 * rig's inert probe app over the window's centre and the rig's virtual pointer, and the probe must count nothing.
 */
public final class WorldKeepsPointerClientGameTest implements FabricClientGameTest {
    private static Runnable raceFocusOut;

    public static void beforeSyntheticFocusOut() {
        if (raceFocusOut == null) return;
        var race = raceFocusOut;
        raceFocusOut = null;
        race.run();
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
                    if (rig.enabled) nativeCapture(context, helper, shell, rig);
                    else AresOs.LOGGER.info("328a: no --session, so the native capture checks did not run");
                }
                // Its listeners reach Minecraft, which only the client thread may do.
                context.runOnClient(client -> shell.close());
            }
            AresOs.LOGGER.info("328a world-keeps-pointer checks passed");
        } catch (IOException error) { throw new UncheckedIOException(error); }
        finally {
            context.runOnClient(client -> {
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
        context.runOnClient(client -> X11.focus(client.getWindow().handle(), true));
        rig.input("abs " + cx + " " + cy);
        rig.input("abs " + (cx + 10) + " " + (cy + 10));
        context.waitTicks(3);
        check(rig.probe().contains("\"pointer_inside\": true"), "The released pointer does not reach the probe: "
                + rig.probe() + " grabbed=" + context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed())
                + " mode=" + Integer.toHexString(context.computeOnClient(client ->
                        GLFW.glfwGetInputMode(client.getWindow().handle(), GLFW.GLFW_CURSOR))));
        // Closing the menu with the pointer on the probe: the safe fallback keeps the pointer free.
        context.runOnClient(client -> client.gui.setScreen(null));
        context.waitTicks(3);
        check(!context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()),
                "Closing the menu took the mouse with the pointer on the probe");

        // Queue a real FocusIn just before the synthetic FocusOut. It must leave Minecraft ready for the next click.
        rig.captureAt(box[0] + 60, box[1] + 60);
        rig.escDuringHandoff(true);
        check(context.computeOnClient(client -> client.isWindowActive() && xFocused(client)),
                "The synthetic FocusOut overwrote the real FocusIn");
        rig.input("abs " + cx + " " + cy);
        context.waitTicks(3);
        context.runOnClient(client -> client.gui.setScreen(null));
        check(context.computeOnClient(WorldKeepsPointerClientGameTest::released),
                "Closing the menu over the probe captured the pointer");
        rig.captureAt(box[0] + 60, box[1] + 60);
        AresOs.LOGGER.info("328a: real Escape released after its GLFW callback and a racing FocusIn allowed recapture");

        // SIGKILL the fake helper while the world stays focused and no screen opens to release the capture for it.
        context.runOnClient(client -> {
            check(xFocused(client) && captured(client), "The game was not focused and captured before helper death");
            client.options.keyUp.setDown(true);
        });
        helper.kill();
        context.waitFor(client -> shell.status().state() != ShellClient.State.CONNECTED && released(client));
        context.runOnClient(client -> {
            check(!HomeScreen.active(client) && client.gui.screen() == null && xFocused(client),
                    "The connected-world gate, a menu or lost focus interfered with helper-loss cleanup");
            check(!client.options.keyUp.isDown(), "Helper death left walking held");
            long handle = client.getWindow().handle();
            X11.checkCursorShown(handle);
            double[] x = new double[1], y = new double[1];
            GLFW.glfwGetCursorPos(handle, x, y);
            check(Math.abs(x[0] - 60) <= 2 && Math.abs(y[0] - 60) <= 2,
                    "Helper death did not restore the pointer to its starting position: " + x[0] + ", " + y[0]);
        });
        check(rig.command("bash", rig.rigFile("state.sh"), rig.root.toString()).contains("X pointer grab: free"),
                "An X client still holds the pointer after helper death");
        rig.input("abs " + cx + " " + cy);
        rig.await(() -> rig.probe().contains("\"pointer_inside\": true"), "free pointer on the probe after helper death");
        AresOs.LOGGER.info("328a: SIGKILL of the fake helper showed the cursor, restored its position and freed the X grab");
    }

    private static boolean captured(Minecraft client) {
        return client.mouseHandler.isMouseGrabbed() && cursorMode(client) == GLFW.GLFW_CURSOR_DISABLED;
    }

    private static boolean released(Minecraft client) {
        return !client.mouseHandler.isMouseGrabbed() && cursorMode(client) == GLFW.GLFW_CURSOR_NORMAL;
    }

    private static int cursorMode(Minecraft client) {
        return GLFW.glfwGetInputMode(client.getWindow().handle(), GLFW.GLFW_CURSOR);
    }

    private static boolean xFocused(Minecraft client) {
        return GLFW.glfwGetWindowAttrib(client.getWindow().handle(), GLFW.GLFW_FOCUSED) == GLFW.GLFW_TRUE;
    }

    private static MouseTestAccess mouse(Minecraft client) { return (MouseTestAccess)(Object)client.mouseHandler; }

    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }

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

        static void focus(long handle, boolean onGame) {
            long display = GLFWNativeX11.glfwGetX11Display();
            long target = onGame ? GLFWNativeX11.glfwGetX11Window(handle)
                    : JNI.invokePP(display, X11.getFunctionAddress("XDefaultRootWindow"));
            JNI.invokePPPI(display, target, 0 /* RevertToNone */, 0L /* CurrentTime */,
                    X11.getFunctionAddress("XSetInputFocus"));
            sync(display);
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
    private static final class Rig implements AutoCloseable {
        final boolean enabled = Boolean.getBoolean("aresos.pointerSession");
        final ClientGameTestContext context;
        Path root, repo;
        Process probe, vinput;
        org.lwjgl.glfw.GLFWCursorPosCallback previousMove;
        org.lwjgl.glfw.GLFWMouseButtonCallback previousButton;
        org.lwjgl.glfw.GLFWScrollCallback previousScroll;
        boolean installed;

        Rig(ClientGameTestContext context) { this.context = context; }

        void start() {
            check(!System.getenv().getOrDefault("WAYLAND_DISPLAY", "wayland-0").equals("wayland-0")
                    && !System.getenv().getOrDefault("DISPLAY", ":0").equals(":0"), "Refusing the owner's display");
            try {
                root = Files.createDirectories(Path.of("p328-rig").toAbsolutePath());
                repo = Path.of(System.getProperty("aresos.repoDir"));
                String[] layout = System.getenv().getOrDefault("ARESOS_POINTER_LAYOUT", "1280x720").split("x");
                Files.writeString(root.resolve("env"), "WAYLAND_DISPLAY=" + System.getenv("WAYLAND_DISPLAY")
                        + "\nDISPLAY=" + System.getenv("DISPLAY") + "\nLAYOUT_W=" + layout[0] + "\nLAYOUT_H=" + layout[1] + "\n");
                Files.deleteIfExists(root.resolve("vinput.sock"));
                Files.deleteIfExists(root.resolve("probe.json"));
                vinput = new ProcessBuilder("python3", "-I", rigFile("vinput.py"), root.toString())
                        .redirectErrorStream(true).redirectOutput(root.resolve("vinput.log").toFile()).start();
                await(() -> Files.exists(root.resolve("vinput.sock")), "the virtual input");
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
            input("abs " + x + " " + y);
            context.waitFor(WorldCapture::pointerOverWorld);
            input("click left");
            context.waitFor(WorldKeepsPointerClientGameTest::captured);
        }

        void escDuringHandoff(boolean race) {
            var previous = context.computeOnClient(client -> {
                long handle = client.getWindow().handle();
                if (race) raceFocusOut = () -> X11.focus(handle, true);
                var keyboard = (KeyboardTestAccess) (Object) client.keyboardHandler;
                return GLFW.glfwSetKeyCallback(handle, (window, key, scancode, action, mods) -> {
                    if (key == GLFW.GLFW_KEY_ESCAPE && action == GLFW.GLFW_PRESS) {
                        check(captured(client), "Escape did not arrive while captured");
                        // The key was already delivered to the game, but the X focus moves before it handles Escape.
                        X11.focus(window, false);
                        check(!xFocused(client), "Escape did not run during an X focus handoff");
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
                context.waitFor(client -> client.gui.screen() instanceof AresOsMenuScreen && released(client));
                context.runOnClient(client -> check(raceFocusOut == null, "The real FocusIn never raced the synthetic event"));
            } finally {
                context.runOnClient(client -> {
                    raceFocusOut = null;
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
                long handle = client.getWindow().handle();
                var move = GLFW.glfwSetCursorPosCallback(handle, previousMove);
                var button = GLFW.glfwSetMouseButtonCallback(handle, previousButton);
                var scroll = GLFW.glfwSetScrollCallback(handle, previousScroll);
                if (move != null) move.free();
                if (button != null) button.free();
                if (scroll != null) scroll.free();
            });
            if (probe != null) probe.destroy();
            if (vinput != null) vinput.destroy();
        }
    }
}
