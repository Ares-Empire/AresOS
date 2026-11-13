package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.launch.AppLauncher;
import dev.aresos.config.AppDefinition;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.test.mixin.KeyboardTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.MouseTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.inventory.ContainerScreen;
import net.minecraft.client.gui.screens.inventory.MerchantScreen;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.DoorBlock;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import org.lwjgl.glfw.GLFW;
import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.platform.InputConstants;

import java.nio.file.Path;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;

public final class AresOsClientGameTest implements FabricClientGameTest {
    @Override
    public void runTest(ClientGameTestContext context) {
        var calls = new CopyOnWriteArrayList<List<String>>();
        AppLauncher fake = command -> {
            calls.add(List.copyOf(command));
            return CompletableFuture.completedFuture(null);
        };
        AppLauncher previous = context.computeOnClient(client -> AresOsClient.replaceLauncher(fake));
        TestWorldSave save;
        try {
            try (TestSingleplayerContext world = context.worldBuilder().adjustSettings(settings -> {
                settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL);
                settings.setAllowCommands(false);
            }).create()) {
                save = world.getWorldSave();
                world.getConnection().waitForChunksRender();
                assertNormalWorld(context, world);
                screenshot(context, "01b-normal-world");
                context.runOnClient(client -> client.player.connection.sendCommand("aresos desktop on"));
                context.waitFor(client -> client.player.getInventory().getItem(0).is(AppItems.APP));
                context.runOnClient(client -> {
                    var stack = client.player.getInventory().getItem(0);
                    check("notepad".equals(stack.get(AppItems.APP_ID)), "Notepad missing from hotbar");
                    check(stack.getMaxStackSize() == 1, "App item is stackable");
                    check(stack.getHoverName().getString().equals("Notepad"), "App name is wrong");
                    check(Identifier.withDefaultNamespace("writable_book").equals(stack.get(DataComponents.ITEM_MODEL)),
                            "App did not borrow writable book model");
                    client.player.getInventory().setSelectedSlot(0);
                });
                world.getServer().runOnServer(server -> {
                    check(!server.getWorldData().isAllowCommands(), "Test world has cheats enabled");
                    var guest = new ServerPlayer(server, world.getConnection().getServerLevel(),
                            new GameProfile(UUID.randomUUID(), "Guest"), ClientInformation.createDefault());
                    check(!LiveMode.toggleForHost(server, guest), "Singleplayer guest could toggle mode");
                    try {
                        check(server.getCommands().getDispatcher().execute("aresos desktop off",
                                server.createCommandSourceStack().withEntity(guest)) == 0,
                                "Guest could disable the desktop marker");
                    } catch (com.mojang.brigadier.exceptions.CommandSyntaxException error) {
                        throw new AssertionError(error);
                    }
                    check(DesktopWorld.isEnabled(server), "Guest changed the desktop marker");
                });
                context.getInput().lookAt(0, -45);
                context.waitFor(client -> ((HudTestAccess) client.gui.hud).aresos$overlayTime() == 0);
                context.runOnClient(client -> client.gui.hud.getChat().clearMessages(true));
                screenshot(context, "01b-hotbar-notepad");
                context.getInput().holdKeyFor(options -> options.keyUse, 16);
                world.getConnection().waitForServerboundPackets();
                context.waitTicks(4);
                check(calls.equals(List.of(notepadCommand())), "Holding one click launched app more than once: " + calls);
                context.getInput().pressKey(options -> options.keyUse);
                context.waitTicks(4);
                check(calls.size() == 2, "Second click did not launch exactly once: " + calls);
                testClickEdges(context, calls);
                testInteractiveTargets(context, world, calls);

                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
                world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer()
                        .gameMode.getGameModeForPlayer() == GameType.CREATIVE, "Server did not enter Build mode"));
                screenshot(context, "01b-build-mode");
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL);
                world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer()
                        .gameMode.getGameModeForPlayer() == GameType.SURVIVAL, "Server did not return to Live mode"));
                screenshot(context, "01b-live-mode");

                testSameTickSelection(context, world, calls);
                testFocusReturn(context);
                testOverlappingLaunches(context, fake);
                context.runOnClient(client -> {
                    AresOsClient.launch("missing-app");
                    check(overlay(client).equals("Unknown AresOS app"), "Unknown app did not show action-bar error");
                    AresOsClient.replaceLauncher(command -> CompletableFuture.failedFuture(new java.io.IOException("Test failure")));
                    AresOsClient.launch("notepad");
                });
                context.waitFor(client -> overlay(client).equals("Couldn't open Notepad"));
                context.runOnClient(client -> AresOsClient.replaceLauncher(fake));

                context.runOnClient(client -> client.player.connection.sendCommand("aresos give notepad"));
                context.waitFor(client -> client.player.getInventory().getItem(1).is(AppItems.APP));
                context.runOnClient(client -> check("notepad".equals(client.player.getInventory().getItem(1)
                        .get(AppItems.APP_ID)), "Give command did not create the configured app"));
                world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().getInventory().clearContent());
            }
            try (TestSingleplayerContext reopened = save.open()) {
                reopened.getConnection().waitForChunksRender();
                reopened.getServer().runOnServer(server -> check(DesktopWorld.isEnabled(server), "Marker did not survive reopen"));
                context.waitFor(client -> client.player.getInventory().getItem(0).is(AppItems.APP));
                context.runOnClient(client -> client.player.connection.sendCommand("aresos desktop off"));
                reopened.getConnection().waitForServerboundPackets();
                reopened.getServer().runOnServer(server -> {
                    check(!DesktopWorld.isEnabled(server), "Desktop off did not clear marker");
                    var player = reopened.getConnection().getServerPlayer();
                    check(!LiveMode.isLive(player), "Desktop off left Live protection enabled");
                    check(player.getInventory().getItem(0).is(AppItems.APP), "Desktop off deleted an existing item");
                    player.getInventory().clearContent();
                });
            }
            try (TestSingleplayerContext reopened = save.open()) {
                reopened.getConnection().waitForChunksRender();
                assertNormalWorld(context, reopened);
                // Existing app items remain usable in normal worlds, but are never placed there.
                reopened.getServer().runOnServer(server -> reopened.getConnection().getServerPlayer()
                        .getInventory().setItem(0, AppItems.create(AresOs.apps().getFirst())));
                context.waitFor(client -> client.player.getMainHandItem().is(AppItems.APP));
                int before = calls.size();
                context.getInput().pressKey(options -> options.keyUse);
                context.waitTick();
                check(calls.size() == before + 1, "Existing app item could not launch in a normal world");
            }
        } finally {
            context.runOnClient(client -> {
                AresOsClient.replaceLauncher(previous);
                AresOsClient.FOCUS_RETURN.reset();
            });
        }
        AresOs.LOGGER.info("01c client checks passed: same-tick number-key and scroll selection (empty -> app, A -> B, app -> empty), "
                + "normal-world defaults, marker on/off and reopen, host-only commands without cheats, "
                + "held-click slot switch, between-tick clicks, door/chest/villager interception with vanilla controls, "
                + "overlapping launch focus return, Build/Live, errors, give command, and five screenshots");
    }

    private static void assertNormalWorld(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            check(!DesktopWorld.isEnabled(server), "New/off world was marked as an AresOS desktop");
            check(world.getConnection().getServerPlayer().getInventory().isEmpty(), "Normal join placed app items");
            check(!server.getWorldData().isAllowCommands(), "Test world has cheats enabled");
        });
        context.getInput().pressKey(InputConstants.KEY_G);
        context.waitFor(client -> overlay(client).equals("Not an AresOS world"));
        context.runOnClient(client -> {
            check(client.gameMode.getPlayerMode() == GameType.SURVIVAL, "Normal mode key changed game mode");
            client.player.connection.sendCommand("aresos give notepad");
        });
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer().getInventory().isEmpty(),
                "Give placed an app in a normal world"));
    }

    private static void testClickEdges(ClientGameTestContext context, List<List<String>> calls) {
        int before = calls.size();
        context.getInput().holdKey(options -> options.keyUse);
        context.waitTicks(6);
        context.getInput().pressKey(InputConstants.KEY_2);
        context.waitTicks(6);
        context.getInput().pressKey(InputConstants.KEY_1);
        context.waitTicks(6);
        check(calls.size() == before + 1, "Held-click slot switch relaunched app: " + calls);
        // One render-thread operation guarantees release/repress happens without a client tick between them.
        context.runOnClient(client -> {
            rawUse(client, GLFW.GLFW_RELEASE);
            rawUse(client, GLFW.GLFW_PRESS);
            check(calls.size() == before + 1, "First release/repress launched before vanilla input processing");
            rawUse(client, GLFW.GLFW_RELEASE);
            rawUse(client, GLFW.GLFW_PRESS);
            check(calls.size() == before + 1, "Second release/repress launched before vanilla input processing");
        });
        context.getInput().releaseKey(options -> options.keyUse);
        context.waitTicks(6);
        check(calls.size() == before + 3, "Between-tick press edges were lost or repeated: " + calls);
    }

    private static void testSameTickSelection(ClientGameTestContext context, TestSingleplayerContext world,
                                              List<List<String>> calls) {
        List<AppDefinition> previousApps = AresOs.apps();
        var appB = new AppDefinition("test-b", "Test app B", List.of("aresos-test-b"), "minecraft:paper", false);
        var apps = new java.util.ArrayList<>(previousApps);
        apps.add(appB);
        context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.copyOf(apps)));
        try {
            world.getServer().runOnServer(server -> world.getConnection().getServerPlayer()
                    .getInventory().setItem(1, AppItems.create(appB)));
            context.waitFor(client -> "test-b".equals(client.player.getInventory().getItem(1).get(AppItems.APP_ID)));
            // Both event batches run on the client thread, so no tick can split selection and use.
            for (boolean scroll : List.of(false, true)) {
                sameTickSelectAndClick(context, calls, scroll, scroll ? 8 : 2, 0, notepadCommand());
                sameTickSelectAndClick(context, calls, scroll, 0, 1, appB.command());
                sameTickSelectAndClick(context, calls, scroll, 1, 2, null);
            }
            context.getInput().pressKey(InputConstants.KEY_2);
            screenshot(context, "01c-selected-app-b");
        } finally {
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(previousApps));
            world.getServer().runOnServer(server -> world.getConnection().getServerPlayer()
                    .getInventory().setItem(1, ItemStack.EMPTY));
            context.waitFor(client -> client.player.getInventory().getItem(1).isEmpty());
            context.getInput().pressKey(InputConstants.KEY_1);
            context.waitTicks(6);
        }
    }

    private static void sameTickSelectAndClick(ClientGameTestContext context, List<List<String>> calls,
                                               boolean scroll, int from, int to, List<String> expected) {
        context.getInput().pressKey(InputConstants.KEY_1 + from);
        context.waitTicks(6);
        int before = calls.size();
        String scenario = (scroll ? "Scroll " : "Number key ") + from + " -> " + to;
        context.runOnClient(client -> {
            check(client.player.getInventory().getSelectedSlot() == from, scenario + ": wrong starting slot");
            if (scroll) {
                ((MouseTestAccess) client.mouseHandler).aresos$onScroll(client.getWindow().handle(), 0, -1);
                check(client.player.getInventory().getSelectedSlot() == to, scenario + ": scroll did not select target");
            } else {
                rawKey(client, InputConstants.KEY_1 + to, GLFW.GLFW_PRESS);
                rawKey(client, InputConstants.KEY_1 + to, GLFW.GLFW_RELEASE);
                check(client.player.getInventory().getSelectedSlot() == from, scenario + ": number key was not queued");
            }
            rawUse(client, GLFW.GLFW_PRESS);
            rawUse(client, GLFW.GLFW_RELEASE);
        });
        context.waitTicks(6);
        context.runOnClient(client -> check(client.player.getInventory().getSelectedSlot() == to,
                scenario + ": vanilla did not select target"));
        var launched = List.copyOf(calls.subList(before, calls.size()));
        check(launched.equals(expected == null ? List.of() : List.of(expected)),
                scenario + ": wrong launches: " + launched);
    }

    /**
     * What the fake launcher records for the default Notepad: notepad.exe on Windows, and no command on AresOS,
     * where an app is launched by its ID through the app helper. Unique among the configured apps, so a recorded
     * launch still names Notepad and nothing else.
     */
    private static List<String> notepadCommand() {
        var command = AresOs.app("notepad").command();
        check(AresOs.apps().stream().filter(app -> app.command().equals(command)).count() == 1,
                "Notepad's launch command does not identify it among " + AresOs.apps());
        return command;
    }

    private static void rawKey(Minecraft client, int key, int action) {
        ((KeyboardTestAccess) client.keyboardHandler).aresos$keyPress(client.getWindow().handle(), action, new KeyEvent(key, 0, 0));
    }

    private static void rawUse(Minecraft client, int action) {
        ((MouseTestAccess) client.mouseHandler).aresos$onButton(client.getWindow().handle(), new MouseButtonInfo(1, 0), action);
    }

    private static void testInteractiveTargets(ClientGameTestContext context, TestSingleplayerContext world,
                                               List<List<String>> calls) {
        BlockPos base = context.computeOnClient(client -> client.player.blockPosition().above(4));
        BlockPos target = base.offset(0, 0, 2);
        world.getServer().runOnServer(server -> {
            var level = world.getConnection().getServerLevel();
            for (int x = -3; x <= 3; x++) for (int z = -3; z <= 4; z++) {
                level.setBlockAndUpdate(base.offset(x, -1, z), Blocks.STONE.defaultBlockState());
                for (int y = 0; y < 4; y++) level.setBlockAndUpdate(base.offset(x, y, z), Blocks.AIR.defaultBlockState());
            }
            var door = Blocks.OAK_DOOR.defaultBlockState();
            level.setBlockAndUpdate(target, door);
            level.setBlockAndUpdate(target.above(), door.setValue(DoorBlock.HALF, DoubleBlockHalf.UPPER));
            world.getConnection().getServerPlayer().teleportTo(base.getX() + 0.5, base.getY(), base.getZ() + 0.5);
        });
        context.waitFor(client -> client.player.blockPosition().equals(base)
                && client.level.getBlockState(target).is(Blocks.OAK_DOOR));
        context.getInput().lookAt(0, 25);
        context.waitTicks(6);
        context.runOnClient(client -> check(client.hitResult instanceof BlockHitResult hit && hit.getBlockPos().equals(target),
                "Door fixture is not under crosshair: " + client.hitResult));
        clickApp(context, world, calls);
        world.getServer().runOnServer(server -> check(!world.getConnection().getServerLevel().getBlockState(target)
                .getValue(DoorBlock.OPEN), "App click opened door"));
        context.getInput().pressKey(InputConstants.KEY_2);
        context.waitTicks(6);
        context.getInput().pressKey(options -> options.keyUse);
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> check(world.getConnection().getServerLevel().getBlockState(target)
                .getValue(DoorBlock.OPEN), "Empty-hand control did not open door"));

        world.getServer().runOnServer(server -> {
            var level = world.getConnection().getServerLevel();
            level.setBlockAndUpdate(target.above(), Blocks.AIR.defaultBlockState());
            level.setBlockAndUpdate(target, Blocks.CHEST.defaultBlockState());
        });
        context.getInput().pressKey(InputConstants.KEY_1);
        context.waitFor(client -> client.level.getBlockState(target).is(Blocks.CHEST));
        context.waitTicks(6);
        context.runOnClient(client -> check(client.hitResult instanceof BlockHitResult hit && hit.getBlockPos().equals(target),
                "Chest fixture is not under crosshair"));
        clickApp(context, world, calls);
        context.getInput().pressKey(InputConstants.KEY_2);
        context.waitTicks(6);
        context.getInput().pressKey(options -> options.keyUse);
        context.waitForScreen(ContainerScreen.class);
        context.runOnClient(client -> client.player.closeContainer());
        context.waitForScreen(null);

        world.getServer().runOnServer(server -> {
            var level = world.getConnection().getServerLevel();
            level.setBlockAndUpdate(target, Blocks.AIR.defaultBlockState());
            var villager = new Villager(EntityTypes.VILLAGER, level);
            villager.setNoAi(true);
            villager.snapTo(target.getX() + 0.5, target.getY(), target.getZ() + 0.5);
            var offers = new MerchantOffers();
            offers.add(new MerchantOffer(new ItemCost(Items.EMERALD), new ItemStack(Items.BREAD), 10, 1, 0));
            villager.setOffers(offers);
            level.addFreshEntity(villager);
        });
        context.getInput().pressKey(InputConstants.KEY_1);
        context.getInput().lookAt(0, 0);
        context.waitFor(client -> client.hitResult instanceof EntityHitResult hit && hit.getEntity() instanceof Villager);
        context.waitTicks(6);
        clickApp(context, world, calls);
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(player.containerMenu == player.inventoryMenu, "App click opened a server container/trade");
        });
        context.getInput().pressKey(InputConstants.KEY_2);
        context.waitTicks(6);
        context.getInput().pressKey(options -> options.keyUse);
        context.waitForScreen(MerchantScreen.class);
        context.runOnClient(client -> client.player.closeContainer());
        context.waitForScreen(null);
        context.getInput().pressKey(InputConstants.KEY_1);
        context.getInput().lookAt(0, -45);
        context.waitTicks(6);
    }

    private static void clickApp(ClientGameTestContext context, TestSingleplayerContext world, List<List<String>> calls) {
        int before = calls.size();
        context.getInput().holdKeyFor(options -> options.keyUse, 8);
        world.getConnection().waitForServerboundPackets();
        context.waitTicks(4);
        check(calls.size() == before + 1, "Interactive target click did not launch exactly once");
        context.runOnClient(client -> check(client.gui.screen() == null, "App click opened a container/trade screen"));
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(player.containerMenu == player.inventoryMenu, "App click interacted on the server");
        });
    }

    private static void testOverlappingLaunches(ClientGameTestContext context, AppLauncher fake) {
        var earlier = new CompletableFuture<Void>();
        var newer = new CompletableFuture<Void>();
        var pending = new java.util.ArrayDeque<>(List.of(earlier, newer));
        context.runOnClient(client -> {
            boolean pauseSetting = client.options.pauseOnLostFocus;
            try {
                client.options.pauseOnLostFocus = true;
                AresOsClient.replaceLauncher(command -> pending.remove());
                AresOsClient.launch("notepad");
                AresOsClient.launch("notepad");
                newer.complete(null);
                loseFocus(client);
                check(client.gui.screen() instanceof PauseScreen, "Newer launch did not capture pause screen");
                earlier.completeExceptionally(new java.io.IOException("Earlier launch failed after newer pause"));
                regainFocus(client);
                check(client.gui.screen() == null, "Earlier launch failure cancelled newer focus return");
            } finally {
                AresOsClient.replaceLauncher(fake);
                ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
                client.options.pauseOnLostFocus = pauseSetting;
            }
        });
    }

    private static void testFocusReturn(ClientGameTestContext context) {
        context.runOnClient(client -> {
            boolean pauseSetting = client.options.pauseOnLostFocus;
            try {
                client.options.pauseOnLostFocus = true;
                AresOsClient.launch("notepad");
                loseFocus(client);
                check(client.gui.screen() instanceof PauseScreen, "Vanilla focus loss did not create a pause menu");
                regainFocus(client);
                check(client.gui.screen() == null, "AresOS focus pause was left open");

                AresOsClient.launch("notepad");
                client.pauseGame(false);
                var manual = client.gui.screen();
                loseFocus(client);
                regainFocus(client);
                check(client.gui.screen() == manual, "Esc-opened pause menu was closed");
                client.gui.setScreen(null);

                AresOsClient.FOCUS_RETURN.reset();
                loseFocus(client);
                var unrelated = client.gui.screen();
                regainFocus(client);
                check(client.gui.screen() == unrelated, "Unrelated focus-loss menu was closed");
                client.gui.setScreen(null);
            } finally {
                ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
                client.options.pauseOnLostFocus = pauseSetting;
            }
        });
    }

    private static void loseFocus(Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(false);
        var access = (MinecraftTestAccess) client;
        access.aresos$setLastActiveTime(0);
        access.aresos$pauseIfInactive();
    }

    private static void regainFocus(Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
        ((MinecraftTestAccess) client).aresos$pauseIfInactive();
    }

    private static String overlay(Minecraft client) {
        var message = ((HudTestAccess) client.gui.hud).aresos$overlayMessage();
        return message == null ? "" : message.getString();
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.getInput().lookAt(0, 15);
        context.waitTicks(2);
        context.takeScreenshot(TestScreenshotOptions.of(name)
                .withDestinationDir(Path.of(System.getProperty("aresos.reviewDir"))));
        context.getInput().lookAt(0, -45);
        context.waitTick();
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
