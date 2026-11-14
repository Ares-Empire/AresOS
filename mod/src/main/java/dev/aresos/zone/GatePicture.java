package dev.aresos.zone;

import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.TreeMap;

/**
 * HUB.md 3.6: an icon becomes size x size cells, each one kind of block or empty, with the doorway cut out.
 * Pure functions over pixels. Nothing here knows the game, so every rule is tested with drawn icons.
 * Columns count from his left as he looks at the front, rows from the ground.
 */
public final class GatePicture {
    /**
     * The version of these rules. A standing logo records the version that drew it, so a logo drawn by older rules
     * is noticed and drawn again (HUB.md 2.5). Raise it with every change that can draw a different picture.
     * 2: a logo is built from its icon's main colours, one block each, plain blocks first (package 39).
     */
    public static final int CONVERTER = 2;
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

    /** The colours are looked at in samples of an eighth of a cell: 64 to a cell. */
    static final int FINE = 8;
    /**
     * Main colours. A colour within JOIN of a more common one (plain Oklab distance) belongs to it, and two groups
     * of colours whose averages end up within NEARLY of each other are one. A group that covers less than MAIN_SHARE
     * of the picture (about a cell and a half of 144) is no main colour. An icon with more than MAIN_MOST is
     * many-coloured and keeps the rule of version 1: each cell the block nearest to its average colour.
     */
    private static final double JOIN = 0.10, NEARLY = 0.07, MAIN_SHARE = 0.01;
    private static final int MAIN_MOST = 6;
    /**
     * The colour of a smoothed edge is no main colour: one that lies between two others (at most BLEND_OFF beside
     * the straight line from one to the other) and covers at most BLEND_SMALLER of what the smaller of the two covers.
     */
    private static final double BLEND_OFF = 0.06, BLEND_SMALLER = 0.5;
    /** Two main colours farther apart than this never share a block; the smaller one takes its next nearest. */
    private static final double SAME_BLOCK = 0.15;
    /**
     * Thin lines. A part of one colour is thin where it is narrower than a cell and more than LINE_FAR samples away
     * from every part of that colour a cell wide. A cell can show a thin part that covers at least LINE_SHARE of it.
     */
    private static final int LINE_FAR = 3;
    private static final double LINE_SHARE = 0.10;

    /** A plain plate's colour, and the square around its figure in the cut icon's pixels. */
    record Plate(int rgb, double left, double top, double side) { }

    /** One of the icon's main colours and the share of the picture that has it. */
    record Main(int rgb, double share) { }

    /** The part of the icon that becomes the picture, as samples: FINE to a cell's side, rows from the top. */
    private record Samples(int across, int[] rgb, double[] covered) { }

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

    /**
     * A picture of cells that are chosen already (row by row from the ground, null for none), with the doorway.
     * The converter builds no red mushroom block any more; the game tests still build and remove one this way,
     * as a gate drawn by version 1 may hold it.
     */
    public static GatePicture ofBlocks(String[] blocks, int size) {
        GateNumbers.checkSize(size);
        if (blocks.length != size * size) throw new IllegalArgumentException(blocks.length + " cells for a picture of " + size);
        var cells = blocks.clone();
        door(cells, size);
        return new GatePicture(size, cells, false);
    }

    public int size() { return size; }
    /** True when the icon was a small figure on a plain plate and the figure was enlarged. */
    public boolean enlarged() { return enlarged; }
    public boolean isEmpty() { return Arrays.stream(cells).allMatch(java.util.Objects::isNull); }

