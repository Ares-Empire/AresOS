package dev.aresos.zone;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.GradientPaint;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.geom.Arc2D;
import java.awt.geom.Ellipse2D;
import java.awt.geom.Line2D;
import java.awt.geom.RoundRectangle2D;
import java.awt.image.BufferedImage;
import java.util.List;
import java.util.function.Consumer;

/**
 * The icons the tests of HUB.md 3.6 draw, 128 pixels a side, with smoothed edges as real icons have them. The unit
 * tests check the cells they become and the client test builds them as logos for the pictures. Every one is a
 * generic shape drawn here; none is a real app's icon or a copy of one.
 */
public final class LogoIcons {
    public record Icon(String id, String name, BufferedImage image) { }

    private LogoIcons() { }

    /** All ten, in the order the pictures show them. */
    public static List<Icon> all() {
        return List.of(new Icon("thin-lines", "Thin lines", thinLines()), new Icon("pale-figure", "Pale figure", paleFigure()),
                new Icon("wheel", "Wheel", wheel()), new Icon("red-figure", "Red figure", redFigure()),
                new Icon("many-colours", "Many colours", manyColours()), new Icon("photo", "Photo", photo()),
                new Icon("gradient", "Gradient", gradient()), new Icon("no-plate", "No plate", noPlate()),
                new Icon("small-figure", "Small figure", smallFigure()), new Icon("see-through", "See-through", seeThrough()));
    }

