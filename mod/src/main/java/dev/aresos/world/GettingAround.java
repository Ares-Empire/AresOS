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
import java.util.function.Supplier;
import java.util.stream.Collectors;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.greedyString;

/**
 * Getting around (HUB.md 2.6, package 37): {@code /go <app>} puts him in front of an app's door, {@code /home} on the
 * home pad. Both move him and nothing else: no block changes, no app opens. A {@code /go} whose arrival is not loaded
 * requests it through the game's ticket system, checks it in a later tick and moves him then ({@link Arrivals}), if
 * the app and its logo's place (or its hand-made zone) are still the same by then. Like {@code /open} and
 * {@code /apps} they exist for the host of an AresOS world only, and only where no other command has the name.
 */
public final class GettingAround {
    private GettingAround() { }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        OwnedNodes.install(dispatcher, Commands.literal("go").requires(AppCommands::allowed)
                .then(Commands.argument("app", greedyString()).suggests(GettingAround::suggestHis)
                        .executes(c -> go(c.getSource(), getString(c, "app")))));
        OwnedNodes.install(dispatcher, Commands.literal("home").requires(AppCommands::allowed)
                .executes(c -> HomeCommands.home(c.getSource())));
    }

    /**
     * Completion with any name {@code /open} takes, for his apps only: {@code /go}, {@code /aresos app swap} and
     * {@code /aresos app move}.
     */
    public static java.util.concurrent.CompletableFuture<com.mojang.brigadier.suggestion.Suggestions> suggestHis(
            com.mojang.brigadier.context.CommandContext<CommandSourceStack> c, com.mojang.brigadier.suggestion.SuggestionsBuilder b) {
        if (!AppCommands.allowed(c.getSource())) return b.buildFuture();
        var listed = listed();
        var reserved = SlashCommands.reserved(c.getSource().getServer());
        var keys = new TreeSet<String>();
        for (var app : listed) if (app.mine()) keys.addAll(OpenPrograms.keys(app, listed, reserved));
        String typed = NameRules.squeeze(b.getRemaining());
        for (String key : keys) if (key.startsWith(typed)) b.suggest(key);
        return b.buildFuture();
    }

    /**
     * One of his installed apps by any name {@code /open} takes, as {@code /go} finds it; empty after one line why
     * not (several match, a program that is not his, one of his that is not installed, nothing).
     */
    public static Optional<AppDefinition> his(CommandSourceStack source, String query) {
        var reserved = SlashCommands.reserved(source.getServer());
        var listed = listed();
        var mine = OpenPrograms.find(listed, query, reserved, AppDefinition::mine);
        if (mine.size() > 1) {
            refuse(source, "Several of your apps match \"" + query + "\": " + mine.stream().map(GettingAround::named)
                    .collect(Collectors.joining(", ")) + ". Type more of the name.");
            return Optional.empty();
        }
        if (mine.isEmpty()) {
            refuse(source, notMine(query, reserved, listed));
            return Optional.empty();
        }
        return Optional.of(mine.getFirst());
    }

    /** The programs the system lists now: the ones {@code /open} takes. */
    private static List<AppDefinition> listed() {
        return AresOs.apps().stream().filter(app -> !app.absent()).toList();
    }

    private static int go(CommandSourceStack source, String query) throws CommandSyntaxException {
        if (!AppCommands.allowed(source)) return 0;
        var player = source.getPlayerOrException();
        var found = his(source, query);
        if (found.isEmpty()) return 0;
        var app = found.get();
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
     * yet, the town's pending work builds the logo as he arrives. Where the spots are not loaded, he is moved a few
     * ticks later, once they are ({@link Arrivals}).
     */
    private static int toLogo(CommandSourceStack source, ServerPlayer player, AppDefinition app, Whereabouts where, boolean complete) {
        var hub = HubData.get(source.getServer());
        var level = source.getServer().getLevel(hub.home().dimension());
        var place = where.place();
        var exit = place.exit(hub.home().dimension(), hub.home().pos());
        String arrived = where.kind() != Whereabouts.Kind.WAITS ? null : complete ? "The town builds " + app.name() + "'s logo here now that you are near."
                : app.name() + "'s logo is built here once the system has listed your programs.";
        String blocked = "Something of yours stands in front of " + app.name() + "'s door (" + place.words()
                + ") with no free spot on the way in, so you stay where you are.";
        String late = app.name() + "'s door (" + place.words() + ") did not load in time, so you stay where you are. Try again in a moment.";
        var server = source.getServer();
        Supplier<Optional<String>> still = () -> {
            var now = AresOs.app(app.id());
            if (!his(now)) return Optional.of(notHis(app));
            return place.equals(Whereabouts.of(server, now, TownKeeper.complete()).place()) ? Optional.empty()
                    : Optional.of(app.name() + "'s logo is no longer at " + place.words() + ", so you stay where you are.");
        };
        return said(source, Arrivals.go(player, level, spots(place, exit.position()), exit.yaw(), exit.pitch(), arrived, blocked, late, still),
                arrived, blocked);
    }

    /** Whether this app, as the apps file has it now, is one of his installed apps. */
    private static boolean his(AppDefinition app) {
        return app != null && app.mine() && !app.absent();
    }

    /** What a waiting {@code /go} says when its app is no longer his by the time its arrival has loaded. */
    private static String notHis(AppDefinition app) {
        return app.name() + " is no longer one of your apps, so you stay where you are.";
    }

    /** The command's lines when {@link Arrivals#go} moved him or refused at once; a later tick says them otherwise. */
    private static int said(CommandSourceStack source, Arrivals.Result result, String arrived, String blocked) {
        return switch (result) {
            case ARRIVED -> {
                if (arrived != null) source.sendSuccess(() -> Component.literal(arrived), false);
                yield 1;
            }
            case BLOCKED -> refuse(source, blocked);
            case LOADING -> 1;
        };
    }

    /**
     * Where he may arrive, in order (two blocks of air on solid ground decide which, {@link HomeSites#isSafe}): the
     * exit point itself, then each block nearer the door, up to the layer in front of the logo, so that he never
     * stands in its doorway.
     */
    static List<Vec3> spots(Place place, Vec3 exit) {
        var ahead = Vec3.atLowerCornerOf(place.facing().getUnitVec3i());
        var spots = new java.util.ArrayList<Vec3>();
        for (int step = 0; step < GateNumbers.EXIT; step++) spots.add(exit.add(ahead.scale(step)));
        return spots;
    }

    /** A world without a town: the exit of the nearest zone of this app he made by hand, in his dimension. */
    private static int toZone(CommandSourceStack source, ServerPlayer player, AppDefinition app) {
        var zone = ZoneData.get(source.getServer()).zones().stream()
                .filter(candidate -> candidate.app().equals(app.id()) && candidate.dimension().equals(player.level().dimension()))
                .min(Comparator.comparingDouble(candidate -> candidate.box().getCenter().distanceToSqr(player.position())));
        if (zone.isEmpty()) return refuse(source, app.name() + " has no logo here.");
        var exit = zone.get().exit();
        var level = source.getServer().getLevel(exit.dimension());
        String blocked = "The exit of " + app.name() + "'s logo is obstructed. Clear it in Build mode; you stay where you are.";
        if (level == null) return refuse(source, blocked);
        String late = "The exit of " + app.name() + "'s logo did not load in time, so you stay where you are. Try again in a moment.";
        var made = zone.get();
        var server = source.getServer();
        Supplier<Optional<String>> still = () -> {
            if (!his(AresOs.app(app.id()))) return Optional.of(notHis(app));
            boolean stands = ZoneData.get(server).zones().stream().anyMatch(candidate -> candidate.id().equals(made.id())
                    && candidate.app().equals(made.app()) && candidate.exit().equals(made.exit()));
            return stands ? Optional.empty() : Optional.of(app.name() + "'s logo here is gone, so you stay where you are.");
        };
        return said(source, Arrivals.go(player, level, List.of(exit.position()), exit.yaw(), exit.pitch(), null, blocked, late, still), null, blocked);
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
