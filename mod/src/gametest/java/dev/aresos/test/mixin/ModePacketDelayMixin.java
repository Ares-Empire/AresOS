package dev.aresos.test.mixin;

import dev.aresos.test.ModeSyncDelay;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.*;
import net.minecraft.server.network.ServerCommonPacketListenerImpl;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ServerCommonPacketListenerImpl.class)
public abstract class ModePacketDelayMixin {
    @Inject(method = "send", at = @At("HEAD"), cancellable = true)
    private void aresos$holdInventoryPackets(Packet<?> packet, CallbackInfo ci) {
        if ((Object) this instanceof ServerGamePacketListenerImpl listener
                && listener.player.getUUID().equals(ModeSyncDelay.player)
                && (packet instanceof ClientboundContainerSetContentPacket || packet instanceof ClientboundContainerSetSlotPacket
                || packet instanceof ClientboundSetPlayerInventoryPacket || packet instanceof ClientboundSetHeldSlotPacket
                || (packet instanceof ClientboundGameEventPacket event
                    && event.getEvent() == ClientboundGameEventPacket.CHANGE_GAME_MODE))) ci.cancel();
    }
}
