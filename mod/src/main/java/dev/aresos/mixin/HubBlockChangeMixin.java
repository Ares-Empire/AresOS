package dev.aresos.mixin;

import dev.aresos.hub.HubData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(LevelChunk.class)
public abstract class HubBlockChangeMixin {
    @Inject(method = "setBlockState", at = @At("RETURN"))
    private void aresos$releaseChangedBlock(BlockPos pos, BlockState state, int flags,
                                           CallbackInfoReturnable<BlockState> ci) {
        BlockState previous = ci.getReturnValue();
        // Observe successful changes at the chunk, so every edit path relinquishes ownership immediately.
        if (previous != null && previous.getBlock() != state.getBlock()
                && ((LevelChunk)(Object)this).getLevel() instanceof ServerLevel level) {
            HubData.blockChanged(level, pos);
        }
    }
}
