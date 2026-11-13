package dev.aresos.zone;

import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.Arrays;

/**
 * HUB.md 3.6: an icon becomes size x size cells, each one kind of block or empty, with the doorway cut out.
 * Pure functions over pixels. Nothing here knows the game, so every rule is tested with drawn icons.
 * Columns count from his left as he looks at the front, rows from the ground.
 */
public final class GatePicture {
    /** A pixel counts as visible from 12% opacity. */
    private static final double VISIBLE = 0.12;
    /**
     * The plate test looks at a copy of this many pixels and at a rim this many pixels deep. In the copy a pixel
     * counts from half opacity, as a cell does: a faint glow around a figure is not part of the figure.
     */
    private static final int PLATE_COPY = 96, RIM = 9;
    private static final double PLATE_OPAQUE = 0.5;
    private static final double PLATE_SAME = 0.05, PLATE_SHARE = 0.80, FIGURE_DIFFERS = 0.10, FIGURE_SHARE = 0.02,
            FIGURE_FILLS = 0.80, FIGURE_MARGIN = 0.10;
    // A centred picture of odd width half-covers a cell on each side. Rounding must not make one side solid
    // and the other empty.
    private static final double HALF = 0.5 - 1e-9;

    /** A plain plate's colour, and the square around its figure in the cut icon's pixels. */
    record Plate(int rgb, double left, double top, double side) { }

    private final int size;
    private final String[] cells;
    private final boolean enlarged;

    private GatePicture(int size, String[] cells, boolean enlarged) {
        this.size = size;
        this.cells = cells;
        this.enlarged = enlarged;
    }

    /**
     * The whole of HUB.md 3.6 up to the door. An icon with nothing visible, or too thin to cover half a cell,
     * gives an empty picture without a door; the caller then builds a plain front.
     */
    public static GatePicture of(BufferedImage icon, int size) {
        GateNumbers.checkSize(size);
        var cut = cut(icon);
        if (cut == null) return new GatePicture(size, new String[size * size], false);
        var plate = plate(cut);
        var cells = blocks(cut, plate, size);
        tidy(cells, size);
        if (Arrays.stream(cells).allMatch(java.util.Objects::isNull)) return new GatePicture(size, cells, false);
        door(cells, size);
        return new GatePicture(size, cells, plate != null);
    }

    /** A front of one block with the doorway: the gate of an app without a readable icon. */
    public static GatePicture plain(String block, int size) {
        GateNumbers.checkSize(size);
        var cells = new String[size * size];
        Arrays.fill(cells, block);
        door(cells, size);
        return new GatePicture(size, cells, false);
    }

    public int size() { return size; }
    /** True when the icon was a small figure on a plain plate and the figure was enlarged. */
    public boolean enlarged() { return enlarged; }
    public boolean isEmpty() { return Arrays.stream(cells).allMatch(java.util.Objects::isNull); }

    /** The block of column u, row v, without its namespace; null where the picture has none. */
    public String at(int u, int v) {
        return u < 0 || v < 0 || u >= size || v >= size ? null : cells[v * size + u];
    }

    /** Step 1: the icon cut to the box of its visible pixels, or null when nothing is visible. */
    static BufferedImage cut(BufferedImage icon) {
        int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, maxX = -1, maxY = -1;
        for (int y = 0; y < icon.getHeight(); y++) for (int x = 0; x < icon.getWidth(); x++) {
            if ((icon.getRGB(x, y) >>> 24) < VISIBLE * 255) continue;
            minX = Math.min(minX, x); maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        }
        return maxX < 0 ? null : icon.getSubimage(minX, minY, maxX - minX + 1, maxY - minY + 1);
    }

