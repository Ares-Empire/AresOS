package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.ClickToLook;
import dev.aresos.client.HomePointer;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldCapture;
import dev.aresos.config.LookMode;
import dev.aresos.focus.ClickLook;
import dev.aresos.item.AppItems;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.WorldKeepsPointerClientGameTest.HelperProcess;
import dev.aresos.test.WorldKeepsPointerClientGameTest.Rig;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.KeyboardTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.world.item.ItemStack;
import org.lwjgl.glfw.GLFW;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.function.Consumer;
import java.util.function.Predicate;

import static dev.aresos.test.WorldKeepsPointerClientGameTest.mouse;
import static dev.aresos.test.WorldKeepsPointerClientGameTest.released;

/**
 * Package 328b: prototype A, "click to look" ({@code look = click}). Through the game's callbacks: the free cursor, the
 * click and key starts, the stillness release, Esc, an app taking the focus and every regrab. With
 * {@code client-test.sh --session}, also the real capture under Xwayland and labwc (package 328a's rig): a click on open
 * world starts look mode, stillness ends it, the pointer reappears where the click was, and it then reaches the second
 * output. Last in the suite, so the screenshot numbering of the others stays.
 */
public final class ClickToLookClientGameTest implements FabricClientGameTest {
    private static final int LEFT = GLFW.GLFW_MOUSE_BUTTON_LEFT;