    /**
     * A fingerprint of the picture as it is built: its size and every cell's block. Two pictures with the same hash
     * build the same blocks, so a standing logo records it and is rebuilt only when the picture really changed.
     */
    public String hash() {
        var text = new StringBuilder().append(size);
        for (String cell : cells) text.append(',').append(cell == null ? "" : cell);
        try {
            var digest = java.security.MessageDigest.getInstance("SHA-256").digest(text.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (java.security.NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("Every Java has SHA-256", impossible);
        }
    }

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
        // Centred on the figure to the half pixel: a figure that is the same left and right stays so in the cells.
        double x = Math.clamp((minX + maxX + 1) / 2.0 - square / 2.0, 0, n - square);
        double y = Math.clamp((minY + maxY + 1) / 2.0 - square / 2.0, 0, n - square);
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
     * the figure's square fills the whole picture, on the plate's colour. A solid cell is painted in one of the
     * icon's main colours, each of which is one block for the whole picture.
     */
    static String[] blocks(BufferedImage cut, Plate plate, int size) {
        double side = plate != null ? plate.side : Math.max(cut.getWidth(), cut.getHeight());
        double left = plate != null ? plate.left : (cut.getWidth() - side) / 2;
        double top = plate != null ? plate.top : cut.getHeight() - side;
        double step = side / size;
        var cells = new String[size * size];
        var means = new double[size * size][];
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) {
            int row = size - 1 - v;
            means[v * size + u] = average(cut, left + u * step, top + row * step, left + (u + 1) * step, top + (row + 1) * step);
        }
        var samples = samples(cut, plate, left, top, side, size * FINE);
        var mains = mainColours(samples);
        if (mains.size() > MAIN_MOST) {
            // Many-coloured, photo-like: no few colours to keep apart. Each cell's own average, as in version 1.
            for (int cell = 0; cell < cells.length; cell++) {
                if (plate != null) cells[cell] = GatePalette.nearest(onPlate(means[cell], plate));
                else if (means[cell][0] >= HALF) cells[cell] = GatePalette.nearest(pack(means[cell][1], means[cell][2], means[cell][3]));
            }
            return cells;
        }

        // One block for each main colour; main colours that got the same block are one from here on.
        String[] blocks = blocksFor(mains);
        var kinds = Arrays.stream(blocks).distinct().toList();
        int across = samples.across;
        int[] kind = new int[across * across];
        for (int i = 0; i < kind.length; i++) kind[i] = samples.covered[i] > 0 ? kinds.indexOf(blocks[nearestMain(mains, samples.rgb[i])]) : -1;
        // Per cell: how much of it each kind covers, and how much of it is a thin part of each kind.
        int count = kinds.size();
        var weight = new double[size * size][count];
        var thinCount = new int[size * size][count];
        for (int k = 0; k < count; k++) {
            var shape = new boolean[kind.length];
            for (int i = 0; i < kind.length; i++) shape[i] = kind[i] == k && samples.covered[i] >= 0.5;
            var thin = thin(shape, across);
            for (int i = 0; i < kind.length; i++) if (thin[i]) thinCount[(size - 1 - i / across / FINE) * size + i % across / FINE][k]++;
        }
        for (int i = 0; i < kind.length; i++) if (kind[i] >= 0) weight[(size - 1 - i / across / FINE) * size + i % across / FINE][kind[i]] += samples.covered[i];
        // The colour that covers most of the cell.
        var most = new int[size * size];
        Arrays.fill(most, -1);
        for (int cell = 0; cell < most.length; cell++) {
            if (plate == null && means[cell][0] < HALF) continue;
            most[cell] = 0;
            for (int k = 1; k < count; k++) if (weight[cell][k] > weight[cell][most[cell]]) most[cell] = k;
        }
        // Unless a thin line of another colour runs through it: of two such lines the one that covers more.
        var pick = most.clone();
        var widest = new int[size * size];
        for (int k = 0; k < count; k++) {
            var line = line(most, thinCount, k, size);
            for (int cell = 0; cell < line.length; cell++) {
                if (!line[cell] || thinCount[cell][k] <= widest[cell]) continue;
                pick[cell] = k;
                widest[cell] = thinCount[cell][k];
            }
        }
        for (int cell = 0; cell < cells.length; cell++) if (pick[cell] >= 0) cells[cell] = kinds.get(pick[cell]);
        return cells;
    }

    /** The icon's main colours, largest first: what {@link #blocks} paints with. For the tests. */
    static List<Main> mainColours(BufferedImage icon, int size) {
        var cut = cut(icon);
        if (cut == null) return List.of();
        var plate = plate(cut);
        double side = plate != null ? plate.side : Math.max(cut.getWidth(), cut.getHeight());
        return mainColours(samples(cut, plate, plate != null ? plate.left : (cut.getWidth() - side) / 2,
                plate != null ? plate.top : cut.getHeight() - side, side, size * FINE));
    }

    /** The square that becomes the picture as across x across samples; on a plate each sample lies on the plate's colour. */
    private static Samples samples(BufferedImage cut, Plate plate, double left, double top, double side, int across) {
        double step = side / across;
        int[] rgb = new int[across * across];
        double[] covered = new double[across * across];
        for (int y = 0; y < across; y++) for (int x = 0; x < across; x++) {
            double[] mean = average(cut, left + x * step, top + y * step, left + (x + 1) * step, top + (y + 1) * step);
            covered[y * across + x] = plate != null ? 1 : Math.min(1, mean[0]);
            rgb[y * across + x] = plate != null ? onPlate(mean, plate) : pack(mean[1], mean[2], mean[3]);
        }
        return new Samples(across, rgb, covered);
    }

    /**
     * The main colours, largest first, found the same way every time. The colours that occur (in steps of 8 a
     * channel) are taken from the most common down: one within JOIN of an earlier one belongs to it, any other
     * starts a new group; three rounds then move each group to the average of its colours and each colour to its
     * nearest group. Small groups and the colours of smoothed edges are dropped.
     */
    private static List<Main> mainColours(Samples samples) {
        // Per colour step: how much it covers, and the sums of its Oklab and sRGB values.
        var steps = new TreeMap<Integer, double[]>();
        double total = 0;
        for (int i = 0; i < samples.rgb.length; i++) {
            double weight = samples.covered[i];
            if (weight <= 0) continue;
            int rgb = samples.rgb[i];
            double[] lab = GatePalette.oklab(rgb);
            double[] sum = steps.computeIfAbsent((rgb >> 19 & 31) << 10 | (rgb >> 11 & 31) << 5 | rgb >> 3 & 31, key -> new double[7]);
            sum[0] += weight;
            for (int c = 0; c < 3; c++) sum[1 + c] += weight * lab[c];
            sum[4] += weight * (rgb >> 16 & 255); sum[5] += weight * (rgb >> 8 & 255); sum[6] += weight * (rgb & 255);
            total += weight;
        }
        if (steps.isEmpty()) return List.of();
        // Most common first; equally common ones in the order of their colour, so the result never depends on chance.
        var colours = new ArrayList<>(steps.values());
        for (double[] colour : colours) for (int c = 1; c < 7; c++) colour[c] /= colour[0];
        colours.sort(Comparator.comparingDouble((double[] colour) -> -colour[0]));
        var groups = new ArrayList<double[]>();
        for (double[] colour : colours) {
            boolean near = false;
            for (double[] group : groups) near |= apart(group, colour) <= JOIN;
            if (!near) groups.add(colour.clone());
        }
        for (int round = 0; round < 3; round++) {
            var sums = new double[groups.size()][7];
            for (double[] colour : colours) {
                int nearest = 0;
                for (int g = 1; g < groups.size(); g++) if (apart(groups.get(g), colour) < apart(groups.get(nearest), colour)) nearest = g;
                sums[nearest][0] += colour[0];
                for (int c = 1; c < 7; c++) sums[nearest][c] += colour[0] * colour[c];
            }
            groups.clear();
            for (double[] sum : sums) {
                if (sum[0] <= 0) continue;
                for (int c = 1; c < 7; c++) sum[c] /= sum[0];
                groups.add(sum);
            }
        }
        // Groups the rounds moved within NEARLY of each other are one colour (two shades of one white): the nearest two first.
        while (groups.size() > 1) {
            int first = 0, second = 1;
            for (int i = 0; i < groups.size(); i++) for (int j = i + 1; j < groups.size(); j++)
                if (apart(groups.get(i), groups.get(j)) < apart(groups.get(first), groups.get(second))) { first = i; second = j; }
            if (apart(groups.get(first), groups.get(second)) >= NEARLY) break;
            double[] into = groups.get(first), from = groups.remove(second);
            for (int c = 1; c < 7; c++) into[c] = (into[0] * into[c] + from[0] * from[c]) / (into[0] + from[0]);
            into[0] += from[0];
        }
        groups.sort(Comparator.comparingDouble((double[] group) -> -group[0]));
        double enough = MAIN_SHARE * total;
        groups.removeIf(group -> group[0] < enough);
        // From the smallest up: a colour between two larger ones is the smoothed edge between them.
        for (int g = groups.size() - 1; g >= 2; g--) if (blend(groups, g)) groups.remove(g);
        var mains = new ArrayList<Main>();
        for (double[] group : groups) mains.add(new Main(pack(group[4], group[5], group[6]), group[0] / total));
        return List.copyOf(mains);
    }

    /** Plain Oklab distance between two colours of {@link #mainColours(Samples)}. */
    private static double apart(double[] first, double[] second) {
        double l = first[1] - second[1], a = first[2] - second[2], b = first[3] - second[3];
        return Math.sqrt(l * l + a * a + b * b);
    }

    private static boolean blend(List<double[]> groups, int index) {
        double[] colour = groups.get(index);
        for (int i = 0; i < groups.size(); i++) for (int j = i + 1; j < groups.size(); j++) {
            double[] from = groups.get(i), to = groups.get(j);
            if (i == index || j == index || colour[0] > BLEND_SMALLER * Math.min(from[0], to[0])) continue;
            double length = apart(from, to), along = 0;
            for (int c = 1; c < 4; c++) along += (colour[c] - from[c]) * (to[c] - from[c]);
            along /= length * length;
            if (along <= 0 || along >= 1) continue;
            double off = 0;
            for (int c = 1; c < 4; c++) off += Math.pow(colour[c] - from[c] - along * (to[c] - from[c]), 2);
            if (Math.sqrt(off) <= BLEND_OFF) return true;
        }
        return false;
    }

    private static int nearestMain(List<Main> mains, int rgb) {
        int nearest = 0;
        for (int m = 1; m < mains.size(); m++)
            if (GatePalette.distance(mains.get(m).rgb, rgb) < GatePalette.distance(mains.get(nearest).rgb, rgb)) nearest = m;
        return nearest;
    }

    /**
     * One block for each main colour, largest first: its nearest block, or the next nearest when a main colour
     * that is not nearly the same already has that block.
     */
    static String[] blocksFor(List<Main> mains) {
        var blocks = new String[mains.size()];
        for (int m = 0; m < blocks.length; m++) {
            int colour = mains.get(m).rgb, index = m;
            blocks[m] = GatePalette.nearestFirst(colour).stream().filter(block -> {
                for (int earlier = 0; earlier < index; earlier++)
                    if (blocks[earlier].equals(block) && GatePalette.distance(colour, mains.get(earlier).rgb) > SAME_BLOCK) return false;
                return true;
            }).findFirst().orElseThrow();
        }
        return blocks;
    }

    /**
     * The thin parts of a shape, as samples: what is narrower than a cell (no FINE x FINE square fits there) and
     * more than LINE_FAR samples from every place where such a square fits. The rim of a wide part is not thin.
     */
    private static boolean[] thin(boolean[] shape, int across) {
        var wide = new boolean[shape.length];
        for (int y = 0; y + FINE <= across; y++) for (int x = 0; x + FINE <= across; x++) {
            boolean fits = true;
            for (int dy = 0; dy < FINE && fits; dy++) for (int dx = 0; dx < FINE && fits; dx++) fits = shape[(y + dy) * across + x + dx];
            if (!fits) continue;
            for (int dy = 0; dy < FINE; dy++) for (int dx = 0; dx < FINE; dx++) wide[(y + dy) * across + x + dx] = true;
        }
        var thin = new boolean[shape.length];
        for (int y = 0; y < across; y++) for (int x = 0; x < across; x++) {
            if (!shape[y * across + x]) continue;
            boolean near = false;
            for (int ny = Math.max(0, y - LINE_FAR); ny <= Math.min(across - 1, y + LINE_FAR) && !near; ny++)
                for (int nx = Math.max(0, x - LINE_FAR); nx <= Math.min(across - 1, x + LINE_FAR) && !near; nx++) near = wide[ny * across + nx];
            thin[y * across + x] = !near;
        }
        return thin;
    }

    /**
     * The cells that show kind k's thin parts: one cell wide and connected where the part is. Every solid cell
     * that is not k's already and has a thin part of k over at least LINE_SHARE of it may show it. From the one
     * with the least of it up, a cell is dropped again while the cells of k around it stay connected without it
     * (a line that lies across two rows of cells is shown in one). At last a single cell goes that neither
     * continues a line nor joins two parts of k: a speck, or the tip of a wide part.
     */
    private static boolean[] line(int[] most, int[][] thinCount, int k, int size) {
        var line = new boolean[most.length];
        var has = new boolean[most.length];
        var order = new ArrayList<Integer>();
        for (int cell = 0; cell < most.length; cell++) {
            line[cell] = most[cell] >= 0 && most[cell] != k && thinCount[cell][k] >= LINE_SHARE * FINE * FINE;
            has[cell] = line[cell] || most[cell] == k;
            if (line[cell]) order.add(cell);
        }
        order.sort(Comparator.comparingInt((Integer cell) -> thinCount[cell][k]));
        boolean dropped = true;
        while (dropped) {
            dropped = false;
            for (int cell : order) {
                if (!line[cell] || !spare(has, size, cell)) continue;
                line[cell] = has[cell] = false;
                dropped = true;
                break;
            }
        }
        var shown = line.clone();
        for (int cell : order) {
            if (!line[cell]) continue;
            var around = around(has, size, cell);
            boolean continues = false;
            for (int[] other : around) continues |= line[other[1] * size + other[0]];
            if (!continues && (around.size() < 2 || connected(around))) shown[cell] = false;
        }
        return shown;
    }

    /** True when a cell has two or more cells of its colour around it and they are connected without it. */
    private static boolean spare(boolean[] has, int size, int cell) {
        var around = around(has, size, cell);
        return around.size() >= 2 && connected(around);
    }

    /** True when the cells of a list, each {column, row}, hang together, touching at sides or corners. */
    private static boolean connected(List<int[]> around) {
        var reached = new boolean[around.size()];
        reached[0] = true;
        for (boolean grew = true; grew; ) {
            grew = false;
            for (int i = 0; i < reached.length; i++) for (int j = 0; j < reached.length && !reached[i]; j++) {
                if (!reached[j] || Math.abs(around.get(i)[0] - around.get(j)[0]) > 1 || Math.abs(around.get(i)[1] - around.get(j)[1]) > 1) continue;
                reached[i] = grew = true;
            }
        }
        for (boolean each : reached) if (!each) return false;
        return true;
    }

    /** The cells of the colour among a cell's eight neighbours, each as {column, row}. */
    private static List<int[]> around(boolean[] has, int size, int cell) {
        var around = new ArrayList<int[]>();
        for (int v = cell / size - 1; v <= cell / size + 1; v++) for (int u = cell % size - 1; u <= cell % size + 1; u++)
            if (u >= 0 && v >= 0 && u < size && v < size && v * size + u != cell && has[v * size + u]) around.add(new int[]{u, v});
        return around;
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

    /** A mean of {@link #average} laid on the plate's colour. */
    private static int onPlate(double[] mean, Plate plate) {
        double covered = Math.min(1, mean[0]);
        return pack(over(mean[1], plate.rgb >> 16 & 255, covered), over(mean[2], plate.rgb >> 8 & 255, covered),
                over(mean[3], plate.rgb & 255, covered));
    }

    private static double over(double figure, int plate, double covered) { return figure * covered + plate * (1 - covered); }

    private static int pack(double r, double g, double b) {
        return (int)Math.round(r) << 16 | (int)Math.round(g) << 8 | (int)Math.round(b);
    }
}
