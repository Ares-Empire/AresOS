package dev.aresos.icon;

import java.awt.image.BufferedImage;
import java.util.*;

public final class PixelIconConverter implements IconConverter {
    @Override public String version() { return "pixel-1"; }
    @Override public BufferedImage convert(BufferedImage source) {
        var result = new BufferedImage(16, 16, BufferedImage.TYPE_INT_ARGB);
        double scale = 14.0 / Math.max(source.getWidth(), source.getHeight());
        int width = Math.max(1, (int)Math.round(source.getWidth() * scale));
        int height = Math.max(1, (int)Math.round(source.getHeight() * scale));
        int[] pixels = new int[width * height];
        Map<Integer, Integer> frequency = new TreeMap<>();
        // Area averaging preserves thin features; binary alpha and a shared palette keep the output crisp.
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            double r = 0, g = 0, b = 0, alpha = 0, area = 0;
            double x0 = x * (double)source.getWidth() / width, x1 = (x+1) * (double)source.getWidth() / width;
            double y0 = y * (double)source.getHeight() / height, y1 = (y+1) * (double)source.getHeight() / height;
            for (int sy = (int)y0; sy < Math.ceil(y1); sy++) for (int sx = (int)x0; sx < Math.ceil(x1); sx++) {
                double weight = (Math.min(sx+1, x1)-Math.max(sx, x0)) * (Math.min(sy+1,y1)-Math.max(sy,y0));
                int color = source.getRGB(sx, sy); double a = (color >>> 24) / 255.0 * weight;
                area += weight; alpha += a;
                r += (color >> 16 & 255) * a; g += (color >> 8 & 255) * a; b += (color & 255) * a;
            }
            if (alpha / area >= 0.5) {
                int color = 0xff000000 | quantize(r/alpha) << 16 | quantize(g/alpha) << 8 | quantize(b/alpha);
                pixels[y * width + x] = color;
                frequency.merge(color, 1, Integer::sum);
            }
        }
        List<Integer> palette = frequency.entrySet().stream()
                .sorted(Comparator.<Map.Entry<Integer,Integer>>comparingInt(Map.Entry::getValue).reversed().thenComparingInt(Map.Entry::getKey))
                .limit(15).map(Map.Entry::getKey).toList();
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            int color = pixels[y * width + x];
            if (color != 0) {
                int best = palette.getFirst(), distance = Integer.MAX_VALUE;
                for (int candidate : palette) {
                    int d = 0;
                    for (int shift = 0; shift <= 16; shift += 8) { int delta = (color >> shift & 255) - (candidate >> shift & 255); d += delta*delta; }
                    if (d < distance) { distance = d; best = candidate; }
                }
                result.setRGB(x + (16-width)/2, y + (16-height)/2, best);
            }
        }
        return result;
    }
    private static int quantize(double value) { return Math.min(255, (int)Math.round(value / 51) * 51); }
}