    @Override public void runTest(ClientGameTestContext context) {
        var previousShell = AresOs.shell();
        Path sockets = null;
        try {
            sockets = Files.createDirectories(Path.of("p328b"));
            try (var helper = new HelperProcess(sockets);
                 var shell = new ShellClient(sockets.resolve("s.sock"), FakeHelper.INSTANCE, FakeHelper.NONCE,
                         FakeHelper.fast());
                 var rig = new Rig(context)) {
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setShell(shell);
                    HomeScreen.forTests(true, null);
                    ClickToLook.forTests(LookMode.CLICK);
                });
                shell.start();
                shell.awaitApps(Duration.ofSeconds(10));
                context.runOnClient(client -> ShellFocusClient.register(shell));
                try (var world = context.worldBuilder().create()) {
                    world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
                    context.waitFor(HomeScreen::active);
                    callbacks(context, helper);
                    if (rig.enabled) nativeLook(context, helper, rig);
                    else AresOs.LOGGER.info("328b: no --session, so the native click-to-look checks did not run");
                }
                // Its listeners reach Minecraft, which only the client thread may do.
                context.runOnClient(client -> shell.close());
            }
            AresOs.LOGGER.info("328b click-to-look checks passed");
        } catch (IOException error) { throw new UncheckedIOException(error); }
        finally {
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

    /** Prototype A through the game's own callbacks (Fabric's test window has no real cursor). */
    private static void callbacks(ClientGameTestContext context, HelperProcess helper) {
        helper.focus(true);
        context.waitTicks(4);
        context.runOnClient(client -> {
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client),
                    "The world holds the mouse with look = click");
            // Vanilla's grab when a screen closes, the helper's and GLFW's regrabs: all of them call grabMouse.
            client.gui.setScreen(null);
            client.mouseHandler.grabMouse();
            check(!client.mouseHandler.isMouseGrabbed(), "A grab that no click or key asked for took the mouse");

            // Package 56 stays first: a primary click on an app slot goes to the app and starts no look mode.
            client.player.getInventory().setItem(0, appStack());
            pointAtSlot(client, 0);
            check(HomePointer.hoveredSlot(client) == 0, "The free pointer does not reach the app slot");
            click(client, LEFT);
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client),
                    "A click on an app slot started look mode");
            client.player.getInventory().setItem(0, ItemStack.EMPTY);

            // A click on open world starts look mode and does nothing else.
            mouse(client).aresos$onMove(client.getWindow().handle(), 20, 20);
            button(client, LEFT, GLFW.GLFW_PRESS);
            check(client.mouseHandler.isMouseGrabbed() && !HomeScreen.freePointer(client),
                    "A click on open world did not start look mode");
            check(!client.mouseHandler.isLeftPressed() && !client.options.keyAttack.isDown(), "The starting click attacked");
            button(client, LEFT, GLFW.GLFW_RELEASE);
            check(!client.options.keyAttack.consumeClick(), "The starting click reached Minecraft's attack");
            // In look mode clicks act as in classic.
            button(client, LEFT, GLFW.GLFW_PRESS);
            check(client.mouseHandler.isLeftPressed() && client.options.keyAttack.isDown(),
                    "A click in look mode did not reach Minecraft");
            button(client, LEFT, GLFW.GLFW_RELEASE);
        });
        long clicked = System.nanoTime();
        waitReal(context, client -> !client.mouseHandler.isMouseGrabbed(), "stillness to end look mode");
        long stillMs = (System.nanoTime() - clicked) / 1_000_000;
        check(stillMs >= ClickLook.LOOK_RELEASE_MS - 100, "Look mode ended after only " + stillMs + " ms");
        context.runOnClient(client -> check(HomeScreen.freePointer(client), "The pointer is not free after look mode"));

        // Moving the mouse keeps look mode on; it ends once the mouse rests.
        context.runOnClient(client -> click(client, LEFT));
        int[] step = {0};
        holdFor(context, 2 * ClickLook.LOOK_RELEASE_MS, client ->
                mouse(client).aresos$onMove(client.getWindow().handle(), 20 + ++step[0] % 50, 20 + step[0] % 7));
        check(context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()),
                "Look mode ended while the mouse moved");
        waitReal(context, client -> !client.mouseHandler.isMouseGrabbed(), "stillness after motion");

        // A movement key starts look mode and walks; held, it keeps look mode on. Other keys start nothing.
        var keyboard = context.computeOnClient(client -> (KeyboardTestAccess)(Object) client.keyboardHandler);
        var w = new KeyEvent(GLFW.GLFW_KEY_W, 17, 0);
        context.runOnClient(client -> {
            check(client.options.keyUp.matches(w), "The test expects W to walk forward");
            var other = new KeyEvent(GLFW.GLFW_KEY_KP_0, 82, 0);
            keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_PRESS, other);
            keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_RELEASE, other);
            check(!client.mouseHandler.isMouseGrabbed(), "A key that does not move started look mode");
            keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_PRESS, w);
            check(client.mouseHandler.isMouseGrabbed() && client.options.keyUp.isDown(),
                    "W did not start look mode and walk");
        });
        holdFor(context, 2 * ClickLook.LOOK_RELEASE_MS, client -> { });
        check(context.computeOnClient(client -> client.mouseHandler.isMouseGrabbed()),
                "Look mode ended while W was held");
        context.runOnClient(client -> keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_RELEASE, w));
        long let = System.nanoTime();
        waitReal(context, client -> !client.mouseHandler.isMouseGrabbed(), "stillness after W");
        check((System.nanoTime() - let) / 1_000_000 >= ClickLook.LOOK_RELEASE_MS - 100, "Look mode ended too soon after W");

        // Esc ends look mode; closing the menu leaves the cursor free (vanilla's grab when a screen closes).
        context.runOnClient(client -> {
            click(client, LEFT);
            check(client.mouseHandler.isMouseGrabbed(), "A click did not start look mode before Esc");
            var esc = new KeyEvent(GLFW.GLFW_KEY_ESCAPE, 9, 0);
            keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_PRESS, esc);
            keyboard.aresos$keyPress(client.getWindow().handle(), GLFW.GLFW_RELEASE, esc);
            check(client.gui.screen() != null && !client.mouseHandler.isMouseGrabbed(), "Esc did not end look mode");
            client.gui.setScreen(null);
            check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client),
                    "Closing the menu took the mouse");
        });

        // An app taking the focus ends look mode; the helper's return leaves the cursor free.
        context.runOnClient(client -> click(client, LEFT));
        helper.focus(false);
        context.waitFor(client -> !client.mouseHandler.isMouseGrabbed());
        helper.focus(true);
        context.waitTicks(6);
        context.runOnClient(client -> check(!client.mouseHandler.isMouseGrabbed() && HomeScreen.freePointer(client),
                "The helper's return to the world took the mouse"));

        // GLFW's focus coming back does not take the mouse either.
        context.runOnClient(client -> ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(false));
        context.waitTicks(2);
        context.runOnClient(client -> ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true));
        context.waitTicks(2);
        context.runOnClient(client -> check(!client.mouseHandler.isMouseGrabbed(), "GLFW's focus regrab took the mouse"));

        // A click that reaches the game just before GLFW's focus still starts look mode once the focus follows.
        context.runOnClient(client -> {
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(false);
            click(client, LEFT);
            check(!client.mouseHandler.isMouseGrabbed(), "Minecraft captured without the window's focus");
            ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
        });
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(client.mouseHandler.isMouseGrabbed(), "The click before the focus did not start look mode");
            client.mouseHandler.releaseMouse();
        });
        AresOs.LOGGER.info("328b: click and key starts, stillness ({} ms), Esc, app focus and regrabs passed", stillMs);
    }

    /** The real capture: the click starts look mode, stillness lets go, and the cursor is a free pointer again. */
    private static void nativeLook(ClientGameTestContext context, HelperProcess helper, Rig rig) {
        context.runOnClient(client -> {
            client.mouseHandler.releaseMouse();
            WorldCapture.forTests(null, true);
        });
        rig.start();
        rig.tool("max", "aresos-desktop");
        rig.tool("activate", "aresos-desktop");
        helper.focus(true);
        context.waitTicks(4);
        int[] box = rig.windowBox();
        rig.moveTo(box, 60, 60, "328b free pointer");
        context.waitTicks(3);
        context.runOnClient(client -> {
            check(WorldCapture.pointerOverWorld(client), "GLFW does not see the free pointer on the world");
            check(released(client) && HomeScreen.freePointer(client), "The world took the pointer before a click");
        });

        // A click on open world starts look mode; the mouse steers the camera as in classic.
        float yaw = context.computeOnClient(client -> client.player.getYRot());
        rig.input("click left");
        context.waitFor(WorldKeepsPointerClientGameTest::captured);
        for (int move = 0; move < 20; move++) rig.input("rel 12 0");
        long lastMove = System.nanoTime();
        // A hitch longer than the stillness: the game is held between ticks while the moves wait in its queue. It must
        // read them before it judges the stillness (the second full run once let go here first).
        try { Thread.sleep(ClickLook.LOOK_RELEASE_MS + 200); }
        catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new RuntimeException(error); }
        context.waitTicks(2);
        float turned = context.computeOnClient(client -> client.player.getYRot()) - yaw;
        check(Math.abs(turned) > 1, "Look mode did not steer the camera (turned " + turned + ")");

        // Stillness ends it through 328a's release; the pointer reappears where the click was.
        waitReal(context, client -> released(client) && WorldCapture.settled(), "stillness to end the native look mode");
        long stillMs = (System.nanoTime() - lastMove) / 1_000_000;
        check(stillMs >= ClickLook.LOOK_RELEASE_MS - 100, "Native look mode ended after only " + stillMs + " ms");
        rig.checkPosition(60, 60, "328b: the pointer after look mode");
        // The cursor shows and moves freely over the world, no X client holds the pointer, and it reaches the other output.
        rig.clean("328b click look mode ended");
        rig.moveOffWorld(box, "328b: the cursor reaches the second output");
        AresOs.LOGGER.info("328b native: camera turned {} degrees; still {} ms; pointer back at the click, then on output 2",
                turned, stillMs);

        // A movement key starts look mode too; the pointer then reappears at the centre of the world's output.
        var previous = context.computeOnClient(client -> {
            var keyboard = (KeyboardTestAccess)(Object) client.keyboardHandler;
            return GLFW.glfwSetKeyCallback(client.getWindow().handle(), keyboard::aresos$nativeKey);
        });
        try {
            rig.moveTo(box, 200, 150, "328b key start");
            rig.input("key w");
            context.waitFor(WorldKeepsPointerClientGameTest::captured);
            waitReal(context, client -> released(client) && WorldCapture.settled(), "stillness after the key start");
            rig.checkPosition(box[2] / 2, box[3] / 2, "328b: the pointer after a key start");
        } finally {
            context.runOnClient(client -> {
                var installed = GLFW.glfwSetKeyCallback(client.getWindow().handle(), previous);
                if (installed != null) installed.free();
            });
        }
        rig.clean("328b key look mode ended");
        AresOs.LOGGER.info("328b native: a key start returned the pointer to the centre of the world's output");
    }

    private static ItemStack appStack() {
        var stack = new ItemStack(AppItems.APP);
        stack.set(AppItems.APP_ID, "pkg328b-not-installed");
        return stack;
    }

    private static void pointAtSlot(Minecraft client, int slot) {
        var w = client.getWindow();
        double scale = (double) w.getScreenWidth() / w.getGuiScaledWidth();
        mouse(client).aresos$onMove(w.handle(), (w.getGuiScaledWidth() / 2 - 80 + slot * 20) * scale,
                (w.getGuiScaledHeight() - 11) * (double) w.getScreenHeight() / w.getGuiScaledHeight());
    }

    private static void button(Minecraft client, int button, int action) {
        mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), action);
    }

    private static void click(Minecraft client, int button) {
        button(client, button, GLFW.GLFW_PRESS);
        button(client, button, GLFW.GLFW_RELEASE);
    }

    /** Fabric's ticks need not follow the clock; the release timer does, so wait in real time. */
    private static void waitReal(ClientGameTestContext context, Predicate<Minecraft> condition, String what) {
        long deadline = System.nanoTime() + Duration.ofSeconds(8).toNanos();
        while (!context.computeOnClient(condition::test)) {
            check(System.nanoTime() < deadline, "Timed out waiting for " + what);
            context.waitTick();
        }
    }

    private static void holdFor(ClientGameTestContext context, long ms, Consumer<Minecraft> eachTick) {
        long end = System.nanoTime() + ms * 1_000_000;
        while (System.nanoTime() < end) {
            context.runOnClient(eachTick::accept);
            context.waitTick();
        }
    }

    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
}
