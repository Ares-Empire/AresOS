package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.mode.ModeInventories;
import dev.aresos.mode.ToggleModePayload;
import dev.aresos.test.mixin.ModeSyncTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.HashedStack;
import net.minecraft.network.protocol.game.*;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;

import java.nio.file.Path;

import static dev.aresos.test.ModeInventoryFixtures.*;

public final class ModeSwitchSafetyClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        TestWorldSave save;
        PersistedInventory savedLive;
        PersistedInventory savedBuild;
        try (var world = context.worldBuilder().adjustSettings(settings -> settings.setAllowCommands(true)).create()) {
            try {
                save = world.getWorldSave();
                world.getConnection().waitForChunksRender();
                var live = world.getServer().computeOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    player.setGameMode(GameType.SURVIVAL);
                    DesktopWorld.setEnabled(server, true);
                    for (int x = -3; x <= 3; x++) for (int z = -3; z <= 3; z++)
                        player.level().setBlockAndUpdate(new BlockPos(x, 149, z), Blocks.STONE.defaultBlockState());
                    player.teleportTo(0.5, 150, 0.5);
                    fill(player, false);
                    player.inventoryMenu.sendAllDataToRemote();
                    for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
                        player.connection.send(new ClientboundSetPlayerInventoryPacket(slot, player.getInventory().getItem(slot).copy()));
                    player.connection.send(new ClientboundSetHeldSlotPacket(player.getInventory().getSelectedSlot()));
                    return capture(player);
                });
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL);
                toggle(context, world, GameType.CREATIVE);
                var build = world.getServer().computeOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    fill(player, true);
                    player.inventoryMenu.sendAllDataToRemote();
                    for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
                        player.connection.send(new ClientboundSetPlayerInventoryPacket(slot, player.getInventory().getItem(slot).copy()));
                    player.connection.send(new ClientboundSetHeldSlotPacket(player.getInventory().getSelectedSlot()));
                    return capture(player);
                });
                context.waitFor(client -> ItemStack.matches(client.player.getInventory().getItem(0), build.items().getFirst())
                        && client.player.getInventory().getSelectedSlot() == build.selected());
                delayedSwitch(context, world, build, live, false);
                delayedSwitch(context, world, live, build, true);
                // Same-position fixture respawn reuses already-compiled sections; rebuild to complete vanilla's load callback.
                context.runOnClient(client -> client.levelExtractor.allChanged());
                world.getConnection().waitForChunksRender();
                context.waitForScreen(null);
                world.getConnection().waitForServerboundPackets();

                // Failure receives the same full-state boundary and must release both locks for a real retry.
                world.getServer().runOnServer(server -> ModeSwitchFaults.failAfterModeChange = world.getConnection().getServerPlayer().getUUID());
                context.getInput().pressKey(InputConstants.KEY_G);
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client -> !ModeSwitchClient.pending());
                world.getConnection().waitForServerboundPackets();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(ModeSwitchFaults.failAfterModeChange == null, "Failure fixture was not exercised");
                    check(!ModeInventories.of(player).pending() && player.gameMode() == GameType.CREATIVE, "Failure did not release server lock");
                    assertExact(player, build, "Failed switch retained Build");
                });
                toggle(context, world, GameType.SURVIVAL);
                world.getServer().runOnServer(server -> assertExact(world.getConnection().getServerPlayer(), live, "Retry retained Live"));
                toggle(context, world, GameType.CREATIVE);
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withEntity(player), "gamemode survival @s");
                    assertExact(player, live, "Command restored Live before immediate save/rejoin");
                    server.getPlayerList().saveAll();
                });
                savedLive = world.getServer().computeOnServer(server -> capturePersisted(world.getConnection().getServerPlayer()));
                // Obtain Build's registry-independent expected value without another switch.
                savedBuild = world.getServer().computeOnServer(server -> {
                    var ops = world.getConnection().getServerPlayer().registryAccess().createSerializationContext(net.minecraft.nbt.NbtOps.INSTANCE);
                    return new PersistedInventory(build.items().stream().map(stack -> ItemStack.OPTIONAL_CODEC.encodeStart(ops, stack).getOrThrow()).toList(), build.selected());
                });
            } catch (RuntimeException | Error error) {
                context.runOnClient(client -> AresOs.LOGGER.error("09b client screen={}, pending={}, player={}", client.gui.screen(), ModeSwitchClient.pending(), client.player));
                AresOs.LOGGER.error("09b client failure before world cleanup", error);
                throw error;
            }
        } finally { ModeSyncDelay.player = null; ModeSwitchFaults.failAfterModeChange = null; }
        try (var reopened = save.open()) {
            reopened.getServer().runOnServer(server -> {
                var player = reopened.getConnection().getServerPlayer();
                check(player.gameMode() == GameType.SURVIVAL && !ModeInventories.of(player).pending(), "Rejoin retained a pending lock or wrong mode");
                assertPersisted(player, savedLive, "Command Live survived rejoin");
            });
            toggle(context, reopened, GameType.CREATIVE);
            reopened.getServer().runOnServer(server -> assertPersisted(reopened.getConnection().getServerPlayer(), savedBuild, "Command then rejoin then G retained Build"));
            toggle(context, reopened, GameType.SURVIVAL);
            reopened.getServer().runOnServer(server -> assertPersisted(reopened.getConnection().getServerPlayer(), savedLive, "Original Live intact after rejoin and G"));
        }
        AresOs.LOGGER.info("09b client checks passed: delayed G and external mode change block client predictions and stale server packets; wrong/early ACK ignored; failure unlocks; command/rejoin retains both inventories");
    }

    private static void delayedSwitch(ClientGameTestContext context, TestSingleplayerContext world,
                                      Inventory source, Inventory destination, boolean external) {
        world.getServer().runOnServer(server -> ModeSyncDelay.player = world.getConnection().getServerPlayer().getUUID());
        if (external) context.runOnClient(client -> client.getConnection().send(new ServerboundChangeGameModePacket(GameType.CREATIVE)));
        else context.getInput().pressKey(InputConstants.KEY_G);
        world.getConnection().waitForServerboundPackets();
        context.waitFor(client -> ModeSwitchClient.pending());
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            assertExact(player, destination, "Delayed destination");
            var modes = ModeInventories.of(player);
            modes.acknowledge(modes.pendingTransaction() - 1);
            modes.acknowledge(modes.pendingTransaction());
            check(modes.pending(), "Wrong or premature acknowledgement released the server lock");
        });
        var target = world.getServer().computeOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var cow = new net.minecraft.world.entity.animal.cow.Cow(net.minecraft.world.entity.EntityTypes.COW, player.level());
            cow.setNoAi(true);
            cow.snapTo(player.getX() + 1, player.getY(), player.getZ(), 0, 0);
            player.level().addFreshEntity(cow);
            return cow.getId();
        });
        context.waitFor(client -> client.level.getEntity(target) != null);
        context.runOnClient(client -> assertPlayerExact(client.player, source, "Old inventory must remain displayed until full sync"));
        context.getInput().pressKey(InputConstants.KEY_Q);
        context.runOnClient(client -> client.getConnection().send(new ServerboundPlayerActionPacket(
                ServerboundPlayerActionPacket.Action.DROP_ITEM, BlockPos.ZERO, Direction.DOWN)));
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> assertExact(world.getConnection().getServerPlayer(), destination, "Delayed switch accepted a stale drop"));
        context.getInput().pressKey(InputConstants.KEY_F);
        context.getInput().pressKey(InputConstants.KEY_9);
        context.getInput().pressKey(InputConstants.KEY_E);
        context.runOnClient(client -> {
            client.player.drop(true);
            client.gameMode.handleContainerInput(0, 36, 0, ContainerInput.PICKUP, client.player);
            client.gameMode.handleCreativeModeItemAdd(new ItemStack(Items.DIAMOND, 64), 36);
            client.gameMode.useItem(client.player, InteractionHand.OFF_HAND);
            client.gameMode.startDestroyBlock(new BlockPos(1, 149, 0), Direction.UP);
            client.gameMode.attack(client.player, client.level.getEntity(target));
            var connection = client.getConnection();
            connection.send(new ServerboundPlayerActionPacket(ServerboundPlayerActionPacket.Action.SWAP_ITEM_WITH_OFFHAND, BlockPos.ZERO, Direction.DOWN));
            connection.send(new ServerboundSetCarriedItemPacket(8));
            connection.send(new ServerboundContainerClickPacket(0, client.player.containerMenu.getStateId(), (short) 36, (byte) 0,
                    ContainerInput.PICKUP, new Int2ObjectOpenHashMap<>(), HashedStack.EMPTY));
            connection.send(new ServerboundSetCreativeModeSlotPacket(36, new ItemStack(Items.DIAMOND, 64)));
            connection.send(new ServerboundUseItemPacket(InteractionHand.OFF_HAND, 0, 0, 0));
            connection.send(new ServerboundAttackPacket(target));
            connection.send(new ServerboundInteractPacket(target, InteractionHand.MAIN_HAND, new Vec3(0, 0.5, 0), false));
            connection.send(new ServerboundUseItemOnPacket(InteractionHand.OFF_HAND,
                    new BlockHitResult(new Vec3(1.5, 150, 0.5), Direction.UP, new BlockPos(1, 149, 0), false), 0));
            connection.send(new ServerboundPlayerActionPacket(ServerboundPlayerActionPacket.Action.START_DESTROY_BLOCK, new BlockPos(1, 149, 0), Direction.UP));
            ClientPlayNetworking.send(ToggleModePayload.INSTANCE);
        });
        context.getInput().pressKey(InputConstants.KEY_G);
        context.waitTicks(3);
        world.getConnection().waitForServerboundPackets();
        context.runOnClient(client -> {
            check(ModeSwitchClient.pending() && client.gui.screen() == null, "Transition unexpectedly unlocked or opened a menu");
            assertPlayerExact(client.player, source, "Local actions during delayed sync");
            check(client.player.containerMenu.getCarried().isEmpty(), "Client predicted a cursor move");
        });
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            assertExact(player, destination, "Actions during delayed sync");
            check(player.inventoryMenu.getCarried().isEmpty(), "Delayed click moved cursor items");
            check(player.level().getBlockState(new BlockPos(1, 149, 0)).is(Blocks.STONE)
                    && player.level().getBlockState(new BlockPos(1, 150, 0)).isAir(), "Stale use/attack changed the world");
            var cow = (net.minecraft.world.entity.LivingEntity) player.level().getEntity(target);
            check(cow != null && cow.isAlive() && cow.getHealth() == cow.getMaxHealth(), "Stale attack damaged an entity");
            cow.discard();
        });
        if (!external) context.takeScreenshot(TestScreenshotOptions.of("09b-switch-pending").withDestinationDir(Path.of(System.getProperty("aresos.modeReviewDir"))));
        if (external) world.getServer().runOnServer(server -> {
            var old = world.getConnection().getServerPlayer();
            long transaction = ModeInventories.of(old).pendingTransaction();
            var replacement = server.getPlayerList().respawn(old, true, net.minecraft.world.entity.Entity.RemovalReason.KILLED);
            old.connection.player = replacement;
            check(ModeInventories.of(replacement).pending() && ModeInventories.of(replacement).pendingTransaction() == transaction,
                    "Player replacement lost the pending transaction");
            assertExact(replacement, destination, "Replacement retained destination and ownership");
        });
        world.getServer().runOnServer(server -> {
            ModeSyncDelay.player = null;
            ModeSyncTestAccess.aresos$release(world.getConnection().getServerPlayer());
        });
        context.waitFor(client -> !ModeSwitchClient.pending());
        world.getConnection().waitForServerboundPackets();
        context.runOnClient(client -> assertPlayerExact(client.player, destination, "Complete client destination"));
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(!ModeInventories.of(player).pending(), "Client acknowledgement did not release server lock");
            assertExact(player, destination, "Complete server destination");
        });
    }

    private static void toggle(ClientGameTestContext context, TestSingleplayerContext world, GameType target) {
        context.getInput().pressKey(InputConstants.KEY_G);
        context.waitFor(client -> !ModeSwitchClient.pending() && client.gameMode.getPlayerMode() == target);
        world.getConnection().waitForServerboundPackets();
    }
}
