package dev.aresos.hub;

import dev.aresos.config.AppDefinition;
import dev.aresos.names.NameRules;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import dev.aresos.zone.ZoneData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.io.IOException;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;

/**
 * The town's logos in the world (HUB.md 3.3 and 3.4): whether a place can take an app's logo now, building it there,
 * and taking it down. A town logo is a gate like one built by hand, built by {@link GateBuilder} with every block
 * going through {@code Placing}; it is recorded in {@code hub.dat} ({@link HubData.Logo}), its trigger zone in
 * {@code zones.dat} without a gate of its own. Who stands where ({@link Assignment}) and when the town is brought in
 * step are the caller's: every function here does one thing or refuses, changing nothing.
 */
public final class Town {
    /** The app a place is checked for when no app is asked about yet; it is never built. */
    private static final String PLACE_CHECK = "aresos-town-place-check";

    private Town() { }

    /**
     * Throws unless an app's logo could be built in a place now. {@link GateBuilder.NotLoaded} says the place is not
     * loaded (neither free nor blocked: try again later); any other refusal names what is in the way, and the place
     * is blocked. On top of a gate's own refusals, the town builds only where the floor under the logo, the layer in
     * front of it and the way in is untouched grass or a block of the hub (HUB.md 3.3).
     */
    public static void check(MinecraftServer server, AppDefinition app, Place place, GatePicture picture) throws IOException {
        check(server, app, place, picture, List.of());
    }

    /**
     * {@link #check} as if the logos of the apps in {@code down} had come down first, as a swap or a move takes them
     * down before it builds (package 37): their blocks read as what {@link #remove} would leave of them (the blocks he
     * changed stay his), their trigger zones as gone. Whether they can come down is {@link #checkRemove}'s.
     */
    public static void check(MinecraftServer server, AppDefinition app, Place place, GatePicture picture, Collection<String> down) throws IOException {
        var hub = hub(server);
        var level = level(server, hub);
        prepare(level, hub, app.id(), plan(hub, app, place, picture), gone(server, level, hub, down));
    }

    /**
     * Throws, changing nothing, unless {@link #remove} would take an app's logo down now: {@link GateBuilder.NotLoaded}
     * while its place is not loaded, otherwise what of his hangs on it; in a frozen town, always. The check
     * {@code remove} itself makes ({@link GateBuilder#checkRemoval}).
     */
    public static void checkRemove(MinecraftServer server, String app) throws IOException {
        var hub = hub(server);
        var logo = hub.logo(app).orElseThrow(() -> new IOException("No logo of " + app + " stands in the town."));
        unfrozen(hub);
        GateBuilder.checkRemoval(level(server, hub), logo.gate());
    }

    /** What taking these apps' logos down would leave, and their zones: the town's own zones only, as {@link #remove}. */
    private static GateBuilder.Gone gone(MinecraftServer server, ServerLevel level, HubData hub, Collection<String> down) {
        if (down.isEmpty()) return GateBuilder.Gone.NONE;
        var blocks = new HashMap<BlockPos, BlockState>();
        var zones = new HashSet<String>();
        for (var app : down) hub.logo(app).ifPresent(logo -> {
            blocks.putAll(GateBuilder.left(level, logo.gate()));
            ZoneData.get(server).zones().stream().filter(zone -> hub.made(logo, zone)).forEach(zone -> zones.add(zone.id()));
        });
        return new GateBuilder.Gone(blocks, zones);
    }

    /**
     * Throws unless a place can take a logo now, whichever app's (HUB.md 3.3, "a place can be built on"), with the
     * same answers as {@link #check}. It plans a full front in the group's concrete: every picture's blocks are part
     * of it, so any app's logo builds where this passes, unless its longer name needs more air above the sign.
     */
    public static void check(MinecraftServer server, Place place) throws IOException {
        var hub = hub(server);
        var full = GatePicture.plain(GatePalette.name(place.group().concrete()), HubLayout.SIZE);
        prepare(level(server, hub), hub, PLACE_CHECK, place.plan(full, hub.home().dimension(), hub.home().pos(), "?", null), GateBuilder.Gone.NONE);
    }

