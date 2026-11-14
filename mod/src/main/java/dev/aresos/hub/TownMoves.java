package dev.aresos.hub;

import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePicture;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * {@code /aresos app swap} and {@code /aresos app move} (package 37): the two ways he arranges the town by hand in
 * version 1. Both are all or nothing. First they check, changing nothing: that the town may change at all (a town of
 * these rules whose records are its own, not frozen, on a complete program list); that each app's logo stands where its
 * place is saved; that the town holds the pictures of the new logos; that the town's own planning puts each app where
 * the command means to; that every logo involved can be taken down now (loaded, nothing of his hangs on it); and that
 * each new place can take its new logo once those logos came down. Only then, in the same server tick, are the places
 * saved and the moved logos built by the town's own pass limited to the command's apps ({@link TownKeeper}, review
 * fixes 2, point 1): there is no second way of building. In that tick the pass takes down and builds only what the
 * checks saw; every other logo, a newcomer, a leaver and a logo due for renewal wait for the next ordinary pass, which
 * the command asks for.
 *
 * <p>How the checks and the pass are kept from agreeing only by chance: each check is the function the pass itself
 * uses, asked before the pass does it. The new places come from {@link TownKeeper#plan}, the pass's own planning with
 * the places it finds blocked; the logos that come down are {@link TownKeeper#down}, the very set the limited pass
 * takes down; a logo's take-down is checked by {@link Town#checkRemove}, which is the check {@link Town#remove} makes;
 * a new logo by {@link Town#check} with the very picture the pass will use and the logos that come down read as their
 * take-downs leave them. Nothing in the world can change between the checks and the pass: one
 * command, one tick, the server thread. The catalogue can (a helper refresh runs on its own thread), so the command takes
 * it once and uses that snapshot throughout, and saves only while the catalogue is still that snapshot. Should the pass
 * still end otherwise, the command says so in one line instead of its own.
 */
public final class TownMoves {
    /** How many places a move passes by in which the moved logo alone cannot stand (its name needs more air). */
    private static final int TRIES = 3;

    private TownMoves() { }

    /**
     * What a swap or move answers: whether it changed the town, its one line, and the pass that followed (its own
     * lines are said after the command's; {@link TownKeeper.Pass#NOTHING} when nothing changed).
     */
    public record Said(boolean done, String line, TownKeeper.Pass pass) {
        static Said no(String line) { return new Said(false, line, TownKeeper.Pass.NOTHING); }
    }

    /**
     * The catalogue as a swap or move takes it, once, at the start (review fixes 1, point 2): his apps and whether the
     * list is complete, for the checks, the saved places and the town's pass alike. {@code token} is what
     * {@link Game#commit} compares when it saves: in this game the very list object the game held then.
     */
    public record Snapshot(Object token, TownKeeper.Programs programs) { }

    /** Saves the new places only while the catalogue is still the snapshot's (its token), under the catalogue's lock. */
    public interface Commit {
        /** False, and nothing saved, when the catalogue changed since the snapshot was taken. */
        boolean save(Object token, Map<String, AppsConfig.Spot> spots) throws IOException;
    }

    /**
     * What the commands take from the game: the catalogue, the pictures the town holds, how to ask the town to read a
     * picture it lacks, where an ordinary pass saves places (the command's own pass saves none), and how the command
     * saves its own. A test gives its own.
     */
    public record Game(Supplier<Snapshot> catalogue, Function<AppDefinition, Optional<GatePicture>> pictures,
                       Consumer<AppDefinition> read, TownKeeper.Spots spots, Commit commit) {
        /** The catalogue as it is now. */
        public TownKeeper.Programs programs() { return catalogue.get().programs(); }
    }

    /**
     * {@code /aresos app swap} in this game: the town's own keeper, pictures and apps file. Server thread. The caller
     * says its line, then {@link #told}.
     */
    public static Said swap(MinecraftServer server, String first, String second) {
        var keeper = TownKeeper.keeper(server);
        return swap(server, keeper, game(server, keeper), first, second);
    }

    /** {@code /aresos app move} in this game. Server thread. The caller says its line, then {@link #told}. */
    public static Said move(MinecraftServer server, String app, AppGroup group) {
        var keeper = TownKeeper.keeper(server);
        return move(server, keeper, game(server, keeper), app, group);
    }

    private static Game game(MinecraftServer server, TownKeeper keeper) {
        return new Game(() -> {
            var apps = AresOs.apps();
            return new Snapshot(apps, new TownKeeper.Programs(apps, TownKeeper.complete()));
        }, keeper::picture, app -> keeper.read(server, List.of(app)), AresOs::saveSpots, AresOs::saveSpotsIf);
    }

    /**
     * After the command's line: the pass's own lines go to his chat (about other apps, or something of his in the way),
     * and what it left (a retry, pictures to read) is scheduled, as after any pass. Nothing when nothing changed.
     */
    public static void told(MinecraftServer server, Said said) {
        if (said.done()) TownKeeper.keeper(server).tell(server, said.pass());
    }

    /**
     * The two apps exchange places. Across two groups each also takes the other place's group as its hand-set group,
     * which is removed where it is the app's own group. Both logos come down and are built in their new places.
     */
    public static Said swap(MinecraftServer server, TownKeeper keeper, Game game, String first, String second) {
        String verb = "swapped";
        var snapshot = game.catalogue().get();
        var programs = snapshot.programs();
        var refusal = refusal(server, programs.complete());
        if (refusal.isPresent()) return Said.no(refusal.get());
        var hub = HubData.get(server);
        var a = app(programs, first);
        var b = app(programs, second);
        if (a.isEmpty() || b.isEmpty()) return Said.no("Nothing was " + verb + ": " + (a.isEmpty() ? first : second) + " is not one of your installed apps.");
        if (a.get().id().equals(b.get().id())) return Said.no("Nothing was " + verb + ": name two different apps.");
        var from = standing(hub, a.get());
        if (from.isEmpty()) return Said.no(why(server, hub, a.get(), verb));
        var to = standing(hub, b.get());
        if (to.isEmpty()) return Said.no(why(server, hub, b.get(), verb));

        // Across two groups, each takes the other's group by hand; within one group, groups stay as they are.
        boolean across = from.get().group() != to.get().group();
        var movedA = a.get().withSpot(to.get().name(), across ? handSet(a.get(), to.get().group()) : a.get().group());
        var movedB = b.get().withSpot(from.get().name(), across ? handSet(b.get(), from.get().group()) : b.get().group());
        var moves = new LinkedHashMap<AppDefinition, Place>();
        moves.put(movedA, to.get());
        moves.put(movedB, from.get());
        var refused = check(server, keeper, game, hub, programs, moves, verb);
        if (refused.isPresent()) return Said.no(refused.get().line());
        return change(server, keeper, game, snapshot, moves, verb, movedA.name() + " now stands at " + to.get().words()
                + ", and " + movedB.name() + " at " + from.get().words() + ".");
    }

    /**
     * The app gets this group as its hand-set group (removed where it is the app's own group) and the first place of
     * the group that is free and can take its logo. Its old logo comes down; its old place is free for others.
     */
    public static Said move(MinecraftServer server, TownKeeper keeper, Game game, String id, AppGroup group) {
        String verb = "moved";
        var snapshot = game.catalogue().get();
        var programs = snapshot.programs();
        var refusal = refusal(server, programs.complete());
        if (refusal.isPresent()) return Said.no(refusal.get());
        var hub = HubData.get(server);
        var app = app(programs, id);
        if (app.isEmpty()) return Said.no("Nothing was " + verb + ": " + id + " is not one of your installed apps.");
        var from = standing(hub, app.get());
        if (from.isEmpty()) return Said.no(why(server, hub, app.get(), verb));
        if (from.get().group() == group)
            return Said.no(app.get().name() + " already stands in " + group.title() + ", " + direction(group) + ". Nothing was " + verb + ".");

        // No place saved: the town's planning gives it the first free place of the group, as it does a newcomer. A place
        // its logo alone cannot take (a longer name needs more air above the sign) is passed by, as the pass would.
        var placeless = app.get().withSpot(null, handSet(app.get(), group));
        var passed = new HashSet<Place>();
        for (int tries = 1; ; tries++) {
            var plan = keeper.plan(server, hub, with(programs.apps(), List.of(placeless)), passed);
            var to = plan.standing().get(app.get().id());
            if (to == null) return Said.no("Nothing was " + verb + ": every place of " + group.title() + " is blocked by something of yours.");
            var moved = placeless.withSpot(to.name(), placeless.group());
            var moves = new LinkedHashMap<AppDefinition, Place>();
            moves.put(moved, to);
            var refused = check(server, keeper, game, hub, programs, moves, verb);
            if (refused.isEmpty()) return change(server, keeper, game, snapshot, moves, verb, moved.name() + " now stands at " + to.words() + ".");
            if (!to.equals(refused.get().unbuildable()) || tries == TRIES) return Said.no(refused.get().line());
            passed.add(to);
        }
    }

    /**
     * Why a check refused: its one line, and the new place whose new logo cannot stand there (null for any other
     * reason; a move passes such a place by).
     */
    private record Refusal(String line, Place unbuildable) {
        Refusal(String line) { this(line, null); }
    }

    /**
     * Every check, changing nothing. Empty when all passed; otherwise the refusal with the one line that says what is
     * in the way and what he can do.
     *
     * @param moves each app as it will be saved (its new place and hand-set group), with its new place
     */
    private static Optional<Refusal> check(MinecraftServer server, TownKeeper keeper, Game game, HubData hub, TownKeeper.Programs programs,
                                           Map<AppDefinition, Place> moves, String verb) {
        String nothing = "Nothing was " + verb + ": ";
        // The pictures the pass will build with. One the town has not read is read away from the server thread.
        var pictures = new LinkedHashMap<String, GatePicture>();
        for (var app : moves.keySet()) {
            var picture = game.pictures().apply(app);
            if (picture.isEmpty()) {
                game.read().accept(app);
                return Optional.of(new Refusal(nothing + "the town is still reading the picture of " + app.name() + ". Try again in a moment."));
            }
            pictures.put(app.id(), picture.get());
        }
        // The town's own planning with the places as they will be saved puts each app where the command means to.
        var plan = keeper.plan(server, hub, with(programs.apps(), moves.keySet()), Set.of());
        for (var move : moves.entrySet())
            if (!move.getValue().equals(plan.standing().get(move.getKey().id())))
                return Optional.of(new Refusal(nothing + "the town would not put " + move.getKey().name() + " at " + move.getValue().words() + ". Try again in a moment."));

        // The logos that come down: the moved apps' own, and any logo of the town that still stands in a new place
        // (a place that changes hands waits for its old logo; it is not blocked). The limited pass takes down exactly
        // these, by the same rule, and no other logo (review fixes 2, point 1).
        var down = TownKeeper.down(hub, scope(moves));
        for (var app : down) {
            var logo = hub.logo(app).orElseThrow();
            String where = Place.parse(logo.place()).map(Place::words).orElse(logo.place());
            try {
                Town.checkRemove(server, app);
            } catch (GateBuilder.NotLoaded notLoaded) {
                return Optional.of(new Refusal(nothing + logo.name() + "'s logo at " + where + " is not loaded. Stand at home and try again."));
            } catch (IOException his) {
                return Optional.of(new Refusal(nothing + logo.name() + "'s logo at " + where + " cannot come down. " + his.getMessage()));
            }
        }
        // Each new place takes its new logo once those logos came down, in the world as their take-downs leave it. No
        // other logo changes in that tick, so the rest of the world is read as it stands.
        for (var move : moves.entrySet()) {
            var app = move.getKey();
            var place = move.getValue();
            try {
                Town.check(server, app, place, pictures.get(app.id()), down);
            } catch (GateBuilder.NotLoaded notLoaded) {
                return Optional.of(new Refusal(nothing + place.words() + " is not loaded. Stand at home and try again."));
            } catch (IOException his) {
                return Optional.of(new Refusal(nothing + app.name() + "'s logo cannot stand at " + place.words() + ". " + his.getMessage(), place));
            }
        }
        return Optional.empty();
    }

    /** The line when a helper refresh changed his apps between the checks and the save. */
    static String changed(String verb) { return "Your apps changed just now. Nothing was " + verb + "; try again."; }

    /**
     * Saves the new places, then the town's pass limited to the moved apps builds them there. The save happens only
     * while the catalogue is still the snapshot the checks used (compared under the catalogue's lock); otherwise
     * nothing changes and one line says to try again. The pass works on that snapshot with the new places, the very
     * apps the checks planned with, saves no place itself and never moves an app of the command on to another place.
     * Then the town is asked for its next ordinary pass, which does what waited. Says {@code done} when every moved logo
     * stands in its new place afterwards; otherwise the one line that says which does not.
     */
    private static Said change(MinecraftServer server, TownKeeper keeper, Game game, Snapshot snapshot, Map<AppDefinition, Place> moves,
                               String verb, String done) {
        var spots = new LinkedHashMap<String, AppsConfig.Spot>();
        for (var app : moves.keySet()) spots.put(app.id(), new AppsConfig.Spot(app.place(), app.group()));
        try {
            if (!game.commit().save(snapshot.token(), spots)) return Said.no(changed(verb));
        } catch (IOException | RuntimeException error) {
            return Said.no("Nothing was " + verb + ": the apps file could not be saved (" + error.getMessage() + ").");
        }
        var programs = new TownKeeper.Programs(with(snapshot.programs().apps(), moves.keySet()), snapshot.programs().complete());
        var pass = keeper.keep(server, programs, game.pictures(), scope(moves));
        keeper.again();
        var hub = HubData.get(server);
        for (var move : moves.entrySet()) {
            var stands = hub.logo(move.getKey().id()).map(HubData.Logo::place);
            if (!stands.equals(Optional.of(move.getValue().name())))
                return new Said(true, "The town did not finish: " + move.getKey().name() + "'s logo does not stand at "
                        + move.getValue().words() + " yet. Its place is saved, and the town keeps trying.", pass);
        }
        return new Said(true, done, pass);
    }

    /** Why the town cannot be changed now, before anything is checked: the answers of {@code hub rebuild}. */
    private static Optional<String> refusal(MinecraftServer server, boolean complete) {
        var hub = HubData.get(server);
        if (hub == null) return Optional.of("This world is not a flat home: it has no town.");
        if (!HubLayout.LOOK.equals(hub.look())) return Optional.of("This town was built by other rules (" + hub.look() + "). This AresOS cannot change it.");
        if (hub.refusal().isPresent()) return Optional.of(TownKeeper.refused(server, hub.refusal().get()));
        if (hub.frozen()) return Optional.of(TownKeeper.frozen(hub));
        if (!complete) return Optional.of("The town waits for the system's list of programs. Nothing changed; try again in a moment.");
        return Optional.empty();
    }

    /** One of his installed apps by ID. */
    private static Optional<AppDefinition> app(TownKeeper.Programs programs, String id) {
        return programs.apps().stream().filter(app -> app.id().equals(id) && TownKeeper.wanted(app)).findFirst();
    }

    /**
     * The place his app's logo stands in, while it is in step: the town's record holds it in the place saved with the
     * app (or the file saves none), in the app's group. Otherwise the town is still at work on it, or it has no logo.
     */
    private static Optional<Place> standing(HubData hub, AppDefinition app) {
        var at = hub.logo(app.id()).flatMap(logo -> Place.parse(logo.place()));
        if (at.isEmpty() || at.get().group() != AppGroup.of(app)) return Optional.empty();
        var saved = Place.parse(app.place());
        return saved.isEmpty() || saved.equals(at) ? at : Optional.empty();
    }

    /** Why an app's logo cannot be moved: it is not in step, or it does not stand. */
    private static String why(MinecraftServer server, HubData hub, AppDefinition app, String verb) {
        String nothing = "Nothing was " + verb + ": ";
        if (hub.logo(app.id()).isPresent()) return nothing + "the town is still moving " + app.name() + "'s logo. Try again in a moment.";
        var where = Whereabouts.of(server, app, true);
        return nothing + switch (where.kind()) {
            case WAITS -> app.name() + "'s logo is not built yet: " + where.place().words() + " is not loaded. Stand at home and try again.";
            case NO_PLACE -> app.name() + " has no logo: every place of " + AppGroup.of(app).title() + " is blocked by something of yours.";
            default -> app.name() + "'s logo is not built yet. Try again in a moment.";
        };
    }

    /** The group saved by hand for an app that now stands in {@code group}: none where it is the app's own group. */
    private static String handSet(AppDefinition app, AppGroup group) {
        return group == AppGroup.of(app.withSpot(app.place(), null)) ? null : group.key();
    }

    /** Each moved app's ID with its new place: the scope of the town's pass for the command. */
    private static Map<String, Place> scope(Map<AppDefinition, Place> moves) {
        var scope = new LinkedHashMap<String, Place>();
        for (var move : moves.entrySet()) scope.put(move.getKey().id(), move.getValue());
        return scope;
    }

    /** His apps with these in place of the ones with their IDs. */
    private static List<AppDefinition> with(List<AppDefinition> apps, Iterable<AppDefinition> changed) {
        var byId = new LinkedHashMap<String, AppDefinition>();
        for (var app : changed) byId.put(app.id(), app);
        var all = new ArrayList<AppDefinition>();
        for (var app : apps) all.add(byId.getOrDefault(app.id(), app));
        return all;
    }

    /** "north", "east" …: the way its avenue runs from home. */
    public static String direction(AppGroup group) { return group.outward().getSerializedName(); }
}
