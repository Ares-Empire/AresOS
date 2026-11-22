package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.HomePointer;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldSearchScreen;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;
import org.lwjgl.glfw.GLFW;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static dev.aresos.test.FreePointerClientGameTest.click;
import static dev.aresos.test.FreePointerClientGameTest.pointAtSlot;
import static dev.aresos.test.GateLogoClientGameTest.stand;
import static dev.aresos.test.WalkInLogosClientGameTest.command;

public final class OpenAppsClientGameTest implements FabricClientGameTest {
    private static final AppDefinition BROWSER = app("browser", "Chrome", "minecraft:compass");
    private static final AppDefinition NOTES = app("notepad", "Notes", "minecraft:writable_book");
    private static final AppDefinition TERMINAL = app("terminal", "Terminal", "minecraft:book");
    private static final List<AppDefinition> APPS = List.of(BROWSER, NOTES, TERMINAL);
    private static final double Y = 150;

    private static AppDefinition app(String id, String name, String item) {
        return new AppDefinition(id, name, List.of(), item, true, "helper", null, null);
    }

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousShell = AresOs.shell();
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(new LinuxAppLauncher()));
        String previousConfig = System.getProperty("aresos.appsConfig");
        try {
            Path sockets = Files.createDirectories(Path.of("p333"));
            Path config = sockets.resolve("apps.json").toAbsolutePath();
            AppsConfig.save(config, APPS);
            System.setProperty("aresos.appsConfig", config.toString());
            try (var helper = new FakeHelper(sockets); var shell = helper.client(FakeHelper.fast())) {
                helper.minor = 3;
                var caps = new ArrayList<>(helper.capabilities);
                caps.addAll(List.of("apps_state", "activate_app"));
                helper.capabilities = caps;
                helper.entries = APPS.stream().map(app -> FakeHelper.entry(app.id(), app.name(), null)).toList();
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setApps(APPS);
                    AppsTestAccess.aresos$setShell(shell);
                    AresOsClient.replaceLauncher(new LinuxAppLauncher(() -> shell));
                    HomeScreen.forTests(true, null);
                    ShellFocusClient.register(shell);
                });
                shell.start();
                shell.awaitApps(Duration.ofSeconds(10));
                try (var world = context.worldBuilder().create();
                     var nativeApps = new FreePointerClientGameTest.NativeApps(context)) {
                    world.getConnection().waitForChunksRender();
                    world.getServer().runOnServer(server -> {
                        var level = world.getConnection().getServerLevel();
                        for (int x = -16; x <= 16; x++) for (int z = 7; z <= 36; z++)
                            level.setBlock(new BlockPos(x, (int) Y - 1, z), Blocks.GRASS_BLOCK.defaultBlockState(), 2);
                    });
                    stand(context, world, new Vec3(0, Y, 20.5), 180, 0);
                    command(context, world, "aresos desktop on");
                    context.waitFor(client -> client.player.connection.getCommands().getRoot().getChild("chrome") != null);
                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer();
                        player.getInventory().clearContent();
                        for (int slot = 0; slot < APPS.size(); slot++)
                            player.getInventory().setItem(slot, AppItems.create(APPS.get(slot)));
                        player.getInventory().setItem(3, new ItemStack(Items.STONE, 8));
                        player.inventoryMenu.broadcastChanges();
                    });
                    context.waitFor(client -> client.player.getInventory().getItem(2).is(AppItems.APP));
                    context.runOnClient(client -> {
                        client.player.getInventory().setSelectedSlot(3);
                        client.gui.hud.getChat().clearMessages(true);
                        client.gui.toastManager().clear();
                    });
                    helper.event("apps_state", Map.of("apps", List.of(
                            Map.of("id", "browser", "windows", 2, "active", true, "hidden", false),
                            Map.of("id", "notepad", "windows", 1, "active", false, "hidden", true),
                            Map.of("id", "terminal", "windows", 1, "active", false, "hidden", false))));
                    context.waitFor(client -> shell.appWindows().size() == 3);
                    context.waitTicks(5);
                    context.takeScreenshot(TestScreenshotOptions.of("333-hotbar-app-marks")
                            .withDestinationDir(Path.of(System.getProperty("aresos.openAppsReviewDir"))));

                    background(helper, nativeApps);
                    context.waitFor(HomeScreen::freePointer);
                    context.runOnClient(client -> {
                        pointAtSlot(client, 0);
                        click(client, GLFW.GLFW_MOUSE_BUTTON_LEFT);
                    });
                    expect(context, helper, "activate_app", 1, "browser");

                    for (boolean focusFirst : new boolean[]{true, false}) {
                        int count = focusFirst ? 1 : 2;
                        background(helper, nativeApps);
                        context.waitFor(HomeScreen::freePointer);
                        if (nativeApps.enabled) {
                            nativeApps.pointAtSlot(1);
                            context.waitFor(client -> HomePointer.hoveredSlot(client) == 1);
                            if (focusFirst) context.runOnClient(client -> nativeApps.beforeRightPress = OpenAppsClientGameTest::foreground);
                            nativeApps.input("button right down");
                            expect(context, helper, "open_app", count, "notepad");
                            context.runOnClient(client -> {
                                nativeApps.beforeRightPress = ignored -> { };
                                if (!focusFirst) foreground(client);
                                check(!client.options.keyUse.isDown(), "Right press leaked into item use");
                            });
                            nativeApps.input("button right up");
                        } else {
                            context.runOnClient(client -> {
                                pointAtSlot(client, 1);
                                if (focusFirst) foreground(client);
                                click(client, GLFW.GLFW_MOUSE_BUTTON_RIGHT);
                                if (!focusFirst) foreground(client);
                            });
                        }
                        expect(context, helper, "open_app", count, "notepad");
                        var request = helper.received("open_app").getLast();
                        helper.event("app_state", Map.of("request_id", request.get("id").getAsString(), "state", "focused"));
                        context.waitTicks(4);
                        context.runOnClient(client -> check(HomeScreen.freePointer(client)
                                && !client.mouseHandler.isMouseGrabbed() && !client.options.keyUse.isDown(),
                                "Right press or release captured the world or leaked into item use"));
                        check(helper.received("open_app").size() == count && helper.received("activate_app").size() == 1,
                                "Right click triggered more than one request");
                    }

                    command(context, world, "chrome");
                    expect(context, helper, "activate_app", 2, "browser");
                    nativeApps.activate("desktop");
                    helper.event("shell_search", Map.of());
                    context.waitForScreen(WorldSearchScreen.class);
                    context.getInput().typeChars("Chrome");
                    context.getInput().pressKey(InputConstants.KEY_RETURN);
                    expect(context, helper, "activate_app", 3, "browser");
                    check("world".equals(FakeHelper.string(helper.received("activate_app").getLast(), "screen")),
                            "World search dropped the screen hint");

                    command(context, world, "aresos logo browser");
                    var gate = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().getLast());
                    check(gate.gate().isPresent(), "The Chrome gate was not built");
                    nativeApps.activate("desktop");
                    helper.event("shell_focus", Map.of("focus", "foreground", "reason", "app_closed"));
                    context.waitFor(client -> !HomeScreen.freePointer(client));
                    context.getInput().pressKey(InputConstants.KEY_1);
                    context.waitFor(client -> client.player.getInventory().getSelectedSlot() == 0);
                    context.runOnClient(client -> check(client.mouseHandler.isMouseGrabbed(),
                            "World input was not captured for the held item"));
                    context.getInput().holdKey(options -> options.keyUse);
                    try { expect(context, helper, "activate_app", 4, "browser"); }
                    finally { context.getInput().releaseKey(options -> options.keyUse); }
                    stand(context, world, gate.exit().position(), gate.exit().yaw(), 0);
                    context.getInput().holdKey(options -> options.keyUp);
                    try { expect(context, helper, "activate_app", 5, "browser"); }
                    finally { context.getInput().releaseKey(options -> options.keyUp); }
                    context.waitTicks(8);
                    check(helper.received("activate_app").size() == 5 && helper.launches.get() == 2,
                            "An app gesture sent an extra request");
                }
            }
            AresOs.LOGGER.info("333 open app checks passed: hotbar marks, free pointer clicks, slash name, world search and walk-in gate");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps);
                AppsTestAccess.aresos$setShell(previousShell);
                AresOsClient.replaceLauncher(previousLauncher);
                AresOsClient.FOCUS_RETURN.reset();
                HomeScreen.forTests(null, null);
            });
        }
    }

    private static void background(FakeHelper helper, FreePointerClientGameTest.NativeApps nativeApps) throws IOException {
        nativeApps.activate("notepad");
        helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
    }

    private static void foreground(Minecraft client) {
        ShellFocusClient.apply(client, new ShellClient.Focus(true, "desktop_activated", null, false));
    }

    private static void expect(ClientGameTestContext context, FakeHelper helper, String op, int count, String app) {
        context.waitFor(client -> helper.received(op).size() >= count);
        var calls = helper.received(op);
        check(calls.size() == count && app.equals(FakeHelper.string(calls.getLast(), "app_id")),
                "Expected " + op + " #" + count + " for " + app + ", got " + calls);
    }

    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
}
