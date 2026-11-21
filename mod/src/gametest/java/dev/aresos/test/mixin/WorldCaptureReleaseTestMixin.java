package dev.aresos.test.mixin;

import dev.aresos.client.WorldCapture;
import dev.aresos.test.WorldKeepsPointerClientGameTest;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(WorldCapture.class)
public abstract class WorldCaptureReleaseTestMixin {
    @Inject(method = "beforePollEvents", at = @At(value = "INVOKE",
            target = "Ldev/aresos/client/WorldCapture$Xlib;focusOut(JJ)V"))
    private static void aresos$raceFocusOut(CallbackInfo ci) {
        WorldKeepsPointerClientGameTest.beforeSyntheticFocusOut();
    }
}
