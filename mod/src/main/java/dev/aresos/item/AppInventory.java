package dev.aresos.item;

import dev.aresos.AresOs;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.networking.v1.*;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import java.io.IOException;
import java.util.*;

public final class AppInventory {
    private AppInventory() { }
    public static void register() {
        PayloadTypeRegistry.serverboundPlay().register(TakeAppPayload.TYPE, TakeAppPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(TakeAppPayload.TYPE, (payload, context) -> take(context.player(), payload.id()));
    }
    public static void populate(ServerPlayer player) { populate(player, AresOs.apps()); }
    public static void populate(ServerPlayer player, List<dev.aresos.config.AppDefinition> apps) {
        if (!LiveMode.isLive(player)) return;
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
        for (var app : apps) {
            if (present.contains(app.id())) continue;
            for (int slot = 9; slot < 36; slot++) if (inventory.getItem(slot).isEmpty()) {
                inventory.setItem(slot, AppItems.create(app)); present.add(app.id()); break;
            }
        }
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
        if (!LiveMode.isLive(player) || !DesktopWorld.isHost(player.level().getServer(), player)
                || player.containerMenu != player.inventoryMenu || !player.inventoryMenu.getCarried().isEmpty()) return;
        var app = AresOs.app(id);
        if (app == null) return;
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
