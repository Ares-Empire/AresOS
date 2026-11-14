package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;

import static dev.aresos.catalogue.AppGroup.GAMES;
import static dev.aresos.catalogue.AppGroup.INTERNET;
import static dev.aresos.catalogue.AppGroup.SYSTEM_TOOLS;
import static dev.aresos.catalogue.AppGroup.WORK_MEDIA;
import static org.junit.jupiter.api.Assertions.*;

/** Who stands where (HUB.md 2.5 and 3.3). */
class AssignmentTest {
    private static final Predicate<Place> NOTHING_BLOCKED = place -> false;

    private static Place place(String name) { return Place.parse(name).orElseThrow(); }

    private static Assignment.App app(String id, AppGroup group) { return new Assignment.App(id, group, null, true); }

    private static Assignment.App app(String id, AppGroup group, String saved) { return new Assignment.App(id, group, place(saved), true); }

    private static Assignment.App gone(String id, AppGroup group, String saved) { return new Assignment.App(id, group, place(saved), false); }

    /** The apps as the next run sees them: each with the place this run saved for it. */
    private static List<Assignment.App> next(List<Assignment.App> apps, Assignment assignment) {
        return apps.stream().map(app -> new Assignment.App(app.id(), app.group(), assignment.saved().get(app.id()), app.wanted())).toList();
    }

    private static Map<String, String> names(Map<String, Place> places) {
        var names = new LinkedHashMap<String, String>();
        places.forEach((app, place) -> names.put(app, place.name()));
        return names;
    }

    /** The five of HUB.md 3.2: the three starters are pinned and come first, then Discord and Lunar Client. */
    private static final List<Assignment.App> DAY_ONE = List.of(app("browser", INTERNET), app("terminal", SYSTEM_TOOLS),
            app("notepad", SYSTEM_TOOLS), app("discord", INTERNET), app("lunar-client", GAMES));

    @Test void dayOneIsTheDesignsTable() {
        var assignment = Assignment.of(DAY_ONE, NOTHING_BLOCKED);
        assertEquals(Map.of("browser", "N0L0", "discord", "N0R0", "lunar-client", "E0L0", "terminal", "S0L0", "notepad", "S0R0"),
                names(assignment.standing()));
        assertEquals(List.of("browser", "terminal", "notepad", "discord", "lunar-client"), List.copyOf(assignment.standing().keySet()));
        assertEquals(assignment.standing(), assignment.saved());
        assertTrue(assignment.skipped().isEmpty());
        assertTrue(assignment.unplaced().isEmpty());
        // Pinned first: a pinned Discord would have the front left place.
        assertEquals(place("N0L0"), Assignment.of(List.of(app("discord", INTERNET), app("browser", INTERNET)), NOTHING_BLOCKED).standing().get("discord"));
    }

    @Test void aNewAppTakesTheNearestFreePlaceOfItsGroupAndNothingElseMoves() {
        var town = next(DAY_ONE, Assignment.of(DAY_ONE, NOTHING_BLOCKED));
        var apps = new ArrayList<>(town);
        apps.add(app("spotify", WORK_MEDIA));
        // A pinned newcomer comes first in the list and still takes no saved place away.
        apps.addFirst(app("firefox", INTERNET));
        var assignment = Assignment.of(apps, NOTHING_BLOCKED);
        assertEquals("W0L0", assignment.standing().get("spotify").name());
        assertEquals("N1L0", assignment.standing().get("firefox").name());
        for (var app : town) assertEquals(app.saved(), assignment.standing().get(app.id()), app.id() + " moved");
        // Run again: the same town.
        assertEquals(assignment.standing(), Assignment.of(next(apps, assignment), NOTHING_BLOCKED).standing());
    }

    @Test void aRemovedAppsPlaceStaysFreeAndItComesBackThere() {
        var town = next(DAY_ONE, Assignment.of(DAY_ONE, NOTHING_BLOCKED));
        var without = town.stream().map(app -> app.id().equals("discord") ? gone("discord", INTERNET, "N0R0") : app).toList();
        var away = Assignment.of(without, NOTHING_BLOCKED);
        assertFalse(away.standing().containsKey("discord"));
        assertFalse(away.standing().containsValue(place("N0R0")), "Someone moved into Discord's place");
        assertEquals(place("N0R0"), away.saved().get("discord"), "The place is not remembered");
        for (var app : town) if (!app.id().equals("discord")) assertEquals(app.saved(), away.standing().get(app.id()));

        var back = Assignment.of(next(town, away), NOTHING_BLOCKED);
        assertEquals(place("N0R0"), back.standing().get("discord"));
        assertEquals(names(Assignment.of(DAY_ONE, NOTHING_BLOCKED).standing()), names(back.standing()));
    }

    @Test void aPlaceTakenWhileItsAppWasAwayIsNotTakenBack() {
        var town = next(DAY_ONE, Assignment.of(DAY_ONE, NOTHING_BLOCKED));
        var apps = new ArrayList<>(town.stream().map(app -> app.id().equals("discord") ? gone("discord", INTERNET, "N0R0") : app).toList());
        apps.add(app("mail", INTERNET));
        var away = Assignment.of(apps, NOTHING_BLOCKED);
        assertEquals(place("N0R0"), away.standing().get("mail"), "The newcomer did not take the nearest free place");
        assertFalse(away.saved().containsKey("discord"), "Discord still remembers a place that is no longer free");

        // Discord comes back: Mail stays, Discord takes the next free place.
        var returning = next(apps, away).stream().map(app -> app.id().equals("discord") ? app("discord", INTERNET) : app).toList();
        var back = Assignment.of(returning, NOTHING_BLOCKED);
        assertEquals(place("N0R0"), back.standing().get("mail"));
        assertEquals(place("N1L0"), back.standing().get("discord"));
    }

