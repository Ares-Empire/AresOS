package dev.aresos.client.mixin;

import dev.aresos.client.WorldSearchScreen;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Package 53d: no crosshair while the search over the world is open. The world stays sharp behind the bar, so the
 * crosshair in the middle of the screen would show through the hits and cross out a letter of a name. The pointer is
 * free meanwhile and there is nothing to aim at. Other screens blur the world, and the crosshair with it.
 */
@Mixin(Hud.class)
public abstract class SearchCrosshairMixin {
    @Shadow @Final private Minecraft minecraft;

    @Inject(method = "extractCrosshair", at = @At("HEAD"), cancellable = true)
    private void aresos$noCrosshairUnderTheSearch(GuiGraphicsExtractor graphics, DeltaTracker delta, CallbackInfo ci) {
        if (minecraft.gui.screen() instanceof WorldSearchScreen) ci.cancel();
    }
}
