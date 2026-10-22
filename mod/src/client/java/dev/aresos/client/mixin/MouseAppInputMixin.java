package dev.aresos.client.mixin;

import dev.aresos.client.AppInput;
import dev.aresos.client.ModeSwitchClient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.MouseHandler;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.input.MouseButtonInfo;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MouseHandler.class)
public abstract class MouseAppInputMixin {
    @Inject(method = "onButton", at = @At("HEAD"), cancellable = true)
    private void aresos$useInput(long handle, MouseButtonInfo button, int action, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (ModeSwitchClient.pending()) { ci.cancel(); return; }
        if (handle == client.getWindow().handle()
                && client.options.keyUse.matchesMouse(new MouseButtonEvent(0, 0, button))) {
            AppInput.onUseInput(client, action);
        }
    }

    @Inject(method = "onScroll", at = @At("HEAD"), cancellable = true)
    private void aresos$blockScroll(long handle, double horizontal, double vertical, CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ci.cancel();
    }
}
