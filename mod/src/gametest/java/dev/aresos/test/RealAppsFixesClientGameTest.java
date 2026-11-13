package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.config.*;
import dev.aresos.item.*;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.*;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.minecraft.client.gui.screens.inventory.ContainerScreen;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.network.chat.Component;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.item.*;
import net.minecraft.world.level.GameType;
import java.nio.file.*;
import java.util.*;

public final class RealAppsFixesClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        var previous = AresOs.apps(); String previousConfig = System.getProperty("aresos.appsConfig");
        var failures = new ArrayList<String>();
        try {
            Path config = Path.of("real-app-fixtures/07b-apps.json").toAbsolutePath();
            // One of his apps, so its item belongs in the inventory; it starts unpinned.
            var app = new AppDefinition("fixture-chest", "Chest fixture", List.of("never-run.exe"), "minecraft:book", false).withMine(true);
            AppsConfig.save(config, List.of(app)); System.setProperty("aresos.appsConfig", config.toString());
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(app)));
            TestWorldSave save;
            try (var world = context.worldBuilder().create()) {
                save = world.getWorldSave(); world.getConnection().waitForChunksRender();
                for (var mode : List.of(GameType.SURVIVAL, GameType.CREATIVE)) {
                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer(); player.setGameMode(mode);
                        check(player.gameMode() == mode, "Chest fixture did not enter " + mode);
                        DesktopWorld.setEnabled(server, mode == GameType.CREATIVE);
                        player.getInventory().clearContent(); player.getInventory().setItem(9, AppItems.create(app));
                        openChest(player);
                    });
                    context.waitForScreen(ContainerScreen.class);
                    click(context, 27); click(context, 54); world.getConnection().waitForServerboundPackets();
                    check(!AppsConfig.load(config).apps().getFirst().pinned(), "Chest pin escaped normal-world/Build guard: " + mode);
                    click(context, 54); click(context, 27); world.getConnection().waitForServerboundPackets();
                    check(!AppsConfig.load(config).apps().getFirst().pinned(), "Chest unpin escaped normal-world/Build guard: " + mode);
                    context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                    context.waitForScreen(null);
                    world.getConnection().waitForServerboundPackets();
                }
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer(); player.setGameMode(GameType.SURVIVAL);
                    check(player.gameMode() == GameType.SURVIVAL, "Live chest fixture mode change was refused");
                    DesktopWorld.setEnabled(server, true);
                    player.getInventory().clearContent(); player.getInventory().setItem(9, AppItems.create(app));
                    openChest(player);
                });
                context.waitForScreen(ContainerScreen.class);
                // Use vanilla client clicks/packets in a real chest menu, not savePins directly.
                click(context, 27); world.getConnection().waitForServerboundPackets();
                context.runOnClient(client -> check(app.id().equals(client.player.containerMenu.getCarried().get(AppItems.APP_ID)), "Chest click did not pick up app"));
                check(!AppsConfig.load(config).apps().getFirst().pinned(), "Chest pickup alone changed pins");
                click(context, 54); world.getConnection().waitForServerboundPackets();
                context.waitTicks(3);
                context.runOnClient(client -> check(app.id().equals(client.player.getInventory().getItem(0).get(AppItems.APP_ID)), "Chest pin did not move app into hotbar"));
                if (!AppsConfig.load(config).apps().getFirst().pinned()) failures.add("07b chest pin: apps.json stayed unpinned");
                // Establish the saved pin even on the unfixed code, to independently test unpin.
                world.getServer().runOnServer(server -> { try { AresOs.savePins(Map.of(app.id(), true)); } catch (Exception e) { throw new RuntimeException(e); } });
                click(context, 54); click(context, 27); world.getConnection().waitForServerboundPackets();
                context.waitTicks(3);
                context.runOnClient(client -> check(app.id().equals(client.player.getInventory().getItem(9).get(AppItems.APP_ID)), "Chest unpin did not move app out of hotbar"));
                if (AppsConfig.load(config).apps().getFirst().pinned()) failures.add("07b chest unpin: apps.json stayed pinned");
                screenshot(context, "07b-chest-unpinned");
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                context.waitForScreen(null);
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    try { AresOs.savePins(Map.of(app.id(), true)); } catch (Exception e) { throw new RuntimeException(e); }
                    var player = world.getConnection().getServerPlayer(); player.getInventory().clearContent();
                    for (int i = 0; i < 9; i++) player.getInventory().setItem(i, new ItemStack(Items.STONE, 12));
                    AppInventory.populate(player);
                    check(app.id().equals(player.getInventory().getItem(9).get(AppItems.APP_ID)), "Full hotbar did not overflow into inventory");
                    player.getInventory().setItem(4, ItemStack.EMPTY);
                });
            }
            context.runOnClient(client -> { try { AppsTestAccess.aresos$setApps(AppsConfig.load(config).apps()); } catch (Exception e) { throw new RuntimeException(e); } });
            try (var reopened = save.open()) {
                reopened.getConnection().waitForChunksRender();
                reopened.getServer().runOnServer(server -> {
                    var inv = reopened.getConnection().getServerPlayer().getInventory();
                    if (!app.id().equals(inv.getItem(4).get(AppItems.APP_ID))) failures.add("07b overflow rejoin: pinned app did not enter freed hotbar slot");
                    int count = 0;
                    for (int i = 0; i < inv.getContainerSize(); i++) if (app.id().equals(inv.getItem(i).get(AppItems.APP_ID))) count++;
                    check(count == 1, "Overflow placement duplicated/dropped app: " + count);
                    for (int i = 0; i < 9; i++) if (i != 4) check(inv.getItem(i).is(Items.STONE) && inv.getItem(i).getCount() == 12, "Ordinary hotbar item was overwritten");
                });
                context.getInput().pressKey(options -> options.keyInventory);
                context.waitForScreen(net.minecraft.client.gui.screens.inventory.InventoryScreen.class);
                screenshot(context, "07b-overflow-after-rejoin");
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
            }
            for (String failure : failures) AresOs.LOGGER.error(failure);
            check(failures.isEmpty(), String.join("; ", failures));
            AresOs.LOGGER.info("07b client checks passed: chest pin/unpin persisted; full-hotbar overflow moved into freed slot on rejoin; exactly one app; ordinary items preserved");
        } catch (Exception error) { throw new RuntimeException(error); }
        finally {
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(previous));
            if (previousConfig == null) System.clearProperty("aresos.appsConfig"); else System.setProperty("aresos.appsConfig", previousConfig);
        }
    }
    private static void openChest(net.minecraft.server.level.ServerPlayer player) {
        player.openMenu(new SimpleMenuProvider((id, inventory, p) -> ChestMenu.threeRows(id, inventory, new SimpleContainer(27)), Component.literal("07b chest fixture")));
    }
    private static void click(ClientGameTestContext context, int slot) {
        context.runOnClient(client -> {
            var screen = (ContainerScreen) client.gui.screen(); var target = client.player.containerMenu.getSlot(slot);
            var event = new MouseButtonEvent((screen.width - 176) / 2.0 + target.x + 8,
                    (screen.height - 168) / 2.0 + target.y + 8, new MouseButtonInfo(0, 0));
            screen.mouseClicked(event, false); screen.mouseDragged(event, 0, 0); screen.mouseReleased(event);
        });
        context.waitTick();
    }
    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.appsReviewDir"))));
    }
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
