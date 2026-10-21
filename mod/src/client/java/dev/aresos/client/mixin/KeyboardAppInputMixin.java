package dev.aresos.client.mixin;

import dev.aresos.client.AppInput;
import net.minecraft.client.KeyboardHandler;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.KeyEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(KeyboardHandler.class)
public abstract class KeyboardAppInputMixin {
    @Inject(method = "keyPress", at = @At("HEAD"))
    private void aresos$useInput(long handle, int action, KeyEvent event, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (handle == client.getWindow().handle() && client.options.keyUse.matches(event)) {
            AppInput.onUseInput(client, action);
        }
    }
}
