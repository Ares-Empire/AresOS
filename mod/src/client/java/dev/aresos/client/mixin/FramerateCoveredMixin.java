package dev.aresos.client.mixin;

import com.mojang.blaze3d.platform.FramerateLimitTracker;
import dev.aresos.client.HomeScreen;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Package 40: a world nobody can see draws at most {@link HomeScreen#COVERED_FRAME_LIMIT} frames a second. */
@Mixin(FramerateLimitTracker.class)
public abstract class FramerateCoveredMixin {
    @Shadow @Final private Minecraft minecraft;

    @Inject(method = "getFramerateLimit", at = @At("RETURN"), cancellable = true)
    private void aresos$slowWhileCovered(CallbackInfoReturnable<Integer> cir) {
        cir.setReturnValue(HomeScreen.framerateLimit(minecraft, cir.getReturnValueI()));
    }
}
