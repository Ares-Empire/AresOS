package dev.aresos.mixin;

import dev.aresos.item.AppInventory;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Dropping an app's item never removes the app (docs/design/HUB.md 2.4): the drop is refused, so nothing can double. */
@Mixin(ServerPlayer.class)
public abstract class AppDropMixin {
    @Inject(method = "drop(Z)V", at = @At("HEAD"), cancellable = true)
    private void aresos$keepHeldApp(boolean all, CallbackInfo ci) {
        if (AppInventory.keepSelected((ServerPlayer) (Object) this)) ci.cancel();
    }

    // Every way an item reaches the ground from a player ends here.
    @Inject(method = "drop(Lnet/minecraft/world/item/ItemStack;ZZ)Lnet/minecraft/world/entity/item/ItemEntity;",
            at = @At("HEAD"), cancellable = true)
    private void aresos$neverOnTheGround(ItemStack stack, boolean randomly, boolean thrownFromHand,
                                         CallbackInfoReturnable<ItemEntity> cir) {
        var player = (ServerPlayer) (Object) this;
        if (AppInventory.keeps(player, stack)) {
            AppInventory.giveBack(player, stack);
            cir.setReturnValue(null);
        }
    }
}
