package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Predicate;

/**
 * Who stands where (HUB.md 2.5 and 3.3), worked out from his apps and the places that cannot be built on. A pure
 * function: it reads no file and no world.
 *
 * <p>A wanted app keeps its saved place when that place is of its group, no app before it kept the same place, and
 * the place is not blocked. Every other wanted app then takes the first place of its group, nearest first, that is
 * neither taken nor blocked. So nothing that keeps its place moves for a newcomer. An app that is not wanted (its
 * program is gone) holds no place: its place is free for others, and it is remembered for the app only until
 * another app takes it.
 *
 * @param standing where each wanted app's logo stands, in the order of the apps given
 * @param saved    what each app's saved {@code place} is after this run, wanted or not; an app missing here has
 *                 none (it never had one, or its place went to another app while it was gone)
 * @param skipped  for each wanted app that had to look for a place, the blocked places it passed, nearest first:
 *                 the chat names them
 * @param unplaced wanted apps for which no place of their group is free: they get no logo this time
 */
public record Assignment(Map<String, Place> standing, Map<String, Place> saved, Map<String, List<Place>> skipped,
                         List<String> unplaced) {
    /**
     * One of his apps, in the order of HUB.md 3.3: pinned apps first, then the rest in the order of the apps file.
     *
     * @param group  the app's group: the one he chose by hand if he did, otherwise {@code AppGroup.of(app)}
     * @param saved  the place saved with the app, or null
     * @param wanted the system says it is installed (HUB.md 3.4, point 1); an app that is not is only remembered
     */
    public record App(String id, AppGroup group, Place saved, boolean wanted) {
        public App {
            Objects.requireNonNull(id, "id");
            Objects.requireNonNull(group, "group");
        }
    }

    public Assignment {
        standing = Collections.unmodifiableMap(standing);
        saved = Collections.unmodifiableMap(saved);
        skipped = Collections.unmodifiableMap(skipped);
        unplaced = List.copyOf(unplaced);
    }

    /**
     * @param blocked whether a place cannot be built on (HUB.md 3.3): something of his stands there. It is asked
     *                at most once a place, only about places no app here has taken yet, nearest first.
     */
    public static Assignment of(List<App> apps, Predicate<Place> blocked) {
        var ids = new HashSet<String>();
        for (var app : apps) if (!ids.add(app.id())) throw new IllegalArgumentException("App listed twice: " + app.id());
        var known = new HashMap<Place, Boolean>();
        Predicate<Place> isBlocked = place -> known.computeIfAbsent(place, blocked::test);

        // First every wanted app that can keep its saved place, so a newcomer never takes it away.
        var taken = new HashSet<Place>();
        var placeOf = new HashMap<String, Place>();
        var skipped = new LinkedHashMap<String, List<Place>>();
        for (var app : apps) {
            var place = app.saved();
            if (!app.wanted() || place == null || place.group() != app.group() || taken.contains(place)) continue;
            if (isBlocked.test(place)) skipped.put(app.id(), new ArrayList<>(List.of(place)));
            else { taken.add(place); placeOf.put(app.id(), place); }
        }
        // Then the others, in order, each to the nearest place of its group that is still free.
        var unplaced = new ArrayList<String>();
        for (var app : apps) {
            if (!app.wanted() || placeOf.containsKey(app.id())) continue;
            var passed = skipped.computeIfAbsent(app.id(), id -> new ArrayList<>());
            var place = Place.inOrder(app.group()).filter(candidate -> !taken.contains(candidate)).filter(candidate -> {
                if (!isBlocked.test(candidate)) return true;
                if (!passed.contains(candidate)) passed.add(candidate);
                return false;
            }).findFirst();
            if (place.isPresent()) { taken.add(place.get()); placeOf.put(app.id(), place.get()); }
            else unplaced.add(app.id());
            if (passed.isEmpty()) skipped.remove(app.id());
        }

        var standing = new LinkedHashMap<String, Place>();
        for (var app : apps) if (placeOf.containsKey(app.id())) standing.put(app.id(), placeOf.get(app.id()));
        // Every other app keeps its saved place in the record, unless an app stands there now or remembers it first.
        var saved = new LinkedHashMap<String, Place>();
        var remembered = new HashSet<>(taken);
        for (var app : apps) {
            var place = standing.get(app.id());
            if (place == null && app.saved() != null && remembered.add(app.saved())) place = app.saved();
            if (place != null) saved.put(app.id(), place);
        }
        return new Assignment(standing, saved, skipped, unplaced);
    }
}
