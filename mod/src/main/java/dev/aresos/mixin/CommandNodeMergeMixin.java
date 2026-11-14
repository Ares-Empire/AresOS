package dev.aresos.mixin;

import com.mojang.brigadier.tree.CommandNode;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Before a later registration would merge into one of AresOS's nodes, ours steps aside (names/OwnedNodes). */
@Mixin(value = CommandNode.class, remap = false)
public abstract class CommandNodeMergeMixin {
    @Inject(method = "addChild", at = @At("HEAD"))
    private void aresos$stepAside(CommandNode<?> node, CallbackInfo ci) {
        dev.aresos.names.OwnedNodes.beforeAdd((CommandNode<?>)(Object)this, node);
    }
}
