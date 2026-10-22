package dev.aresos.zone;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

public record ZoneReturnPayload(long visit, boolean returned) implements CustomPacketPayload {
    public static final Type<ZoneReturnPayload> TYPE = new Type<>(AresOs.id("zone_return"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ZoneReturnPayload> CODEC = StreamCodec.of(
            (buf, payload) -> { buf.writeLong(payload.visit); buf.writeBoolean(payload.returned); },
            buf -> new ZoneReturnPayload(buf.readLong(), buf.readBoolean()));
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
