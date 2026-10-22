package dev.aresos.client.mixin;

import dev.aresos.client.ModeSwitchClient;
import net.minecraft.client.multiplayer.MultiPlayerGameMode;
import net.minecraft.world.InteractionResult;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(MultiPlayerGameMode.class)
public abstract class ModeSwitchInteractionMixin {
    @Inject(method = {"handleContainerInput", "handlePlaceRecipe", "handleInventoryButtonClick",
            "handleCreativeModeItemAdd", "handleCreativeModeItemDrop", "attack", "releaseUsingItem", "piercingAttack",
            "handlePickItemFromBlock", "handlePickItemFromEntity", "handleSlotStateChanged"}, at = @At("HEAD"), cancellable = true)
    private void aresos$blockItemAction(CallbackInfo ci) {
        if (ModeSwitchClient.pending()) ci.cancel();
    }

    @Inject(method = {"startDestroyBlock", "continueDestroyBlock", "destroyBlock"}, at = @At("HEAD"), cancellable = true)
    private void aresos$blockMining(CallbackInfoReturnable<Boolean> cir) {
        if (ModeSwitchClient.pending()) cir.setReturnValue(false);
    }

    @Inject(method = {"useItem", "useItemOn", "interact"}, at = @At("HEAD"), cancellable = true)
    private void aresos$blockUse(CallbackInfoReturnable<InteractionResult> cir) {
        if (ModeSwitchClient.pending()) cir.setReturnValue(InteractionResult.PASS);
    }
}
