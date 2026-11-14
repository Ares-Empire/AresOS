package dev.aresos.hub;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** The orchestrator's decision for step 3: a big change is said in one line; what is in his way, one by one. */
class TownLinesTest {
    private static TownLines built(int count) {
        var lines = new TownLines();
        for (int i = 1; i <= count; i++) lines.add(TownLines.Kind.BUILT, "App " + i + " is new. It stands in Internet, north.");
        return lines;
    }

    private static List<String> texts(int count) {
        var texts = new ArrayList<String>();
        for (int i = 1; i <= count; i++) texts.add("App " + i + " is new. It stands in Internet, north.");
        return texts;
    }

    @Test
    void fiveChangesAreSaidOneByOne() {
        assertEquals(texts(5), built(5).said(false, false, 0));
    }

    /** The orchestrator's decision in review fixes 1 (step B, point 6): a first build says one line, whatever the count. */
    @Test
    void aFirstBuildIsOneLineWhateverTheCount() {
        assertEquals(List.of("The town is built: 5 logos. /apps lists them."), built(5).said(true, false, 0));
        assertEquals(List.of("The town is built: 1 logo. /apps lists it."), built(1).said(true, false, 0));
        var blocked = built(2);
        blocked.add(TownLines.Kind.WAY, "N0L0 is blocked by something of yours, so App 2 stands at N0R0.");
        assertEquals(List.of("The town is built: 2 logos. /apps lists them.", "N0L0 is blocked by something of yours, so App 2 stands at N0R0."),
                blocked.said(true, false, 0));
        // Only lines about his things: nothing was built, nothing to sum up.
        var way = new TownLines();
        way.add(TownLines.Kind.WAY, "Mail has no free place in Internet: every place there is blocked.");
        assertEquals(List.of("Mail has no free place in Internet: every place there is blocked."), way.said(true, false, 0));
    }

    @Test
    void sixChangesAreOneLine() {
        assertEquals(List.of("The town is built: 6 logos. /apps lists them."), built(6).said(true, false, 0));
        assertEquals(List.of("The town changed: 6 logos built. /apps lists where your apps stand."), built(6).said(false, false, 0));
    }

    @Test
    void fortyAppsOnTheFirstBuildAreOneLineAndWhatIsInHisWayIsSaidOneByOne() {
        var lines = built(40);
        lines.add(TownLines.Kind.WAY, "N1L0 is blocked by something of yours, so Mail stands at N1R0.");
        lines.add(TownLines.Kind.WAY, "The logo of Chrome stays: his torch. The town tries again later.");
        assertEquals(List.of("The town is built: 40 logos. /apps lists them.",
                "N1L0 is blocked by something of yours, so Mail stands at N1R0.",
                "The logo of Chrome stays: his torch. The town tries again later."), lines.said(true, false, 0));
    }

    @Test
    void manyChangesOfEveryKindAreCountedInOneLine() {
        var lines = built(3);
        lines.add(TownLines.Kind.MOVED, "Chrome moved to Internet, north.");
        lines.add(TownLines.Kind.RENEWED, "The logo of Spotify was renewed.");
        lines.add(TownLines.Kind.DOWN, "Mail left My apps. Its logo came down.");
        lines.add(TownLines.Kind.DOWN, "Far is no longer installed. Its logo came down; its place is kept for its return.");
        lines.add(TownLines.Kind.WAY, "N2L0 is blocked by something of yours, so App 3 stands at N2R0.");
        // Not a first build when something came down or moved, even with no logo standing before.
        for (boolean first : new boolean[] {true, false})
            assertEquals(List.of("The town changed: 3 logos built, 1 moved, 1 renewed, 2 taken down. /apps lists where your apps stand.",
                    "N2L0 is blocked by something of yours, so App 3 stands at N2R0."), lines.said(first, false, 0));
    }

    @Test
    void aRebuildIsAlwaysOneLine() {
        var lines = new TownLines();
        lines.add(TownLines.Kind.RENEWED, "The logo of Chrome was renewed.");
        lines.add(TownLines.Kind.RENEWED, "The logo of Discord was renewed.");
        lines.add(TownLines.Kind.MOVED, "Mail moved to Internet, north.");
        lines.add(TownLines.Kind.WAY, "N0L0 is blocked by something of yours, so Mail stands at N1L0.");
        assertEquals(List.of("The town was rebuilt from the rules: 2 logos built again, 1 moved. 1 more is built again when you come near.",
                "N0L0 is blocked by something of yours, so Mail stands at N1L0."), lines.said(false, true, 1));
        assertEquals(List.of("The town was rebuilt from the rules: no logo stood to build again."), new TownLines().said(false, true, 0));
        assertEquals(List.of("The town was rebuilt from the rules: 1 logo built again."), single().said(false, true, 0));
    }

    private static TownLines single() {
        var lines = new TownLines();
        lines.add(TownLines.Kind.RENEWED, "The logo of Chrome was renewed.");
        return lines;
    }

    @Test
    void nothingChangedSaysNothing() {
        assertEquals(List.of(), new TownLines().said(true, false, 0));
    }
}
