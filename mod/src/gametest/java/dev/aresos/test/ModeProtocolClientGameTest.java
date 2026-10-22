package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.mode.ModeInventories;
import dev.aresos.mode.ModeSwitchStatePayload;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.ModeSyncTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.world.level.GameType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.Vec3;

import java.nio.file.Path;

import static dev.aresos.test.ModeInventoryFixtures.*;

public final class ModeProtocolClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        TestWorldSave save;
        PersistedInventory live;
        PersistedInventory build;
        var world = context.worldBuilder().create();
        boolean disconnected = false;
        try {
            save = world.getWorldSave();
            world.getConnection().waitForChunksRender();
            live = world.getServer().computeOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                player.setGameMode(GameType.SURVIVAL);
                DesktopWorld.setEnabled(server, true);
                fill(player, false);
                player.getInventory().setItem(9, ItemStack.EMPTY);
                player.getInventory().setItem(10, new ItemStack(Items.EMERALD, 2));
                ModeSyncTestAccess.aresos$release(player);
                return capturePersisted(player);
            });
            try {
                context.runOnClient(client -> check(ClientPlayNetworking.unregisterReceiver(ModeSwitchStatePayload.TYPE.id()) != null,
                        "State receiver was not registered before removal"));
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(!ServerPlayNetworking.canSend(player, ModeSwitchStatePayload.TYPE), "Unregistration did not reach server");
                    check(!player.setGameMode(GameType.CREATIVE), "Unsupported real client entered Build");
                    assertPersisted(player, live, "Unsupported real client retained Live");
                    check(player.gameMode() == GameType.SURVIVAL && !ModeInventories.of(player).pending()
                            && !ModeInventories.of(player).hasStoredInventories(), "Unsupported real client changed mode or transaction state");
                });
                context.waitFor(client -> ((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().stream()
                        .anyMatch(message -> message.content().getString().contains("does not support")));
                screenshot(context, "09c-unsupported-client");
            } finally {
                context.runOnClient(client -> ClientPlayNetworking.registerReceiver(ModeSwitchStatePayload.TYPE,
                        (state, packetContext) -> ModeSwitchClient.receive(state)));
            }
            world.getConnection().waitForServerboundPackets();
            toggle(context, world, GameType.CREATIVE);
            build = world.getServer().computeOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                fill(player, true);
                player.getInventory().setItem(10, new ItemStack(Items.EMERALD, 3));
                ModeSyncTestAccess.aresos$release(player);
                return capturePersisted(player);
            });
            ModeSyncDelay.dropAcknowledgements = true;
            world.getServer().runOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                check(player.setGameMode(GameType.SURVIVAL), "Supported external change refused");
                check(ModeInventories.of(player).pending(), "Supported external change bypassed acknowledgement");
                assertPersisted(player, live, "Prepared timeout destination");
                var drop = new ItemEntity(player.level(), player.getX(), player.getY(), player.getZ(), new ItemStack(Items.EMERALD, 7));
                drop.setNoGravity(true);
                drop.setDeltaMovement(Vec3.ZERO);
                drop.setNoPickUpDelay();
                player.level().addFreshEntity(drop);
                check(totalItems(player, Items.EMERALD) == 12, "Client pickup fixture total was not 12");
                drop.playerTouch(player);
                // Keep the collision site loaded but away from the reconnect spawn, where pickups are allowed again.
                if (!drop.isRemoved()) drop.setPos(player.getX() + 4, player.getY(), player.getZ());
            });
            context.waitFor(client -> !ModeSwitchClient.pending() && client.gameMode.getPlayerMode() == GameType.SURVIVAL);
            world.getConnection().waitForServerboundPackets();
            world.getServer().runOnServer(server -> check(ModeInventories.of(world.getConnection().getServerPlayer()).pending(),
                    "Dropped acknowledgement released the server lock"));
            context.waitFor(client -> client.gui.screen() instanceof DisconnectedScreen, 600);
            disconnected = true;
            context.runOnClient(client -> {
                String message = client.gui.screen().getNarrationMessage().getString();
                check(message.contains("timed out") && message.contains("restored") && message.contains("Reconnect"),
                        "Timeout screen omitted recovery explanation");
            });
            screenshot(context, "09c-timeout-recovery");
        } finally {
            ModeSyncDelay.dropAcknowledgements = false;
            if (disconnected) {
                // The timeout already closed the world; Fabric's context.close() requires a connected world.
                context.waitFor(client -> client.getSingleplayerServer() == null);
                context.setScreen(TitleScreen::new);
            } else world.close();
        }
        try (var reopened = save.open()) {
            reopened.getConnection().waitForChunksRender();
            reopened.getServer().runOnServer(server -> {
                var player = reopened.getConnection().getServerPlayer();
                check(player.gameMode() == GameType.CREATIVE && !ModeInventories.of(player).pending(), "Timeout recovery did not persist original Build mode");
                assertPersisted(player, build, "Timeout recovery persisted original Build");
                check(totalItems(player, Items.EMERALD) == 12,
                        "Pending pickup lost items after timeout/reconnect: expected 12 across both inventories and world, got "
                                + totalItems(player, Items.EMERALD));
                check(player.level().getEntitiesOfClass(ItemEntity.class,
                        player.getBoundingBox().inflate(8), drop -> drop.getItem().is(Items.EMERALD)
                                && drop.getItem().getCount() == 7).size() == 1, "Pending pickup did not survive in the world after reconnect");
            });
            context.runOnClient(client -> {
                client.player.setYRot(-90);
                client.player.setXRot(22);
            });
            context.waitTicks(4);
            screenshot(context, "09d-pickup-after-reconnect");
            toggle(context, reopened, GameType.SURVIVAL);
            reopened.getServer().runOnServer(server -> assertPersisted(reopened.getConnection().getServerPlayer(), live,
                    "Timeout recovery retained inactive Live"));
            toggle(context, reopened, GameType.CREATIVE);
            reopened.getServer().runOnServer(server -> assertPersisted(reopened.getConnection().getServerPlayer(), build,
                    "Timeout recovery retained Build after retry"));
        }
        AresOs.LOGGER.info("09c client checks passed: unregistered receiver refuses unchanged; lost ACK disconnects visibly; original Build and inactive Live survive restart and retry");
        AresOs.LOGGER.info("09d client checks passed: pending pickup preserves all 12 emeralds across both inventories and the world after timeout and reconnect");
    }

    private static void toggle(ClientGameTestContext context, TestSingleplayerContext world, GameType target) {
        context.getInput().pressKey(InputConstants.KEY_G);
        context.waitFor(client -> !ModeSwitchClient.pending() && client.gameMode.getPlayerMode() == target);
        world.getConnection().waitForServerboundPackets();
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.modeReviewDir"))));
    }
}
