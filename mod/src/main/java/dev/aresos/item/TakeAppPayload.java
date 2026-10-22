package dev.aresos.item;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.*;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

public record TakeAppPayload(String id) implements CustomPacketPayload {
    public static final Type<TakeAppPayload> TYPE = new Type<>(AresOs.id("take_app"));
    public static final StreamCodec<RegistryFriendlyByteBuf, TakeAppPayload> CODEC = StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, TakeAppPayload::id, TakeAppPayload::new);
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
