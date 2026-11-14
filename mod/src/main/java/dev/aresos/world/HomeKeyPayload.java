package dev.aresos.world;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** The H key was pressed (package 37): take the host home, as {@code /aresos home} does. */
public record HomeKeyPayload() implements CustomPacketPayload {
    public static final HomeKeyPayload INSTANCE = new HomeKeyPayload();
    public static final Type<HomeKeyPayload> TYPE = new Type<>(AresOs.id("go_home"));
    public static final StreamCodec<RegistryFriendlyByteBuf, HomeKeyPayload> CODEC = StreamCodec.unit(INSTANCE);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
