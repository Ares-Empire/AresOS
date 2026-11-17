package dev.aresos.client.mixin;

import dev.aresos.client.HomeSwitch;
import dev.aresos.client.HomeWorkingScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.LevelLoadingScreen;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Package 48: during a home switch the game's loading screens show "Making your new home…" instead of their terrain
 * progress, over the same background, so two loads read as one wait. The loading screen itself stays: it closes
 * itself when the world is ready, which the switch waits for.
 */
@Mixin(LevelLoadingScreen.class)
public abstract class LevelLoadingCoverMixin {
    @Inject(method = "extractRenderState", at = @At("HEAD"), cancellable = true)
    private void aresos$workingLine(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta, CallbackInfo ci) {
        if (!HomeSwitch.busy()) return;
        var screen = (Screen) (Object) this;
        HomeWorkingScreen.draw(graphics, Minecraft.getInstance().font, HomeSwitch.working(), screen.width, screen.height);
        ci.cancel();
    }
}
