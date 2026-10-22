package dev.aresos.client.mixin;

import dev.aresos.client.ModeSwitchClient;
import net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(CreativeModeInventoryScreen.class)
public abstract class ModeSwitchCreativeMixin {
    @Inject(method = "slotClicked", at = @At("HEAD"), cancellable = true)
    private void aresos$blockCreativeClick(CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ci.cancel();
    }

    @Inject(method = "handleHotbarLoadOrSave", at = @At("HEAD"), cancellable = true)
    private static void aresos$blockSavedHotbar(CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ci.cancel();
    }
}
