package dev.aresos.client.mixin;

import dev.aresos.client.AppInput;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class MinecraftAppInputMixin {
    @Inject(method = "startUseItem", at = @At("HEAD"), cancellable = true)
    private void aresos$consumeAppUse(CallbackInfo ci) {
        // Includes held-button repeats and runs before block/entity interaction packets can be sent.
        if (AppInput.consumeAppUse((Minecraft) (Object) this)) ci.cancel();
    }
}
