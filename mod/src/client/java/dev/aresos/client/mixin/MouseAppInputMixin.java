package dev.aresos.client.mixin;

import dev.aresos.client.AppInput;
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
    @Inject(method = "onButton", at = @At("HEAD"))
    private void aresos$useInput(long handle, MouseButtonInfo button, int action, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (handle == client.getWindow().handle()
                && client.options.keyUse.matchesMouse(new MouseButtonEvent(0, 0, button))) {
            AppInput.onUseInput(client, action);
        }
    }
}
