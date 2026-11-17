package dev.aresos.client.mixin;

import dev.aresos.client.HomeScreen;
import dev.aresos.client.HomeSwitch;
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
 * Package 46, owner fix 1: the home screen shows no "Saving world" text (the owner, 2026-11-16: "Hide it"). The game
 * fades it in at the bottom right while the integrated server saves: the supervisor's {@code save_world}, the autosave
 * every five minutes, the save on each pause. In the home screen ({@link HomeScreen#home}) the HUD
 * skips drawing it, including every part of New home and recovery when no desktop world is open. The saves stay as
 * they are, and so does the player's own "Autosave Indicator" option, which
 * decides everywhere else.
 */
@Mixin(Hud.class)
public abstract class SavingIndicatorMixin {
    @Shadow @Final private Minecraft minecraft;

    @Inject(method = "extractSavingIndicator", at = @At("HEAD"), cancellable = true)
    private void aresos$noSavingTextAtHome(GuiGraphicsExtractor graphics, DeltaTracker delta, CallbackInfo ci) {
        if (HomeSwitch.busy() || HomeScreen.home(minecraft)) ci.cancel();
    }
}
