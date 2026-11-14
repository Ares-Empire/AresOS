package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.ZoneData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;

import java.util.HashSet;

/**
 * Where one of his apps has its logo in this world, or why it has none (HUB.md 2.6): what {@code /apps} says after
 * the app's commands, and where {@code /go} takes him. It only reads: the town's records, the apps file's saved
 * place, the zones file and which chunks are loaded. It never loads a chunk.
 *
 * @param place the logo's place: where it stands, or the saved place it waits for; null when there is none
 */
public record Whereabouts(Kind kind, Place place) {
    public enum Kind {
        /** Its logo stands in {@code place}. */
        STANDS,
        /** Its place is not loaded: the town builds the logo when he comes near (its pending work, every 5 seconds). */
        WAITS,
        /** Its place is loaded but holds no logo yet: the town is still at work (a picture to read, a logo to take down first). */
        BUILDING,
        /** The town has no complete program list in this game yet, and builds nothing until it has one. */
        NO_LIST,
        /** No place of its group is free: every one is blocked by something of his. */
        NO_PLACE,
        /** The town is frozen (package 36, review fixes 2): it builds nothing until {@code /aresos hub trust}. */
        FROZEN,
        /** The town's file does not fit this world: the town builds nothing here. */
        REFUSED,
        /** This world has no town (it is not a flat home of these rules). */
        NO_TOWN
    }

    /**
     * @param complete whether a complete program list arrived in this game ({@link TownKeeper#complete})
     */
    public static Whereabouts of(MinecraftServer server, AppDefinition app, boolean complete) {
        var hub = HubData.get(server);
        if (hub == null || !HubLayout.LOOK.equals(hub.look())) return new Whereabouts(Kind.NO_TOWN, null);
        var level = server.getLevel(hub.home().dimension());
        if (level == null) return new Whereabouts(Kind.NO_TOWN, null);
        var saved = Place.parse(app.place()).orElse(null);
        // Its record: the logo stands where the record says, also in a frozen town (nothing moves there).
        var standing = hub.logo(app.id()).flatMap(logo -> Place.parse(logo.place()));
        if (standing.isPresent()) return new Whereabouts(Kind.STANDS, standing.get());
        if (hub.refusal().isPresent()) {
            // A refused file holds no record that is read: its doorway at the saved place shows the logo stands.
            boolean doorway = saved != null && doorway(server, hub, app, saved);
            return new Whereabouts(doorway ? Kind.STANDS : Kind.REFUSED, saved);
        }
        if (hub.frozen()) return new Whereabouts(Kind.FROZEN, saved);
        if (saved != null && !loaded(level, hub, saved)) return new Whereabouts(Kind.WAITS, saved);
        if (!complete) return new Whereabouts(Kind.NO_LIST, saved);
        return saved == null ? new Whereabouts(Kind.NO_PLACE, null) : new Whereabouts(Kind.BUILDING, saved);
    }

    /**
     * What {@code /apps} says about it: the place in words ("Games, east, front row, left"), or in a few words why
     * its logo does not stand ("Games: no free place").
     */
    public String said(AppGroup group) {
        return switch (kind) {
            case STANDS -> place.words();
            case WAITS -> place.words() + ", built when you come near";
            case BUILDING -> place.words() + ", being built";
            case NO_LIST -> group.title() + ": no logo until the system has listed your programs";
            case NO_PLACE -> group.title() + ": no free place";
            case FROZEN -> group.title() + ": the town is frozen";
            case REFUSED -> group.title() + ": the town's file does not fit this world";
            case NO_TOWN -> group.title() + ": no town in this world";
        };
    }

    /** Whether the zones file holds this app's doorway at the place: a zone of the app with the place's niche as its box. */
    private static boolean doorway(MinecraftServer server, HubData hub, AppDefinition app, Place place) {
        var plan = place.plan(GatePicture.plain(GatePalette.name(place.group().concrete()), HubLayout.SIZE),
                hub.home().dimension(), hub.home().pos(), app.name(), null);
        return ZoneData.get(server).zones().stream().anyMatch(zone -> zone.app().equals(app.id())
                && zone.dimension().equals(hub.home().dimension()) && zone.min().equals(plan.nicheMin()) && zone.max().equals(plan.nicheMax()));
    }

    /** Whether every chunk the place's logo and its way in stand on is loaded, with its entities, as the town needs them. */
    private static boolean loaded(ServerLevel level, HubData hub, Place place) {
        var plan = place.plan(GatePicture.plain(GatePalette.name(place.group().concrete()), HubLayout.SIZE),
                hub.home().dimension(), hub.home().pos(), "?", null);
        var chunks = new HashSet<Long>();
        for (BlockPos pos : plan.space()) chunks.add(ChunkPos.pack(pos.getX() >> 4, pos.getZ() >> 4));
        return chunks.stream().allMatch(chunk -> level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) && level.areEntitiesLoaded(chunk));
    }
}
