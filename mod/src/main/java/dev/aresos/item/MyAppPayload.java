package dev.aresos.item;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.*;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** The Apps screen asks for a program to become one of his ({@code mine}) or to leave My apps. */
public record MyAppPayload(String id, boolean mine) implements CustomPacketPayload {
    public static final Type<MyAppPayload> TYPE = new Type<>(AresOs.id("my_app"));
    public static final StreamCodec<RegistryFriendlyByteBuf, MyAppPayload> CODEC = StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, MyAppPayload::id, ByteBufCodecs.BOOL, MyAppPayload::mine, MyAppPayload::new);
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
