package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.*;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.MouseTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import org.lwjgl.glfw.GLFW;

import java.io.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;

/** Last in the suite: callbacks cover the game rules; --session also drives real small windows on headless labwc. */
public final class FreePointerClientGameTest implements FabricClientGameTest {
    private static final AppDefinition NOTES = new AppDefinition("notepad", "Pointer Notes", List.of(),
            "minecraft:writable_book", true, "helper", null, null);
    private static final AppDefinition TERMINAL = new AppDefinition("terminal", "Pointer Terminal", List.of(),
            "minecraft:book", true, "helper", null, null);

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(new LinuxAppLauncher()));
        Path sockets = null;
        try {
            Path config = Files.createDirectories(Path.of("pointer-fixture")).resolve("apps.json").toAbsolutePath();
            AppsConfig.save(config, List.of(NOTES, TERMINAL));
            System.setProperty("aresos.appsConfig", config.toString());
            sockets = Files.createDirectories(Path.of("p56"));
            try (var helper = new FakeHelper(sockets); var shell = helper.client(FakeHelper.fast());
                 var nativeApps = new NativeApps(context)) {
                helper.launchState = "focused";
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setApps(List.of(NOTES, TERMINAL));
                    AppsTestAccess.aresos$setShell(shell);
                    AresOsClient.replaceLauncher(new LinuxAppLauncher(() -> shell));
                    HomeScreen.forTests(true, null);
                    ShellFocusClient.register(shell);
                });
                shell.start();
                shell.awaitApps(Duration.ofSeconds(10));
                try (var world = context.worldBuilder().create()) {
                    // The actual defect: a background event arrives before a desktop world is playable. Frames in
                    // between must not erase it, and setScreen(null) must not capture behind the focused app.
                    background(helper, "notepad");
                    context.waitTicks(4);
                    world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
                    context.waitFor(HomeScreen::freePointer);
                    context.runOnClient(client -> {
                        client.gui.setScreen(null);
                        client.mouseHandler.grabMouse();
                        check(!client.mouseHandler.isMouseGrabbed(), "A loading/screen-close path recaptured behind an app");
                    });
                    setupHotbar(context, world);
                    nativeApps.activate("notepad");
                    checkEdges(context, helper, nativeApps);
                    hotbar(context, world, helper, nativeApps);
                    lostRelease(context, helper);
                    gates(context, world, helper);
                    nativeApps.activate("desktop");
                    flight(context, world);
                    background(helper, "notepad"); context.waitTicks(2);
                    shell.close();
                    context.waitFor(client -> !HomeScreen.active(client));
                    context.runOnClient(client -> {
                        check(!HomeScreen.freePointer(client), "A disconnected helper kept pointer rules");
                        client.mouseHandler.grabMouse();
                        check(client.mouseHandler.isMouseGrabbed(), "Helper loss left capture blocked");
                    });
                }
            }
            AresOs.LOGGER.info("56 free-pointer checks passed: early focus and screen-close capture, all edges slow/fast, "
                    + "Alt+Tab and close, live unpaused world, hover/name screenshot, open_app and failure chat, both "
                    + "activation/click orders, lost mouse releases, empty/non-app/world entry without item use, vanilla gates and measured "
                    + "Live/Build/vanilla flight with/without sprint and unchanged FOV");
        } catch (IOException error) { throw new UncheckedIOException(error); }
        finally {
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            context.runOnClient(client -> {
                HomeScreen.forTests(null, null);
                AppsTestAccess.aresos$setApps(previousApps);
                AppsTestAccess.aresos$setShell(previousShell);
                AresOsClient.replaceLauncher(previousLauncher);
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
                AresOsClient.FOCUS_RETURN.reset();
            });
            if (sockets != null) try { Files.deleteIfExists(sockets.resolve("s.sock")); Files.deleteIfExists(sockets); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    private static void setupHotbar(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.getInventory().clearContent();
            player.getInventory().setItem(0, AppItems.create(NOTES));
            player.getInventory().setItem(3, AppItems.create(TERMINAL));
            player.getInventory().setItem(2, new ItemStack(Items.STONE, 8));
            player.inventoryMenu.broadcastChanges();
        });
        context.waitFor(client -> client.player.getInventory().getItem(3).is(AppItems.APP));
        context.runOnClient(client -> client.player.getInventory().setSelectedSlot(2));
    }

    private static void checkEdges(ClientGameTestContext context, FakeHelper helper, NativeApps nativeApps) {
        long before = context.computeOnClient(client -> client.level.getGameTime());
        float yaw = context.computeOnClient(client -> client.player.getYRot());
        float pitch = context.computeOnClient(client -> client.player.getXRot());
        int width = context.computeOnClient(client -> client.getWindow().getScreenWidth());
        int height = context.computeOnClient(client -> client.getWindow().getScreenHeight());
        for (boolean slow : new boolean[]{true, false}) for (int side = 0; side < 4; side++) {
            double dx = side == 0 ? -320 : side == 1 ? 320 : 0;
            double dy = side == 2 ? -220 : side == 3 ? 220 : 0;
            nativeApps.input("move 640 360");
            int steps = slow ? 16 : 1;
            for (int step = 1; step <= steps; step++) {
                double x = width / 2d + dx * step / steps, y = height / 2d + dy * step / steps;
                nativeApps.input("move " + (int)(640 + dx * step / steps) + " " + (int)(360 + dy * step / steps));
                context.runOnClient(client -> {
                    // GLFW can say focused behind a native Wayland app: exercise that exact game callback too.
                    ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
                    mouse(client).aresos$onMove(client.getWindow().handle(), x, y);
                    client.mouseHandler.handleAccumulatedMovement();
                    client.mouseHandler.grabMouse();
                    check(client.player.getYRot() == yaw && client.player.getXRot() == pitch, "Motion turned the background world");
                    check(client.gui.screen() == null && !client.isPaused(), "Motion opened a menu or paused the world");
                    check(!client.mouseHandler.isMouseGrabbed(), "Motion/capture attempt took the free pointer");
                    check(GLFW.glfwGetInputMode(client.getWindow().handle(), GLFW.GLFW_CURSOR) == GLFW.GLFW_CURSOR_NORMAL,
                            "The free pointer is not a normal system cursor");
                });
                context.waitTick();
            }
        }
        check(context.computeOnClient(client -> client.level.getGameTime()) > before, "The town stopped living");
        nativeApps.activate("terminal");
        background(helper, "terminal"); context.waitTicks(2);
        nativeApps.activate("notepad");
        nativeApps.altTab();
        background(helper, "terminal"); context.waitTicks(2);
        nativeApps.closeTerminal();
        nativeApps.expectActive("notepad");
        background(helper, "notepad"); context.waitTicks(2);
        context.runOnClient(client -> {
            mouse(client).aresos$onMove(client.getWindow().handle(), 20, 20);
            client.mouseHandler.handleAccumulatedMovement();
            check(client.player.getYRot() == yaw && client.player.getXRot() == pitch, "Switch/close let motion turn the view");
        });
    }

    private static void hotbar(ClientGameTestContext context, TestSingleplayerContext world, FakeHelper helper, NativeApps nativeApps) {
        nativeApps.pointAtSlot(3);
        context.waitTicks(2);
        context.runOnClient(client -> pointAtSlot(client, 3));
        String hoverState = context.computeOnClient(client -> "slot=" + HomePointer.hoveredSlot(client)
                + " free=" + HomeScreen.freePointer(client) + " x=" + client.mouseHandler.getScaledXPos(client.getWindow())
                + " y=" + client.mouseHandler.getScaledYPos(client.getWindow()) + " gui=" + client.getWindow().getGuiScaledWidth()
                + "x" + client.getWindow().getGuiScaledHeight() + " hidden=" + client.gui.hud.isHidden()
                + " stack=" + client.player.getInventory().getItem(3) + " screen=" + client.gui.screen());
        check(context.computeOnClient(client -> HomePointer.hoveredSlot(client)) == 3, "App slot did not highlight: " + hoverState);
        context.runOnClient(client -> {
            check(client.player.getInventory().getSelectedSlot() == 2, "Hover changed the selected slot");
            client.gui.hud.getChat().clearMessages(true);
            client.gui.hud.setOverlayMessage(net.minecraft.network.chat.Component.empty(), false);
            client.gui.toastManager().clear();
        });
        context.waitTicks(5);
        context.takeScreenshot(TestScreenshotOptions.of("56-taskbar-hover")
                .withDestinationDir(Path.of(System.getProperty("aresos.pointerReviewDir"))));
        nativeApps.screenshot();
        context.runOnClient(client -> {
            mouse(client).aresos$onScroll(client.getWindow().handle(), 0, -1);
            check(client.player.getInventory().getSelectedSlot() == 3, "The free pointer changed vanilla hotbar scrolling");
        });
        context.getInput().pressKey(com.mojang.blaze3d.platform.InputConstants.KEY_3);
        context.waitFor(client -> client.player.getInventory().getSelectedSlot() == 2);
        int opened = helper.launches.get();
        // The helper's activation arrives before the button callback.
        context.runOnClient(client -> {
            ShellFocusClient.apply(client, new ShellClient.Focus(true, "desktop_activated", null, false));
            click(client, GLFW.GLFW_MOUSE_BUTTON_LEFT);
            check(!client.mouseHandler.isMouseGrabbed(), "App click captured the world");
        });
        context.waitFor(client -> helper.launches.get() == opened + 1);
        check(helper.received("open_app").getLast().get("app_id").getAsString().equals("terminal"), "Wrong hotbar app opened");
        nativeApps.reopenTerminal(); nativeApps.activate("terminal"); background(helper, "terminal");
        context.waitTicks(3);
        // Reverse ordering: the callback first, a delayed foreground event second.
        context.runOnClient(client -> {
            pointAtSlot(client, 0); click(client, GLFW.GLFW_MOUSE_BUTTON_LEFT);
            ShellFocusClient.apply(client, new ShellClient.Focus(true, "desktop_activated", null, false));
        });
        context.waitFor(client -> helper.launches.get() == opened + 2);
        context.waitTicks(4);
        check(context.computeOnClient(HomeScreen::freePointer), "Delayed focus after an app click captured the pointer");
        nativeApps.activate("notepad"); background(helper, "notepad"); context.waitTicks(2);
        // A denied open follows the exact item launcher path and leaves the same persistent chat line.
        helper.entries = List.of(FakeHelper.entry("notepad", "Pointer Notes", "not_installed"), FakeHelper.entry("terminal", "Pointer Terminal", null));
        helper.override = request -> {
            if (request.get("op").getAsString().equals("open_app") && request.get("app_id").getAsString().equals("notepad")) {
                var reply = new com.google.gson.JsonObject(); reply.add("id", request.get("id")); reply.addProperty("ok", false);
                reply.addProperty("error", "not_installed"); reply.addProperty("message", "fixture missing"); return reply;
            }
            return null;
        };
        context.runOnClient(client -> { pointAtSlot(client, 0); click(client, GLFW.GLFW_MOUSE_BUTTON_LEFT); });
        context.waitFor(client -> ((ChatMessagesTestAccess)(Object)client.gui.hud.getChat()).aresos$messages().stream()
                .anyMatch(line -> line.content().getString().contains("Couldn't open Pointer Notes:")));
        context.runOnClient(client -> ShellFocusClient.apply(client,
                new ShellClient.Focus(true, "desktop_activated", null, false)));
        context.waitTicks(3);
        check(context.computeOnClient(HomeScreen::freePointer), "A delayed activation after a failed app click captured the pointer");
        helper.override = request -> null;
        if (nativeApps.enabled) {
            nativeApps.pointAtSlot(3);
            context.waitTicks(3);
            String nativeState = context.computeOnClient(client -> "slot=" + HomePointer.hoveredSlot(client)
                    + " free=" + HomeScreen.freePointer(client) + " xy=" + client.mouseHandler.getScaledXPos(client.getWindow())
                    + "," + client.mouseHandler.getScaledYPos(client.getWindow()) + " screen=" + client.getWindow().getScreenWidth()
                    + "x" + client.getWindow().getScreenHeight() + " app=" + client.player.getInventory().getItem(3));
            AresOs.LOGGER.info("56 native hover: {}", nativeState);
            context.waitFor(client -> HomePointer.hoveredSlot(client) == 3);
            nativeApps.input("click left");
            context.waitFor(client -> helper.launches.get() == opened + 3);
            check(context.computeOnClient(HomeScreen::freePointer), "Native app-slot click captured the pointer");
            nativeApps.activate("terminal"); background(helper, "terminal"); context.waitTicks(2);
        }
        for (int slot : new int[]{1, 2, -1}) {
            background(helper, "notepad"); context.waitTicks(2);
            context.runOnClient(client -> {
                if (slot < 0) mouse(client).aresos$onMove(client.getWindow().handle(), 20, 20);
                else pointAtSlot(client, slot);
                click(client, GLFW.GLFW_MOUSE_BUTTON_LEFT);
                check(client.mouseHandler.isMouseGrabbed() && !HomeScreen.freePointer(client), "Non-app click did not enter the world");
                check(!client.options.keyAttack.isDown() && !client.options.keyUse.isDown(), "Entry click leaked into item input");
            });
        }
        world.getConnection().waitForServerboundPackets();
        check(world.getServer().computeOnServer(server -> world.getConnection().getServerPlayer().getInventory().getItem(2).getCount()) == 8,
                "A background/entry click used the stone stack");
    }

    private static void gates(ClientGameTestContext context, TestSingleplayerContext world, FakeHelper helper) {
        background(helper, "notepad"); context.waitTicks(2);
        context.runOnClient(client -> {
            HomeScreen.forTests(false, null);
            ShellFocusClient.apply(client, new ShellClient.Focus(false, "app_activated", "notepad", false));
            check(!HomeScreen.freePointer(client), "A game the session didn't start got pointer rules");
            client.mouseHandler.grabMouse(); check(client.mouseHandler.isMouseGrabbed(), "Non-session capture was blocked");
            HomeScreen.forTests(true, null);
        });
        world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, false));
        background(helper, "notepad"); context.waitTicks(2);
        context.runOnClient(client -> {
            check(!HomeScreen.freePointer(client), "Normal world got the taskbar");
            client.mouseHandler.grabMouse(); check(client.mouseHandler.isMouseGrabbed(), "Normal world capture was blocked");
        });
        world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
        context.waitFor(AresOsClient::acceptsAppCommands);
        context.runOnClient(client -> ShellFocusClient.apply(client, new ShellClient.Focus(true, "app_closed", "notepad", true)));
    }

    private static void lostRelease(ClientGameTestContext context, FakeHelper helper) {
        for (int button : new int[]{GLFW.GLFW_MOUSE_BUTTON_LEFT, GLFW.GLFW_MOUSE_BUTTON_RIGHT, GLFW.GLFW_MOUSE_BUTTON_MIDDLE}) {
            background(helper, "notepad");
            context.waitTicks(2);
            context.runOnClient(client -> {
                pointAtSlot(client, 0);
                mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), GLFW.GLFW_PRESS);
                // That release was delivered to an app. Close/Alt+Tab back without sending it to Minecraft.
                ShellFocusClient.apply(client, new ShellClient.Focus(true, "app_closed", "notepad", true));
                mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), GLFW.GLFW_PRESS);
                if (button == GLFW.GLFW_MOUSE_BUTTON_LEFT) check(client.options.keyAttack.isDown(), "Normal attack press was swallowed");
                if (button == GLFW.GLFW_MOUSE_BUTTON_RIGHT) check(client.options.keyUse.isDown(), "Normal use press was swallowed");
                mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), GLFW.GLFW_RELEASE);
                check(!client.options.keyAttack.isDown() && !client.options.keyUse.isDown(), "A lost app release left world input held");
                check(!client.mouseHandler.isLeftPressed() && !client.mouseHandler.isRightPressed()
                        && !client.mouseHandler.isMiddlePressed(), "A lost app release left a raw mouse button held");
                net.minecraft.client.KeyMapping.releaseAll();
                AppInput.reset();
            });
        }
    }

    private record Flight(double speed, float fov) { }
    private static void flight(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> { DesktopWorld.setEnabled(server, false); world.getConnection().getServerPlayer().setGameMode(GameType.CREATIVE); });
        context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE && client.player.getAbilities().getFlyingSpeed() == .05f);
        Flight normal = measure(context, world, false), sprint = measure(context, world, true);
        for (GameType mode : new GameType[]{GameType.SURVIVAL, GameType.CREATIVE}) {
            world.getServer().runOnServer(server -> { DesktopWorld.setEnabled(server, true); world.getConnection().getServerPlayer().setGameMode(mode); });
            context.waitFor(client -> client.gameMode.getPlayerMode() == mode && client.player.getAbilities().getFlyingSpeed() == LiveMode.DESKTOP_FLYING_SPEED);
            for (boolean running : new boolean[]{false, true}) {
                Flight measured = measure(context, world, running), vanilla = running ? sprint : normal;
                check(Math.abs(measured.speed / vanilla.speed - 1.5) < .02, mode + " flight ratio " + measured.speed / vanilla.speed);
                check(Math.abs(measured.speed - (running ? 32.7 : 16.4)) < .6, mode + " blocks/s " + measured.speed);
                check(Math.abs(measured.fov - vanilla.fov) < .0001, mode + " widened FOV: " + measured.fov + " vs " + vanilla.fov);
                AresOs.LOGGER.info("56 measured {} {} flight: {} blocks/s; FOV {} (vanilla {} blocks/s, FOV {})",
                        mode, running ? "sprint" : "plain", measured.speed, measured.fov, vanilla.speed, vanilla.fov);
            }
        }
    }

    private static Flight measure(ClientGameTestContext context, TestSingleplayerContext world, boolean sprint) {
        world.getServer().runOnServer(server -> {
            var p = world.getConnection().getServerPlayer(); p.teleportTo(0.5, 200, 0.5);
            p.getAbilities().flying = true; p.onUpdateAbilities(); p.setDeltaMovement(Vec3.ZERO);
        });
        context.waitFor(client -> client.player.getY() > 199 && client.player.getAbilities().flying);
        context.runOnClient(client -> { client.player.setYRot(0); client.player.setXRot(0); client.player.setDeltaMovement(Vec3.ZERO); });
        context.getInput().holdKey(options -> options.keyUp);
        if (sprint) context.getInput().holdKey(options -> options.keySprint);
        try {
            context.waitTicks(60);
            Vec3 start = context.computeOnClient(client -> client.player.position());
            context.waitTicks(20);
            Vec3 end = context.computeOnClient(client -> client.player.position());
            return new Flight(end.subtract(start).horizontalDistance(), context.computeOnClient(client -> client.player.getFieldOfViewModifier(true, 1)));
        } finally {
            context.getInput().releaseKey(options -> options.keyUp);
            if (sprint) context.getInput().releaseKey(options -> options.keySprint);
            context.waitTicks(3);
        }
    }

    private static void pointAtSlot(Minecraft client, int slot) {
        var w = client.getWindow();
        double scale = (double)w.getScreenWidth() / w.getGuiScaledWidth();
        mouse(client).aresos$onMove(w.handle(), (w.getGuiScaledWidth() / 2 - 80 + slot * 20) * scale,
                (w.getGuiScaledHeight() - 11) * (double)w.getScreenHeight() / w.getGuiScaledHeight());
    }
    private static MouseTestAccess mouse(Minecraft client) { return (MouseTestAccess)(Object)client.mouseHandler; }
    private static void click(Minecraft client, int button) {
        mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), GLFW.GLFW_PRESS);
        mouse(client).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(button, 0), GLFW.GLFW_RELEASE);
    }
    private static void background(FakeHelper helper, String app) {
        try { helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", app)); }
        catch (IOException error) { throw new UncheckedIOException(error); }
    }
    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }

    private static final class NativeApps implements AutoCloseable {
        final boolean enabled = Boolean.getBoolean("aresos.pointerSession");
        final ClientGameTestContext context;
        final Map<String, Process> apps = new HashMap<>();
        Path root, repo;
        Process input;
        BufferedWriter commands;
        BufferedReader replies;
        org.lwjgl.glfw.GLFWCursorPosCallback previousMove;
        org.lwjgl.glfw.GLFWMouseButtonCallback previousButton;
        NativeApps(ClientGameTestContext context) throws IOException {
            this.context = context;
            if (!enabled) return;
            check(!System.getenv().getOrDefault("WAYLAND_DISPLAY", "wayland-0").equals("wayland-0")
                    && !System.getenv().getOrDefault("DISPLAY", ":0").equals(":0"), "Refusing the owner's display");
            root = Files.createDirectories(Path.of("pointer-native").toAbsolutePath());
            repo = Path.of(System.getProperty("aresos.repoDir"));
            Files.writeString(root.resolve("env"), "WAYLAND_DISPLAY=" + System.getenv("WAYLAND_DISPLAY") + "\nDISPLAY=" + System.getenv("DISPLAY") + "\n");
            input = new ProcessBuilder("python3", repo.resolve("reviews/56-free-pointer/rig/pointer.py").toString(), root.toString())
                    .redirectError(ProcessBuilder.Redirect.INHERIT).start();
            commands = input.outputWriter(); replies = input.inputReader();
            check("ready".equals(replies.readLine()), "Virtual input did not start");
            // Fabric deliberately does not attach native input callbacks and renders at a virtual window size.
            // Restore mouse input for this final test only, mapping real content coordinates to that virtual size.
            context.runOnClient(client -> {
                long handle = client.getWindow().handle();
                previousMove = GLFW.glfwSetCursorPosCallback(handle, (window, x, y) -> {
                    var w = client.getWindow();
                    var real = (net.fabricmc.fabric.impl.client.gametest.util.WindowHooks)(Object)w;
                    mouse(client).aresos$onMove(window, x * w.getScreenWidth() / real.fabric_getRealWidth(),
                            y * w.getScreenHeight() / real.fabric_getRealHeight());
                });
                previousButton = GLFW.glfwSetMouseButtonCallback(handle, (window, button, action, modifiers) ->
                        mouse(client).aresos$onButton(window, new MouseButtonInfo(button, modifiers), action));
            });
            open("notepad"); open("terminal");
        }
        void open(String app) throws IOException {
            apps.put(app, new ProcessBuilder("/usr/bin/foot", "--app-id=aresos.pkg56." + app, "--window-size-pixels=480x260",
                    "--title=Pointer " + app, "/usr/bin/sleep", "1800").redirectError(ProcessBuilder.Redirect.DISCARD).start());
            context.waitTicks(5);
        }
        void reopenTerminal() { if (enabled) try { open("terminal"); } catch(IOException e) { throw new UncheckedIOException(e); } }
        void activate(String app) { if (enabled) tool("activate", app); }
        void closeTerminal() { if (enabled) { tool("close", "terminal"); apps.get("terminal").destroy(); } }
        void altTab() { if (enabled) { input("mods alt"); input("key tab"); input("mods"); context.waitTicks(3); expectActive("terminal"); } }
        void expectActive(String app) { if (enabled) tool("list", app); }
        void pointAtSlot(int slot) {
            if (!enabled) return;
            String command = context.computeOnClient(client -> {
                var w = client.getWindow();
                // Fabric's render size can differ from the real maximized window. Use compositor coordinates.
                try (var stack = org.lwjgl.system.MemoryStack.stackPush()) {
                    var x = stack.mallocInt(1); var y = stack.mallocInt(1);
                    GLFW.glfwGetWindowPos(w.handle(), x, y);
                    var real = (net.fabricmc.fabric.impl.client.gametest.util.WindowHooks)(Object)w;
                    return "move " + (x.get(0) + (int)((w.getGuiScaledWidth() / 2 - 80 + slot * 20)
                            * (double)real.fabric_getRealWidth() / w.getGuiScaledWidth()))
                            + " " + (y.get(0) + (int)((w.getGuiScaledHeight() - 11)
                            * (double)real.fabric_getRealHeight() / w.getGuiScaledHeight()));
                }
            });
            AresOs.LOGGER.info("56 native pointer command: {}", command);
            input("move 10 10");
            input(command);
        }
        void screenshot() {
            if (!enabled) return;
            try {
                var p = new ProcessBuilder("grim", "-c", Path.of(System.getProperty("aresos.pointerReviewDir"))
                        .resolve("56-session-hover.png").toString()).redirectError(ProcessBuilder.Redirect.INHERIT).start();
                check(p.waitFor() == 0, "Compositor screenshot failed");
            } catch(IOException e) { throw new UncheckedIOException(e); }
            catch(InterruptedException e) { Thread.currentThread().interrupt(); throw new RuntimeException(e); }
        }
        void input(String command) {
            if (!enabled) return;
            try { commands.write(command + "\n"); commands.flush(); check("done".equals(replies.readLine()), "Virtual input failed: " + command); }
            catch(IOException e) { throw new UncheckedIOException(e); }
        }
        void tool(String action, String app) {
            try {
                var p = new ProcessBuilder("python3", repo.resolve("reviews/40-real-home/rig/tl.py").toString(), root.toString(), action, (app.equals("desktop") ? "aresos-desktop" : "aresos.pkg56." + app))
                        .redirectErrorStream(true).start();
                String output = new String(p.getInputStream().readAllBytes());
                check(p.waitFor() == 0, "Native app action failed: " + output);
                if (action.equals("activate") || action.equals("list")) check(output.lines().anyMatch(line -> line.contains(app.equals("desktop") ? "aresos-desktop" : "aresos.pkg56." + app) && line.contains("activated")), "App did not take focus: " + output);
            } catch(IOException e) { throw new UncheckedIOException(e); } catch(InterruptedException e) { Thread.currentThread().interrupt(); throw new RuntimeException(e); }
        }
        @Override public void close() {
            if (enabled && input != null) context.runOnClient(client -> {
                var move = GLFW.glfwSetCursorPosCallback(client.getWindow().handle(), previousMove);
                var button = GLFW.glfwSetMouseButtonCallback(client.getWindow().handle(), previousButton);
                if (move != null) move.free();
                if (button != null) button.free();
            });
            for (var app : apps.values()) app.destroy();
            if (input != null) input.destroy();
        }
    }
}
