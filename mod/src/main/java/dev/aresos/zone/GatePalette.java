package dev.aresos.zone;

import java.util.ArrayList;
import java.util.List;

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
    private static final double[][] OKLAB;
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
    }

    private GatePalette() { }

    /**
     * The block nearest to a colour: Oklab distance with lightness counted half, so the right hue wins over the
     * right brightness. Plain RGB distance turned a bright red orange.
     */
    public static String nearest(int rgb) {
        double[] wanted = oklab(rgb);
        int best = 0;
        double distance = Double.MAX_VALUE;
        for (int i = 0; i < OKLAB.length; i++) {
            double l = 0.5 * (wanted[0] - OKLAB[i][0]), a = wanted[1] - OKLAB[i][1], b = wanted[2] - OKLAB[i][2];
            double d = l * l + a * a + b * b;
            if (d < distance) { distance = d; best = i; }
        }
        return BLOCKS.get(best).block();
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