    /**
     * Step 2, the plate test: when the icon's rim is one colour and a small figure sits on it, the plate's colour
     * and the square to enlarge. Null for every other icon.
     */
    static Plate plate(BufferedImage cut) {
        int n = PLATE_COPY;
        // The copy: the cut icon centred on a see-through square, as n x n pixels.
        double side = Math.max(cut.getWidth(), cut.getHeight()), step = side / n;
        double left = (cut.getWidth() - side) / 2, top = (cut.getHeight() - side) / 2;
        int[] rgb = new int[n * n];
        boolean[] visible = new boolean[n * n];
        for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) {
            double[] mean = average(cut, left + x * step, top + y * step, left + (x + 1) * step, top + (y + 1) * step);
            visible[y * n + x] = mean[0] >= PLATE_OPAQUE;
            rgb[y * n + x] = pack(mean[1], mean[2], mean[3]);
        }
        var rim = new ArrayList<Integer>();
        for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            if (visible[y * n + x] && nearSeeThrough(visible, n, x, y)) rim.add(rgb[y * n + x]);
        if (rim.isEmpty()) return null;
        int colour = pack(median(rim, 16), median(rim, 8), median(rim, 0));
        long same = rim.stream().filter(pixel -> GatePalette.distance(pixel, colour) <= PLATE_SAME).count();
        if (same < PLATE_SHARE * rim.size()) return null;
        int count = 0, minX = n, minY = n, maxX = -1, maxY = -1;
        for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) {
            if (!visible[y * n + x] || GatePalette.distance(rgb[y * n + x], colour) <= FIGURE_DIFFERS) continue;
            count++;
            minX = Math.min(minX, x); maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        }
        int width = maxX - minX + 1, height = maxY - minY + 1;
        if (count < FIGURE_SHARE * n * n || width > FIGURE_FILLS * n || height > FIGURE_FILLS * n) return null;
        int square = (int)Math.min(n, Math.round(Math.max(width, height) * (1 + 2 * FIGURE_MARGIN)));
        long x = Math.clamp(Math.round((minX + maxX + 1) / 2.0 - square / 2.0), 0, n - square);
        long y = Math.clamp(Math.round((minY + maxY + 1) / 2.0 - square / 2.0), 0, n - square);
        return new Plate(colour, left + x * step, top + y * step, square * step);
    }

    /** A see-through pixel or the picture's edge within RIM pixels, sideways or up and down. */
    private static boolean nearSeeThrough(boolean[] visible, int n, int x, int y) {
        for (int d = 1; d <= RIM; d++) {
            if (x - d < 0 || x + d >= n || y - d < 0 || y + d >= n) return true;
            if (!visible[y * n + x - d] || !visible[y * n + x + d] || !visible[(y - d) * n + x] || !visible[(y + d) * n + x])
                return true;
        }
        return false;
    }

    private static int median(ArrayList<Integer> pixels, int shift) {
        return pixels.stream().mapToInt(pixel -> pixel >> shift & 255).sorted().skip(pixels.size() / 2).findFirst().orElseThrow();
    }

    /**
     * Steps 3 and 4: each cell's block, or null. Without a plate the icon keeps its proportions, is centred
     * sideways and stands on the ground, and a cell is solid when at least half of it is covered. With a plate
     * the figure's square fills the whole picture, on the plate's colour.
     */
    static String[] blocks(BufferedImage cut, Plate plate, int size) {
        double side = plate != null ? plate.side : Math.max(cut.getWidth(), cut.getHeight());
        double left = plate != null ? plate.left : (cut.getWidth() - side) / 2;
        double top = plate != null ? plate.top : cut.getHeight() - side;
        double step = side / size;
        var cells = new String[size * size];
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) {
            int row = size - 1 - v;
            double[] mean = average(cut, left + u * step, top + row * step, left + (u + 1) * step, top + (row + 1) * step);
            if (plate != null) {
                double covered = Math.min(1, mean[0]);
                cells[v * size + u] = GatePalette.nearest(pack(over(mean[1], plate.rgb >> 16 & 255, covered),
                        over(mean[2], plate.rgb >> 8 & 255, covered), over(mean[3], plate.rgb & 255, covered)));
            } else if (mean[0] >= HALF) cells[v * size + u] = GatePalette.nearest(pack(mean[1], mean[2], mean[3]));
        }
        return cells;
    }

    /** Step 5: a solid cell that touches no other solid cell, not even at a corner, is dropped. */
    static void tidy(String[] cells, int size) {
        var loose = new ArrayList<Integer>();
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) {
            if (cells[v * size + u] == null) continue;
            boolean touches = false;
            for (int dv = -1; dv <= 1; dv++) for (int du = -1; du <= 1; du++) {
                int nu = u + du, nv = v + dv;
                if ((du != 0 || dv != 0) && nu >= 0 && nv >= 0 && nu < size && nv < size && cells[nv * size + nu] != null)
                    touches = true;
            }
            if (!touches) loose.add(v * size + u);
        }
        for (int index : loose) cells[index] = null;
    }

    /** Step 6: the doorway is cleared; a missing post beside it or bar above it becomes black concrete. */
    static void door(String[] cells, int size) {
        int left = GateNumbers.doorLeft(size);
        for (int v = 0; v <= GateNumbers.DOOR_HEIGHT; v++) for (int u = left - 1; u <= left + GateNumbers.DOOR_WIDTH; u++) {
            boolean opening = v < GateNumbers.DOOR_HEIGHT && u >= left && u < left + GateNumbers.DOOR_WIDTH;
            if (opening) cells[v * size + u] = null;
            else if (cells[v * size + u] == null) cells[v * size + u] = GatePalette.BLACK;
        }
    }

    /**
     * The share of a rectangle that is covered, and the mean colour of what covers it: {coverage, red, green,
     * blue}. The rectangle is in the image's pixels; outside the image is see-through.
     */
    private static double[] average(BufferedImage image, double x0, double y0, double x1, double y1) {
        double alpha = 0, r = 0, g = 0, b = 0;
        int right = Math.min(image.getWidth(), (int)Math.ceil(x1)), bottom = Math.min(image.getHeight(), (int)Math.ceil(y1));
        for (int y = Math.max(0, (int)Math.floor(y0)); y < bottom; y++) for (int x = Math.max(0, (int)Math.floor(x0)); x < right; x++) {
            double weight = (Math.min(x + 1, x1) - Math.max(x, x0)) * (Math.min(y + 1, y1) - Math.max(y, y0));
            if (weight <= 0) continue;
            int argb = image.getRGB(x, y);
            double a = (argb >>> 24) / 255.0 * weight;
            alpha += a;
            r += (argb >> 16 & 255) * a; g += (argb >> 8 & 255) * a; b += (argb & 255) * a;
        }
        if (alpha == 0) return new double[4];
        return new double[]{alpha / ((x1 - x0) * (y1 - y0)), r / alpha, g / alpha, b / alpha};
    }

    private static double over(double figure, int plate, double covered) { return figure * covered + plate * (1 - covered); }

    private static int pack(double r, double g, double b) {
        return (int)Math.round(r) << 16 | (int)Math.round(g) << 8 | (int)Math.round(b);
    }
}
