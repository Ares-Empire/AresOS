package pkg41.frames.mixin;

import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Records package 48's actual creation entry; does not change its plan or flow. */
@Mixin(targets = "dev.aresos.client.HomePlan", remap = false)
abstract class HomePlanMixin {
    @Shadow @Final private String kind;

    @Inject(method = "create", at = @At("HEAD"), remap = false)
    private void pkg318$creation(CallbackInfo info) {
        pkg41.frames.Observations.creation(kind);
    }
}
