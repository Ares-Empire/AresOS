package dev.aresos.zone;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.IntStream;

/**
 * The 60 blocks a gate is built from (HUB.md 2.3): the wall's 48 and twelve more, each with the average colour
 * of its side texture. The numbers were measured from the game's own files with the development task
 * `measureBlockColours` (plain mean of each sRGB channel, rounded); no texture is in this repo. The wall keeps its
 * own, slightly different numbers in {@link LogoPixels#PALETTE}, so walls and floors come out as before.
 */
public final class GatePalette {
    /** The niche's back, the door posts and the bar over the door. */
    public static final String BLACK = "black_concrete";
    public static final List<LogoPixels.Color> BLOCKS;
    /**
     * Plain blocks first (HUB.md 3.6): a block with spots, bricks, a frame or a pattern shows its texture from the
     * pad (the red mushroom block's white spots did). Where it would be chosen, the plain block nearest to its own
     * colour is built in its place, when that one is within this distance of it; the patterned block stays in the
     * table as the colour to aim at (no plain block is as red as the mushroom block, and red wool stands in for it).
     */
    static final double PATTERN = 0.06;
    /** The plain blocks: the dyed 48 (concrete, wool, terracotta) and three of the twelve that have one flat colour. */
    private static final int PLAIN_DYED = 48;
    private static final java.util.Set<String> PLAIN_MORE = java.util.Set.of("snow_block", "blue_ice", "smooth_sandstone");
    private static final double[][] OKLAB;
    private static final boolean[] PLAIN;
    /** For each block the block that is built: itself, or the plain block that stands in for it. */
    private static final int[] BUILT;
    static {
        String[] dyes = {"white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
                "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"};
        String[] materials = {"concrete", "wool", "terracotta"};
        int[][] dyed = {
                {0xcfd5d6, 0xe06101, 0xa9309f, 0x2489c7, 0xf1af15, 0x5ea919, 0xd6658f, 0x373a3e,
                 0x7d7d73, 0x157788, 0x64209c, 0x2d2f8f, 0x603c20, 0x495b24, 0x8e2121, 0x080a0f},
                {0xeaeced, 0xf17614, 0xbe45b4, 0x3aafd9, 0xf9c628, 0x70b91a, 0xee8dac, 0x3f4448,
                 0x8e8e87, 0x158a91, 0x7a2aad, 0x35399d, 0x724829, 0x556e1c, 0xa12723, 0x15151a},
                {0xd2b2a1, 0xa25426, 0x96586d, 0x716d8a, 0xba8523, 0x687635, 0xa24e4f, 0x3a2a24,
                 0x876b62, 0x575b5b, 0x764656, 0x4a3c5b, 0x4d3324, 0x4c532a, 0x8f3d2f, 0x251710}};
        var blocks = new ArrayList<LogoPixels.Color>();
        for (int material = 0; material < materials.length; material++) for (int dye = 0; dye < dyes.length; dye++)
            blocks.add(new LogoPixels.Color(dyes[dye] + "_" + materials[material], dyed[material][dye]));
        // The twelve of HUB.md 2.3. All are full blocks that do not fall, burn, tick or change by themselves.
        blocks.add(new LogoPixels.Color("red_mushroom_block", 0xc82f2d));
        blocks.add(new LogoPixels.Color("emerald_block", 0x2acb58));
        blocks.add(new LogoPixels.Color("lapis_block", 0x1f438c));
        blocks.add(new LogoPixels.Color("amethyst_block", 0x8662bf));
        blocks.add(new LogoPixels.Color("snow_block", 0xf9fefe));
        blocks.add(new LogoPixels.Color("iron_block", 0xdcdcdc));
        blocks.add(new LogoPixels.Color("polished_diorite", 0xc1c1c3));
        blocks.add(new LogoPixels.Color("smooth_stone", 0xcecece));
        blocks.add(new LogoPixels.Color("smooth_sandstone", 0xe0d6aa));
        blocks.add(new LogoPixels.Color("honeycomb_block", 0xe5941e));
        blocks.add(new LogoPixels.Color("prismarine_bricks", 0x63ac9e));
        blocks.add(new LogoPixels.Color("blue_ice", 0x74a8fd));
        BLOCKS = List.copyOf(blocks);
        OKLAB = BLOCKS.stream().map(color -> oklab(color.rgb())).toArray(double[][]::new);
        PLAIN = new boolean[BLOCKS.size()];
        for (int i = 0; i < PLAIN.length; i++) PLAIN[i] = i < PLAIN_DYED || PLAIN_MORE.contains(BLOCKS.get(i).block());
        BUILT = new int[PLAIN.length];
        for (int i = 0; i < BUILT.length; i++) {
            BUILT[i] = i;
            if (PLAIN[i]) continue;
            int nearest = 0;
            for (int j = 1; j < PLAIN.length; j++) if (PLAIN[j] && away(OKLAB[i], j) < away(OKLAB[i], nearest)) nearest = j;
            if (away(OKLAB[i], nearest) <= PATTERN) BUILT[i] = nearest;
        }
    }