    /**
     * Builds an app's logo in a place and records it, or throws with the reason and changes nothing. The sign shows
     * the app's name and its main short name. One logo an app: an app whose logo stands is refused. A frozen town
     * builds nothing.
     */
    public static HubData.Logo build(MinecraftServer server, AppDefinition app, Place place, GatePicture picture) throws IOException {
        var hub = hub(server);
        unfrozen(hub);
        if (hub.logo(app.id()).isPresent()) throw new IOException("The logo of " + app.name() + " already stands in the town.");
        var level = level(server, hub);
        var prepared = prepare(level, hub, app.id(), plan(hub, app, place, picture), GateBuilder.Gone.NONE);
        var built = GateBuilder.place(prepared);
        var gate = built.gate().orElseThrow();
        // The town's zone opens the app and keeps its exit; its blocks are protected through hub.dat, not by the zone.
        var zone = new AppZone(built.id(), app.id(), built.dimension(), built.min(), built.max(), built.exit(), List.of());
        try {
            ZoneData.get(server).add(zone);
        } catch (IllegalArgumentException conflict) {
            GateBuilder.takeDown(level, gate, prepared.plan().sign());
            throw new IOException(conflict.getMessage());
        }
        var sign = prepared.plan().sign();
        var logo = new HubData.Logo(app.id(), place.name(), picture.hash(), GatePicture.CONVERTER, sign.name(),
                Optional.ofNullable(sign.shortName()).filter(name -> !name.isBlank()), zone.id(), gate);
        hub.add(logo);
        return logo;
    }

    /**
     * Takes an app's logo down: each of its blocks that is still the recorded one (the doormat goes back to the ground
     * it replaced, grass that turned to dirt under it back to grass), its sign, its zone and its record. A block he
     * changed is his and stays. So is a sign or zone that is no longer what the town made (review fixes 1, step B,
     * point 2): a sign he edited, an entity or zone of his that took the recorded ID. Those stay and leave the record
     * with the logo, whose removal still counts as done. Refuses, changing nothing, while its place is not loaded
     * ({@link GateBuilder.NotLoaded}) or when something of his hangs on it, and in a frozen town.
     */
    public static GateBuilder.Removal remove(MinecraftServer server, String app) throws IOException {
        var hub = hub(server);
        var logo = hub.logo(app).orElseThrow(() -> new IOException("No logo of " + app + " stands in the town."));
        unfrozen(hub);
        var removal = GateBuilder.takeDown(level(server, hub), logo.gate(), hub.sign(logo).orElseThrow());
        ZoneData.get(server).remove(zone -> hub.made(logo, zone));
        hub.remove(app);
        return removal;
    }

    /** The gate an app's logo is in a place of this town: its picture, its name and main short name on the sign. */
    public static GatePlan plan(HubData hub, AppDefinition app, Place place, GatePicture picture) {
        return place.plan(picture, hub.home().dimension(), hub.home().pos(), app.name(), NameRules.mainName(app));
    }

    private static GateBuilder.Prepared prepare(ServerLevel level, HubData hub, String app, GatePlan plan, GateBuilder.Gone gone) throws IOException {
        var prepared = GateBuilder.prepare(level, app, plan, gone);
        for (var pos : plan.space()) {
            if (pos.getY() != plan.origin().getY()) continue;
            var floor = pos.below();
            var left = gone.blocks().get(floor);
            // A block of a logo that comes down first counts as what its take-down leaves.
            boolean grass = (left != null ? left : level.getBlockState(floor)).is(Blocks.GRASS_BLOCK);
            if (!grass && (left != null || !hub.holds(level, floor)))
                throw new IOException("The ground at " + floor.toShortString() + " isn't untouched grass. No blocks changed.");
        }
        return prepared;
    }

    /** The record of this world's town; refuses where there is none, or where other rules than these built it. */
    private static HubData hub(MinecraftServer server) throws IOException {
        var hub = HubData.get(server);
        if (hub == null) throw new IOException("This world is not a flat home: it has no town.");
        if (!HubLayout.LOOK.equals(hub.look())) throw new IOException("This town was built by other rules (" + hub.look() + ").");
        var refusal = hub.refusal();
        if (refusal.isPresent()) throw new IOException(TownKeeper.refused(server, refusal.get()));
        return hub;
    }

    /** Refuses in a frozen town (review fixes 2, point 1): it builds and removes nothing until he trusts its records. */
    private static void unfrozen(HubData hub) throws IOException {
        if (hub.frozen()) throw new IOException("The town is frozen: it builds and removes nothing until you type /aresos hub trust.");
    }

    private static ServerLevel level(MinecraftServer server, HubData hub) throws IOException {
        var level = server.getLevel(hub.home().dimension());
        if (level == null) throw new IOException("The town's dimension does not exist.");
        return level;
    }
}
