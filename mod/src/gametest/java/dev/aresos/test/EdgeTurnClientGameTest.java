package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.EdgeLook;
import dev.aresos.client.HomePointer;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.LookSetting;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldCapture;
import dev.aresos.config.LookMode;
import dev.aresos.focus.EdgeTurn;
import dev.aresos.item.AppItems;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.WorldKeepsPointerClientGameTest.HelperProcess;
import dev.aresos.test.WorldKeepsPointerClientGameTest.Rig;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.lwjgl.glfw.GLFW;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;

import static dev.aresos.test.WorldKeepsPointerClientGameTest.mouse;
import static dev.aresos.test.WorldKeepsPointerClientGameTest.released;

/**
 * Package 328c: prototype B, "edge turning" ({@code look = edge}). Through the game's callbacks: the world never takes
 * the mouse; the cursor at the left, right and top edges turns the view, except where another output touches the edge
 * or the pointer has left the world; the arrow keys turn and Q and E stay vanilla's; a click acts on what the crosshair
 * aims at without a capture; nothing turns or acts while an app is in front. With {@code client-test.sh --session},
 * also the real cursor under Xwayland and labwc (package 328a's rig): at the left edge the view turns left, at the
 * edge beside the second output it does not turn and the cursor crosses. Package 343 also checks up and down tilt
 * with the cursor parked on the top edge, and uses unnumbered screenshots to keep the suite's numbering.
 */
public final class EdgeTurnClientGameTest implements FabricClientGameTest {
    private static final int LEFT = GLFW.GLFW_MOUSE_BUTTON_LEFT, RIGHT = GLFW.GLFW_MOUSE_BUTTON_RIGHT;
    /** How long a check lets the view turn (or not), in real time: the turning follows the clock. */
    private static final long SETTLE_MS = 400;
    // What EdgeClickTestMixin saw Minecraft do. Client thread only.
    public static int attacks, uses;
    public static boolean attackHeld;

