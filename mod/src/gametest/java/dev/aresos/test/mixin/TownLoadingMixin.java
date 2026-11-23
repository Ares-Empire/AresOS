package dev.aresos.test.mixin;

import dev.aresos.test.TownLoading;
import dev.aresos.zone.GateBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(GateBuilder.class)
public abstract class TownLoadingMixin {
    @Inject(method = "loaded", at = @At("HEAD"), cancellable = true)
    private static void aresos$delay(ServerLevel level, Iterable<BlockPos> cells, CallbackInfoReturnable<Boolean> cir) {
        if (TownLoading.delayed(level, cells)) cir.setReturnValue(false);
    }
}
