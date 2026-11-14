package dev.aresos.world;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.hub.HubData;
import dev.aresos.hub.Place;
import dev.aresos.hub.TownKeeper;
import dev.aresos.hub.Whereabouts;
import dev.aresos.item.AppCommands;
import dev.aresos.names.NameRules;
import dev.aresos.names.OpenPrograms;
import dev.aresos.names.OwnedNodes;
import dev.aresos.names.SlashCommands;
import dev.aresos.zone.GateNumbers;
import dev.aresos.zone.WalkInZones;
import dev.aresos.zone.ZoneData;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.Vec3;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.TreeSet;
import java.util.stream.Collectors;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.greedyString;

/**
 * Getting around (HUB.md 2.6, package 37): {@code /go <app>} puts him in front of an app's door, {@code /home} on the
 * home pad. Both move him and nothing else: no block changes, no app opens, no chunk is held. Like {@code /open} and
 * {@code /apps} they exist for the host of an AresOS world only, and only where no other command has the name.
 */
public final class GettingAround {
    private GettingAround() { }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        OwnedNodes.install(dispatcher, Commands.literal("go").requires(AppCommands::allowed)
                .then(Commands.argument("app", greedyString()).suggests((c, b) -> {
                    if (!AppCommands.allowed(c.getSource())) return b.buildFuture();
                    // Any name /open takes, for his apps only.
                    var listed = listed();
                    var reserved = SlashCommands.reserved(c.getSource().getServer());
                    var keys = new TreeSet<String>();
                    for (var app : listed) if (app.mine()) keys.addAll(OpenPrograms.keys(app, listed, reserved));
                    String typed = NameRules.squeeze(b.getRemaining());
                    for (String key : keys) if (key.startsWith(typed)) b.suggest(key);
                    return b.buildFuture();
                }).executes(c -> go(c.getSource(), getString(c, "app")))));
        OwnedNodes.install(dispatcher, Commands.literal("home").requires(AppCommands::allowed)
                .executes(c -> HomeCommands.home(c.getSource())));
    }

    /** The programs the system lists now: the ones {@code /open} takes. */
    private static List<AppDefinition> listed() {
        return AresOs.apps().stream().filter(app -> !app.absent()).toList();
    }

    private static int go(CommandSourceStack source, String query) throws CommandSyntaxException {
        if (!AppCommands.allowed(source)) return 0;
        var player = source.getPlayerOrException();
        var reserved = SlashCommands.reserved(source.getServer());
        var listed = listed();
        var mine = OpenPrograms.find(listed, query, reserved, AppDefinition::mine);
        if (mine.size() > 1)
            return refuse(source, "Several of your apps match \"" + query + "\": " + mine.stream().map(GettingAround::named)
                    .collect(Collectors.joining(", ")) + ". Type more of the name.");
        if (mine.isEmpty()) return refuse(source, notMine(query, reserved, listed));
        var app = mine.getFirst();
        boolean complete = TownKeeper.complete();
        var where = Whereabouts.of(source.getServer(), app, complete);
        return switch (where.kind()) {
            case STANDS, WAITS -> toLogo(source, player, app, where, complete);
            case NO_TOWN -> toZone(source, player, app);
            case BUILDING -> refuse(source, app.name() + "'s logo at " + where.place().words() + " is not built yet. Try again in a moment.");
            case NO_LIST -> refuse(source, app.name() + " has no logo yet: the town builds nothing until the system has listed your programs.");
            case NO_PLACE -> refuse(source, app.name() + " has no logo: every place of " + dev.aresos.catalogue.AppGroup.of(app).title() + " is blocked by something of yours.");
            case FROZEN -> refuse(source, app.name() + "'s logo does not stand in the town, and the town is frozen: /aresos hub trust lets it build again.");
            case REFUSED -> refuse(source, app.name() + "'s logo does not stand in the town, and the town's file does not fit this world, so the town builds nothing here.");
        };
    }

    /** Why a name finds none of his apps: a program of his that is gone, programs that are not his, or nothing. */
    private static String notMine(String query, java.util.Set<String> reserved, List<AppDefinition> listed) {
        var gone = OpenPrograms.find(AresOs.apps(), query, reserved, app -> app.mine() && app.absent());
        if (!gone.isEmpty()) return gone.getFirst().name() + " is not installed: the system no longer lists it, so it has no logo.";
        var others = OpenPrograms.find(listed, query, reserved, app -> !app.mine());
        if (others.size() == 1)
            return others.getFirst().name() + " is not one of your apps. /aresos app add " + others.getFirst().id() + " adds it.";
        if (others.size() > 1)
            return "None of your apps matches \"" + query + "\". /aresos app add <program> adds one of these: "
                    + others.stream().map(app -> app.name() + " (" + app.id() + ")").collect(Collectors.joining(", ")) + ".";
        return "No program matches \"" + query + "\".";
    }

    /**
     * To the exit point of his app's logo, looking at its door (HUB.md 3.2). Where his own build stands there, to the
     * nearest free spot on the way in towards the door; where there is none, nowhere. For a place that is not loaded
     * yet, the town's pending work builds the logo as he arrives.
     */
    private static int toLogo(CommandSourceStack source, ServerPlayer player, AppDefinition app, Whereabouts where, boolean complete) {
        var hub = HubData.get(source.getServer());
        var level = source.getServer().getLevel(hub.home().dimension());
        var place = where.place();
        var exit = place.exit(hub.home().dimension(), hub.home().pos());
        var spot = arrival(level, place, exit.position());
        if (spot.isEmpty())
            return refuse(source, "Something of yours stands in front of " + app.name() + "'s door (" + place.words()
                    + ") with no free spot on the way in, so you stay where you are.");
        HomeCommands.teleport(player, level, spot.get(), exit.yaw(), exit.pitch());
        WalkInZones.arrived(player);
        if (where.kind() == Whereabouts.Kind.WAITS) {
            String line = complete ? "The town builds " + app.name() + "'s logo here now that you are near."
                    : app.name() + "'s logo is built here once the system has listed your programs.";
            source.sendSuccess(() -> Component.literal(line), false);
        }
        return 1;
    }

    /**
     * The first spot from the exit point towards the door where he can stand (two blocks of air on solid ground):
     * the exit point itself, then each block nearer the door, up to the layer in front of the logo, so that he
     * never stands in its doorway. Reading a block of a place that is not loaded loads its chunk, as the teleport
     * there would; nothing holds it.
     */
    static Optional<Vec3> arrival(ServerLevel level, Place place, Vec3 exit) {
        var ahead = Vec3.atLowerCornerOf(place.facing().getUnitVec3i());
        for (int step = 0; step < GateNumbers.EXIT; step++) {
            var spot = exit.add(ahead.scale(step));
            if (HomeSites.isSafe(level, spot)) return Optional.of(spot);
        }
        return Optional.empty();
    }

    /** A world without a town: the exit of the nearest zone of this app he made by hand, in his dimension. */
    private static int toZone(CommandSourceStack source, ServerPlayer player, AppDefinition app) {
        var zone = ZoneData.get(source.getServer()).zones().stream()
                .filter(candidate -> candidate.app().equals(app.id()) && candidate.dimension().equals(player.level().dimension()))
                .min(Comparator.comparingDouble(candidate -> candidate.box().getCenter().distanceToSqr(player.position())));
        if (zone.isEmpty()) return refuse(source, app.name() + " has no logo here.");
        var exit = zone.get().exit();
        var level = source.getServer().getLevel(exit.dimension());
        if (level == null || !HomeSites.isSafe(level, exit.position()))
            return refuse(source, "The exit of " + app.name() + "'s logo is obstructed. Clear it in Build mode; you stay where you are.");
        HomeCommands.teleport(player, level, exit.position(), exit.yaw(), exit.pitch());
        WalkInZones.arrived(player);
        return 1;
    }

    private static String named(AppDefinition app) {
        String main = NameRules.mainName(app);
        return main.isEmpty() ? app.name() : app.name() + " (/" + main + ")";
    }

    private static int refuse(CommandSourceStack source, String line) {
        source.sendFailure(Component.literal(line));
        return 0;
    }
}
