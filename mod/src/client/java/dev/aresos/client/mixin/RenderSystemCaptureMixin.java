package dev.aresos.client.mixin;

import com.mojang.blaze3d.systems.RenderSystem;
import dev.aresos.client.WorldCapture;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(RenderSystem.class)
public abstract class RenderSystemCaptureMixin {
    @Inject(method = "pollEvents", at = @At("HEAD"))
    private static void aresos$beforePollEvents(CallbackInfo ci) {
        WorldCapture.beforePollEvents();
    }

    @Inject(method = "pollEvents", at = @At("RETURN"))
    private static void aresos$afterPollEvents(CallbackInfo ci) {
        WorldCapture.afterPollEvents();
    }
}