    /** A dark tile with a ring and an arc over it, both 4 pixels wide: half a cell once the figure is enlarged. */
    public static BufferedImage thinLines() {
        return draw(g -> {
            g.setColor(new Color(0x15171c));
            g.fill(new RoundRectangle2D.Double(4, 4, 120, 120, 30, 30));
            g.setColor(new Color(0xf2f4f7));
            g.setStroke(new BasicStroke(4, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.draw(new Ellipse2D.Double(46, 54, 36, 36));
            g.draw(new Arc2D.Double(26, 34, 76, 76, 20, 140, Arc2D.OPEN));
        });
    }

    /** A violet disc with a pale speech bubble and three dots: a pale figure whose smoothed edge mixes with its plate. */
    public static BufferedImage paleFigure() {
        return draw(g -> {
            var violet = new Color(0x5b53d6);
            g.setColor(violet);
            g.fillOval(2, 2, 124, 124);
            g.setColor(new Color(0xe8e6ff));
            g.fill(new RoundRectangle2D.Double(34, 40, 60, 40, 22, 22));
            g.fill(new Polygon(new int[]{46, 62, 44}, new int[]{76, 76, 94}, 3));
            g.setColor(violet);
            for (int dot = 0; dot < 3; dot++) g.fillOval(44 + 15 * dot, 54, 10, 10);
        });
    }

    /** A round figure in four colours: three wedges, a teal middle, and between them a light ring that darkens a little downwards. */
    public static BufferedImage wheel() {
        return draw(g -> {
            int[] wedges = {0xf57c00, 0x7b1fa2, 0x7cb342};
            for (int wedge = 0; wedge < 3; wedge++) {
                g.setColor(new Color(wedges[wedge]));
                g.fill(new Arc2D.Double(2, 2, 124, 124, 90 + 120 * wedge, 120, Arc2D.PIE));
            }
            g.setPaint(new GradientPaint(0, 34, new Color(0xffffff), 0, 94, new Color(0xe4e7ec)));
            g.fillOval(34, 34, 60, 60);
            g.setColor(new Color(0x00838f));
            g.fillOval(44, 44, 40, 40);
        });
    }

    /** A strong red heart with nothing around it. */
    public static BufferedImage redFigure() {
        return draw(g -> {
            g.setColor(new Color(0xe5261f));
            g.fillOval(6, 12, 62, 62);
            g.fillOval(60, 12, 62, 62);
            g.fill(new Polygon(new int[]{11, 117, 64}, new int[]{58, 58, 120}, 3));
        });
    }

    /** Sixteen patches, each its own hue. */
    public static BufferedImage manyColours() {
        return draw(g -> {
            for (int patch = 0; patch < 16; patch++) {
                g.setColor(Color.getHSBColor(patch / 16f, 0.75f, 0.9f));
                g.fillRect(4 + 30 * (patch % 4), 4 + 30 * (patch / 4), 30, 30);
            }
        });
    }

    /** Photo-like: a sky, a sun, two hills and a lake, with every pixel a little off its neighbours. */
    public static BufferedImage photo() {
        var image = draw(g -> {
            g.setPaint(new GradientPaint(0, 0, new Color(0x4a90d9), 0, 80, new Color(0xcfe6f5)));
            g.fillRect(0, 0, 128, 128);
            g.setColor(new Color(0xfff2b0));
            g.fillOval(82, 14, 26, 26);
            g.setColor(new Color(0x5d8a4e));
            g.fillOval(-40, 58, 130, 120);
            g.setColor(new Color(0x3f6b3a));
            g.fillOval(50, 70, 130, 120);
            g.setPaint(new GradientPaint(0, 100, new Color(0x2f6f9f), 0, 128, new Color(0x1d4f7a)));
            g.fillOval(18, 100, 70, 40);
        });
        for (int y = 0; y < 128; y++) for (int x = 0; x < 128; x++) {
            // The same grain every time: a small hash of the pixel's place.
            int grain = (x * 73 + y * 151 + (x * y) % 17 * 29) % 25 - 12, rgb = image.getRGB(x, y);
            image.setRGB(x, y, 0xff000000 | channel(rgb >> 16, grain) << 16 | channel(rgb >> 8, grain) << 8 | channel(rgb, grain));
        }
        return image;
    }

    /** A rounded tile whose colour runs from coral in one corner to violet in the other, with a white triangle. */
    public static BufferedImage gradient() {
        return draw(g -> {
            g.setPaint(new GradientPaint(8, 8, new Color(0xff8a65), 120, 120, new Color(0x5e35b1)));
            g.fill(new RoundRectangle2D.Double(4, 4, 120, 120, 30, 30));
            g.setColor(Color.WHITE);
            g.fill(new Polygon(new int[]{50, 50, 86}, new int[]{40, 88, 64}, 3));
        });
    }

    /** A tree, taller than wide, with nothing beside its trunk. */
    public static BufferedImage noPlate() {
        var tree = new BufferedImage(64, 128, BufferedImage.TYPE_INT_ARGB);
        paint(tree, g -> {
            g.setColor(new Color(0x6d4c41));
            g.fillRect(24, 74, 16, 54);
            g.setColor(new Color(0x2e7d32));
            g.fillOval(0, 0, 64, 86);
        });
        return tree;
    }

    /** A small sun on a plain teal tile: the sun is enlarged and the tile's colour fills the logo. */
    public static BufferedImage smallFigure() {
        return draw(g -> {
            g.setColor(new Color(0x17748a));
            g.fill(new RoundRectangle2D.Double(0, 0, 128, 128, 32, 32));
            g.setColor(new Color(0xf1af15));
            g.fillOval(40, 40, 48, 48);
            g.setColor(new Color(0xe06101));
            g.fillOval(53, 53, 22, 22);
        });
    }

    /** A magnifying glass: a thick ring and a handle, most of the square see-through. */
    public static BufferedImage seeThrough() {
        return draw(g -> {
            g.setColor(new Color(0x455a64));
            g.setStroke(new BasicStroke(16));
            g.draw(new Ellipse2D.Double(14, 14, 68, 68));
            g.setColor(new Color(0xfb8c00));
            g.setStroke(new BasicStroke(18, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.draw(new Line2D.Double(84, 84, 112, 112));
        });
    }

    private static int channel(int value, int grain) { return Math.clamp((value & 255) + grain, 0, 255); }

    private static BufferedImage draw(Consumer<Graphics2D> picture) {
        var icon = new BufferedImage(128, 128, BufferedImage.TYPE_INT_ARGB);
        paint(icon, picture);
        return icon;
    }

    private static void paint(BufferedImage icon, Consumer<Graphics2D> picture) {
        var graphics = icon.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        graphics.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
        picture.accept(graphics);
        graphics.dispose();
    }
}
