package dev.aresos.item;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ModeInventories;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.networking.v1.*;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.item.ItemStack;
import java.io.IOException;
import java.util.*;

/**
 * The app items in a player's inventory. The inventory holds My apps and nothing else (docs/design/HUB.md 2.4):
 * an app that is his has one item, an app that is not his has none. When this runs is {@link MyAppsGame}'s job.
 */
public final class AppInventory {
    private AppInventory() { }
    public static void register() {
        PayloadTypeRegistry.serverboundPlay().register(TakeAppPayload.TYPE, TakeAppPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(TakeAppPayload.TYPE, (payload, context) -> take(context.player(), payload.id()));
        PayloadTypeRegistry.serverboundPlay().register(MyAppPayload.TYPE, MyAppPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(MyAppPayload.TYPE,
                (payload, context) -> MyAppsGame.asked(context.player(), payload.id(), payload.mine()));
        MyAppsGame.register();
    }
    public static List<AppDefinition> populate(ServerPlayer player) { return populate(player, AresOs.apps()); }
    /**
     * Live mode only. Takes out the items of apps that are not his, puts pinned apps in the hotbar, gives every
     * item its current look and name, and puts each of his apps that has no item in the first free slot beside
     * the hotbar. Another item is never moved or replaced.
     *
     * @return his apps that have no item now, because no slot was free
     */
    public static List<AppDefinition> populate(ServerPlayer player, List<AppDefinition> apps) {
        if (!LiveMode.isLive(player)) return List.of();
        sweep(player, apps);
        AppItems.placePinned(player, apps);
        var inventory = player.getInventory();
        var present = new HashSet<String>();
        for (int i = 0; i < inventory.getContainerSize(); i++) {
            var stack = inventory.getItem(i);
            if (stack.is(AppItems.APP)) {
                String id = stack.get(AppItems.APP_ID);
                present.add(id);
                apps.stream().filter(app -> app.id().equals(id)).findFirst().ifPresent(app -> {
                    var fresh = AppItems.create(app);
                    stack.set(net.minecraft.core.component.DataComponents.ITEM_MODEL, fresh.get(net.minecraft.core.component.DataComponents.ITEM_MODEL));
                    stack.set(net.minecraft.core.component.DataComponents.CUSTOM_NAME, fresh.get(net.minecraft.core.component.DataComponents.CUSTOM_NAME));
                });
            }
        }
        var without = new ArrayList<AppDefinition>();
        for (var app : apps) {
            if (!app.mine() || present.contains(app.id())) continue;
            boolean placed = false;
            for (int slot = 9; slot < 36 && !placed; slot++) if (inventory.getItem(slot).isEmpty()) {
                inventory.setItem(slot, AppItems.create(app));
                placed = true;
            }
            if (!placed) without.add(app);
        }
        return List.copyOf(without);
    }

    /** True for the item of an app that is known and is not one of his. An item of an unknown app is left alone. */
    public static boolean notHis(ItemStack stack, List<AppDefinition> apps) {
        if (!stack.is(AppItems.APP)) return false;
        String id = stack.get(AppItems.APP_ID);
        return apps.stream().anyMatch(app -> app.id().equals(id) && !app.mine());
    }

    /** Takes the items of apps that are not his out of the inventory he holds, in either mode. No other slot is touched. */
    public static int sweep(ServerPlayer player, List<AppDefinition> apps) {
        var inventory = player.getInventory();
        int removed = 0;
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) if (notHis(inventory.getItem(slot), apps)) {
            inventory.setItem(slot, ItemStack.EMPTY);
            removed++;
        }
        return removed;
    }

    public static boolean has(ServerPlayer player, String id) {
        var inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            var stack = inventory.getItem(slot);
            if (stack.is(AppItems.APP) && id.equals(stack.get(AppItems.APP_ID))) return true;
        }
        return false;
    }

    /** An app's item in an AresOS world never lies on the ground: dropping it (Q) must not remove the app. */
    public static boolean keeps(ServerPlayer player, ItemStack stack) {
        return stack.is(AppItems.APP) && DesktopWorld.isEnabled(player.level().getServer());
    }

