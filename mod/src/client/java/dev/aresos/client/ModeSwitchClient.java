package dev.aresos.client;

import dev.aresos.mode.ModeSwitchAckPayload;
import dev.aresos.mode.ModeSwitchStatePayload;
import dev.aresos.mode.ToggleModePayload;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;

public final class ModeSwitchClient {
    private static boolean pending;
    private static long transaction;
    private static long completed;

    private ModeSwitchClient() { }

    public static boolean pending() { return pending; }

    public static void reset() { pending = false; transaction = 0; completed = 0; }

    public static void requestToggle() {
        if (pending) return;
        pending = true;
        ClientPlayNetworking.send(ToggleModePayload.INSTANCE);
    }

    public static void receive(ModeSwitchStatePayload state) {
        if (state.transaction() <= completed) return;
        if (!state.complete()) {
            transaction = state.transaction();
            pending = true;
        } else if (state.transaction() == transaction) {
            // TCP orders every old input before this acknowledgement, and every new input after it.
            ClientPlayNetworking.send(new ModeSwitchAckPayload(transaction));
            completed = transaction;
            discardItemKeys(Minecraft.getInstance());
            AresOsClient.discardModeToggle();
            pending = false;
        }
    }

    public static void discardItemKeys(Minecraft client) {
        var options = client.options;
        for (var key : new KeyMapping[]{options.keyAttack, options.keyUse, options.keyPickItem,
                options.keyDrop, options.keySwapOffhand, options.keyInventory,
                options.keyLoadHotbarActivator, options.keySaveHotbarActivator}) discard(key);
        for (var key : options.keyHotbarSlots) discard(key);
    }

    private static void discard(KeyMapping key) {
        while (key.consumeClick()) { }
        key.setDown(false);
    }
}
