package dev.aresos.zone;

import dev.aresos.AresOs;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

public record ZoneLaunchPayload(String app, long visit) implements CustomPacketPayload {
    public static final Type<ZoneLaunchPayload> TYPE = new Type<>(AresOs.id("zone_launch"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ZoneLaunchPayload> CODEC = StreamCodec.of(
            (buf, payload) -> { buf.writeUtf(payload.app); buf.writeLong(payload.visit); },
            buf -> new ZoneLaunchPayload(buf.readUtf(), buf.readLong()));
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
