package dev.aresos.test.mixin;

import com.mojang.blaze3d.platform.Window;
import dev.aresos.client.WorldCapture;
import dev.aresos.test.WorldKeepsPointerClientGameTest;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Named points of a release where the native test moves the real X focus (WorldKeepsPointerClientGameTest.races). */
@Mixin(WorldCapture.class)
public abstract class WorldCaptureReleaseTestMixin {
    @Inject(method = "release", at = @At("HEAD"))
    private static void aresos$asked(Window window, double x, double y, WorldCapture.CursorMode minecraft, CallbackInfo ci) {
        WorldKeepsPointerClientGameTest.seam("asked");
    }

    @Inject(method = "beforePollEvents", at = @At(value = "INVOKE",
            target = "Ldev/aresos/client/WorldCapture$Xlib;putBack(JI)V"))
    private static void aresos$queued(CallbackInfo ci) {
        WorldKeepsPointerClientGameTest.seam("queued");
    }

    // After GLFW let go, before the mode turns normal: where RECHECK-1's race sat, now inside one event.
    @Inject(method = "ownFocusEvent", at = @At(value = "INVOKE",
            target = "Lorg/lwjgl/glfw/GLFW;glfwSetInputMode(JII)V"))
    private static void aresos$normal(long handle, boolean focused, CallbackInfoReturnable<Boolean> cir) {
        WorldKeepsPointerClientGameTest.seam("normal");
    }

    @Inject(method = "finish", at = @At("HEAD"))
    private static void aresos$show(CallbackInfo ci) {
        WorldKeepsPointerClientGameTest.seam("show");
    }

    @Inject(method = "afterPollEvents", at = @At("HEAD"))
    private static void aresos$polled(CallbackInfo ci) {
        WorldKeepsPointerClientGameTest.seam("polled");
    }
}
