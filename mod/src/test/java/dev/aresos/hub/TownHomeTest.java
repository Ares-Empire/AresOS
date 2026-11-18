package dev.aresos.hub;

import dev.aresos.config.AppDefinition;
import dev.aresos.shell.HomeState;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GatePicture;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.Level;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class TownHomeTest {
    @BeforeAll static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    private static HubData hub() {
        return new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(Level.OVERWORLD, new BlockPos(0, 64, 0)),
                new HubData.Fixed(List.of(), List.of()));
    }

    private static AppDefinition app(String id, String name) {
        return new AppDefinition(id, name, List.of(), "minecraft:paper", false, "helper", null, null,
                null, true, null, List.of(id));
    }

    @Test void recordedFrontAndUnbuiltPictureMatchTheTownCellByCell() {
        int size = HubLayout.SIZE;
        var blocks = new String[size * size];
        Arrays.fill(blocks, "white_wool");
        blocks[0] = null;
        blocks[size * (size - 1) + 1] = "blue_ice";
        blocks[size + 2] = "emerald_block";
        var picture = GatePicture.ofBlocks(blocks, size);
        var hub = hub();
        var app = app("notes", "Notes").withSpot("N1L0", "internet");
        var place = Place.parse("N0R0").orElseThrow();
        var plan = Town.plan(hub, app, place, picture);
        var recorded = plan.blocks().entrySet().stream()
                .map(entry -> new AppZone.Placed(entry.getKey(), "minecraft:" + entry.getValue())).toList();
        var gate = new AppZone.Gate(recorded, List.of(), Optional.empty());
        hub.add(new HubData.Logo(app.id(), place.name(), picture.hash(), GatePicture.CONVERTER, app.name(),
                Optional.of("notes"), "fixture", gate));

        var unbuilt = app("other", "Other").withSpot("?", "future_group");
        var state = TownHome.capture(List.of(app, unbuilt), hub, Map.of("notes", 2),
                definition -> definition == unbuilt ? Optional.of(picture) : Optional.empty()).orElseThrow();
        var standing = state.apps().getFirst();
        assertEquals("N0R0", standing.place(), "the record wins over a future move");
        assertEquals("internet", standing.group());
        assertEquals(2, standing.slot());
        assertTrue(standing.standing());
        var waiting = state.apps().getLast();
        assertFalse(waiting.standing());
        assertNull(waiting.place());
        assertNull(waiting.slot());
        assertEquals("system_tools", waiting.group());

        for (int row = 0; row < size; row++) for (int col = 0; col < size; col++) {
            int y = size - 1 - row;
            String expected = picture.at(col, y);
            assertEquals(expected, plan.blocks().get(plan.at(0, col, y)), "front at " + col + "," + y);
            assertEquals(expected == null ? "" : expected, standing.front().get(row * size + col));
            assertEquals(standing.front().get(row * size + col), waiting.front().get(row * size + col));
        }
        assertEquals("blue_ice", standing.front().get(1));
        assertEquals("", standing.front().get((size - 1) * size + size / 2));
    }

    @Test void waitsForPicturesAndForShortNamesAndUsesTheOrderedLiveSlots() {
        var hub = hub();
        var notes = app("notes", "Notes");
        var term = app("term", "Terminal");
        var nameless = app("newapp", "New App").withNames(List.of());
        var apps = List.of(notes, term, nameless);
        var slots = Map.of("notes", 7, "term", 2);
        assertTrue(TownHome.capture(apps, hub, slots, app -> Optional.empty()).isEmpty());

        var first = TownHome.capture(apps, hub, slots, app -> Optional.of(TownKeeper.plainFront(app))).orElseThrow();
        assertEquals(List.of("notes", "term"), first.apps().stream().map(HomeState.App::id).toList());
        assertEquals(List.of(7, 2), first.apps().stream().map(HomeState.App::slot).toList());
        var second = TownHome.capture(List.of(notes, term, nameless.withNames(List.of("nowready"))), hub,
                Map.of("notes", 2, "term", 7), app -> Optional.of(TownKeeper.plainFront(app))).orElseThrow();
        assertEquals(List.of(2, 7), second.apps().subList(0, 2).stream().map(HomeState.App::slot).toList());
        assertEquals("nowready", second.apps().getLast().shortName());
    }

    @Test void waitsWhenAllMyAppsNeedNamesButPublishesAnEmptyMyApps() {
        var hub = hub();
        var notes = app("notes", "Notes").withNames(List.of());
        var term = app("term", "Terminal").withNames(List.of());
        var unowned = app("other", "Other").withMine(false);

        assertTrue(TownHome.capture(List.of(notes, term, unowned), hub, Map.of(),
                app -> Optional.of(TownKeeper.plainFront(app))).isEmpty());

        var named = TownHome.capture(List.of(notes.withNames(List.of("notes")), term, unowned), hub, Map.of(),
                app -> Optional.of(TownKeeper.plainFront(app))).orElseThrow();
        assertEquals(List.of("notes"), named.apps().stream().map(HomeState.App::shortName).toList());

        var empty = TownHome.capture(List.of(unowned), hub, Map.of(), app -> Optional.empty()).orElseThrow();
        assertTrue(empty.apps().isEmpty());
    }
}
