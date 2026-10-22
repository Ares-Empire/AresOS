package dev.aresos.test;

import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;

import java.util.ArrayList;
import java.util.List;

final class ModeInventoryFixtures {
    static void registerStateReceiver(ServerPlayer player) {
        // Embedded connections have no client handshake. Advertise the receiver through Fabric's real registration path.
        net.fabricmc.fabric.impl.networking.server.ServerNetworkingImpl.getAddon(player.connection).handle(
                new net.fabricmc.fabric.impl.networking.RegistrationPayload(
                        net.fabricmc.fabric.impl.networking.RegistrationPayload.REGISTER,
                        List.of(dev.aresos.mode.ModeSwitchStatePayload.TYPE.id())));
        check(net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.canSend(player,
                dev.aresos.mode.ModeSwitchStatePayload.TYPE), "Fixture did not register the state channel");
    }

    static void acknowledge(net.minecraft.server.level.ServerPlayer player) {
        var modes = dev.aresos.mode.ModeInventories.of(player);
        modes.acknowledge(modes.pendingTransaction());
    }

    static boolean switchAndAcknowledge(net.minecraft.server.level.ServerPlayer player, net.minecraft.world.level.GameType target) {
        boolean switched = dev.aresos.mode.ModeInventories.of(player).switchTo(player, target, true);
        // Server-only fixtures have no client; explicitly simulate receipt of the complete state.
        acknowledge(player);
        return switched;
    }

    record Inventory(List<ItemStack> items, int selected) { }
    record PersistedInventory(List<Tag> items, int selected) { }

    static PersistedInventory capturePersisted(ServerPlayer player) {
        var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
        var items = new ArrayList<Tag>();
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
            items.add(ItemStack.OPTIONAL_CODEC.encodeStart(ops, player.getInventory().getItem(slot)).getOrThrow());
        return new PersistedInventory(List.copyOf(items), player.getInventory().getSelectedSlot());
    }

    static void assertPersisted(ServerPlayer player, PersistedInventory expected, String message) {
        // Dynamic registry holders have new identities after a server restart. Compare every persisted component by value.
        check(capturePersisted(player).equals(expected), message + ": serialized items/components/counts/slots or selected slot changed");
        var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
        var rebound = expected.items.stream().map(tag -> ItemStack.OPTIONAL_CODEC.parse(ops, tag).getOrThrow()).toList();
        assertExact(player, new Inventory(rebound, expected.selected), message);
    }

    static Inventory capture(ServerPlayer player) {
        return capturePlayer(player);
    }

    static int totalItems(ServerPlayer player, net.minecraft.world.item.Item item) {
        return totalItems(player, stack -> stack.is(item));
    }

    static int totalItems(ServerPlayer player, ItemStack prototype) {
        return totalItems(player, stack -> ItemStack.isSameItemSameComponents(stack, prototype));
    }

    private static int totalItems(ServerPlayer player, java.util.function.Predicate<ItemStack> matches) {
        int total = 0;
        for (var stack : capture(player).items()) if (matches.test(stack)) total += stack.getCount();
        var output = net.minecraft.world.level.storage.TagValueOutput.createWithContext(
                net.minecraft.util.ProblemReporter.DISCARDING, player.registryAccess());
        var modes = dev.aresos.mode.ModeInventories.of(player);
        modes.write(output);
        var stored = output.buildResult().getCompoundOrEmpty(dev.aresos.mode.ModeInventories.SAVE_KEY);
        String inactive = modes.activeInventory(player) == net.minecraft.world.level.GameType.CREATIVE ? "live" : "build";
        var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
        for (var tag : stored.getCompoundOrEmpty(inactive).getListOrEmpty("items")) {
            var stack = ItemStack.OPTIONAL_CODEC.parse(ops, tag).getOrThrow();
            if (matches.test(stack)) total += stack.getCount();
        }
        for (var entity : player.level().getAllEntities())
            if (entity instanceof net.minecraft.world.entity.item.ItemEntity drop && !drop.isRemoved() && matches.test(drop.getItem()))
                total += drop.getItem().getCount();
        return total;
    }

    static void assertInactive(ServerPlayer player, PersistedInventory expected, String message) {
        var output = net.minecraft.world.level.storage.TagValueOutput.createWithContext(
                net.minecraft.util.ProblemReporter.DISCARDING, player.registryAccess());
        var modes = dev.aresos.mode.ModeInventories.of(player);
        modes.write(output);
        String inactive = modes.activeInventory(player) == net.minecraft.world.level.GameType.CREATIVE ? "live" : "build";
        var tag = output.buildResult().getCompoundOrEmpty(dev.aresos.mode.ModeInventories.SAVE_KEY).getCompoundOrEmpty(inactive);
        check(tag.getListOrEmpty("items").stream().toList().equals(expected.items())
                && tag.getIntOr("selected", -1) == expected.selected(), message + ": inactive items/components/counts/slots or selection changed");
    }

    static Inventory capturePlayer(net.minecraft.world.entity.player.Player player) {
        var items = new ArrayList<ItemStack>();
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
            items.add(player.getInventory().getItem(slot).copy());
        return new Inventory(List.copyOf(items), player.getInventory().getSelectedSlot());
    }

    static void assertExact(ServerPlayer player, Inventory expected, String message) {
        assertPlayerExact(player, expected, message);
    }

    static void assertPlayerExact(net.minecraft.world.entity.player.Player player, Inventory expected, String message) {
        var actual = capturePlayer(player);
        check(actual.selected == expected.selected, message + ": selected slot " + actual.selected);
        check(actual.items.size() == expected.items.size(), message + ": slot count");
        for (int slot = 0; slot < actual.items.size(); slot++)
            check(ItemStack.matches(actual.items.get(slot), expected.items.get(slot)), message + ": item/components/count in slot " + slot
                    + "; actual=" + actual.items.get(slot) + " " + actual.items.get(slot).getComponentsPatch()
                    + "; expected=" + expected.items.get(slot) + " " + expected.items.get(slot).getComponentsPatch());
    }

    static void fill(ServerPlayer player, boolean build) {
        var inventory = player.getInventory();
        inventory.clearContent();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            var stack = new ItemStack(build ? Items.QUARTZ_BLOCK : Items.PAPER, slot + 1);
            stack.set(DataComponents.CUSTOM_NAME, Component.literal((build ? "Build " : "Live ") + slot));
            var data = new CompoundTag();
            data.putString("mode", build ? "build" : "live");
            data.putInt("slot", slot);
            stack.set(DataComponents.CUSTOM_DATA, CustomData.of(data));
            inventory.setItem(slot, stack);
        }
        var sword = new ItemStack(build ? Items.DIAMOND_PICKAXE : Items.IRON_SWORD);
        sword.setDamageValue(build ? 17 : 9);
        sword.set(DataComponents.CUSTOM_NAME, Component.literal(build ? "Builder's pick" : "Live sword"));
        inventory.setItem(6, sword);
        inventory.setItem(36, new ItemStack(Items.IRON_BOOTS));
        inventory.setItem(37, new ItemStack(Items.IRON_LEGGINGS));
        inventory.setItem(38, new ItemStack(Items.IRON_CHESTPLATE));
        inventory.setItem(39, new ItemStack(Items.IRON_HELMET));
        inventory.setItem(40, new ItemStack(build ? Items.TORCH : Items.SHIELD));
        inventory.setSelectedSlot(build ? 2 : 5);
    }

    static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