    private GatePalette() { }

    /**
     * The block for a colour: the nearest of the 60, or the plain block that stands in for it. Distance is Oklab
     * with lightness counted half, so the right hue wins over the right brightness (plain RGB distance turned a
     * bright red orange).
     */
    public static String nearest(int rgb) {
        double[] wanted = oklab(rgb);
        int best = 0;
        for (int i = 1; i < OKLAB.length; i++) if (away(wanted, i) < away(wanted, best)) best = i;
        return BLOCKS.get(BUILT[best]).block();
    }

    /** The blocks that can be built for a colour: the one {@link #nearest} picks first, then the next best, and so on. */
    public static List<String> nearestFirst(int rgb) {
        double[] wanted = oklab(rgb);
        // A stable sort: blocks equally far keep the palette's order, as nearest() takes the first.
        return IntStream.range(0, OKLAB.length).boxed().sorted(Comparator.comparingDouble(i -> away(wanted, i)))
                .map(i -> BLOCKS.get(BUILT[i]).block()).distinct().toList();
    }

    /** The block that is built where this one is the nearest: itself, or the plain block that stands in for it. */
    public static String built(String block) {
        for (int i = 0; i < BUILT.length; i++) if (BLOCKS.get(i).block().equals(block)) return BLOCKS.get(BUILT[i]).block();
        throw new IllegalArgumentException("Not a palette block: " + block);
    }

    /** True for a block of one flat colour; false for one with spots, bricks or a pattern. */
    public static boolean plain(String block) {
        for (int i = 0; i < PLAIN.length; i++) if (BLOCKS.get(i).block().equals(block)) return PLAIN[i];
        throw new IllegalArgumentException("Not a palette block: " + block);
    }

    private static double away(double[] wanted, int block) {
        double l = 0.5 * (wanted[0] - OKLAB[block][0]), a = wanted[1] - OKLAB[block][1], b = wanted[2] - OKLAB[block][2];
        return Math.sqrt(l * l + a * a + b * b);
    }

    /**
     * A vanilla block ID as a gate names its blocks: without the {@code minecraft:} namespace. The groups' concretes
     * are written as full IDs ({@link dev.aresos.catalogue.AppGroup#concrete()}), as the hub records its blocks.
     */
    public static String name(String id) {
        String vanilla = "minecraft:";
        String name = id.startsWith(vanilla) ? id.substring(vanilla.length()) : id;
        if (name.isEmpty() || name.indexOf(':') >= 0) throw new IllegalArgumentException("Not a vanilla block: " + id);
        return name;
    }

    /** Plain Oklab distance between two sRGB colours. */
    public static double distance(int first, int second) {
        double[] a = oklab(first), b = oklab(second);
        return Math.sqrt((a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) + (a[2] - b[2]) * (a[2] - b[2]));
    }

    /** sRGB to Oklab (L, a, b), with Björn Ottosson's published matrices. */
    static double[] oklab(int rgb) {
        double r = linear(rgb >> 16 & 255), g = linear(rgb >> 8 & 255), b = linear(rgb & 255);
        double l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
        double m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
        double s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
        return new double[]{0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s};
    }

    private static double linear(int channel) {
        double value = channel / 255.0;
        return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
    }
}
