package dev.aresos.focus;

import java.util.ArrayList;
import java.util.List;

/**
 * Package 328c, prototype B ("edge turning"), the part that needs no game. With {@code look = edge} the cursor is always
 * free in a session's connected desktop world. The view turns while the cursor rests near the left, right or top edge of
 * the world's window (labwc keeps it maximized on its output), faster the nearer it is, and the left and right arrow
 * keys turn too. Where another output touches an edge, that part of the edge does not turn: the cursor passes through
 * to the other screen. The client ({@code EdgeLook}) feeds it the window, the outputs and the cursor once a frame.
 */
public final class EdgeTurn {
    /** The band along an edge in which the view turns, in the window's pixels (brief 328c: start at 48). */
    public static final int EDGE_PX = 48;
    /** The top turning speed: at the edge itself, and for an arrow key (brief 328c: start at 120). */
    public static final double EDGE_TURN_DEG_PER_S = 120;
    /** A frame longer than this turns as if it took this long, so a hitch or a save never swings the view round. */
    public static final double LONGEST_FRAME_S = 0.1;
    /** The arrow keys' codes (GLFW's, which Minecraft uses). Q (drop) and E (inventory) stay vanilla's. */
    public static final int LEFT_ARROW = 263, RIGHT_ARROW = 262;

    private EdgeTurn() { }

    /** A rectangle in the compositor's layout: the world's window or an output. */
    public record Box(int x, int y, int width, int height) {
        int right() { return x + width; }
        int bottom() { return y + height; }
    }

    /** A stretch along an edge, from {@code from} up to (not including) {@code to}, in the window's pixels. */
    public record Range(int from, int to) {
        boolean contains(double at) { return at >= from && at < to; }
    }

    /**
     * Where other outputs touch the window's left, right and top edges. There the cursor passes through and the view
     * does not turn; everywhere else along those edges it turns.
     */
    public record Shared(List<Range> left, List<Range> right, List<Range> top) {
        public static final Shared NONE = new Shared(List.of(), List.of(), List.of());

        /** From the real layout: each output whose far side lies on one of the window's edges shares where they overlap. */
        public static Shared of(Box window, List<Box> outputs) {
            var left = new ArrayList<Range>();
            var right = new ArrayList<Range>();
            var top = new ArrayList<Range>();
            for (var output : outputs) {
                if (output.width() <= 0 || output.height() <= 0) continue;
                if (output.right() == window.x()) add(left, output.y(), output.bottom(), window.y(), window.bottom());
                if (output.x() == window.right()) add(right, output.y(), output.bottom(), window.y(), window.bottom());
                if (output.bottom() == window.y()) add(top, output.x(), output.right(), window.x(), window.right());
            }
            return new Shared(List.copyOf(left), List.copyOf(right), List.copyOf(top));
        }

        private static void add(List<Range> ranges, int from, int to, int edgeFrom, int edgeTo) {
            int start = Math.max(from, edgeFrom), end = Math.min(to, edgeTo);
            if (start < end) ranges.add(new Range(start - edgeFrom, end - edgeFrom));
        }

        private static boolean any(List<Range> ranges, double at) {
            for (var range : ranges) if (range.contains(at)) return true;
            return false;
        }
    }

    /** Degrees per second: yaw (negative turns left) and pitch (negative looks up), as Minecraft's rotations count. */
    public record Rate(double yaw, double pitch) {
        public static final Rate STILL = new Rate(0, 0);

        public boolean still() { return yaw == 0 && pitch == 0; }

        /** Degrees for a frame that took {@code seconds}, at most {@link #LONGEST_FRAME_S}. */
        public Rate over(double seconds) {
            double time = Math.clamp(seconds, 0, LONGEST_FRAME_S);
            return new Rate(yaw * time, pitch * time);
        }
    }

    /**
     * The turn for a cursor at {@code x, y} in a window of {@code width} by {@code height} (its own pixels, 0,0 at its
     * top left). Inside the band of an edge that is not shared there, it turns towards that edge: at full speed on the
     * edge's last pixel, falling to nothing {@link #EDGE_PX} pixels in. A corner turns both ways. Outside the window,
     * nothing.
     */
    public static Rate edges(double x, double y, int width, int height, Shared shared) {
        if (!(x >= 0 && y >= 0 && x < width && y < height)) return Rate.STILL;
        double yaw = 0, pitch = 0;
        if (!Shared.any(shared.left(), y)) yaw -= speed(x);
        if (!Shared.any(shared.right(), y)) yaw += speed(width - 1 - x);
        if (!Shared.any(shared.top(), x)) pitch -= speed(y);
        return new Rate(yaw, pitch);
    }

    /** Whether the cursor is in a band that turns, so whether it is worth asking if the pointer is still on the world. */
    public static boolean turns(double x, double y, int width, int height, Shared shared) {
        return !edges(x, y, width, height, shared).still();
    }

    /** The arrow keys turn at the top speed as well; together with an edge, never faster than the top speed. */
    public static Rate keys(Rate edges, boolean leftArrow, boolean rightArrow) {
        double yaw = edges.yaw() + ((rightArrow ? 1 : 0) - (leftArrow ? 1 : 0)) * EDGE_TURN_DEG_PER_S;
        return new Rate(Math.clamp(yaw, -EDGE_TURN_DEG_PER_S, EDGE_TURN_DEG_PER_S), edges.pitch());
    }

    /** Which way a key turns: -1 left, 1 right, 0 not at all (every key but the two arrows, Q and E among them). */
    public static int direction(int key) {
        return key == LEFT_ARROW ? -1 : key == RIGHT_ARROW ? 1 : 0;
    }

    /**
     * Degrees per second at {@code distance} pixels from an edge's last pixel: the top speed there, nothing from the
     * band's end. Inside that last pixel (a fractional position) it is the top speed too.
     */
    static double speed(double distance) {
        if (distance >= EDGE_PX) return 0;
        return EDGE_TURN_DEG_PER_S * (1 - Math.max(0, distance) / EDGE_PX);
    }
}
