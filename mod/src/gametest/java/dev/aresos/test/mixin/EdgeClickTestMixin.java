package dev.aresos.test.mixin;

import dev.aresos.test.EdgeTurnClientGameTest;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Package 328c: what a click on the world reached in Minecraft (EdgeTurnClientGameTest). An attack or a use counts only
 * where Minecraft's own method body ran to one of its returns, so not where the mod's gate cancelled it.
 */
@Mixin(Minecraft.class)
public abstract class EdgeClickTestMixin {
    @Inject(method = "startAttack", at = @At("RETURN"))
    private void aresos$attacked(CallbackInfoReturnable<Boolean> cir) {
        EdgeTurnClientGameTest.attacks++;
    }

    @Inject(method = "startUseItem", at = @At("RETURN"))
    private void aresos$used(CallbackInfo ci) {
        EdgeTurnClientGameTest.uses++;
    }

    @Inject(method = "continueAttack", at = @At("HEAD"))
    private void aresos$held(boolean held, CallbackInfo ci) {
        EdgeTurnClientGameTest.attackHeld = held;
    }
}
