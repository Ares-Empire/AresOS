package dev.aresos.zone;

import com.mojang.serialization.Codec;
import dev.aresos.AresOs;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;

import java.util.ArrayList;
import java.util.List;

public final class ZoneData extends SavedData {
    private static final Codec<ZoneData> CODEC = AppZone.CODEC.listOf().fieldOf("zones")
            .xmap(ZoneData::new, data -> List.copyOf(data.zones)).codec();
    private static final SavedDataType<ZoneData> TYPE = new SavedDataType<>(AresOs.id("zones"),
            () -> new ZoneData(List.of()), CODEC, null);
    private final List<AppZone> zones;

    private ZoneData(List<AppZone> zones) { this.zones = new ArrayList<>(zones); }
    public static ZoneData get(MinecraftServer server) { return server.getDataStorage().computeIfAbsent(TYPE); }
    public List<AppZone> zones() { return List.copyOf(zones); }

    public String conflict(AppZone candidate) {
        if (candidate.touchesPlayer(candidate.exit().position())) return "Stand fully outside the zone to save its exit point.";
        if (candidate.blocksExit(candidate.exit())) return "Logo would obstruct its own exit point. Leave standing space clear.";
        for (var zone : zones) if (zone.dimension().equals(candidate.dimension())) {
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
