package dev.aresos.mixin;

import dev.aresos.mode.ModeInventories;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ServerGamePacketListenerImpl.class)
public abstract class ModeSwitchPacketMixin {
    @Shadow public ServerPlayer player;

    @Inject(method = {"handlePlayerAction", "handleUseItem", "handleUseItemOn", "handleAttack", "handleInteract",
            "handleSetCarriedItem", "handleContainerClick", "handleSetCreativeModeSlot", "handleContainerClose",
            "handlePlaceRecipe", "handleContainerButtonClick", "handlePickItemFromBlock", "handlePickItemFromEntity",
            "handleSelectTrade", "handleEditBook", "handleRenameItem", "handleSetBeaconPacket",
            "handleBundleItemSelectedPacket", "handleContainerSlotStateChanged"},
            at = @At(value = "INVOKE", target = "Lnet/minecraft/network/protocol/PacketUtils;ensureRunningOnSameThread(Lnet/minecraft/network/protocol/Packet;Lnet/minecraft/network/PacketListener;Lnet/minecraft/server/level/ServerLevel;)V", shift = At.Shift.AFTER),
            cancellable = true)
    private void aresos$ignoreUnacknowledgedInput(CallbackInfo ci) {
        if (ModeInventories.of(player).pending()) ci.cancel();
    }
}
