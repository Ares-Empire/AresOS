package dev.aresos.zone;

import java.awt.image.BufferedImage;
import java.util.List;
import java.util.ArrayList;

/** Original numeric color approximations; textures are supplied by Minecraft at runtime. */
public final class LogoPixels {
    public record Color(String block, int rgb) { }
    public record Pixel(int x, int y, String block) { }
    public record Image(int width, int height, List<Pixel> pixels) { }
    public static final List<Color> PALETTE;
    static {
        String[] names = {"white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
                "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"};
        int[][] colors = {
                {0xcfd5d6,0xe06101,0xa9309f,0x2389c6,0xf1af15,0x5ea818,0xd5658e,0x36393d,
                 0x7d7d73,0x157788,0x64209c,0x2c2e8f,0x603b1f,0x495b24,0x8e2020,0x080a0f},
                {0xe9ecec,0xf07613,0xbd44b3,0x3aafd9,0xf8c527,0x70b919,0xed8dac,0x3e4447,
                 0x8e8e86,0x158991,0x792aac,0x35399d,0x724728,0x546d1b,0xa12722,0x141519},
                {0xd1b1a1,0xa15325,0x95576c,0x716c89,0xba8523,0x677535,0xa04d4e,0x392a23,
                 0x876b62,0x575b5b,0x764656,0x4a3b5b,0x4d3323,0x4c532a,0x8f3d2e,0x251610}};
        String[] materials = {"concrete", "wool", "terracotta"};
        var palette = new ArrayList<Color>();
        for (int material = 0; material < materials.length; material++) for (int color = 0; color < names.length; color++)
            palette.add(new Color(names[color] + "_" + materials[material], colors[material][color]));
        PALETTE = List.copyOf(palette);
    }

    private LogoPixels() { }

    public static String nearest(int rgb) {
        String best = null;
        int distance = Integer.MAX_VALUE;
        for (var candidate : PALETTE) {
            int d = 0;
            for (int shift = 0; shift <= 16; shift += 8) {
                int delta = (rgb >> shift & 255) - (candidate.rgb >> shift & 255);
                d += delta * delta;
            }
            if (d < distance) { distance = d; best = candidate.block; }
        }
        return best;
    }

    public static Image convert(BufferedImage source) {
        double scale = Math.min(1, 32.0 / Math.max(source.getWidth(), source.getHeight()));
        int width = Math.max(1, (int)Math.round(source.getWidth() * scale));
        int height = Math.max(1, (int)Math.round(source.getHeight() * scale));
        var pixels = new ArrayList<Pixel>();
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            double x0 = x * (double)source.getWidth() / width, x1 = (x + 1.0) * source.getWidth() / width;
            double y0 = y * (double)source.getHeight() / height, y1 = (y + 1.0) * source.getHeight() / height;
            double alpha = 0, area = 0, r = 0, g = 0, b = 0;
            for (int sy = (int)y0; sy < Math.ceil(y1); sy++) for (int sx = (int)x0; sx < Math.ceil(x1); sx++) {
                double weight = (Math.min(sx + 1, x1) - Math.max(sx, x0)) * (Math.min(sy + 1, y1) - Math.max(sy, y0));
                int rgb = source.getRGB(sx, sy);
                double a = (rgb >>> 24) / 255.0 * weight;
                area += weight; alpha += a;
                r += (rgb >> 16 & 255) * a; g += (rgb >> 8 & 255) * a; b += (rgb & 255) * a;
            }
            if (alpha / area >= 0.5) pixels.add(new Pixel(x, y,
                    nearest((int)Math.round(r / alpha) << 16 | (int)Math.round(g / alpha) << 8 | (int)Math.round(b / alpha))));
        }
        return new Image(width, height, List.copyOf(pixels));
    }
}
