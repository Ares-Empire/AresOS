package dev.aresos.zone;

import com.mojang.serialization.Codec;
import dev.aresos.AresOs;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;

import java.util.ArrayList;
import java.util.List;

public final class ZoneData extends SavedData {
    /** The contents of {@code data/aresos/zones.dat}. */
    public static final Codec<ZoneData> CODEC = AppZone.CODEC.listOf().fieldOf("zones")
            .xmap(ZoneData::new, data -> List.copyOf(data.zones)).codec();
    private static final SavedDataType<ZoneData> TYPE = new SavedDataType<>(AresOs.id("zones"),
            () -> new ZoneData(List.of()), CODEC, null);
    private final List<AppZone> zones;

    private ZoneData(List<AppZone> zones) { this.zones = new ArrayList<>(zones); }
    public static ZoneData get(MinecraftServer server) { return server.getDataStorage().computeIfAbsent(TYPE); }
    public List<AppZone> zones() { return List.copyOf(zones); }

    /** Ownership is a saved coordinate and block ID, never membership of the colour palette. */
    public java.util.Map<net.minecraft.core.BlockPos, String> gateBlocks(net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level> dimension) {
        var blocks = new java.util.HashMap<net.minecraft.core.BlockPos, String>();
        for (var zone : zones) if (zone.dimension().equals(dimension))
            zone.gate().ifPresent(gate -> gate.placed().forEach(placed -> blocks.put(placed.pos(), placed.block())));
        return blocks;
    }

    /** The entity IDs of every gate's sign. */
    public java.util.Set<java.util.UUID> signs() {
        return zones.stream().flatMap(zone -> zone.gate().flatMap(AppZone.Gate::sign).stream())
                .collect(java.util.stream.Collectors.toUnmodifiableSet());
    }

    public String conflict(AppZone candidate) { return conflict(candidate, java.util.Set.of()); }

    /** {@link #conflict} as if the zones with these IDs were gone (their gates come down first). */
    public String conflict(AppZone candidate, java.util.Set<String> leaving) {
        if (candidate.touchesPlayer(candidate.exit().position())) return "Stand fully outside the zone to save its exit point.";
        if (candidate.blocksExit(candidate.exit())) return "Logo would obstruct its own exit point. Leave standing space clear.";
        for (var zone : zones) if (zone.dimension().equals(candidate.dimension()) && !leaving.contains(zone.id())) {
            if (zone.box().intersects(candidate.box())) return "Zone overlaps " + zone.app() + ". Remove or move that zone first.";
            if (zone.touchesPlayer(candidate.exit().position()) || candidate.touchesPlayer(zone.exit().position()))
                return "Zone would cover an exit point. Leave space outside both zones.";
            if (candidate.blocksExit(zone.exit()) || zone.blocksExit(candidate.exit()))
                return "Logo blocks would obstruct an exit point. Leave standing space clear outside both zones.";
        }
        return null;
    }

    public void add(AppZone zone) {
        String conflict = conflict(zone);
        if (conflict != null) throw new IllegalArgumentException(conflict);
        zones.add(zone); setDirty();
    }

    public int remove(java.util.function.Predicate<AppZone> predicate) {
        int before = zones.size(); zones.removeIf(predicate);
        if (before != zones.size()) setDirty();
        return before - zones.size();
    }
}
