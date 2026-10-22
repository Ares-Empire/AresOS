package dev.aresos.test.mixin;

import dev.aresos.mode.ModeSwitchAckPayload;
import dev.aresos.test.ModeSyncDelay;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientPlayNetworking.class)
public abstract class ModeAckLossMixin {
    @Inject(method = "send", at = @At("HEAD"), cancellable = true)
    private static void aresos$loseAck(CustomPacketPayload payload, CallbackInfo ci) {
        if (ModeSyncDelay.dropAcknowledgements && payload instanceof ModeSwitchAckPayload) ci.cancel();
    }
}
