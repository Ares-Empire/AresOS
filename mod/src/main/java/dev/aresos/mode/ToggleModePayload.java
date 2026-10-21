package dev.aresos.mode;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

public record ToggleModePayload() implements CustomPacketPayload {
    public static final ToggleModePayload INSTANCE = new ToggleModePayload();
    public static final Type<ToggleModePayload> TYPE = new Type<>(AresOs.id("toggle_mode"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ToggleModePayload> CODEC = StreamCodec.unit(INSTANCE);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
