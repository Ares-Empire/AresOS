package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ModeInventories;
import dev.aresos.mode.ToggleModePayload;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.network.chat.Component;
import net.minecraft.client.gui.screens.inventory.ContainerScreen;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.nio.file.Path;
import java.util.List;

import static dev.aresos.test.ModeInventoryFixtures.*;

public final class ModeInventoriesClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        String previousConfig = System.getProperty("aresos.appsConfig");
        try {
            Path config = Path.of("mode-inventory-fixtures/apps.json").toAbsolutePath();
            var app = new AppDefinition("mode-notes", "Mode Notes", List.of("never-run.exe"), "minecraft:book", true);
            AppsConfig.save(config, List.of(app));
            System.setProperty("aresos.appsConfig", config.toString());
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(app)));
            TestWorldSave save;
            Inventory live;
            Inventory build;
            PersistedInventory savedLive;
            PersistedInventory savedBuild;
            PersistedInventory repinnedLive;
            try (var world = context.worldBuilder().create()) {
                save = world.getWorldSave();
                world.getConnection().waitForChunksRender();
                context.getInput().pressKey(InputConstants.KEY_G);
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(!ModeInventories.of(player).hasStoredInventories(), "Normal G created stored inventories");
                    player.setGameMode(GameType.SURVIVAL);
                    DesktopWorld.setEnabled(server, true);
                    for (int x = -5; x <= 5; x++) for (int z = -5; z <= 5; z++)
                        server.overworld().setBlockAndUpdate(new BlockPos(x, 149, z), Blocks.STONE.defaultBlockState());
                    player.teleportTo(0.5, 150, 0.5);
                    fill(player, false);
                    player.getInventory().setItem(0, AppItems.create(app));
                    player.getInventory().setItem(9, ItemStack.EMPTY);
                });
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL && client.player.getY() > 149);
                // Use the real number key so the client and server agree before taking the selected-slot snapshot.
                context.getInput().pressKey(InputConstants.KEY_6);
                world.getConnection().waitForServerboundPackets();
                screenshot(context, "09-live-hotbar");
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    player.inventoryMenu.clicked(36, 0, ContainerInput.PICKUP, player);
                    player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
                });
                check(!AppsConfig.load(config).apps().getFirst().pinned(), "Live unpin did not persist");
                live = world.getServer().computeOnServer(server -> capture(world.getConnection().getServerPlayer()));
                savedLive = world.getServer().computeOnServer(server -> capturePersisted(world.getConnection().getServerPlayer()));
                toggle(context, world, GameType.CREATIVE, 0);
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(player.getInventory().isEmpty(), "First Build switch leaked Live items");
                    fill(player, true);
                    // Creative-supplied app items can move around without changing the Live pin configuration.
                    player.getInventory().setItem(9, AppItems.create(app));
                    player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
                    player.inventoryMenu.clicked(36, 0, ContainerInput.PICKUP, player);
                    player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
                    player.inventoryMenu.broadcastChanges();
                });
                check(!AppsConfig.load(config).apps().getFirst().pinned(), "Build app placement changed pins");
                context.getInput().pressKey(InputConstants.KEY_3);
                world.getConnection().waitForServerboundPackets();
                build = world.getServer().computeOnServer(server -> capture(world.getConnection().getServerPlayer()));
                savedBuild = world.getServer().computeOnServer(server -> capturePersisted(world.getConnection().getServerPlayer()));
                screenshot(context, "09-build-hotbar");
                toggle(context, world, GameType.SURVIVAL, live.selected());
                world.getServer().runOnServer(server -> assertExact(world.getConnection().getServerPlayer(), live, "G restored Live"));
                check(!AppsConfig.load(config).apps().getFirst().pinned(), "Returning Live repinned the Build app");

                context.getInput().pressKey(options -> options.keyInventory);
                context.waitForScreen(InventoryScreen.class);
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> {
                    var overlay = ((HudTestAccess) client.gui.hud).aresos$overlayMessage();
                    return overlay != null && overlay.getString().contains("Close the menu");
                });
                world.getServer().runOnServer(server -> assertExact(world.getConnection().getServerPlayer(), live, "Open inventory G"));
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                context.waitForScreen(null);
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().openMenu(
                        new SimpleMenuProvider((id, inventory, p) -> ChestMenu.threeRows(id, inventory, new SimpleContainer(27)),
                                Component.literal("Mode-switch chest fixture"))));
                context.waitForScreen(ContainerScreen.class);
                world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer().containerMenu
                        != world.getConnection().getServerPlayer().inventoryMenu, "Chest fixture closed before switch packet"));
                context.runOnClient(client -> ClientPlayNetworking.send(ToggleModePayload.INSTANCE));
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(player.gameMode() == GameType.SURVIVAL, "Open container packet changed mode");
                    assertExact(player, live, "Open container packet");
                });
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                context.waitForScreen(null);

                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(player.containerMenu == player.inventoryMenu, "Chest close packet has not reached the server");
                });
                for (int i = 0; i < 50; i++) {
                    toggle(context, world, i % 2 == 0 ? GameType.CREATIVE : GameType.SURVIVAL,
                            i % 2 == 0 ? build.selected() : live.selected());
                    var expected = i % 2 == 0 ? build : live;
                    world.getServer().runOnServer(server -> assertExact(world.getConnection().getServerPlayer(), expected, "Host rapid switch"));
                }
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    // Save immediately after a switch, before another tick or packet can run.
                    check(LiveMode.toggleForHost(server, player), "Final Build switch failed");
                    server.getPlayerList().saveAll();
                });
            }
            try (var reopened = save.open()) {
                reopened.getServer().runOnServer(server -> {
                    var player = reopened.getConnection().getServerPlayer();
                    check(player.gameMode() == GameType.CREATIVE, "Ordinary desktop rejoin changed Build mode");
                    assertPersisted(player, savedBuild, "Build survived server restart");
                });
                toggle(context, reopened, GameType.SURVIVAL, live.selected());
                reopened.getServer().runOnServer(server -> {
                    var player = reopened.getConnection().getServerPlayer();
                    assertPersisted(player, savedLive, "Inactive Live survived restart");
                    player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
                    player.inventoryMenu.clicked(36, 0, ContainerInput.PICKUP, player);
                });
                check(AppsConfig.load(config).apps().getFirst().pinned(), "Live repin did not persist after Build rejoin");
                repinnedLive = reopened.getServer().computeOnServer(server -> capturePersisted(reopened.getConnection().getServerPlayer()));
                // Also exercise home arrival: it must swap BEFORE its forced survival game mode and login packet.
                reopened.getServer().runOnServer(server -> {
                    var player = reopened.getConnection().getServerPlayer();
                    NetherHome.recordHome(server, new NetherHome.Home(server.overworld().dimension(), new Vec3(0.5, 150, 0.5), 0, 0));
                    check(LiveMode.toggleForHost(server, player), "Home setup Build switch failed");
                });
            }
            try (var reopened = save.open()) {
                reopened.getServer().runOnServer(server -> {
                    var player = reopened.getConnection().getServerPlayer();
                    check(player.gameMode() == GameType.SURVIVAL, "Home rejoin did not enter Live");
                    assertPersisted(player, repinnedLive, "Home rejoin restored exact Live");
                    check(app.id().equals(player.getInventory().getItem(0).get(AppItems.APP_ID)), "Home rejoin lost Live app placement");
                    check(player.getInventory().getSelectedSlot() == live.selected(), "Home rejoin lost selected Live slot");
                });
                toggle(context, reopened, GameType.CREATIVE, build.selected());
                reopened.getServer().runOnServer(server -> assertPersisted(reopened.getConnection().getServerPlayer(), savedBuild, "Inactive Build survived home arrival"));
            }
            AresOs.LOGGER.info("09 client checks passed: G restores exact inventories/selected slots; empty first Build; 50 host switches; Build and Live survive server restarts; home arrival swaps safely; only Live edits pins; menus refuse G; normal G creates no snapshots");
        } catch (Exception error) { throw new RuntimeException(error); }
        finally {
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(previousApps));
            if (previousConfig == null) System.clearProperty("aresos.appsConfig"); else System.setProperty("aresos.appsConfig", previousConfig);
        }
    }

    private static void toggle(ClientGameTestContext context, TestSingleplayerContext world, GameType mode, int selected) {
        context.getInput().pressKey(InputConstants.KEY_G);
        world.getConnection().waitForServerboundPackets();
        context.waitFor(client -> client.gameMode.getPlayerMode() == mode && client.player.getInventory().getSelectedSlot() == selected);
        context.waitFor(client -> !dev.aresos.client.ModeSwitchClient.pending());
        world.getConnection().waitForServerboundPackets();
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.getInput().lookAt(0, 10);
        context.waitTicks(5);
        context.runOnClient(client -> {
            client.gui.hud.getChat().clearMessages(true);
            client.gui.hud.setOverlayMessage(Component.empty(), false);
            client.gui.toastManager().clear();
        });
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.modeReviewDir"))));
    }
}
