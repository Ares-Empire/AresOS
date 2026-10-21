package dev.aresos.test.mixin;

import dev.aresos.test.ProvisioningAudit;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Level.class)
public abstract class BlockWriteAuditMixin {
    @Inject(method = "setBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/block/state/BlockState;II)Z", at = @At("HEAD"))
    private void aresos$countWrites(BlockPos pos, BlockState state, int flags, int updateDepth, CallbackInfoReturnable<Boolean> cir) {
        ProvisioningAudit.blockWrite((Level) (Object) this);
    }
}
