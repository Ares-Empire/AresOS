package dev.aresos.client.mixin;

import dev.aresos.client.HomeScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.sounds.MusicManager;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Package 40, review fixes 1: while covered the home screen is silent (orchestrator, 2026-11-15). The music manager
 * ticks even in a pause, so it would start the next song or change the song meanwhile; it stands still instead, and
 * the song that was playing goes on where it was when the cover ends ({@link HomeScreen#pausing}).
 */
@Mixin(MusicManager.class)
public abstract class MusicCoveredMixin {
    @Shadow @Final private Minecraft minecraft;

    @Inject(method = "tick", at = @At("HEAD"), cancellable = true)
    private void aresos$silentWhileCovered(CallbackInfo ci) {
        if (HomeScreen.covered(minecraft)) ci.cancel();
    }
}
