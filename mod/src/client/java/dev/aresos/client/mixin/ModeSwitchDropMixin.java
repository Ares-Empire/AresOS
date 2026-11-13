package dev.aresos.client.mixin;

import dev.aresos.client.ModeSwitchClient;
import net.minecraft.client.player.LocalPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(LocalPlayer.class)
public abstract class ModeSwitchDropMixin {
    @Inject(method = "drop", at = @At("HEAD"), cancellable = true)
    private void aresos$blockDrop(boolean all, CallbackInfoReturnable<Boolean> cir) {
        // Q on an app's item does nothing (the server refuses it too; this spares the item a flicker).
        var player = (LocalPlayer) (Object) this;
        if (ModeSwitchClient.pending() || (player.getInventory().getSelectedItem().is(dev.aresos.item.AppItems.APP)
                && dev.aresos.client.AppsScreen.active(net.minecraft.client.Minecraft.getInstance()))) cir.setReturnValue(false);
    }
}
