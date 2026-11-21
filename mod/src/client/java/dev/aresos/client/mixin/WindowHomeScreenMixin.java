package dev.aresos.client.mixin;

import com.mojang.blaze3d.platform.DisplayData;
import com.mojang.blaze3d.platform.Window;
import dev.aresos.client.HomeScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Package 40: in an AresOS session the game's window is the desktop. labwc already makes it cover the screen without
 * a frame and keeps it below every app, so the game's own fullscreen is never used there: a GLFW fullscreen window
 * minimizes itself whenever another window takes the focus (that closed the world in the owner's try-out), and it
 * would not stay below the apps. A saved {@code fullscreen:true} is ignored and F11 changes nothing.
 */
@Mixin(Window.class)
public abstract class WindowHomeScreenMixin {
    @Redirect(method = "<init>", at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/platform/DisplayData;isFullscreen()Z"))
    private boolean aresos$startWindowed(DisplayData display) {
        return !HomeScreen.session() && display.isFullscreen();
    }

    @Inject(method = "toggleFullScreen", at = @At("HEAD"), cancellable = true)
    private void aresos$stayTheDesktop(CallbackInfo ci) {
        if (HomeScreen.session()) ci.cancel();
    }

    // Package 328a: GLFW's focus callback, inside its event handling (WorldCapture.focusChanged says why).
    @Inject(method = "onFocus", at = @At("HEAD"))
    private void aresos$focusChanged(long handle, boolean focused, CallbackInfo ci) {
        dev.aresos.client.WorldCapture.focusChanged(handle, focused);
    }
}
