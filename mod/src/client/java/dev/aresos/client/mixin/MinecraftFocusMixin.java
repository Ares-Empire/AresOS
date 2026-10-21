package dev.aresos.client.mixin;

import dev.aresos.client.AresOsClient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class MinecraftFocusMixin {
    @Inject(method = "pauseIfInactive", at = @At("HEAD"))
    private void aresos$returnToWorld(CallbackInfo ci) {
        var client = (Minecraft) (Object) this;
        if (client.player == null) {
            AresOsClient.FOCUS_RETURN.reset();
        } else if (client.getWindow().isFocused()
                && AresOsClient.FOCUS_RETURN.regainedFocus(client.gui.screen())) {
            client.gui.setScreen(null);
        } else if (!client.getWindow().isFocused()) {
            AresOsClient.FOCUS_RETURN.focusLost(System.nanoTime(), client.gui.screen());
        }
    }

    @Redirect(method = "pauseIfInactive", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/client/Minecraft;pauseGame(Z)V"))
    private void aresos$rememberFocusPause(Minecraft client, boolean suppressMenu) {
        boolean capture = AresOsClient.FOCUS_RETURN.beforeFocusPause(System.nanoTime(), client.gui.screen());
        client.pauseGame(suppressMenu);
        if (capture && client.gui.screen() instanceof PauseScreen) {
            AresOsClient.FOCUS_RETURN.recordPause(client.gui.screen());
        }
    }
}
