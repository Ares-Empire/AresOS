package dev.aresos.hub;

import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.icon.AppIcons;
import dev.aresos.names.NameRules;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.PictureReader;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Keeps the town in step with his apps (HUB.md 3.4). One pass ({@link #keep}) compares what should stand with what
 * stands: it takes down the logos that should not stand, builds the missing ones and renews the ones whose picture,
 * converter or sign changed, paves the avenues on to their groups' farthest rows and writes the counts on the groups'
 * names, and says each change in one chat line ({@link TownLines}: one line for many). Every caller goes through it:
 * the runs this class starts by itself (the host enters the world, a complete program list arrives, My apps changes),
 * the commands that change where apps stand ({@link #run}) and {@code /aresos hub rebuild} ({@link #rebuild}).
 *
 * <p>The rules a pass keeps: it runs only on a complete program list and only in a flat home of these rules
 * ({@code hub.dat} says {@code flat-1}). Wanted are the apps of My apps the system lists. Nothing of his is touched:
 * a place where a logo cannot be built is blocked and the app goes on to its group's next place; a logo whose removal
 * is refused stays and is tried again at the next run; a place that is not loaded waits, and the pass is retried every
 * few seconds while he is in the world (so also when he comes near). A place that still holds the town's own logo is
 * not blocked: that logo comes down first, then the new one is built, so a place can change hands in one pass.
 *
 * <p>A frozen town ({@link HubData#frozen}, review fixes 2) changes nothing in the world: no pass runs, {@code hub
 * rebuild} refuses, until he types {@code /aresos hub trust}.
 *
 * <p>Pictures are read away from the server thread (an icon may take seconds to read; {@link PictureReader}, which
 * drops them when the server stops); a pass only uses pictures already read and names the apps it still needs.
 */
public final class TownKeeper {
    /** His apps as the apps file has them, and whether the system's program list behind it is complete. */
    public record Programs(List<AppDefinition> apps, boolean complete) {
        public Programs { apps = List.copyOf(apps); }
    }

    /**
     * What one pass did. {@code lines}: one chat line a change. {@code pending}: work waits for a place to load (or
     * for a place found blocked to be passed by): try again in a few seconds. {@code pictures}: the apps whose
     * picture the pass needed and did not have; read them, then pass again.
     */
    public record Pass(List<String> lines, boolean pending, Set<String> pictures) {
        public Pass { lines = List.copyOf(lines); pictures = Set.copyOf(pictures); }
        static final Pass NOTHING = new Pass(List.of(), false, Set.of());
    }

    /** Where a pass saves the apps' places: {@code AresOs::saveSpots} in the game. */
    @FunctionalInterface
    public interface Spots { void save(Map<String, AppsConfig.Spot> spots) throws IOException; }

    /** A pass that left work waiting runs again after this long. */
    private static final int RETRY_TICKS = 100;
    /** How many blocked places one chat line names. */
    private static final int NAMED_PLACES = 3;
    /** The most rounds one pass makes: each further round follows a build refused in a place that looked free. */
    private static final int ROUNDS = 3;
    private static final AtomicBoolean ASKED = new AtomicBoolean();
    private static volatile boolean complete;
    // Server thread only, like the servers themselves.
    private static final Map<MinecraftServer, TownKeeper> KEEPERS = new WeakHashMap<>();

    /**
     * A picture as read, with the icon's path it was read for. {@code icon} empty: the app has no readable icon, and
     * its logo has a plain front in its group's colour, which is made when asked for, for the group the app has then
     * (package 37: a logo moved to another group needs no picture read again).
     */
    private record Read(String path, Optional<GatePicture> icon) { }

    // One keeper a server; everything below is touched on its thread only.
    /** Places a build refused although they looked free: blocked for this session, so the next pass moves on. */
    private final Set<Place> refused = new HashSet<>();
    /** Lines about lasting conditions (a logo that stays, an app with no place): said once a run he started. */
    private final Set<String> said = new HashSet<>();
    private final Map<String, Read> pictures = new HashMap<>();
    /** Apps whose logo {@code hub rebuild} asked to be built again and that still stand as they were. */
    private final Set<String> renew = new HashSet<>();
    private CompletableFuture<Map<String, Read>> reading;
    private boolean stale, due, pending;
    private long retryAt;

    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(TownKeeper::tick);
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            if (!DesktopWorld.isHost(server, handler.player)) return;
            notice(server).ifPresent(line -> handler.player.sendSystemMessage(Component.literal(line)));
            ask();
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(KEEPERS::remove);
    }

    /**
     * The line he reads as he enters a world whose town's records are in doubt: its town file does not fit the world
     * (the town does nothing here), or the town is frozen (the world was not provably saved with its records). Empty
     * otherwise.
     */
    public static Optional<String> notice(MinecraftServer server) {
        var hub = HubData.get(server);
        if (hub == null || !HubLayout.LOOK.equals(hub.look())) return Optional.empty();
        var refusal = hub.refusal();
        if (refusal.isPresent()) return Optional.of(refused(server, refusal.get()));
        return hub.frozen() ? Optional.of(frozen(hub)) : Optional.empty();
    }

    /**
     * The freeze's line (review fixes 2, point 4): as he enters a frozen world, and {@code hub rebuild}'s refusal. Also
     * when the town file holds no logo: a logo it does not hold may stand.
     */
    public static String frozen(HubData hub) {
        int logos = hub.logos().size();
        return "This world was opened without the town's records since its last visit, so the town builds and removes nothing. "
                + (logos == 0 ? "Its records hold no logo: look the town over" : "Look over its " + (logos == 1 ? "logo" : logos + " logos"))
                + ", then type /aresos hub trust.";
    }

    /** What he reads about a town file that does not fit his world: why, where it is, and how to start afresh. */
    public static String refused(MinecraftServer server, String why) {
        var file = HubData.townFile(server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).toAbsolutePath().normalize());
        return "The town's file " + file + " does not fit this world (" + why + "), so the town builds nothing here and takes nothing down."
                + " To start the town afresh, close the world and move that file out of the world's folder.";
    }

    /**
     * {@code /aresos hub trust}: ends the freeze, the records are the town's again as they are (its seal is renewed at
     * the next save), and a pass follows. Its line says what that means, or empty when the town was not frozen.
     */
    public static Optional<String> trust(MinecraftServer server) {
        var hub = HubData.get(server);
        if (hub == null || !hub.trust()) return Optional.empty();
        ask();
        int logos = hub.logos().size();
        return Optional.of("The town trusts its records again" + (logos == 0 ? "; they hold no logo." : " and keeps their "
                + (logos == 1 ? "logo" : logos + " logos") + " in step with your apps.")
                + " Anything of a logo they do not hold is yours from now on, and the town may build that app a logo of its own.");
    }

    /** Any thread: a complete program list from the system went into the apps file. From now on the town may follow. */
    public static void listed() {
        complete = true;
        ask();
    }

    /** Any thread: his apps changed. The town follows within a few ticks, with every picture read afresh. */
    public static void ask() { ASKED.set(true); }

    /** Whether a complete program list arrived in this game: before that, the town does nothing. */
    public static boolean complete() { return complete; }

    /**
     * Whether the town tells the host about a new app in this world. Then its line ("Spotify is new. It stands in
     * Work & Media, west. /spotify opens it.") is the one line about it, and My apps does not say its own.
     */
    public static boolean speaks(MinecraftServer server) {
        var hub = HubData.get(server);
        return complete && hub != null && HubLayout.LOOK.equals(hub.look()) && hub.refusal().isEmpty() && !hub.frozen();
    }

    /**
     * Server thread: one pass now, with the pictures already read (an app whose picture is missing is built when it
     * has been read, a few ticks later). Its lines go to the host's chat. For commands that change where apps stand
     * ({@code hub rebuild}, {@code swap}, {@code move}): save the apps' places first, then call this.
     */
    public static Pass run(MinecraftServer server) { return keeper(server).runNow(server); }

    /** This server's keeper: its pictures, its retries and the places a build refused in this game. */
    static TownKeeper keeper(MinecraftServer server) { return KEEPERS.computeIfAbsent(server, ignored -> new TownKeeper()); }

    private static void tick(MinecraftServer server) {
        if (complete) keeper(server).step(server);
    }

    static boolean wanted(AppDefinition app) { return app.mine() && !app.absent(); }

    private void step(MinecraftServer server) {
        if (ASKED.getAndSet(false)) stale = true;
        if (reading != null) {
            if (!reading.isDone()) return;
            // Dropped: the server stops (PictureReader); nothing more is done.
            if (reading.isCancelled()) {
                reading = null;
                return;
            }
            try {
                reading.join().forEach(pictures::put);
            } catch (RuntimeException error) {
                AresOs.LOGGER.error("Could not read the town's pictures", error);
            }
            reading = null;
            due = true;
        }
        boolean retry = pending && server.getTickCount() >= retryAt;
        if (!stale && !due && !retry) return;
        var hub = HubData.get(server);
        // Refused or frozen: the town changes nothing in this world; trust asks for a pass.
        if (hub == null || !HubLayout.LOOK.equals(hub.look()) || hub.refusal().isPresent() || hub.frozen()) {
            stale = due = pending = false;
            return;
        }
        // Only while he is in the world: the lines are for him, and it is his presence that loads the places.
        if (host(server).isEmpty()) return;
        if (stale) {
            stale = false;
            said.clear();
            read(server, AresOs.apps().stream().filter(TownKeeper::wanted).toList());
            return;
        }
        due = false;
        runNow(server);
    }

    /**
     * Server thread: {@code /aresos hub rebuild} now, with the pictures already read; its line goes to the host's
     * chat. The caller checks first that there is a town and a complete list (otherwise nothing happens).
     */
    public static Pass rebuild(MinecraftServer server) {
        var keeper = keeper(server);
        return keeper.tell(server, keeper.rebuild(server, new Programs(AresOs.apps(), complete), keeper::picture, AresOs::saveSpots));
    }

    private Pass runNow(MinecraftServer server) {
        return tell(server, keep(server, new Programs(AresOs.apps(), complete), this::picture, AresOs::saveSpots));
    }

    /** Says a pass's lines to the host and schedules what it left: a retry, pictures to read. */
    Pass tell(MinecraftServer server, Pass pass) {
        var host = host(server);
        for (var line : pass.lines()) {
            AresOs.LOGGER.info("Town: {}", line);
            host.ifPresent(player -> player.sendSystemMessage(Component.literal(line)));
        }
        pending = pass.pending();
        retryAt = server.getTickCount() + RETRY_TICKS;
        if (!pass.pictures().isEmpty()) read(server, AresOs.apps().stream().filter(app -> pass.pictures().contains(app.id())).toList());
        return pass;
    }

    private static Optional<ServerPlayer> host(MinecraftServer server) {
        return server.getPlayerList().getPlayers().stream().filter(player -> DesktopWorld.isHost(server, player)).findFirst();
    }

    /** Reads the apps' pictures on the server's picture reader; a pass follows when they are in. */
    void read(MinecraftServer server, List<AppDefinition> apps) {
        if (reading != null) {
            stale = true;
            return;
        }
        reading = PictureReader.of(server).read(apps, app -> new Read(AppIcons.path(app), GateBuilder.icon(app, HubLayout.SIZE)));
    }

    /**
     * The picture of this app's logo as the town holds it: its icon as read, while it was read for the icon the app
     * has now, or a plain front in the colour of the group the app has now. Empty when it has not been read.
     */
    Optional<GatePicture> picture(AppDefinition app) {
        var read = pictures.get(app.id());
        if (read == null || !Objects.equals(read.path(), AppIcons.path(app))) return Optional.empty();
        return Optional.of(read.icon().orElseGet(() -> GatePicture.plain(GateBuilder.concrete(app), HubLayout.SIZE)));
    }

    /**
     * One pass on the server thread (HUB.md 3.4). Does nothing on an incomplete list or outside a flat home of these
     * rules. Saves each app's place through {@code spots} when it changed (keeping its group), then takes down, builds
     * and renews, in that order; then paves the avenues on to their groups' farthest rows and writes the counts on the
     * groups' names.
     *
     * @param pictures the picture of an app's logo, or empty when it has not been read yet
     */
    public Pass keep(MinecraftServer server, Programs programs, Function<AppDefinition, Optional<GatePicture>> pictures, Spots spots) {
        return keep(server, programs, pictures, spots, false, Set.of());
    }

    /**
     * {@link #keep} for {@code swap} and {@code move} ({@link TownMoves}): the same pass, without its line that the
     * logos of {@code quiet} moved, since the command's own line names their new places.
     */
    Pass keep(MinecraftServer server, Programs programs, Function<AppDefinition, Optional<GatePicture>> pictures, Spots spots, Set<String> quiet) {
        return keep(server, programs, pictures, spots, false, quiet);
    }

    /**
     * {@code /aresos hub rebuild} (HUB.md 2.5) as one pass: every standing logo is taken down and built again from
     * the rules, in the place saved with its app. What he changed in a logo is his and stays; where it is in the way
     * the logo stands one place on, as for any blocked place. A logo whose place is not loaded is built again when it
     * is; one he hangs something on stays as it was until he takes that away. Says one line, plus a line for each
     * thing of his in the way. Changes nothing on an incomplete list or outside a flat home of these rules. A frozen
     * town is not rebuilt: its one line is the freeze's.
     */
    public Pass rebuild(MinecraftServer server, Programs programs, Function<AppDefinition, Optional<GatePicture>> pictures, Spots spots) {
        var hub = HubData.get(server);
        if (!programs.complete() || hub == null || !HubLayout.LOOK.equals(hub.look()) || hub.refusal().isPresent()) return Pass.NOTHING;
        if (hub.frozen()) return new Pass(List.of(frozen(hub)), false, Set.of());
        for (var logo : hub.logos()) renew.add(logo.app());
        said.clear();
        refused.clear();
        return keep(server, programs, pictures, spots, true, Set.of());
    }

    private Pass keep(MinecraftServer server, Programs programs, Function<AppDefinition, Optional<GatePicture>> pictures, Spots spots,
                      boolean rebuilt, Set<String> quiet) {
        if (!programs.complete()) return Pass.NOTHING;
        var hub = HubData.get(server);
        // A town file that does not fit this world (point 3), or a frozen town (review fixes 2, point 1): the town
        // builds, takes down, renews and paves nothing, and puts no zone back.
        if (hub == null || !HubLayout.LOOK.equals(hub.look()) || hub.refusal().isPresent() || hub.frozen()) return Pass.NOTHING;
        var level = server.getLevel(hub.home().dimension());
        if (level == null) return Pass.NOTHING;

        var apps = new LinkedHashMap<String, AppDefinition>();
        for (var app : programs.apps()) apps.putIfAbsent(app.id(), app);
        boolean first = hub.logos().isEmpty();
        var lines = new TownLines();
        var need = new LinkedHashSet<String>();
        var cameDown = new HashSet<String>();
        Round round;
        // A build refused in a place that looked free blocks that place, and the app goes on to its group's next
        // place in this same pass: a few more rounds, each only after a new refusal.
        for (int rounds = 1; ; rounds++) {
            int refusals = refused.size();
            round = round(server, hub, apps, pictures, spots, lines, cameDown, quiet);
            need.addAll(round.need());
            if (refused.size() == refusals || rounds == ROUNDS) break;
        }
        renew.retainAll(hub.logos().stream().map(HubData.Logo::app).collect(Collectors.toSet()));
        doorways(server, hub, lines);
        // 5. Roads and names.
        boolean roads = roads(level, hub, round.assignment());
        return new Pass(lines.said(first, rebuilt, round.waiting()), round.pending() || !roads, need);
    }

    /** What one round of a pass left: who stands where, work that waits, pictures it lacked, rebuilt logos that wait. */
    private record Round(Assignment assignment, boolean pending, Set<String> need, int waiting) { }

    /** Points 1 to 4 and 6 of HUB.md 3.4, once. */
    private Round round(MinecraftServer server, HubData hub, Map<String, AppDefinition> apps, Function<AppDefinition, Optional<GatePicture>> pictures,
                        Spots spots, TownLines lines, Set<String> cameDown, Set<String> quiet) {
        var saved = new HashMap<String, Place>();
        for (var app : apps.values()) {
            var place = saved(app, hub.logo(app.id()));
            if (place != null) saved.put(app.id(), place);
        }
        var assignment = plan(server, hub, apps.values(), Set.of());

        save(apps.values(), assignment, spots, lines);
        boolean pending = false;
        int waiting = 0;

        // 2. Take down what should not stand, or not there.
        var stays = new HashSet<String>();
        var waitingFor = new HashSet<Place>();
        for (var logo : hub.logos()) {
            var target = assignment.standing().get(logo.app());
            var at = Place.parse(logo.place());
            if (target != null && at.equals(Optional.of(target))) continue;
            try {
                Town.remove(server, logo.app());
                cameDown.add(logo.app());
                if (target == null) lines.add(TownLines.Kind.DOWN, gone(apps.get(logo.app()), logo));
            } catch (IOException refusal) {
                stays.add(logo.app());
                at.ifPresent(waitingFor::add);
                if (refusal instanceof GateBuilder.NotLoaded) pending = true;
                else once(lines, "The logo of " + logo.name() + " stays: " + refusal.getMessage() + " The town tries again later.");
            }
        }

        // 3. and 4. Build what is missing, renew what changed or what a rebuild asked for.
        var need = new LinkedHashSet<String>();
        for (var entry : assignment.standing().entrySet()) {
            var app = apps.get(entry.getKey());
            var place = entry.getValue();
            // Its old logo stands somewhere else still; one logo an app.
            if (stays.contains(app.id())) continue;
            var standing = hub.logo(app.id());
            // The town's logo that stands there comes down first.
            if (standing.isEmpty() && waitingFor.contains(place)) continue;
            var picture = pictures.apply(app);
            if (picture.isEmpty()) {
                need.add(app.id());
                continue;
            }
            if (standing.isPresent()) {
                if (!changed(standing.get(), app, picture.get()) && !renew.contains(app.id())) continue;
                try {
                    Town.remove(server, app.id());
                } catch (IOException refusal) {
                    if (refusal instanceof GateBuilder.NotLoaded) {
                        pending = true;
                        if (renew.contains(app.id())) waiting++;
                    } else once(lines, "The logo of " + app.name() + " stays as it was: " + refusal.getMessage() + " The town tries again later.");
                    continue;
                }
            }
            try {
                Town.build(server, app, place, picture.get());
                renew.remove(app.id());
                boolean moved = cameDown.contains(app.id());
                if (standing.isPresent()) lines.add(TownLines.Kind.RENEWED, "The logo of " + app.name() + " was renewed.");
                else if (!(moved && quiet.contains(app.id())))
                    lines.add(moved ? TownLines.Kind.MOVED : TownLines.Kind.BUILT, built(app, place, saved.get(app.id()), moved));
            } catch (GateBuilder.NotLoaded notLoaded) {
                pending = true;
            } catch (IOException refusal) {
                // It looked free with a full front, but this app's logo cannot stand there: a longer name needs more
                // air above the sign, or a block he changed in its old logo stayed his. The place is blocked from now
                // on; the next round moves the app on and says so.
                refused.add(place);
                pending = true;
                if (standing.isPresent()) {
                    cameDown.add(app.id());
                    lines.add(TownLines.Kind.WAY, "The logo of " + app.name() + " came down to be renewed but cannot stand at "
                            + place.name() + " again: " + refusal.getMessage());
                }
            }
        }

        // 6. Blocked places, and apps with no place at all.
        for (var skip : assignment.skipped().entrySet()) {
            var app = apps.get(skip.getKey());
            var to = assignment.standing().get(skip.getKey());
            var places = skip.getValue();
            if (places.isEmpty()) continue;
            String named = places.stream().limit(NAMED_PLACES).map(Place::name).collect(Collectors.joining(", "))
                    + (places.size() > NAMED_PLACES ? " and " + (places.size() - NAMED_PLACES) + " more" : "");
            if (to != null) once(lines, named + (places.size() == 1 ? " is" : " are") + " blocked by something of yours, so "
                    + app.name() + " stands at " + to.name() + ".");
        }
        for (var id : assignment.unplaced())
            once(lines, apps.get(id).name() + " has no free place in " + AppGroup.of(apps.get(id)).title() + ": every place there is blocked.");
        return new Round(assignment, pending, need, waiting);
    }

    /**
     * Who stands where after a pass with these apps (HUB.md 3.3): pinned apps first, then the others in the order of
     * the apps file, each app with the place saved with it (or where its logo stands), the places that cannot be built
     * on as the pass finds them. The pass's own planning, and the one {@link TownMoves} checks a swap or move with
     * before it changes anything, so the two cannot plan apart.
     *
     * @param also places taken as blocked on top of the ones the pass finds (a place where one app's logo cannot stand)
     */
    Assignment plan(MinecraftServer server, HubData hub, Collection<AppDefinition> apps, Set<Place> also) {
        var occupied = new HashSet<Place>();
        for (var logo : hub.logos()) Place.parse(logo.place()).ifPresent(occupied::add);
        var unique = new LinkedHashMap<String, AppDefinition>();
        for (var app : apps) unique.putIfAbsent(app.id(), app);
        var order = new ArrayList<AppDefinition>();
        unique.values().stream().filter(AppDefinition::pinned).forEach(order::add);
        unique.values().stream().filter(app -> !app.pinned()).forEach(order::add);
        var input = new ArrayList<Assignment.App>();
        for (var app : order) input.add(new Assignment.App(app.id(), AppGroup.of(app), saved(app, hub.logo(app.id())), wanted(app)));
        return Assignment.of(input, place -> also.contains(place) || blocked(server, place, occupied));
    }

    /**
     * Each standing logo's trigger zone (review fixes 1, step B, point 5). One missing from {@code zones.dat} (a mod of
     * packages 33 to 35 sees it as a plain zone, and its {@code zone remove} takes it away) is put back as the town made
     * it, if nothing else claims its space: no other zone in its box or at its exit, the check every new zone passes.
     * Otherwise the logo stays without a doorway, said once. A zone of his that took the logo's zone ID is his and
     * stays. Not in a frozen town, whose passes do nothing (review fixes 2, point 1).
     */
    private void doorways(MinecraftServer server, HubData hub, TownLines lines) {
        var zones = ZoneData.get(server);
        for (var logo : hub.logos()) {
            var made = hub.zone(logo);
            if (made.isEmpty()) continue;
            var named = zones.zones().stream().filter(zone -> zone.id().equals(logo.zone())).toList();
            if (named.stream().anyMatch(zone -> hub.made(logo, zone))) continue;
            if (!named.isEmpty()) {
                once(lines, "The logo of " + logo.name() + " opens nothing: a zone of yours has its doorway's ID.");
                continue;
            }
            if (zones.conflict(made.get()) != null) {
                once(lines, "The logo of " + logo.name() + " opens nothing: its doorway's zone is gone and a zone of yours is in its place.");
                continue;
            }
            zones.add(made.get());
            AresOs.LOGGER.info("Town: the doorway of {}'s logo was missing from the zones file and is back", logo.name());
        }
    }

    /**
     * HUB.md 3.4, point 5: each avenue paved on to its group's farthest row in use (an app placed there, or a logo
     * that still stands), never back; and on each group's name the number of apps that have their place in it.
     *
     * @return false when part of it waits for its ground to be loaded
     */
    private static boolean roads(ServerLevel level, HubData hub, Assignment assignment) {
        var farthest = new EnumMap<AppGroup, Integer>(AppGroup.class);
        var counts = new EnumMap<AppGroup, Integer>(AppGroup.class);
        for (var place : assignment.standing().values()) {
            farthest.merge(place.group(), place.row(), Math::max);
            counts.merge(place.group(), 1, Integer::sum);
        }
        for (var logo : hub.logos()) Place.parse(logo.place()).ifPresent(place -> farthest.merge(place.group(), place.row(), Math::max));
        boolean done = true;
        for (var group : AppGroup.clockwise()) {
            done &= FlatHub.pave(level, hub, group, farthest.getOrDefault(group, 0));
            done &= FlatHub.count(level, hub, group, counts.getOrDefault(group, 0));
        }
        return done;
    }

    /** The place saved with the app; when the file has none, the place its logo stands in, so it does not move. */
    private static Place saved(AppDefinition app, Optional<HubData.Logo> logo) {
        var place = Place.parse(app.place());
        if (place.isEmpty() && logo.isPresent()) place = Place.parse(logo.get().place());
        return place.orElse(null);
    }

    private boolean blocked(MinecraftServer server, Place place, Set<Place> occupied) {
        // The town's own logo stands there: its app keeps it, or it comes down before another is built.
        if (occupied.contains(place)) return false;
        if (refused.contains(place)) return true;
        try {
            Town.check(server, place);
            return false;
        } catch (GateBuilder.NotLoaded notLoaded) {
            // Neither free nor blocked: an app may take it, and its build waits until the place is loaded.
            return false;
        } catch (IOException his) {
            return true;
        }
    }

    /** Saves the places that changed. A place text this mod cannot read stays as it is unless the app gets a place. */
    private void save(Iterable<AppDefinition> apps, Assignment assignment, Spots spots, TownLines lines) {
        var changes = new LinkedHashMap<String, AppsConfig.Spot>();
        for (var app : apps) {
            var now = assignment.saved().get(app.id());
            var before = Place.parse(app.place());
            if (now == null ? before.isEmpty() : before.equals(Optional.of(now))) continue;
            changes.put(app.id(), new AppsConfig.Spot(now == null ? null : now.name(), app.group()));
        }
        if (changes.isEmpty()) return;
        try {
            spots.save(changes);
        } catch (IOException | RuntimeException error) {
            once(lines, "The town could not save where your apps stand: " + error.getMessage());
        }
    }

    /** A line about something in his way or a lasting condition: said once a run he started. */
    private void once(TownLines lines, String line) {
        if (said.add(line)) lines.add(TownLines.Kind.WAY, line);
    }

    /** Whether a standing logo shows something else than the app's logo would now (HUB.md 3.4, point 4). */
    private static boolean changed(HubData.Logo logo, AppDefinition app, GatePicture picture) {
        return !logo.picture().equals(picture.hash()) || logo.converter() != GatePicture.CONVERTER
                || !logo.name().equals(app.name()) || !logo.shortName().equals(shortName(app));
    }

    private static Optional<String> shortName(AppDefinition app) {
        return Optional.ofNullable(NameRules.mainName(app)).filter(name -> !name.isBlank());
    }

    private static String built(AppDefinition app, Place place, Place saved, boolean moved) {
        String where = place.group().title() + ", " + place.group().outward().getSerializedName();
        String opens = shortName(app).map(name -> " /" + name + " opens it.").orElse("");
        if (moved) return app.name() + " moved to " + where + "." + opens;
        if (saved == null) return app.name() + " is new. It stands in " + where + "." + opens;
        return app.name() + " stands in " + where + "." + opens;
    }

    private static String gone(AppDefinition app, HubData.Logo logo) {
        if (app == null) return "The logo of " + logo.name() + " came down: the app is gone from your apps file.";
        if (app.absent()) return app.name() + " is no longer installed. Its logo came down; its place is kept for its return.";
        if (!app.mine()) return app.name() + " left My apps. Its logo came down.";
        return "The logo of " + app.name() + " came down.";
    }
}
