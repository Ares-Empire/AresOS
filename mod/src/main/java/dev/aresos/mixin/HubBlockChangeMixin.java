package dev.aresos.mixin;

import dev.aresos.hub.HubData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
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
        // Observe successful changes at the chunk, so every edit path relinquishes ownership immediately. A light's
        // state is only ever his edit (its level, water in it): the moment it changes it is his, and changing it back
        // later does not give it back. Other blocks let go on a change of kind only, because some of their states
        // follow the neighbours by themselves (a mushroom block's faces).
        if (previous != null && previous != state && (previous.getBlock() != state.getBlock() || previous.is(Blocks.LIGHT))
                && ((LevelChunk)(Object)this).getLevel() instanceof ServerLevel level) {
            HubData.blockChanged(level, pos);
        }
    }
}
