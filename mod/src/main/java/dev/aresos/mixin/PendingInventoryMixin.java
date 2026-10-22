package dev.aresos.mixin;

import dev.aresos.mode.ModeInventories;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Inventory.class)
public abstract class PendingInventoryMixin implements Container {
    @Shadow @Final public Player player;

    @Unique private boolean aresos$blocked() {
        return player instanceof ServerPlayer serverPlayer && ModeInventories.of(serverPlayer).blocksInsertions();
    }

    @Inject(method = "add(ILnet/minecraft/world/item/ItemStack;)Z", at = @At("HEAD"), cancellable = true)
    private void aresos$refuseInsertion(int slot, ItemStack stack, CallbackInfoReturnable<Boolean> cir) {
        // Return failure before touching the caller's stack, including creative's overflow-discard path.
        if (aresos$blocked()) cir.setReturnValue(false);
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) { return !aresos$blocked(); }
    @Override public boolean canTakeItem(Container destination, int slot, ItemStack stack) { return !aresos$blocked(); }

    @Inject(method = "placeItemBackInInventory(Lnet/minecraft/world/item/ItemStack;Z)V", at = @At("HEAD"), cancellable = true)
    private void aresos$dropReturnedStack(ItemStack stack, boolean sendPacket, CallbackInfo ci) {
        if (aresos$blocked()) {
            // Vanilla splits the input before calling add and ignores a refusal. Use its full-inventory fallback.
            if (!stack.isEmpty()) player.drop(stack, false);
            ci.cancel();
        }
    }
}
