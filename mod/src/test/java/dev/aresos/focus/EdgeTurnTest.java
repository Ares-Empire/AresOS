package dev.aresos.focus;

import dev.aresos.focus.EdgeTurn.Box;
import dev.aresos.focus.EdgeTurn.Range;
import dev.aresos.focus.EdgeTurn.Rate;
import dev.aresos.focus.EdgeTurn.Shared;
import org.junit.jupiter.api.Test;

import java.util.List;

import static dev.aresos.focus.EdgeTurn.EDGE_PX;
import static dev.aresos.focus.EdgeTurn.EDGE_TURN_DEG_PER_S;
import static org.junit.jupiter.api.Assertions.*;

class EdgeTurnTest {
    private static final int W = 1280, H = 720;
    private static final Box WORLD = new Box(0, 0, W, H);
    private static final double MAX = EDGE_TURN_DEG_PER_S;

    @Test void theTunablesAreTheBriefsStartingValues() {
        assertEquals(48, EDGE_PX);
        assertEquals(120, EDGE_TURN_DEG_PER_S);
    }

    @Test void eachEdgeTurnsTowardsItselfFasterNearer() {
        // Left: at the last pixel the top speed, halfway in half of it, from the band's end nothing.
        assertEquals(new Rate(-MAX, 0), EdgeTurn.edges(0, 360, W, H, Shared.NONE));
        assertEquals(-MAX / 2, EdgeTurn.edges(EDGE_PX / 2.0, 360, W, H, Shared.NONE).yaw(), 1e-9);
        assertEquals(Rate.STILL, EdgeTurn.edges(EDGE_PX, 360, W, H, Shared.NONE));
        double near = EdgeTurn.edges(5, 360, W, H, Shared.NONE).yaw(), far = EdgeTurn.edges(40, 360, W, H, Shared.NONE).yaw();
        assertTrue(near < far && far < 0, near + " " + far);
        // Right turns right; top looks up (Minecraft's pitch goes negative upwards).
        assertEquals(new Rate(MAX, 0), EdgeTurn.edges(W - 1, 360, W, H, Shared.NONE));
        assertEquals(new Rate(0, -MAX), EdgeTurn.edges(640, 0, W, H, Shared.NONE));
        // The bottom edge (the hotbar) and the middle never turn.
        assertEquals(Rate.STILL, EdgeTurn.edges(640, H - 1, W, H, Shared.NONE));
        assertEquals(Rate.STILL, EdgeTurn.edges(640, 360, W, H, Shared.NONE));
        // A corner turns both ways.
        assertEquals(new Rate(-MAX, -MAX), EdgeTurn.edges(0, 0, W, H, Shared.NONE));
        // Outside the window (a stale or foreign position): nothing.
        assertEquals(Rate.STILL, EdgeTurn.edges(-1, 360, W, H, Shared.NONE));
        assertEquals(Rate.STILL, EdgeTurn.edges(W, 360, W, H, Shared.NONE));
        assertEquals(Rate.STILL, EdgeTurn.edges(Double.NaN, 360, W, H, Shared.NONE));
        assertTrue(EdgeTurn.turns(3, 360, W, H, Shared.NONE));
        assertFalse(EdgeTurn.turns(640, 360, W, H, Shared.NONE));
    }

    @Test void anEdgeBesideAnotherOutputLetsTheCursorThrough() {
        // The session's test layout: the world's output at 0,0 and the second output right of it.
        var shared = Shared.of(WORLD, List.of(WORLD, new Box(W, 0, W, H)));
        assertEquals(new Shared(List.of(), List.of(new Range(0, H)), List.of()), shared);
        assertEquals(Rate.STILL, EdgeTurn.edges(W - 1, 360, W, H, shared));
        assertFalse(EdgeTurn.turns(W - 2, 0 + 100, W, H, shared));
        // The other edges still turn.
        assertEquals(new Rate(-MAX, 0), EdgeTurn.edges(0, 360, W, H, shared));
        // The top right corner looks up but does not turn right.
        assertEquals(new Rate(0, -MAX), EdgeTurn.edges(W - 1, 0, W, H, shared));
        // A monitor on the left, at negative coordinates, shares the left edge instead.
        var left = Shared.of(WORLD, List.of(new Box(-1920, -200, 1920, 1080), WORLD));
        assertEquals(List.of(new Range(0, H)), left.left());
        assertEquals(Rate.STILL, EdgeTurn.edges(0, 360, W, H, left));
        assertEquals(new Rate(MAX, 0), EdgeTurn.edges(W - 1, 360, W, H, left));
    }

