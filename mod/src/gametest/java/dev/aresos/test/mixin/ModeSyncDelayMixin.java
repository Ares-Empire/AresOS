package dev.aresos.test.mixin;

import dev.aresos.mode.ModeInventories;
import dev.aresos.test.ModeSyncDelay;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ModeInventories.class)
public abstract class ModeSyncDelayMixin {
    @Inject(method = "sync", at = @At("HEAD"), cancellable = true)
    private static void aresos$delay(ServerPlayer player, CallbackInfo ci) {
        if (player.getUUID().equals(ModeSyncDelay.player)) ci.cancel();
    }
}
