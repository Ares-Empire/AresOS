package dev.aresos.client.mixin;

import dev.aresos.client.AppInput;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.client.HomeScreen;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Minecraft.class)
public abstract class MinecraftAppInputMixin {
    @Inject(method = "startUseItem", at = @At("HEAD"), cancellable = true)
    private void aresos$consumeAppUse(CallbackInfo ci) {
        // Includes held-button repeats and runs before block/entity interaction packets can be sent.
        if (ModeSwitchClient.pending() || HomeScreen.freePointer((Minecraft) (Object) this)
                || AppInput.consumeAppUse((Minecraft) (Object) this)) ci.cancel();
    }

    @Inject(method = "handleKeybinds", at = @At("HEAD"))
    private void aresos$discardSwitchInput(CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ModeSwitchClient.discardItemKeys((Minecraft) (Object) this);
    }

    @Inject(method = "startAttack", at = @At("HEAD"), cancellable = true)
    private void aresos$ignoreBackgroundAttack(CallbackInfoReturnable<Boolean> ci) {
        if (HomeScreen.freePointer((Minecraft) (Object) this)) ci.setReturnValue(false);
    }

    @Inject(method = "continueAttack", at = @At("HEAD"), cancellable = true)
    private void aresos$ignoreBackgroundBreaking(boolean held, CallbackInfo ci) {
        if (HomeScreen.freePointer((Minecraft) (Object) this)) ci.cancel();
    }
}