    @Test void aPartlySharedEdgeLetsThroughOnlyWhereItTouches() {
        // A taller monitor beside the lower half of the world's right edge.
        var shared = Shared.of(WORLD, List.of(WORLD, new Box(W, 360, 1920, 1080)));
        assertEquals(List.of(new Range(360, H)), shared.right());
        assertEquals(Rate.STILL, EdgeTurn.edges(W - 1, 500, W, H, shared));
        assertEquals(new Rate(MAX, 0), EdgeTurn.edges(W - 1, 100, W, H, shared));
        assertEquals(new Rate(MAX, 0), EdgeTurn.edges(W - 1, 359, W, H, shared));
        // A monitor above part of the top edge.
        var above = Shared.of(WORLD, List.of(WORLD, new Box(800, -1080, 1920, 1080)));
        assertEquals(List.of(new Range(800, W)), above.top());
        assertEquals(Rate.STILL, EdgeTurn.edges(900, 0, W, H, above));
        assertEquals(new Rate(0, -MAX), EdgeTurn.edges(300, 0, W, H, above));
        // A window away from the layout's origin counts along its own edge.
        var moved = new Box(1920, 100, W, H);
        assertEquals(List.of(new Range(0, 200)), Shared.of(moved, List.of(new Box(0, 0, 1920, 300))).left());
        // Outputs that do not touch, overlap the world or are empty share nothing.
        assertEquals(Shared.NONE, Shared.of(WORLD, List.of(WORLD, new Box(W + 1, 0, W, H), new Box(W, H, W, H),
                new Box(0, -H, 0, H), new Box(200, 200, 400, 300))));
    }

    @Test void theArrowsTurnAtTheTopSpeedAndQAndEDoNot() {
        assertEquals(new Rate(-MAX, 0), EdgeTurn.keys(Rate.STILL, true, false));
        assertEquals(new Rate(MAX, 0), EdgeTurn.keys(Rate.STILL, false, true));
        assertEquals(Rate.STILL, EdgeTurn.keys(Rate.STILL, true, true));
        assertEquals(Rate.STILL, EdgeTurn.keys(Rate.STILL, false, false));
        // With an edge: never faster than the top speed, and an opposite key cancels it.
        assertEquals(new Rate(-MAX, -MAX), EdgeTurn.keys(new Rate(-MAX, -MAX), true, false));
        assertEquals(new Rate(0, 0), EdgeTurn.keys(new Rate(MAX, 0), true, false));
        assertEquals(-MAX, EdgeTurn.keys(new Rate(-MAX / 2, 0), true, false).yaw(), 1e-9);
        // The arrows are GLFW's codes; Q (drop) and E (inventory) keep their vanilla meaning.
        assertEquals(-1, EdgeTurn.direction(263));
        assertEquals(1, EdgeTurn.direction(262));
        assertEquals(0, EdgeTurn.direction('Q'));
        assertEquals(0, EdgeTurn.direction('E'));
        assertEquals(0, EdgeTurn.direction('A'));
    }

    @Test void aFrameTurnsByItsTimeAndAHitchNeverSwingsTheView() {
        assertEquals(-6, new Rate(-MAX, 0).over(0.05).yaw(), 1e-9);
        assertEquals(-3, new Rate(0, -MAX / 2).over(0.05).pitch(), 1e-9);
        assertEquals(-MAX * EdgeTurn.LONGEST_FRAME_S, new Rate(-MAX, 0).over(3).yaw(), 1e-9);
        assertTrue(new Rate(-MAX, 0).over(-1).still());
        assertTrue(Rate.STILL.still());
        assertFalse(new Rate(0, -1).still());
    }
}
