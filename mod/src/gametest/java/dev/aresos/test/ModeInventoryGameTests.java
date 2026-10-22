package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.mode.ModeInventories;
import dev.aresos.mixin.GameModeAccess;
import dev.aresos.world.DesktopWorld;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.component.DataComponents;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.TagValueOutput;

import java.util.UUID;

import static dev.aresos.test.ModeInventoryFixtures.*;

public final class ModeInventoryGameTests {
    @GameTest(environment = "aresos-test:desktop")
    public void externalSurvivalChangeRestoresLiveInsteadOfOverwritingIt(GameTestHelper helper) {
        var player = join(helper, true);
        try {
            fill(player, false);
            var live = capture(player);
            check(switchAndAcknowledge(player, GameType.CREATIVE), "G to Build failed");
            fill(player, true);
            var build = capture(player);
            var server = player.level().getServer();
            server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withEntity(player), "gamemode survival @s");
            acknowledge(player);
            assertExact(player, live, "/gamemode survival must restore Live");
            check(switchAndAcknowledge(player, GameType.CREATIVE), "G after command failed");
            assertExact(player, build, "G after command must restore Build");
        } finally { leave(player); }
        helper.succeed();
    }

    private static ServerPlayer join(GameTestHelper helper, boolean desktop) {
        return connect(helper, desktop, true).player();
    }

    private record Connected(ServerPlayer player, EmbeddedChannel channel) { }

    private static Connected connect(GameTestHelper helper, boolean desktop, boolean supportsState) {
        var server = helper.getLevel().getServer();
        DesktopWorld.setEnabled(server, false);
        var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "InventoryTest"), false);
        var player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
        var connection = new Connection(PacketFlow.SERVERBOUND);
        var channel = new EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, player, cookie);
        if (supportsState) registerStateReceiver(player);
        player.setGameMode(GameType.SURVIVAL);
        DesktopWorld.setEnabled(server, desktop);
        return new Connected(player, channel);
    }

    private static void leave(ServerPlayer player) { player.level().getServer().getPlayerList().remove(player); }

    private static CompoundTag savedModes(ServerPlayer player) {
        var output = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, player.registryAccess());
        ModeInventories.of(player).write(output);
        return output.buildResult();
    }

    private static void readModes(ServerPlayer player, CompoundTag tag) {
        ModeInventories.of(player).read(TagValueInput.create(ProblemReporter.DISCARDING, player.registryAccess(), tag));
    }

    @GameTest(environment = "aresos-test:desktop")
    public void unregisteredStateChannelRefusesBeforeAnyMutation(GameTestHelper helper) {
        var fixture = connect(helper, true, false);
        var player = fixture.player();
        try {
            fill(player, false);
            var original = capture(player);
            var modes = ModeInventories.of(player);
            var stored = savedModes(player);
            var previousMode = player.gameMode.getPreviousGameModeForPlayer();
            long transaction = modes.pendingTransaction();
            check(!net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.canSend(player,
                    dev.aresos.mode.ModeSwitchStatePayload.TYPE), "Unsupported fixture registered the state channel");
            check(!player.setGameMode(GameType.CREATIVE), "Unregistered state channel accepted an external mode change");
            ((GameModeAccess) player.gameMode).aresos$setMode(GameType.CREATIVE, GameType.SURVIVAL);
            modes.rejectToggle(player);
            assertExact(player, original, "Unsupported protocol refusal");
            check(player.gameMode() == GameType.SURVIVAL && player.gameMode.getPreviousGameModeForPlayer() == previousMode,
                    "Unsupported protocol changed mode history");
            check(modes.activeInventory(player) == GameType.SURVIVAL && savedModes(player).equals(stored),
                    "Unsupported protocol changed ownership or snapshots");
            check(!modes.pending() && modes.pendingTransaction() == transaction, "Unsupported protocol began a transaction");
            check(fixture.channel().outboundMessages().stream().anyMatch(packet ->
                    packet instanceof net.minecraft.network.protocol.game.ClientboundSystemChatPacket chat
                            && chat.content().getString().contains("does not support")), "Unsupported protocol gave no visible explanation");
        } finally { leave(player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void lostAcknowledgementRollsBackOriginalStateWithinTimeout(GameTestHelper helper) {
        lostAcknowledgement(helper, false);
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void replacementKeepsOriginalRollbackAndDeadline(GameTestHelper helper) {
        lostAcknowledgement(helper, true);
    }

    private static void lostAcknowledgement(GameTestHelper helper, boolean replace) {
        var fixture = connect(helper, true, true);
        var player = fixture.player();
        var current = new ServerPlayer[]{player};
        fill(player, false);
        var live = capture(player);
        check(switchAndAcknowledge(player, GameType.CREATIVE), "Timeout setup failed");
        fill(player, true);
        var build = capture(player);
        player.getAbilities().flying = true;
        var previousMode = player.gameMode.getPreviousGameModeForPlayer();
        var stored = savedModes(player);
        var modes = ModeInventories.of(player);
        check(player.setGameMode(GameType.SURVIVAL), "Supported external switch was refused");
        assertExact(player, live, "Unacknowledged destination");
        long transaction = modes.pendingTransaction();
        modes.acknowledge(transaction - 1);
        check(modes.pending(), "Wrong acknowledgement released the lock");
        helper.runAtTickTime(100, () -> {
            check(modes.pending(), "Unacknowledged destination unlocked before rollback");
            assertExact(player, live, "Pending destination changed before timeout");
            if (replace) {
                var replacement = player.level().getServer().getPlayerList().respawn(player, true,
                        net.minecraft.world.entity.Entity.RemovalReason.KILLED);
                player.connection.player = replacement;
                current[0] = replacement;
                check(ModeInventories.of(replacement).pendingTransaction() == transaction
                        && ModeInventories.of(replacement).pending(), "Replacement lost pending transaction");
            }
        });
        helper.runAtTickTime(205, () -> {
            var restored = current[0];
            var restoredModes = ModeInventories.of(restored);
            try {
                assertExact(restored, build, "Lost acknowledgement must roll back Build");
                check(restored.gameMode() == GameType.CREATIVE && restored.gameMode.getPreviousGameModeForPlayer() == previousMode
                        && restored.getAbilities().flying, "Timeout lost original mode, history or flight");
                check(restoredModes.activeInventory(restored) == GameType.CREATIVE && savedModes(restored).equals(stored),
                        "Timeout changed original ownership or stored snapshots");
                check(!restoredModes.pending(), "Timeout left a pending switch");
                check(!fixture.channel().isOpen(), "Timeout left stale destination input on a live connection");
                check(fixture.channel().outboundMessages().stream().anyMatch(packet ->
                        packet instanceof net.minecraft.network.protocol.common.ClientboundDisconnectPacket disconnect
                                && disconnect.reason().getString().contains("timed out")
                                && disconnect.reason().getString().contains("restored")), "Timeout gave no visible recovery message");
                restoredModes.acknowledge(transaction);
                assertExact(restored, build, "Late acknowledgement changed rollback");
            } finally { leave(restored); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void pendingPickupSurvivesTimeoutAcrossBothInventoriesAndWorld(GameTestHelper helper) {
        var player = join(helper, true);
        var position = helper.absolutePos(new net.minecraft.core.BlockPos(1, 2, 1));
        player.snapTo(position.getX() + 0.5, position.getY(), position.getZ() + 0.5);
        var emerald = new ItemStack(Items.EMERALD);
        emerald.set(DataComponents.CUSTOM_NAME, Component.literal("Pickup " + player.getUUID()));
        player.getInventory().clearContent();
        player.getInventory().setItem(0, emerald.copyWithCount(2));
        check(switchAndAcknowledge(player, GameType.CREATIVE), "Pickup Build setup failed");
        player.getInventory().setItem(0, emerald.copyWithCount(3));
        var build = capture(player);
        check(player.setGameMode(GameType.SURVIVAL), "Pickup pending switch failed");
        var drop = new net.minecraft.world.entity.item.ItemEntity(player.level(), player.getX(), player.getY(), player.getZ(),
                emerald.copyWithCount(7));
        drop.setNoGravity(true);
        drop.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        drop.setNoPickUpDelay();
        drop.setTarget(player.getUUID());
        player.level().addFreshEntity(drop);
        check(totalItems(player, emerald) == 12, "Pickup fixture total was not 12: " + totalItems(player, emerald));
        // Exercise vanilla collision directly so this regression does not depend on world generation or movement.
        drop.playerTouch(player);
        helper.runAtTickTime(205, () -> {
            try {
                check(!ModeInventories.of(player).pending(), "Pickup timeout did not finish");
                check(totalItems(player, emerald) == 12,
                        "Pending pickup lost items on rollback: expected 12 across both inventories and world, got " + totalItems(player, emerald));
                assertExact(player, build, "Pickup timeout original Build");
                check(!drop.isRemoved() && drop.getItem().getCount() == 7, "Pending pickup did not leave the items in the world");
            } finally { drop.discard(); leave(player); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void pendingDirectWritesSurviveRollbackAndPlayerReplacement(GameTestHelper helper) {
        var player = join(helper, true);
        fill(player, false);
        check(switchAndAcknowledge(player, GameType.CREATIVE), "Direct-write setup failed");
        fill(player, true);
        var build = capture(player);
        check(player.setGameMode(GameType.SURVIVAL), "Direct-write switch failed");
        player.level().getServer().getCommands().performPrefixedCommand(
                player.level().getServer().createCommandSourceStack().withEntity(player), "item replace entity @s inventory.0 with diamond 7");
        check(player.getInventory().getItem(9).is(Items.DIAMOND) && player.getInventory().getItem(9).getCount() == 7,
                "Direct command fixture did not write the destination");
        // The same fallback covers dispenser equipment setters and transfers that mutate a stack in place.
        player.setItemSlot(net.minecraft.world.entity.EquipmentSlot.HEAD, new ItemStack(Items.DIAMOND_HELMET));
        player.getInventory().getItem(10).grow(3);
        var retainedLive = capturePersisted(player);
        var replacement = player.level().getServer().getPlayerList().respawn(player, true,
                net.minecraft.world.entity.Entity.RemovalReason.KILLED);
        player.connection.player = replacement;
        helper.runAtTickTime(205, () -> {
            try {
                check(!ModeInventories.of(replacement).pending(), "Direct-write timeout did not finish");
                assertExact(replacement, build, "Direct-write original Build rollback");
                assertInactive(replacement, retainedLive, "Direct-write retained Live after replacement/rollback");
                check(totalItems(replacement, Items.DIAMOND) == 7, "Direct command items vanished on rollback");
            } finally { leave(replacement); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void firstSwitchDirectWritesInitializeRetainedDestination(GameTestHelper helper) {
        var player = join(helper, true);
        fill(player, false);
        var live = capture(player);
        check(player.setGameMode(GameType.CREATIVE), "First direct-write switch failed");
        player.getInventory().setItem(8, new ItemStack(Items.LAPIS_LAZULI, 11));
        var retainedBuild = capturePersisted(player);
        helper.runAtTickTime(205, () -> {
            try {
                check(!ModeInventories.of(player).pending(), "First direct-write timeout did not finish");
                assertExact(player, live, "First direct-write original Live rollback");
                assertInactive(player, retainedBuild, "First direct-write retained Build");
            } finally { leave(player); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void refusedSwitchRetainsExternalChangesInOriginalInventory(GameTestHelper helper) {
        var player = join(helper, true);
        fill(player, false);
        ModeInventories.of(player).rejectToggle(player);
        player.getInventory().setItem(8, new ItemStack(Items.REDSTONE, 13));
        var retained = capture(player);
        helper.runAtTickTime(205, () -> {
            try {
                check(!ModeInventories.of(player).pending(), "Refused-switch timeout did not finish");
                assertExact(player, retained, "Refused-switch external changes");
                check(!ModeInventories.of(player).hasStoredInventories(), "Refused-switch recovery initialized snapshots");
            } finally { leave(player); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void pendingInsertionsAndMendingResumeOnlyAfterAcknowledgement(GameTestHelper helper) {
        for (var target : new GameType[]{GameType.SURVIVAL, GameType.CREATIVE}) {
            var player = join(helper, true);
            var position = helper.absolutePos(new net.minecraft.core.BlockPos(1, 2, 1));
            player.snapTo(position.getX() + 0.5, position.getY(), position.getZ() + 0.5);
            net.minecraft.world.entity.ExperienceOrb orb = null;
            net.minecraft.world.entity.item.ItemEntity drop = null;
            try {
                player.getInventory().clearContent();
                var tool = new ItemStack(Items.IRON_PICKAXE);
                tool.setDamageValue(50);
                tool.enchant(player.registryAccess().lookupOrThrow(net.minecraft.core.registries.Registries.ENCHANTMENT)
                        .getOrThrow(net.minecraft.world.item.enchantment.Enchantments.MENDING), 1);
                player.getInventory().setItem(0, tool);
                player.getInventory().setSelectedSlot(0);
                player.getInventory().setItem(1, new ItemStack(Items.COPPER_INGOT, 2));
                check(switchAndAcknowledge(player, GameType.CREATIVE), "Insertion Build setup failed");
                player.getInventory().setItem(0, tool.copy());
                player.getInventory().setItem(1, new ItemStack(Items.COPPER_INGOT, 2));
                if (target == GameType.CREATIVE) check(switchAndAcknowledge(player, GameType.SURVIVAL), "Insertion Live setup failed");
                check(player.setGameMode(target), "Insertion pending switch failed");
                var original = capture(player);
                var incoming = new ItemStack(Items.COPPER_INGOT, 5);
                check(!player.getInventory().add(incoming) && incoming.getCount() == 5, "Pending add consumed its source stack in " + target);
                var damaged = new ItemStack(Items.IRON_AXE);
                damaged.setDamageValue(12);
                check(!player.getInventory().add(4, damaged) && damaged.getCount() == 1 && damaged.getDamageValue() == 12,
                        "Pending indexed/damaged add consumed its source stack");
                check(net.minecraft.world.level.block.entity.HopperBlockEntity.addItem(null, player.getInventory(), incoming, null).getCount() == 5,
                        "Pending hopper merge consumed its source stack");
                check(net.minecraft.world.level.block.entity.HopperBlockEntity.addItem(null, player.getInventory(), damaged, null).getCount() == 1,
                        "Pending hopper insertion consumed its source stack");
                check(!player.getInventory().canTakeItem(new SimpleContainer(1), 1, player.getInventory().getItem(1)),
                        "Pending inventory allowed hopper extraction");
                orb = new net.minecraft.world.entity.ExperienceOrb(player.level(), player.getX(), player.getY(), player.getZ(), 5);
                player.level().addFreshEntity(orb);
                int xp = player.totalExperience;
                player.takeXpDelay = 0;
                orb.playerTouch(player);
                check(!orb.isRemoved() && player.totalExperience == xp && player.takeXpDelay == 0,
                        "Pending XP pickup spent the orb or XP delay");
                assertExact(player, original, "Pending insertion/mending in " + target);
                var returned = new ItemStack(Items.GOLD_INGOT, 4);
                player.getInventory().placeItemBackInInventory(returned);
                var returnedDrops = player.level().getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class,
                        player.getBoundingBox().inflate(4), entity -> entity.getItem() == returned);
                check(returnedDrops.size() == 1 && returnedDrops.getFirst().getItem().getCount() == 4,
                        "Pending returned stack was split/lost instead of dropped");
                returnedDrops.getFirst().discard();
                acknowledge(player);
                check(player.getInventory().add(incoming) && incoming.isEmpty(), "Acknowledgement did not restore insertions");
                check(net.minecraft.world.level.block.entity.HopperBlockEntity.addItem(null, player.getInventory(), damaged, null).isEmpty(),
                        "Acknowledgement did not restore hopper insertion");
                orb.playerTouch(player);
                check(orb.isRemoved() && player.getInventory().getItem(0).getDamageValue() < 50,
                        "Acknowledgement did not restore mending");
                drop = new net.minecraft.world.entity.item.ItemEntity(player.level(), player.getX(), player.getY(), player.getZ(), new ItemStack(Items.COAL, 3));
                drop.setNoPickUpDelay();
                player.level().addFreshEntity(drop);
                drop.playerTouch(player);
                check(drop.isRemoved(), "Acknowledgement did not restore item pickup");
            } finally {
                if (orb != null) orb.discard();
                if (drop != null) drop.discard();
                leave(player);
            }
        }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 240)
    public void acknowledgementCancelsRollbackDeadline(GameTestHelper helper) {
        var player = join(helper, true);
        fill(player, false);
        check(switchAndAcknowledge(player, GameType.CREATIVE), "Acknowledged setup switch failed");
        fill(player, true);
        var build = capture(player);
        var stored = savedModes(player);
        helper.runAtTickTime(205, () -> {
            try {
                assertExact(player, build, "Acknowledged switch rolled back later");
                check(player.gameMode() == GameType.CREATIVE && !ModeInventories.of(player).pending()
                        && savedModes(player).equals(stored), "Acknowledged switch retained its recovery deadline");
            } finally { leave(player); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void exactInventoriesSurviveFiftyRapidSwitches(GameTestHelper helper) {
        var player = join(helper, true);
        try {
            fill(player, false);
            var live = capture(player);
            var modes = ModeInventories.of(player);
            check(switchAndAcknowledge(player, GameType.CREATIVE), "First Build switch failed");
            check(player.getInventory().isEmpty() && player.getInventory().getSelectedSlot() == 0, "First Build inventory was not empty");
            fill(player, true);
            var build = capture(player);
            for (int i = 0; i < 50; i++) {
                boolean toLive = i % 2 == 0;
                check(switchAndAcknowledge(player, toLive ? GameType.SURVIVAL : GameType.CREATIVE), "Rapid switch failed: " + i);
                assertExact(player, toLive ? live : build, "Rapid switch " + i);
            }
        } finally { leave(player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void failedSaveAndLoadsPreserveOriginalState(GameTestHelper helper) {
        var player = join(helper, true);
        try {
            fill(player, false);
            // This component's persistent codec requires a positive stack size.
            player.getInventory().getItem(0).set(DataComponents.MAX_STACK_SIZE, 0);
            var original = capture(player);
            var modes = ModeInventories.of(player);
            check(!switchAndAcknowledge(player, GameType.CREATIVE), "Invalid item unexpectedly serialized");
            assertExact(player, original, "Failed save");
            check(player.gameMode() == GameType.SURVIVAL && !modes.hasStoredInventories(), "Failed save committed mode or snapshots");
            fill(player, false);
            original = capture(player);
            check(switchAndAcknowledge(player, GameType.CREATIVE), "Setup switch failed");
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Setup return failed");
            var valid = savedModes(player);
            for (String corruption : new String[]{"slot", "item", "version", "type"}) {
                var broken = valid.copy();
                var data = broken.getCompoundOrEmpty(ModeInventories.SAVE_KEY);
                switch (corruption) {
                    case "slot" -> data.getCompoundOrEmpty("build").putInt("selected", 9);
                    case "item" -> data.getCompoundOrEmpty("build").getListOrEmpty("items").set(0, new CompoundTag());
                    case "version" -> data.putInt("version", 999);
                    case "type" -> broken.put(ModeInventories.SAVE_KEY, StringTag.valueOf("unreadable"));
                }
                // An unknown item must fail rather than becoming an empty slot.
                if (corruption.equals("item")) {
                    var unknown = new CompoundTag(); unknown.putString("id", "aresos:unknown_item"); unknown.putInt("count", 1);
                    data.getCompoundOrEmpty("build").getListOrEmpty("items").set(0, unknown);
                }
                readModes(player, broken);
                check(!switchAndAcknowledge(player, GameType.CREATIVE), "Corrupt load accepted: " + corruption);
                assertExact(player, original, "Failed load " + corruption);
                check(player.gameMode() == GameType.SURVIVAL && savedModes(player).equals(broken), "Failed load discarded data or mode");
            }
            readModes(player, valid);
        } finally { leave(player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void failureAfterModeChangeRollsBackInventoryModeAndFlight(GameTestHelper helper) {
        var player = join(helper, true);
        try {
            fill(player, false);
            var live = capture(player);
            var modes = ModeInventories.of(player);
            check(switchAndAcknowledge(player, GameType.CREATIVE), "Rollback setup failed");
            fill(player, true);
            var build = capture(player);
            player.getAbilities().flying = true;
            var before = savedModes(player);
            ModeSwitchFaults.failAfterModeChange = player.getUUID();
            check(!switchAndAcknowledge(player, GameType.SURVIVAL), "Injected mode failure committed");
            assertExact(player, build, "Rollback after mode mutation");
            check(player.gameMode() == GameType.CREATIVE && player.getAbilities().flying
                    && savedModes(player).equals(before), "Rollback lost mode, flight or stored snapshots");
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Valid retry after rollback failed");
            assertExact(player, live, "Retry after rollback");
        } finally { ModeSwitchFaults.failAfterModeChange = null; leave(player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void playersNeverShareSnapshots(GameTestHelper helper) {
        var first = join(helper, true);
        var second = join(helper, true);
        try {
            fill(first, false);
            fill(second, true);
            var firstLive = capture(first);
            var secondLive = capture(second);
            check(switchAndAcknowledge(first, GameType.CREATIVE), "First player switch failed");
            assertExact(second, secondLive, "Other player's active inventory");
            check(!ModeInventories.of(second).hasStoredInventories(), "First player created second player's snapshots");
            check(switchAndAcknowledge(second, GameType.CREATIVE), "Second player switch failed");
            check(switchAndAcknowledge(first, GameType.SURVIVAL), "First player return failed");
            check(switchAndAcknowledge(second, GameType.SURVIVAL), "Second player return failed");
            assertExact(first, firstLive, "First player's Live");
            assertExact(second, secondLive, "Second player's Live");
        } finally { leave(first); leave(second); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void containerCursorAndCraftingRefuseWithoutMovingItems(GameTestHelper helper) {
        var player = join(helper, true);
        try {
            fill(player, false);
            var original = capture(player);
            var modes = ModeInventories.of(player);
            player.openMenu(new SimpleMenuProvider((id, inventory, p) -> ChestMenu.threeRows(id, inventory, new SimpleContainer(27)), Component.literal("Inventory fixture")));
            check(!switchAndAcknowledge(player, GameType.CREATIVE), "Open chest allowed switching");
            assertExact(player, original, "Open chest refusal");
            player.closeContainer();
            var carried = new ItemStack(Items.DIAMOND, 7);
            player.inventoryMenu.setCarried(carried);
            check(!switchAndAcknowledge(player, GameType.CREATIVE), "Cursor allowed switching");
            check(ItemStack.matches(player.inventoryMenu.getCarried(), carried), "Refusal lost cursor item");
            player.inventoryMenu.setCarried(ItemStack.EMPTY);
            player.inventoryMenu.getCraftSlots().setItem(0, new ItemStack(Items.OAK_PLANKS, 4));
            check(!switchAndAcknowledge(player, GameType.CREATIVE), "Crafting allowed switching");
            check(player.inventoryMenu.getCraftSlots().getItem(0).getCount() == 4, "Refusal changed crafting stack");
            assertExact(player, original, "Crafting refusal");
            check(player.gameMode() == GameType.SURVIVAL && !modes.hasStoredInventories(), "Menu refusal changed mode or created snapshots");
            player.inventoryMenu.getCraftSlots().clearContent();
        } finally { leave(player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:normal")
    public void normalWorldNeverCreatesInventoryStorage(GameTestHelper helper) {
        var player = join(helper, false);
        try {
            fill(player, false);
            var original = capture(player);
            check(!switchAndAcknowledge(player, GameType.CREATIVE), "Normal world switched");
            assertExact(player, original, "Normal world");
            var output = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, player.registryAccess());
            player.saveWithoutId(output);
            check(!output.buildResult().contains(ModeInventories.SAVE_KEY), "Normal world created stored inventories");
        } finally { leave(player); }
        helper.succeed();
    }
}
