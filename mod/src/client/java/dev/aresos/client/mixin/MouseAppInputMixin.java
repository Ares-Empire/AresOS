package dev.aresos.client.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.mojang.blaze3d.platform.Window;
import dev.aresos.client.AppInput;
import dev.aresos.client.ClickToLook;
import dev.aresos.client.EdgeLook;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.client.HomePointer;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.WorldCapture;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.MouseHandler;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.input.MouseButtonInfo;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.lwjgl.glfw.GLFW;

@Mixin(MouseHandler.class)
public abstract class MouseAppInputMixin {
    @Shadow private boolean mouseGrabbed;
    @Shadow private double xpos;
    @Shadow private double ypos;
    @Shadow private boolean ignoreFirstMove;

    @Inject(method = "onButton", at = @At("HEAD"), cancellable = true)
    private void aresos$useInput(long handle, MouseButtonInfo button, int action, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (handle == client.getWindow().handle()) ClickToLook.input(client);
        boolean pending = ModeSwitchClient.pending();
        if (handle == client.getWindow().handle() && (!pending || action == GLFW.GLFW_RELEASE)
                && HomePointer.button(client, button.button(), action)) {
            ci.cancel(); return;
        }
        if (pending) { ci.cancel(); return; }
        if (handle == client.getWindow().handle()
                && client.options.keyUse.matchesMouse(new MouseButtonEvent(0, 0, button))) {
            AppInput.onUseInput(client, action);
        }
    }

    @Inject(method = "onScroll", at = @At("HEAD"), cancellable = true)
    private void aresos$blockScroll(long handle, double horizontal, double vertical, CallbackInfo ci) {
        if (handle == Minecraft.getInstance().getWindow().handle()) ClickToLook.input(Minecraft.getInstance());
        if (ModeSwitchClient.pending()) ci.cancel();
    }

    // Package 328b: real motion keeps look mode on (not the capture's own first move, not an unchanged position).
    // Package 328c: edge turning trusts the cursor position once one has arrived.
    @Inject(method = "onMove", at = @At("HEAD"))
    private void aresos$lookMoved(long handle, double x, double y, CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (handle != client.getWindow().handle()) return;
        EdgeLook.moved();
        if (!ignoreFirstMove && (x != xpos || y != ypos)) ClickToLook.input(client);
    }

    @Inject(method = "grabMouse", at = @At("HEAD"), cancellable = true)
    private void aresos$keepPointerFree(CallbackInfo ci) {
        var client = Minecraft.getInstance();
        if (HomeScreen.freePointer(client)) {
            // Loading may have captured before the desktop marker/player became active.
            ((MouseHandler) (Object) this).releaseMouse();
            ci.cancel();
        } else if (!WorldCapture.allowed(client)) {
            // Package 328a: without the compositor's focus and the pointer on the world, labwc's lock would not hold
            // the hidden pointer. The pointer stays free until a click on the world.
            ci.cancel();
        }
    }

    // Package 328a: the cursor is hidden before Minecraft's capture warps it (WorldCapture says why).
    @WrapOperation(method = "grabMouse", at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/platform/InputConstants;grabOrReleaseMouse(Lcom/mojang/blaze3d/platform/Window;IDD)V"))
    private void aresos$captureHidden(Window window, int mode, double x, double y, Operation<Void> original) {
        WorldCapture.grab(window, x, y, (w, m, px, py) -> original.call(w, m, px, py));
    }

    @WrapOperation(method = "releaseMouse", at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/platform/InputConstants;grabOrReleaseMouse(Lcom/mojang/blaze3d/platform/Window;IDD)V"))
    private void aresos$release(Window window, int mode, double x, double y, Operation<Void> original) {
        WorldCapture.release(window, x, y, (w, m, px, py) -> original.call(w, m, px, py));
    }

    // Package 328a: whenever the world lets go of the mouse in a desktop world, nothing it held stays held.
    @Inject(method = "releaseMouse", at = @At("HEAD"))
    private void aresos$releaseHeld(CallbackInfo ci) {
        if (mouseGrabbed && (WorldCapture.ownsCapture() || HomeScreen.active(Minecraft.getInstance()))) {
            KeyMapping.releaseAll();
            AppInput.reset();
        }
    }

    @Inject(method = "turnPlayer", at = @At("HEAD"), cancellable = true)
    private void aresos$ignoreBackgroundMotion(double elapsed, CallbackInfo ci) {
        if (HomeScreen.freePointer(Minecraft.getInstance())) ci.cancel();
    }
}
