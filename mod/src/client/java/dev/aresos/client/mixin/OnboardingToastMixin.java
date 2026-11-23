package dev.aresos.client.mixin;

import dev.aresos.client.HomeOnboarding;
import dev.aresos.client.HomeScreen;
import net.minecraft.client.gui.components.toasts.Toast;
import net.minecraft.client.gui.components.toasts.ToastManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ToastManager.class)
abstract class OnboardingToastMixin {
    @Inject(method = "addToast", at = @At("HEAD"), cancellable = true)
    private void aresos$hideOnboarding(Toast toast, CallbackInfo ci) {
        var manager = (ToastManager) (Object) this;
        if (HomeOnboarding.hidesToast(HomeScreen.home(manager.getMinecraft()), toast.getClass())) ci.cancel();
    }
}