    @Test void twoAppsWithOneSavedPlaceTheFirstKeepsIt() {
        var assignment = Assignment.of(List.of(app("a", INTERNET, "N0R0"), app("b", INTERNET, "N0R0")), NOTHING_BLOCKED);
        assertEquals(place("N0R0"), assignment.standing().get("a"));
        assertEquals(place("N0L0"), assignment.standing().get("b"));
        // A place he moved out of another group by hand: the app stands in its own group.
        var moved = Assignment.of(List.of(app("steam", GAMES, "N0L0")), NOTHING_BLOCKED);
        assertEquals(place("E0L0"), moved.standing().get("steam"));
        assertEquals(place("E0L0"), moved.saved().get("steam"));
        assertThrows(IllegalArgumentException.class, () -> Assignment.of(List.of(app("a", GAMES), app("a", INTERNET)), NOTHING_BLOCKED));
    }

    @Test void aBlockedPlaceIsSkippedAndNamed() {
        var asked = new HashMap<Place, Integer>();
        Predicate<Place> blocked = place -> {
            asked.merge(place, 1, Integer::sum);
            return Set.of(place("N0R0"), place("N1L0"), place("S0L0")).contains(place);
        };
        var assignment = Assignment.of(DAY_ONE, blocked);
        assertEquals(Map.of("browser", "N0L0", "discord", "N1R0", "lunar-client", "E0L0", "terminal", "S0R0", "notepad", "S1L0"),
                names(assignment.standing()));
        // Each app that passed a blocked place says so; Notepad passed his build at S0L0 too.
        assertEquals(Map.of("discord", List.of(place("N0R0"), place("N1L0")), "terminal", List.of(place("S0L0")), "notepad", List.of(place("S0L0"))),
                assignment.skipped());
        assertTrue(asked.values().stream().allMatch(count -> count == 1), "A place was looked at twice: " + asked);

        // His shed now stands on Discord's saved place: Discord goes on to the next free place, the others stay.
        var town = next(DAY_ONE, Assignment.of(DAY_ONE, NOTHING_BLOCKED));
        var shed = Assignment.of(town, place -> place.equals(place("N0R0")));
        assertEquals(place("N1L0"), shed.standing().get("discord"));
        assertEquals(place("N1L0"), shed.saved().get("discord"));
        assertEquals(List.of(place("N0R0")), shed.skipped().get("discord"));
        assertEquals(place("N0L0"), shed.standing().get("browser"));
        assertEquals(1, shed.skipped().size());
    }

    @Test void aGroupWithNoFreePlaceLeavesItsAppWithoutALogo() {
        var assignment = Assignment.of(List.of(app("browser", INTERNET), app("steam", GAMES, "E0L0")), place -> place.group() == GAMES);
        assertEquals(List.of("steam"), assignment.unplaced());
        assertFalse(assignment.standing().containsKey("steam"));
        assertEquals(place("E0L0"), assignment.saved().get("steam"), "An app with nowhere to go forgets its place");
        assertEquals(Place.ROWS * (Place.ROWS + 1), assignment.skipped().get("steam").size());
        assertEquals(place("N0L0"), assignment.standing().get("browser"));
    }

    /** HUB.md 2.2's forty apps with fourteen in one group: System & Tools fills rows 0 to 3, nearest first. */
    @Test void fortyAppsWithFourteenInOneGroup() {
        var counts = Map.of(SYSTEM_TOOLS, 14, INTERNET, 10, WORK_MEDIA, 9, GAMES, 7);
        var apps = new ArrayList<Assignment.App>();
        // Interleaved, as an apps file would have them.
        for (int i = 0; apps.size() < 40; i++) for (var group : List.of(SYSTEM_TOOLS, INTERNET, WORK_MEDIA, GAMES))
            if (i < counts.get(group)) apps.add(app(group.name().toLowerCase() + "-" + i, group));
        assertEquals(40, apps.size());
        var assignment = Assignment.of(apps, NOTHING_BLOCKED);
        assertEquals(40, assignment.standing().size());
        assertEquals(40, new HashSet<>(assignment.standing().values()).size());
        for (var group : AppGroup.values()) {
            var expected = Place.inOrder(group).limit(counts.get(group)).toList();
            var actual = apps.stream().filter(app -> app.group() == group).map(app -> assignment.standing().get(app.id())).toList();
            assertEquals(expected, actual, group.title());
        }
        assertEquals(3, assignment.standing().values().stream().mapToInt(Place::row).max().orElseThrow());
        assertEquals(List.of("S3L0", "S3R0"), assignment.standing().values().stream().filter(place -> place.row() == 3).map(Place::name).toList());

        // One of them leaves and another joins the same group: the newcomer takes the freed place, nobody else moves.
        var town = next(apps, assignment);
        var changed = new ArrayList<Assignment.App>();
        for (var app : town) changed.add(app.id().equals("system_tools-4") ? new Assignment.App(app.id(), app.group(), app.saved(), false) : app);
        changed.add(app("htop", SYSTEM_TOOLS));
        var after = Assignment.of(changed, NOTHING_BLOCKED);
        assertEquals(assignment.standing().get("system_tools-4"), after.standing().get("htop"));
        for (var app : town) if (!app.id().equals("system_tools-4")) assertEquals(app.saved(), after.standing().get(app.id()), app.id());
    }
}
