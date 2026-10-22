package dev.aresos.mode;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Sent before mutation and after all vanilla destination-state packets on the same connection. */
public record ModeSwitchStatePayload(long transaction, boolean complete) implements CustomPacketPayload {
    public static final Type<ModeSwitchStatePayload> TYPE = new Type<>(AresOs.id("mode_switch_state"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ModeSwitchStatePayload> CODEC = StreamCodec.composite(
            ByteBufCodecs.VAR_LONG, ModeSwitchStatePayload::transaction,
            ByteBufCodecs.BOOL, ModeSwitchStatePayload::complete, ModeSwitchStatePayload::new);
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
