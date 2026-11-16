// DEVELOPMENT AID of package 41 (measurement only, never shipped).
package pkg41.frames.mixin;

import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
abstract class FrameMixin {
    @Inject(method = "runTick", at = @At("HEAD"))
    private void pkg41$frame(boolean advanceGameTime, CallbackInfo info) {
        pkg41.frames.Frames.mark();
    }
}