    @Override public void runTest(ClientGameTestContext context) {
        var previousShell = AresOs.shell();
        Path sockets = null;
        try {
            sockets = Files.createDirectories(Path.of("p328c"));
            try (var helper = new HelperProcess(sockets);
                 var shell = new ShellClient(sockets.resolve("s.sock"), FakeHelper.INSTANCE, FakeHelper.NONCE,
                         FakeHelper.fast());
                 var rig = new Rig(context)) {
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setShell(shell);
                    HomeScreen.forTests(true, null);
                    LookSetting.forTests(LookMode.EDGE);
                });
                shell.start();
                shell.awaitApps(Duration.ofSeconds(10));
                context.runOnClient(client -> ShellFocusClient.register(shell));
                try (var world = context.worldBuilder().create()) {
                    world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
                    context.waitFor(HomeScreen::active);
                    callbacks(context, helper);
                    if (rig.enabled) nativeEdges(context, helper, rig);
                    else AresOs.LOGGER.info("328c: no --session, so the native edge-turning checks did not run");
                }
                // Its listeners reach Minecraft, which only the client thread may do.
                context.runOnClient(client -> shell.close());
            }
            AresOs.LOGGER.info("328c edge-turning checks passed");
        } catch (IOException error) { throw new UncheckedIOException(error); }
        finally {
            context.getInput().releaseKey(EdgeTurn.LEFT_ARROW);
            context.getInput().releaseKey(EdgeTurn.RIGHT_ARROW);
            context.getInput().releaseKey(EdgeTurn.UP_ARROW);
            context.getInput().releaseKey(EdgeTurn.DOWN_ARROW);
            context.runOnClient(client -> {
                client.mouseHandler.releaseMouse();
                KeyMapping.releaseAll();
                HomeScreen.forTests(null, null);
                AppsTestAccess.aresos$setShell(previousShell);
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
            if (sockets != null) try { Files.deleteIfExists(sockets.resolve("s.sock")); Files.deleteIfExists(sockets); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    /** Prototype B through the game's own callbacks (Fabric's test window has no real cursor). */
    private static void callbacks(ClientGameTestContext context, HelperProcess helper) {
        helper.focus(true);
        context.waitTicks(4);
        int[] size = context.computeOnClient(client ->
                new int[] {client.getWindow().getScreenWidth(), client.getWindow().getScreenHeight()});
        int w = size[0], h = size[1];
        context.runOnClient(client -> {
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            // The session's layout, in Minecraft's screen units: the world's output, and a second one right of it.
            var world = new EdgeTurn.Box(0, 0, w, h);
            EdgeLook.layoutForTests(world, List.of(world, new EdgeTurn.Box(w, 0, w, h)));
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client),
                    "The world holds the mouse with look = edge");
            // Vanilla's grab when a screen closes, the helper's and GLFW's regrabs: all of them call grabMouse.
            client.gui.setScreen(null);
            client.mouseHandler.grabMouse();
            check(!client.mouseHandler.isMouseGrabbed(), "A grab took the mouse with look = edge");

            // The arrows are free in the home: no key of vanilla, Fabric API or AresOS is bound to them by default.
            var arrows = List.of("key.keyboard.left", "key.keyboard.right", "key.keyboard.up", "key.keyboard.down");
            for (var key : client.options.keyMappings) {
                String bound = key.saveString();
                check(!arrows.contains(bound), key.getName() + " is bound to " + bound + ", which edge turning uses");
            }
            check(client.options.keyDrop.saveString().equals("key.keyboard.q")
                    && client.options.keyInventory.saveString().equals("key.keyboard.e"), "Q and E are not drop and inventory");
            client.player.setXRot(30);
        });

        // In the middle nothing turns.
        moveTo(context, w / 2.0, h / 2.0);
        checkStill(context, "the cursor in the middle");

        // The left edge turns left, the top edge looks up.
        moveTo(context, 1, h / 2.0);
        float[] before = view(context);
        long start = System.nanoTime();
        holdFor(context, SETTLE_MS);
        float[] after = view(context);
        double seconds = (System.nanoTime() - start) / 1e9;
        float turned = after[0] - before[0];
        check(turned < -1 && turned >= -EdgeTurn.EDGE_TURN_DEG_PER_S * (seconds + EdgeTurn.LONGEST_FRAME_S)
                && after[1] == before[1], "The left edge turned the view " + turned + " degrees in " + seconds + " s");
        moveTo(context, w / 2.0, 1);
        before = view(context);
        holdFor(context, SETTLE_MS);
        after = view(context);
        check(after[1] < before[1] - 1 && after[0] == before[0],
                "The top edge did not look up: " + before[1] + " -> " + after[1]);

        // The right edge touches the second output: it lets the cursor through and does not turn.
        moveTo(context, w - 1, h / 2.0);
        checkStill(context, "the cursor at the edge beside the second output");
        // Without the second output it turns right.
        context.runOnClient(client -> EdgeLook.layoutForTests(new EdgeTurn.Box(0, 0, w, h),
                List.of(new EdgeTurn.Box(0, 0, w, h))));
        before = view(context);
        holdFor(context, SETTLE_MS);
        after = view(context);
        check(after[0] > before[0] + 1, "The right edge without a neighbour did not turn right: " + before[0] + " -> " + after[0]);
        // A second output beside only the lower half: the upper half turns, the lower lets through.
        context.runOnClient(client -> EdgeLook.layoutForTests(new EdgeTurn.Box(0, 0, w, h),
                List.of(new EdgeTurn.Box(0, 0, w, h), new EdgeTurn.Box(w, h / 2, w, h))));
        moveTo(context, w - 1, h * 3 / 4.0);
        checkStill(context, "the cursor where the second output touches half the edge");
        moveTo(context, w - 1, h / 4.0);
        before = view(context);
        holdFor(context, SETTLE_MS);
        after = view(context);
        check(after[0] > before[0] + 1, "The half of the edge without a neighbour did not turn: " + before[0] + " -> " + after[0]);

        // The pointer left the world (onto the other output or an app): its last position at the edge turns nothing.
        moveTo(context, 1, h / 2.0);
        context.runOnClient(client -> WorldCapture.forTests(Boolean.FALSE, false));
        checkStill(context, "the pointer that left the world at the left edge");
        context.runOnClient(client -> WorldCapture.forTests(Boolean.TRUE, false));

        // The arrow keys turn at the top speed, and only while held.
        moveTo(context, w / 2.0, h / 2.0);
        context.getInput().holdKey(EdgeTurn.RIGHT_ARROW);
        before = view(context);
        holdFor(context, SETTLE_MS);
        after = view(context);
        context.getInput().releaseKey(EdgeTurn.RIGHT_ARROW);
        check(after[0] > before[0] + 1, "The right arrow did not turn right: " + before[0] + " -> " + after[0]);
        context.getInput().holdKey(EdgeTurn.LEFT_ARROW);
        before = view(context);
        holdFor(context, SETTLE_MS);
        after = view(context);
        context.getInput().releaseKey(EdgeTurn.LEFT_ARROW);
        check(after[0] < before[0] - 1, "The left arrow did not turn left: " + before[0] + " -> " + after[0]);
        checkStill(context, "the arrows released");
        arrowTilt(context, w, h);

        // Q drops and E opens the inventory as in vanilla. Nothing turns under a screen, and closing it takes no mouse.
        context.runOnClient(client -> client.player.getInventory().setItem(
                client.player.getInventory().getSelectedSlot(), new ItemStack(Items.STICK, 2)));
        context.getInput().pressKey(GLFW.GLFW_KEY_Q);
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(client.player.getInventory().getSelectedItem().getCount() < 2, "Q did not drop with look = edge");
            client.player.getInventory().setItem(client.player.getInventory().getSelectedSlot(), ItemStack.EMPTY);
        });
        context.getInput().pressKey(GLFW.GLFW_KEY_E);
        context.waitFor(client -> client.gui.screen() != null);
        moveTo(context, 1, h / 2.0);
        context.getInput().holdKey(EdgeTurn.LEFT_ARROW);
        context.getInput().holdKey(EdgeTurn.DOWN_ARROW);
        checkStill(context, "the inventory open with the cursor at the edge and Left and Down held");
        context.getInput().releaseKey(EdgeTurn.LEFT_ARROW);
        context.getInput().releaseKey(EdgeTurn.DOWN_ARROW);
        context.runOnClient(client -> {
            client.gui.setScreen(null);
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client), "Closing the inventory took the mouse");
        });

        // A click on the world acts on what the crosshair aims at, and never captures. A held attack stays held.
        moveTo(context, w / 2.0, h / 3.0);
        int[] counts = context.computeOnClient(client -> new int[] {attacks, uses});
        context.runOnClient(client -> button(client, LEFT, GLFW.GLFW_PRESS));
        context.waitTicks(3);
        context.runOnClient(client -> {
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client), "A click with look = edge captured");
            check(client.options.keyAttack.isDown() && client.mouseHandler.isLeftPressed(), "The press did not reach Minecraft");
            check(attacks > counts[0], "The click did not attack");
            check(attackHeld, "A held attack does not count without the capture");
            button(client, LEFT, GLFW.GLFW_RELEASE);
            check(!client.options.keyAttack.isDown(), "The release did not reach Minecraft");
            button(client, RIGHT, GLFW.GLFW_PRESS);
            button(client, RIGHT, GLFW.GLFW_RELEASE);
        });
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(uses > counts[1], "The right click did not use");
            check(!attackHeld && !client.mouseHandler.isMouseGrabbed(), "The attack stayed held, or the use captured");
        });

        // Package 56's taskbar stays first: a primary click on an app slot goes to the app, never to an attack.
        int attacksBefore = context.computeOnClient(client -> {
            client.player.getInventory().setItem(0, appStack());
            pointAtSlot(client, 0);
            check(HomePointer.hoveredSlot(client) == 0, "The free pointer does not reach the app slot");
            button(client, LEFT, GLFW.GLFW_PRESS);
            check(!client.options.keyAttack.isDown(), "A click on an app slot reached Minecraft's attack");
            button(client, LEFT, GLFW.GLFW_RELEASE);
            return attacks;
        });
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(attacks == attacksBefore && !client.mouseHandler.isMouseGrabbed(), "A click on an app slot attacked or captured");
            client.player.getInventory().setItem(0, ItemStack.EMPTY);
        });

        // Movement keys walk as in classic, and take no mouse.
        context.getInput().holdKey(options -> options.keyUp);
        context.waitTicks(2);
        context.runOnClient(client -> check(client.options.keyUp.isDown() && !client.mouseHandler.isMouseGrabbed(),
                "W did not walk, or it took the mouse"));
        context.getInput().releaseKey(options -> options.keyUp);

        // While an app is in front the world ignores the mouse and the keys turn nothing; its press only brings it back.
        helper.focus(false);
        context.waitFor(HomeScreen::ignoresMouse);
        moveTo(context, 1, h / 2.0);
        context.getInput().holdKey(EdgeTurn.RIGHT_ARROW);
        checkStill(context, "an app in front with the cursor at the edge and an arrow held");
        context.getInput().releaseKey(EdgeTurn.RIGHT_ARROW);
        moveTo(context, w / 2.0, h / 3.0);
        int attacksBehind = context.computeOnClient(client -> attacks);
        context.runOnClient(client -> {
            button(client, LEFT, GLFW.GLFW_PRESS);
            check(!client.options.keyAttack.isDown() && !client.mouseHandler.isMouseGrabbed(),
                    "The press that brings the world back attacked or captured");
            button(client, LEFT, GLFW.GLFW_RELEASE);
            check(!HomeScreen.ignoresMouse(client), "The press did not bring the world to the front");
        });
        context.waitTicks(2);
        context.runOnClient(client -> check(attacks == attacksBehind, "The press behind an app attacked"));
        helper.focus(true);
        context.waitTicks(6);
        context.runOnClient(client -> check(!client.mouseHandler.isMouseGrabbed() && !HomeScreen.ignoresMouse(client),
                "The helper's return to the world took the mouse or left it ignored"));
        AresOs.LOGGER.info("328c: edges, pass-through, leave, arrows, Q and E, clicks and an app in front passed");
    }

    private static void arrowTilt(ClientGameTestContext context, int width, int height) {
        var input = context.getInput();
        double middle = width / 2.0;
        context.runOnClient(client -> client.player.setXRot(0));
        moveTo(context, middle, 0);
        context.waitFor(client -> client.player.getXRot() < -15);

        // At the topmost pixel, adding the opposite arrow to the band would leave the view stuck looking up.
        input.holdKey(EdgeTurn.DOWN_ARROW);
        context.waitFor(client -> client.player.getXRot() == 90);
        checkStill(context, "Down held at the lower pitch limit with the cursor on the top edge");
        tiltScreenshot(context, "343-down-at-top-edge");
        input.releaseKey(EdgeTurn.DOWN_ARROW);

        input.holdKey(EdgeTurn.UP_ARROW);
        context.waitFor(client -> client.player.getXRot() < -15);
        moveTo(context, middle, height / 2.0);
        context.runOnClient(client -> client.player.setXRot(-60));
        context.waitFor(client -> client.player.getXRot() == -90);
        checkStill(context, "Up held at the upper pitch limit away from the bands");
        tiltScreenshot(context, "343-up-at-upper-limit");

        input.holdKey(EdgeTurn.DOWN_ARROW);
        context.runOnClient(client -> client.player.setXRot(0));
        checkStill(context, "both tilt arrows held away from the bands");
        moveTo(context, middle, 0);
        context.waitFor(client -> client.player.getXRot() < -15);
        moveTo(context, middle, height / 2.0);
        input.releaseKey(EdgeTurn.UP_ARROW);
        input.releaseKey(EdgeTurn.DOWN_ARROW);
        context.runOnClient(client -> client.player.setXRot(0));
        AresOs.LOGGER.info("343: Down beat the top band, Up and Down reached the pitch limits, and both left the band in control");
    }

    private static void tiltScreenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).disableCounterPrefix()
                .withDestinationDir(Path.of(System.getProperty("aresos.edgeTiltReviewDir"))));
    }

    /** The real cursor: the left edge turns, the edge beside the second output lets it through, and it never captures. */
    private static void nativeEdges(ClientGameTestContext context, HelperProcess helper, Rig rig) {
        context.runOnClient(client -> {
            client.mouseHandler.releaseMouse();
            // The real layout from here on, and GLFW's own hover test.
            LookSetting.forTests(LookMode.EDGE);
            WorldCapture.forTests(null, true);
            client.player.setXRot(0);
        });
        rig.start();
        rig.tool("max", "aresos-desktop");
        rig.tool("activate", "aresos-desktop");
        helper.focus(true);
        context.waitTicks(4);
        rig.clean("328c start");
        int[] box = rig.windowBox();
        check(box[0] + box[2] == rig.sideOutputX, "The world's window does not end where the second output starts: "
                + java.util.Arrays.toString(box) + ", second output at " + rig.sideOutputX);

        // The left edge turns the view left, and the cursor stays a free pointer where it rests.
        rig.moveTo(box, 2, box[3] / 2, "328c left edge");
        float[] before = view(context);
        holdFor(context, SETTLE_MS);
        float[] after = view(context);
        float turned = after[0] - before[0];
        check(turned < -1, "The left edge did not turn the view left (turned " + turned + ")");
        context.runOnClient(client -> check(released(client) && WorldCapture.settled() && !WorldCapture.ownsCapture(),
                "Edge turning captured the pointer"));
        rig.checkPosition(2, box[3] / 2, "328c: the cursor at the left edge");

        // The edge beside the second output does not turn, and the cursor crosses it.
        rig.moveTo(box, box[2] - 2, box[3] / 2, "328c right edge");
        checkStill(context, "the real cursor at the edge beside the second output");
        rig.moveOffWorld(box, "328c: the cursor crosses to the second output");
        checkStill(context, "the real cursor on the second output");

        // Its leave event stops the turning: from the top band, where it turns up, onto the second output.
        context.runOnClient(client -> client.player.setXRot(60));
        rig.moveTo(box, box[2] - 10, 4, "328c top band beside the second output");
        before = view(context);
        holdFor(context, SETTLE_MS / 2);
        after = view(context);
        check(after[1] < before[1] - 1 && after[0] == before[0],
                "The top band did not look up, or the shared right edge turned: " + java.util.Arrays.toString(before)
                        + " -> " + java.util.Arrays.toString(after));
        rig.moveOffWorld(box, "328c: the cursor leaves the top band for the second output");
        checkStill(context, "the real cursor after it left the world from the top band");

        // A click acts without a capture: the pointer stays where it was, free.
        rig.moveTo(box, 640, 300, "328c click");
        rig.input("button left down");
        context.waitFor(client -> client.options.keyAttack.isDown());
        context.runOnClient(client -> check(released(client) && !WorldCapture.ownsCapture(),
                "A click on the world captured with look = edge"));
        rig.input("button left up");
        context.waitFor(client -> !client.options.keyAttack.isDown());
        rig.checkPosition(640, 300, "328c: the cursor after a click");
        rig.clean("328c edge turning");
        AresOs.LOGGER.info("328c native: left edge turned {} degrees; the edge beside output 2 let the cursor through", turned);
    }

    private static ItemStack appStack() {
        var stack = new ItemStack(AppItems.APP);
        stack.set(AppItems.APP_ID, "pkg328c-not-installed");
        return stack;
    }

    private static void pointAtSlot(Minecraft client, int slot) {
        var w = client.getWindow();
        double scale = (double) w.getScreenWidth() / w.getGuiScaledWidth();
        mouse(client).aresos$onMove(w.handle(), (w.getGuiScaledWidth() / 2 - 80 + slot * 20) * scale,
                (w.getGuiScaledHeight() - 11) * (double) w.getScreenHeight() / w.getGuiScaledHeight());
    }

    private static void moveTo(ClientGameTestContext context, double x, double y) {
        context.runOnClient(client -> mouse(client).aresos$onMove(client.getWindow().handle(), x, y));
        context.waitTicks(2);
    }

    /** Yaw and pitch. */
    private static float[] view(ClientGameTestContext context) {
        return context.computeOnClient(client -> new float[] {client.player.getYRot(), client.player.getXRot()});
    }

    private static void checkStill(ClientGameTestContext context, String what) {
        float[] before = view(context);
        holdFor(context, SETTLE_MS);
        float[] after = view(context);
        check(before[0] == after[0] && before[1] == after[1], "The view turned with " + what + ": "
                + java.util.Arrays.toString(before) + " -> " + java.util.Arrays.toString(after));
    }

    private static void button(Minecraft client, int button, int action) {
        mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), action);
    }

    /** Fabric's ticks need not follow the clock; the turning does, so hold in real time. */
    private static void holdFor(ClientGameTestContext context, long ms) {
        long end = System.nanoTime() + ms * 1_000_000;
        while (System.nanoTime() < end) context.waitTick();
    }

    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
}
