package dev.aresos.hub;

import dev.aresos.config.AppDefinition;
import dev.aresos.names.NameRules;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import dev.aresos.zone.ZoneData;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;

import java.io.IOException;
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
    private Town() { }

    /**
     * Throws unless an app's logo could be built in a place now. {@link GateBuilder.NotLoaded} says the place is not
     * loaded (neither free nor blocked: try again later); any other refusal names what is in the way, and the place
     * is blocked. On top of a gate's own refusals, the town builds only where the floor under the logo, the layer in
     * front of it and the way in is untouched grass or a block of the hub (HUB.md 3.3).
     */
    public static void check(MinecraftServer server, AppDefinition app, Place place, GatePicture picture) throws IOException {
        var hub = hub(server);
        prepare(level(server, hub), hub, app, place, picture);
    }

    /**
     * Builds an app's logo in a place and records it, or throws with the reason and changes nothing. The sign shows
     * the app's name and its main short name. One logo an app: an app whose logo stands is refused.
     */
    public static HubData.Logo build(MinecraftServer server, AppDefinition app, Place place, GatePicture picture) throws IOException {
        var hub = hub(server);
        if (hub.logo(app.id()).isPresent()) throw new IOException("The logo of " + app.name() + " already stands in the town.");
        var level = level(server, hub);
        var prepared = prepare(level, hub, app, place, picture);
        var built = GateBuilder.place(prepared);
        var gate = built.gate().orElseThrow();
        // The town's zone opens the app and keeps its exit; its blocks are protected through hub.dat, not by the zone.
        var zone = new AppZone(built.id(), app.id(), built.dimension(), built.min(), built.max(), built.exit(), List.of());
        try {
            ZoneData.get(server).add(zone);
        } catch (IllegalArgumentException conflict) {
            GateBuilder.takeDown(level, gate);
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
     * changed is his and stays. Refuses, changing nothing, while its place is not loaded ({@link
     * GateBuilder.NotLoaded}) or when something of his hangs on it.
     */
    public static GateBuilder.Removal remove(MinecraftServer server, String app) throws IOException {
        var hub = hub(server);
        var logo = hub.logo(app).orElseThrow(() -> new IOException("No logo of " + app + " stands in the town."));
        var removal = GateBuilder.takeDown(level(server, hub), logo.gate());
        ZoneData.get(server).remove(zone -> zone.id().equals(logo.zone()));
        hub.remove(app);
        return removal;
    }

    /** The gate an app's logo is in a place of this town: its picture, its name and main short name on the sign. */
    public static GatePlan plan(HubData hub, AppDefinition app, Place place, GatePicture picture) {
        return place.plan(picture, hub.home().dimension(), hub.home().pos(), app.name(), NameRules.mainName(app));
    }

    private static GateBuilder.Prepared prepare(ServerLevel level, HubData hub, AppDefinition app, Place place, GatePicture picture) throws IOException {
        var plan = plan(hub, app, place, picture);
        var prepared = GateBuilder.prepare(level, app.id(), plan);
        for (var pos : plan.space()) {
            if (pos.getY() != plan.origin().getY()) continue;
            var floor = pos.below();
            if (!level.getBlockState(floor).is(Blocks.GRASS_BLOCK) && !hub.holds(level, floor))
                throw new IOException("The ground at " + floor.toShortString() + " isn't untouched grass. No blocks changed.");
        }
        return prepared;
    }

    /** The record of this world's town; refuses where there is none, or where other rules than these built it. */
    private static HubData hub(MinecraftServer server) throws IOException {
        var hub = HubData.get(server);
        if (hub == null) throw new IOException("This world is not a flat home: it has no town.");
        if (!HubLayout.LOOK.equals(hub.look())) throw new IOException("This town was built by other rules (" + hub.look() + ").");
        return hub;
    }

    private static ServerLevel level(MinecraftServer server, HubData hub) throws IOException {
        var level = server.getLevel(hub.home().dimension());
        if (level == null) throw new IOException("The town's dimension does not exist.");
        return level;
    }
}
