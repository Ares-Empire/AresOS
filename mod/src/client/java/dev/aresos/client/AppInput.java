package dev.aresos.client;

import dev.aresos.item.AppItems;
import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import org.lwjgl.glfw.GLFW;

public final class AppInput {
    private static boolean useHeld;
    private static int pendingUsePresses;

    private AppInput() { }

    public static ItemStack heldApp(Minecraft client) {
        if (client.player == null) return ItemStack.EMPTY;
        if (client.player.getMainHandItem().is(AppItems.APP)) return client.player.getMainHandItem();
        if (client.player.getOffhandItem().is(AppItems.APP)) return client.player.getOffhandItem();
        return ItemStack.EMPTY;
    }

    public static void onUseInput(Minecraft client, int action) {
        if (action == GLFW.GLFW_RELEASE) {
            useHeld = false;
        } else if (action == GLFW.GLFW_PRESS && !useHeld) {
            useHeld = true;
            if (client.gui.screen() != null || client.gui.overlay() != null
                    || client.gameMode == null || client.player == null || client.player.isSpectator()) return;
            pendingUsePresses++;
        }
    }

    public static boolean consumeAppUse(Minecraft client) {
        // Vanilla has applied queued hotbar keys by startUseItem; raw input still sees the old slot.
        boolean pressed = pendingUsePresses > 0;
        if (pressed) pendingUsePresses--;
        ItemStack app = heldApp(client);
        if (app.isEmpty()) return false;
        if (pressed) AresOsClient.launch(app.get(AppItems.APP_ID));
        return true;
    }

    public static void endTick() {
        // Discard clicks vanilla ignored (for example, while using another item or opening a screen).
        pendingUsePresses = 0;
    }
}
