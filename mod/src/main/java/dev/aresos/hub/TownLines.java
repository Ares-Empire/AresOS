package dev.aresos.hub;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * What a pass of the town says in the chat (HUB.md 3.4, point 6). One line a change while there are few. When one
 * pass has more than {@link #FEW} lines of the ordinary kind (a logo built, moved, renewed or taken down), it says one
 * line for all of them instead, so a first build of forty apps does not fill the chat. Lines about something of his
 * in the way (a blocked place, a removal that was refused) are always said one by one, after that line.
 * {@code /aresos hub rebuild} always says one line.
 */
public final class TownLines {
    /** At most this many ordinary lines are said one by one. */
    public static final int FEW = 5;

    /** What a line is about. {@link #WAY}: something of his is in the way, or something went wrong. */
    public enum Kind { BUILT, MOVED, RENEWED, DOWN, WAY }

    public record Line(Kind kind, String text) { }

    private final List<Line> lines = new ArrayList<>();

    public void add(Kind kind, String text) { lines.add(new Line(kind, text)); }

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
        if (!rebuilt && ordinary.size() <= FEW) return lines.stream().map(Line::text).toList();
        var counts = new EnumMap<Kind, Integer>(Kind.class);
        for (var line : ordinary) counts.merge(line.kind(), 1, Integer::sum);
        var said = new ArrayList<String>();
        said.add(rebuilt ? rebuilt(counts, waiting) : first && counts.keySet().equals(java.util.Set.of(Kind.BUILT))
                ? "The town is built: " + logos(ordinary.size()) + ". /apps lists them."
                : "The town changed: " + parts(counts, List.of(Kind.BUILT, Kind.MOVED, Kind.RENEWED, Kind.DOWN)) + ". /apps lists where your apps stand.");
        lines.stream().filter(line -> line.kind() == Kind.WAY).map(Line::text).forEach(said::add);
        return said;
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
