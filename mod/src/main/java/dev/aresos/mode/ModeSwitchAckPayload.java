package dev.aresos.mode;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

public record ModeSwitchAckPayload(long transaction) implements CustomPacketPayload {
    public static final Type<ModeSwitchAckPayload> TYPE = new Type<>(AresOs.id("mode_switch_ack"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ModeSwitchAckPayload> CODEC = StreamCodec.composite(
            ByteBufCodecs.VAR_LONG, ModeSwitchAckPayload::transaction, ModeSwitchAckPayload::new);
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
