package dev.aresos.client.mixin;

import dev.aresos.client.AresOsMenuScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Gui;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Package 48: in the home screen the AresOS menu replaces the game's. Every game menu in Minecraft 26.2 is made here:
 * {@code Minecraft.pauseGame} is its only caller, and Esc, F3+Esc ({@code KeyboardHandler.keyPress}) and focus loss
 * ({@code Minecraft.pauseIfInactive}) all go through that. So one check catches each way in, a mod's call included.
 */
@Mixin(Gui.class)
public abstract class GuiMenuMixin {
    @Inject(method = "setPauseScreen", at = @At("HEAD"), cancellable = true)
    private void aresos$openAresOsMenu(boolean suppressMenu, boolean singleplayer, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (!AresOsMenuScreen.replacesGameMenu(client)) return;
        // As the game does: a menu opens only over the world, never over another screen.
        var gui = (Gui) (Object) this;
        if (gui.screen() == null) gui.setScreen(new AresOsMenuScreen());
        ci.cancel();
    }
}
