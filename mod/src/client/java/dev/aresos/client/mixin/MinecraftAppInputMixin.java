package dev.aresos.client.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import dev.aresos.client.AppInput;
import dev.aresos.client.EdgeLook;
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
        if (ModeSwitchClient.pending() || HomeScreen.ignoresMouse((Minecraft) (Object) this)
                || AppInput.consumeAppUse((Minecraft) (Object) this)) ci.cancel();
    }

    @Inject(method = "handleKeybinds", at = @At("HEAD"))
    private void aresos$discardSwitchInput(CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ModeSwitchClient.discardItemKeys((Minecraft) (Object) this);
    }

    @Inject(method = "startAttack", at = @At("HEAD"), cancellable = true)
    private void aresos$ignoreBackgroundAttack(CallbackInfoReturnable<Boolean> ci) {
        if (HomeScreen.ignoresMouse((Minecraft) (Object) this)) ci.setReturnValue(false);
    }

    @Inject(method = "continueAttack", at = @At("HEAD"), cancellable = true)
    private void aresos$ignoreBackgroundBreaking(boolean held, CallbackInfo ci) {
        if (HomeScreen.ignoresMouse((Minecraft) (Object) this)) ci.cancel();
    }

    // Package 328c: with look = edge the world never holds the mouse, and a held attack still breaks what the crosshair
    // aims at. Vanilla counts a held attack only while the mouse is captured.
    @ModifyExpressionValue(method = "handleKeybinds", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/client/MouseHandler;isMouseGrabbed()Z"))
    private boolean aresos$edgeHeldAttack(boolean grabbed) {
        return grabbed || EdgeLook.clicksAct((Minecraft) (Object) this);
    }
}