    /** Q in the world: the item stays in the hand. The client has already taken it out, so it is sent again. */
    public static boolean keepSelected(ServerPlayer player) {
        var inventory = player.getInventory();
        if (!keeps(player, inventory.getSelectedItem())) return false;
        player.connection.send(inventory.createInventoryUpdatePacket(inventory.getSelectedSlot()));
        return true;
    }

    /** Q over a slot, or a click outside the window with the item on the cursor: the click does nothing. */
    public static boolean keepsOnClick(ServerPlayer player, AbstractContainerMenu menu, int slot, ContainerInput input) {
        if (input == ContainerInput.THROW)
            return slot >= 0 && slot < menu.slots.size() && menu.getCarried().isEmpty() && keeps(player, menu.getSlot(slot).getItem());
        return slot == AbstractContainerMenu.SLOT_CLICKED_OUTSIDE && input != ContainerInput.QUICK_CRAFT && keeps(player, menu.getCarried());
    }

    /**
     * The last line of defence: something still tried to put an app's item on the ground (a menu closed over a
     * full inventory, a death, a creative drop). The item goes into a free slot instead. With no free slot, or
     * during a mode switch, it is let go: the app is still his and its item is made again when there is room.
     */
    public static void giveBack(ServerPlayer player, ItemStack stack) {
        var inventory = player.getInventory();
        if (!ModeInventories.of(player).pending()) {
            // Beside the hotbar first: an item that lands in the hotbar would look like a pin he never made.
            for (int index = 0; index < 36; index++) {
                int slot = (index + 9) % 36;
                if (inventory.getItem(slot).isEmpty()) {
                    inventory.setItem(slot, stack.copy());
                    return;
                }
            }
        }
        MyAppsGame.changed();
    }

    public static Set<String> hotbar(ServerPlayer player) {
        var ids = new HashSet<String>();
        for (int i = 0; i < 9; i++) {
            var stack = player.getInventory().getItem(i);
            if (stack.is(AppItems.APP) && stack.get(AppItems.APP_ID) != null) ids.add(stack.get(AppItems.APP_ID));
        }
        return Set.copyOf(ids);
    }
    public static void savePins(ServerPlayer player, Set<String> before) {
        if (!LiveMode.isLive(player) || !DesktopWorld.isHost(player.level().getServer(), player)) return;
        var after = hotbar(player);
        var changes = new HashMap<String, Boolean>();
        for (var app : AresOs.apps()) if (before.contains(app.id()) != after.contains(app.id()))
            changes.put(app.id(), after.contains(app.id()));
        if (changes.isEmpty()) return;
        try { AresOs.savePins(changes); }
        catch (IOException | RuntimeException error) {
            AresOs.LOGGER.error("Could not save hotbar pins; config left intact", error);
            player.sendSystemMessage(Component.literal("Could not save app pins: " + error.getMessage()));
        }
    }
    private static void take(ServerPlayer player, String id) {
        if (ModeInventories.of(player).pending()
                || !LiveMode.isLive(player) || !DesktopWorld.isHost(player.level().getServer(), player)
                || player.containerMenu != player.inventoryMenu || !player.inventoryMenu.getCarried().isEmpty()) return;
        var app = AresOs.app(id);
        // Only one of his apps has an item to pick up; a program that is not his is added first.
        if (app == null || !app.mine()) return;
        // Move an existing item instead of duplicating it. The cursor is managed by vanilla inventory packets.
        var before = hotbar(player);
        ItemStack stack = ItemStack.EMPTY;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            var existing = player.getInventory().getItem(i);
            if (existing.is(AppItems.APP) && id.equals(existing.get(AppItems.APP_ID))) {
                stack = existing; player.getInventory().setItem(i, ItemStack.EMPTY); break;
            }
        }
        if (stack.isEmpty()) stack = AppItems.create(app);
        ((AppMenuPins)player.inventoryMenu).aresos$beginMove(before);
        player.inventoryMenu.setCarried(stack);
        player.inventoryMenu.broadcastChanges();
    }
}
