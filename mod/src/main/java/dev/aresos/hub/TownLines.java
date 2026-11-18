package dev.aresos.hub;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * What a pass of the town says in the chat (HUB.md 3.4, point 6). One line a change while there are few. When one
 * pass has more than {@link #FEW} lines of the ordinary kind (a logo built, moved, renewed or taken down), it says one
 * line for all of them instead, so forty new apps do not fill the chat. A first build (no logo stood, and the pass
 * only built) is always one line, whatever the count ("The town is built: 5 logos. /apps lists them.", the
 * orchestrator's decision in review fixes 1). Lines about something of his in the way (a blocked place, a removal that
 * was refused) are always said one by one, after that line. {@code /aresos hub rebuild} always says one line.
 */
public final class TownLines {
    /** At most this many ordinary lines are said one by one. */
    public static final int FEW = 5;

    /** What a line is about. {@link #WAY}: something of his is in the way, or something went wrong. */
    public enum Kind { BUILT, MOVED, RENEWED, DOWN, WAY }

    public record Line(Kind kind, String text) { }

    private final List<Line> lines = new ArrayList<>();
    private boolean changeStarted;

    public void add(Kind kind, String text) { lines.add(new Line(kind, text)); }

    /** A standing logo needs moving or renewing, even if its replacement cannot be built this pass. */
    public void changeStarted() { changeStarted = true; }

    public boolean isEmpty() { return lines.isEmpty(); }

    /**
     * The lines as he reads them.
     *
     * @param first   no logo stood before this pass: a pass of only builds is "the town is built"
     * @param rebuilt this pass is {@code /aresos hub rebuild}'s: one line however few changed
     * @param waiting logos of a rebuild that still stand as they were, because their place is not loaded
     */
    public List<String> said(boolean first, boolean rebuilt, int waiting) {
        var ordinary = lines.stream().filter(line -> line.kind() != Kind.WAY).toList();
        boolean firstBuild = first && !ordinary.isEmpty() && ordinary.stream().allMatch(line -> line.kind() == Kind.BUILT);
        if (!rebuilt && !firstBuild && ordinary.size() <= FEW) return lines.stream().map(Line::text).toList();
        var counts = new EnumMap<Kind, Integer>(Kind.class);
        for (var line : ordinary) counts.merge(line.kind(), 1, Integer::sum);
        var said = new ArrayList<String>();
        said.add(rebuilt ? rebuilt(counts, waiting) : firstBuild
                ? "The town is built: " + logos(ordinary.size()) + ". /apps lists " + (ordinary.size() == 1 ? "it." : "them.")
                : "The town changed: " + parts(counts, List.of(Kind.BUILT, Kind.MOVED, Kind.RENEWED, Kind.DOWN)) + ". /apps lists where your apps stand.");
        lines.stream().filter(line -> line.kind() == Kind.WAY).map(Line::text).forEach(said::add);
        return said;
    }

    /**
     * The first build belongs to the home, rather than to one pass. Keep its ordinary lines until its places and
     * pictures are ready, for at most 200 ticks (about 10 seconds) after the first actual build.
     * A complete first pass still speaks at once.
     * WAY lines never wait. A rebuild, a changed app list or an ordinary change ends this first build.
     */
    public static final class FirstBuild {
        public static final int WAIT_TICKS = 200;
        private final TownLines built = new TownLines();
        private Set<String> apps;
        private long until = Long.MAX_VALUE;
        private boolean finished;

        /** The server tick also checks the bound while a picture is still being read. */
        public List<String> expire(long tick) {
            if (finished || apps == null || tick < until) return List.of();
            return finish();
        }

        /** A move or swap ends this build too; its command speaks for the changed logos. */
        public List<String> finish() {
            if (finished) return List.of();
            finished = true;
            return built.said(true, false, 0);
        }

        public List<String> said(TownLines pass, boolean first, boolean rebuilt, int waiting,
                                 boolean pending, long tick, Set<String> wanted) {
            if (finished) return pass.said(first, rebuilt, waiting);
            // A rebuild has its own single line, including the logos built in earlier passes.
            if (rebuilt) {
                finished = true;
                return pass.said(first, true, waiting);
            }
            if (apps == null) {
                if (!first) {
                    finished = true;
                    return pass.said(false, false, waiting);
                }
                apps = Set.copyOf(wanted);
            }
            if (pass.changeStarted || !apps.equals(wanted) || pass.lines.stream().anyMatch(line -> line.kind() != Kind.BUILT && line.kind() != Kind.WAY)) {
                finished = true;
                var said = new ArrayList<>(built.said(true, false, 0));
                said.addAll(pass.said(false, false, waiting));
                return said;
            }
            if (until == Long.MAX_VALUE && pass.lines.stream().anyMatch(line -> line.kind() == Kind.BUILT)) until = tick + WAIT_TICKS;
            pass.lines.stream().filter(line -> line.kind() == Kind.BUILT).forEach(built.lines::add);
            var said = new ArrayList<String>();
            if (!pending || tick >= until) {
                finished = true;
                said.addAll(built.said(true, false, 0));
            }
            pass.lines.stream().filter(line -> line.kind() == Kind.WAY).map(Line::text).forEach(said::add);
            return said;
        }
    }

    private static String rebuilt(Map<Kind, Integer> counts, int waiting) {
        String done = counts.isEmpty() ? "no logo stood to build again" : parts(counts, List.of(Kind.RENEWED, Kind.BUILT, Kind.MOVED, Kind.DOWN));
        return "The town was rebuilt from the rules: " + done + "."
                + (waiting == 0 ? "" : " " + waiting + (waiting == 1 ? " more is" : " more are") + " built again when you come near.");
    }

    /** "7 logos built, 2 moved, 1 taken down": the noun on the first count only. */
    private static String parts(Map<Kind, Integer> counts, List<Kind> order) {
        var parts = new ArrayList<String>();
        for (var kind : order) {
            int count = counts.getOrDefault(kind, 0);
            if (count == 0) continue;
            String verb = switch (kind) {
                case BUILT -> "built";
                case MOVED -> "moved";
                case RENEWED -> order.getFirst() == Kind.RENEWED ? "built again" : "renewed";
                case DOWN -> "taken down";
                case WAY -> throw new IllegalArgumentException("Not an ordinary line");
            };
            parts.add((parts.isEmpty() ? logos(count) : String.valueOf(count)) + " " + verb);
        }
        return String.join(", ", parts);
    }

    private static String logos(int count) { return count + (count == 1 ? " logo" : " logos"); }
}
