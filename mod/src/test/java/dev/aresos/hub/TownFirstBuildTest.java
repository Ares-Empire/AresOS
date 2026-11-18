package dev.aresos.hub;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TownFirstBuildTest {
    private static final Set<String> APPS = Set.of("the-first-app-list");

    private static TownLines built(int count) {
        var lines = new TownLines();
        for (int i = 0; i < count; i++) lines.add(TownLines.Kind.BUILT, "App " + i + " is new.");
        return lines;
    }

    private static List<String> pass(TownLines.FirstBuild build, TownLines lines, boolean first, boolean pending, long tick) {
        return build.said(lines, first, false, 0, pending, tick, APPS);
    }

    @Test
    void aCompleteFirstPassSpeaksImmediatelyWhateverTheCount() {
        assertEquals(List.of("The town is built: 1 logo. /apps lists it."),
                pass(new TownLines.FirstBuild(), built(1), true, false, 3));
        assertEquals(List.of("The town is built: 40 logos. /apps lists them."),
                pass(new TownLines.FirstBuild(), built(40), true, false, 3));
    }

    @Test
    void twoPassesOfOneFirstBuildSayOneTotal() {
        var build = new TownLines.FirstBuild();
        assertEquals(List.of(), pass(build, built(32), true, true, 3));
        assertEquals(List.of(), pass(build, built(0), false, true, 53));
        assertEquals(List.of("The town is built: 40 logos. /apps lists them."), pass(build, built(8), false, false, 103));
        assertEquals(List.of(), pass(build, built(0), false, false, 303));
    }

    @Test
    void wayLinesInEitherPassAreSaidOnceAndNeverWait() {
        var build = new TownLines.FirstBuild();
        var first = built(32);
        first.add(TownLines.Kind.WAY, "Something of yours blocks N0L0.");
        assertEquals(List.of("Something of yours blocks N0L0."), pass(build, first, true, true, 3));
        var second = built(8);
        second.add(TownLines.Kind.WAY, "Something of yours blocks S4L0.");
        assertEquals(List.of("The town is built: 40 logos. /apps lists them.", "Something of yours blocks S4L0."),
                pass(build, second, false, false, 103));
    }

    @Test
    void aRealChangeAfterCompletionSpeaksAsBefore() {
        var build = new TownLines.FirstBuild();
        pass(build, built(40), true, false, 3);
        var change = new TownLines();
        for (int i = 0; i < 6; i++) change.add(TownLines.Kind.RENEWED, "An icon changed.");
        assertEquals(List.of("The town changed: 6 logos renewed. /apps lists where your apps stand."),
                pass(build, change, false, false, 4));
        assertEquals(List.of("App 0 is new."), pass(build, built(1), false, false, 5));
    }

    @Test
    void afterTheBoundLaterBuildsSpeakAsBefore() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        assertEquals(200, TownLines.FirstBuild.WAIT_TICKS);
        assertEquals(List.of(), pass(build, built(0), false, true, 202));
        assertEquals(List.of("The town is built: 32 logos. /apps lists them."), pass(build, built(0), false, true, 203));
        assertEquals(List.of("The town changed: 8 logos built. /apps lists where your apps stand."),
                pass(build, built(8), false, false, 303));
    }

    @Test
    void theBoundAlsoExpiresWhileWaitingForPicturesWithoutAnotherPass() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        assertEquals(List.of(), build.expire(202));
        assertEquals(List.of("The town is built: 32 logos. /apps lists them."), build.expire(203));
        assertEquals(List.of(), build.expire(204));
        assertEquals(List.of("The town changed: 8 logos built. /apps lists where your apps stand."),
                pass(build, built(8), false, false, 303));
    }

    @Test
    void theBoundStartsWithTheFirstActualBuild() {
        var build = new TownLines.FirstBuild();
        assertEquals(List.of(), pass(build, built(0), true, true, 3));
        assertEquals(List.of(), pass(build, built(0), true, true, 503));
        assertEquals(List.of(), build.expire(603));
        assertEquals(List.of(), pass(build, built(32), true, true, 703));
        assertEquals(List.of(), build.expire(902));
        assertEquals(List.of("The town is built: 32 logos. /apps lists them."), build.expire(903));
    }

    @Test
    void aChangeEndsTheFirstBuildBeforeItsReplacementCanSpeak() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        var deferred = new TownLines();
        deferred.changeStarted();
        assertEquals(List.of("The town is built: 32 logos. /apps lists them."), pass(build, deferred, false, true, 4));
        var later = built(8);
        later.add(TownLines.Kind.MOVED, "App moved to Games, east.");
        assertEquals(List.of("The town changed: 8 logos built, 1 moved. /apps lists where your apps stand."),
                pass(build, later, false, false, 103));
    }

    @Test
    void anOrdinaryChangeEndsAnIncompleteFirstBuild() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        var change = new TownLines();
        change.add(TownLines.Kind.RENEWED, "The logo of Chrome was renewed.");
        assertEquals(List.of("The town is built: 32 logos. /apps lists them.", "The logo of Chrome was renewed."),
                pass(build, change, false, true, 4));
        assertEquals(List.of("The town changed: 8 logos built. /apps lists where your apps stand."),
                pass(build, built(8), false, false, 103));
    }

    @Test
    void aChangedAppListIsNotPartOfTheOriginalFirstBuild() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        assertEquals(List.of("The town is built: 32 logos. /apps lists them.",
                        "The town changed: 9 logos built. /apps lists where your apps stand."),
                build.said(built(9), false, false, 0, false, 103, Set.of("a-new-list")));
    }

    @Test
    void aMoveOrSwapEndsTheFirstBuildBeforeItsLaterPass() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        assertEquals(List.of("The town is built: 32 logos. /apps lists them."), build.finish());
        assertEquals(List.of(), build.finish());
        assertEquals(List.of("The town changed: 8 logos built. /apps lists where your apps stand."),
                pass(build, built(8), false, false, 103));
    }

    @Test
    void aRebuildKeepsItsOwnSingleLine() {
        var build = new TownLines.FirstBuild();
        pass(build, built(32), true, true, 3);
        var rebuild = new TownLines();
        rebuild.add(TownLines.Kind.RENEWED, "The logo of Chrome was renewed.");
        assertEquals(List.of("The town was rebuilt from the rules: 1 logo built again. 8 more are built again when you come near."),
                build.said(rebuild, false, true, 8, true, 4, APPS));
    }

    @Test
    void anExistingTownKeepsItsOrdinaryLines() {
        assertEquals(List.of("The town changed: 6 logos built. /apps lists where your apps stand."),
                pass(new TownLines.FirstBuild(), built(6), false, true, 3));
    }
}
