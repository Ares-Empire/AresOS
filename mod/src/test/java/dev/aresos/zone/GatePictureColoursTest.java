package dev.aresos.zone;

import org.junit.jupiter.api.Test;

import java.awt.image.BufferedImage;
import java.util.ArrayDeque;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.IntPredicate;

import static org.junit.jupiter.api.Assertions.*;

/**
 * HUB.md 3.6, the colours: a logo is built from its icon's main colours, one plain block each, and a thin line
 * stays a line. The icons are {@link LogoIcons}' drawings, the ones the client test builds for the pictures.
 */
class GatePictureColoursTest {
    private static final int SIZE = GateNumbers.SIZE;

    /** Every block of a picture. */
    private static Set<String> blocks(GatePicture picture) {
        var blocks = new TreeSet<String>();
        for (int v = 0; v < picture.size(); v++) for (int u = 0; u < picture.size(); u++) if (picture.at(u, v) != null) blocks.add(picture.at(u, v));
        return blocks;
    }

    /** The cells before tidy and door, as {@link GatePicture#blocks} gives them: index v * SIZE + u. */
    private static String[] cells(BufferedImage icon) {
        var cut = GatePicture.cut(icon);
        return GatePicture.blocks(cut, GatePicture.plate(cut), SIZE);
    }

    /** The cell a pixel of the cut icon falls into, on an enlarged plate. */
    private static int cell(GatePicture.Plate plate, double x, double y) {
        double step = plate.side() / SIZE;
        int u = (int)Math.floor((x - plate.left()) / step), row = (int)Math.floor((y - plate.top()) / step);
        return u < 0 || row < 0 || u >= SIZE || row >= SIZE ? -1 : (SIZE - 1 - row) * SIZE + u;
    }

    /** The cells reached from one cell over cells of one sort; lines hang together at corners too, backgrounds do not. */
    private static boolean[] reach(int from, IntPredicate sort, boolean corners) {
        var reached = new boolean[SIZE * SIZE];
        var next = new ArrayDeque<Integer>();
        reached[from] = true;
        next.add(from);
        while (!next.isEmpty()) {
            int cell = next.remove();
            for (int dv = -1; dv <= 1; dv++) for (int du = -1; du <= 1; du++) {
                int u = cell % SIZE + du, v = cell / SIZE + dv;
                if ((du == 0 && dv == 0) || (!corners && du != 0 && dv != 0) || u < 0 || v < 0 || u >= SIZE || v >= SIZE) continue;
                if (reached[v * SIZE + u] || !sort.test(v * SIZE + u)) continue;
                reached[v * SIZE + u] = true;
                next.add(v * SIZE + u);
            }
        }
        return reached;
    }

    @Test void thinLightLinesOnADarkPlateStayConnectedLinesOfTheLightBlock() {
        var icon = LogoIcons.thinLines();
        var picture = GatePicture.of(icon, SIZE);
        assertTrue(picture.enlarged());
        // Version 1 averaged the lines into the plate: six blocks, four of them greys the icon does not have.
        assertEquals(Set.of("black_wool", "white_wool"), blocks(picture));
        assertEquals(2, GatePicture.mainColours(icon, SIZE).size());

        var cut = GatePicture.cut(icon);
        var plate = GatePicture.plate(cut);
        var cells = GatePicture.blocks(cut, plate, SIZE);
        IntPredicate light = cell -> "white_wool".equals(cells[cell]);
        // Where a line is drawn, its cell or the next one is light; and a light cell has a drawn line in it.
        var drawn = new boolean[SIZE * SIZE];
        for (int y = 0; y < cut.getHeight(); y++) for (int x = 0; x < cut.getWidth(); x++) {
            if ((cut.getRGB(x, y) >> 8 & 255) < 200) continue;
            int cell = cell(plate, x + 0.5, y + 0.5);
            if (cell < 0) continue;
            drawn[cell] = true;
            boolean shown = false;
            for (int dv = -1; dv <= 1; dv++) for (int du = -1; du <= 1; du++) {
                int u = cell % SIZE + du, v = cell / SIZE + dv;
                shown |= u >= 0 && v >= 0 && u < SIZE && v < SIZE && light.test(v * SIZE + u);
            }
            assertTrue(shown, "the line drawn at " + x + ", " + y + " is not shown");
        }
        for (int cell = 0; cell < cells.length; cell++) if (light.test(cell)) assertTrue(drawn[cell], "a light cell without a line: " + cell);

        // The arch is one line from foot to foot; the icon's feet are at (30, 104) and (98, 104), the cut starts at (4, 4).
        int left = cell(plate, 26, 98), right = cell(plate, 94, 98), middle = cell(plate, 60, 58);
        assertTrue(light.test(left) && light.test(right), "the arch's feet");
        var arch = reach(left, light, true);
        assertTrue(arch[right], "the arch is broken");
        // The ring is a second line, closed: the dark cell in its middle is cut off from the dark around it.
        assertFalse(light.test(middle));
        var inside = reach(middle, cell -> !light.test(cell), false);
        assertFalse(inside[0], "the ring is open");
        int ringCell = -1;
        for (int cell = 0; cell < cells.length; cell++) if (light.test(cell) && !arch[cell]) ringCell = cell;
        assertTrue(ringCell >= 0, "the ring is missing or runs into the arch");
        var ring = reach(ringCell, light, true);
        for (int cell = 0; cell < cells.length; cell++) assertEquals(light.test(cell), arch[cell] || ring[cell], "a light cell of neither line: " + cell);
        // One cell wide: 4 pixels of line are half a cell, and no light cell has a full block of four around it.
        for (int v = 0; v + 1 < SIZE; v++) for (int u = 0; u + 1 < SIZE; u++)
            assertFalse(light.test(v * SIZE + u) && light.test(v * SIZE + u + 1) && light.test((v + 1) * SIZE + u) && light.test((v + 1) * SIZE + u + 1),
                    "the line is two cells wide at " + u + ", " + v);
    }

    @Test void aPaleFigureWithSmoothedEdgesHasNoBlockBetweenItAndItsPlate() {
        var icon = LogoIcons.paleFigure();
        var picture = GatePicture.of(icon, SIZE);
        assertTrue(picture.enlarged());
        // Version 1 put amethyst, blue ice, iron and polished diorite on the bubble's edge.
        assertEquals(Set.of("blue_wool", "white_wool"), blocks(picture));
        assertEquals(2, GatePicture.mainColours(icon, SIZE).size());
        // The three dots are still there: plate-coloured cells with the pale bubble on every side.
        var cells = cells(icon);
        int dots = 0;
        for (int v = 1; v < SIZE - 1; v++) for (int u = 1; u < SIZE - 1; u++)
            if (cells[v * SIZE + u].equals("blue_wool") && cells[(v + 1) * SIZE + u].equals("white_wool") && cells[(v - 1) * SIZE + u].equals("white_wool")) dots++;
        assertTrue(dots >= 3 && dots <= 6, dots + " dot cells");
    }

    @Test void aLightRingWithASlightGradientIsOneBlockAndClosed() {
        var icon = LogoIcons.wheel();
        var picture = GatePicture.of(icon, SIZE);
        assertFalse(picture.enlarged());
        // Four colours and the ring: five blocks. Version 1 built the ring from six light blocks.
        assertEquals(Set.of("orange_wool", "lime_concrete", "purple_wool", "cyan_wool", "white_wool"), blocks(picture));
        var cells = cells(icon);
        IntPredicate ring = cell -> "white_wool".equals(cells[cell]);
        int first = -1, count = 0;
        for (int cell = 0; cell < cells.length; cell++) if (ring.test(cell)) { first = cell; count++; }
        assertTrue(count >= 12 && count <= 16, count + " ring cells");
        var whole = reach(first, ring, true);
        for (int cell = 0; cell < cells.length; cell++) assertEquals(ring.test(cell), whole[cell], "the ring is in pieces at " + cell);
        // The teal middle is shut in by it.
        int middle = (SIZE / 2) * SIZE + SIZE / 2;
        assertEquals("cyan_wool", cells[middle]);
        var inside = reach(middle, cell -> !ring.test(cell), false);
        for (int cell = 0; cell < cells.length; cell++) if (inside[cell]) assertEquals("cyan_wool", cells[cell], "the ring is open at " + cell);
    }

    @Test void aStrongRedIsAPlainRedBlock() {
        var picture = GatePicture.of(LogoIcons.redFigure(), SIZE);
        // The heart, and the black posts of its door. Version 1: red mushroom block, with white spots.
        assertEquals(Set.of("red_wool", "black_concrete"), blocks(picture));
        assertTrue(GatePalette.plain("red_wool"));
        assertFalse(GatePalette.plain("red_mushroom_block"));
    }

    @Test void aManyColouredIconKeepsEachCellsOwnColour() {
        var icon = LogoIcons.manyColours();
        assertTrue(GatePicture.mainColours(icon, SIZE).size() > 6, "sixteen hues are more than a few main colours");
        var blocks = blocks(GatePicture.of(icon, SIZE));
        // Sixteen patches give ten blocks: neighbouring hues share one. All of them plain.
        assertEquals(Set.of("blue_wool", "light_blue_wool", "lime_wool", "magenta_wool", "orange_wool", "pink_concrete", "purple_wool",
                "red_wool", "yellow_concrete", "yellow_wool"), blocks);
        for (String block : blocks) assertTrue(GatePalette.plain(block), block);
    }

    @Test void aPhotoLikeIconKeepsEachCellsOwnColour() {
        var icon = LogoIcons.photo();
        assertTrue(GatePicture.mainColours(icon, SIZE).size() > 6);
        var picture = GatePicture.of(icon, SIZE);
        var blocks = blocks(picture);
        assertTrue(blocks.size() >= 8 && blocks.size() <= 14, blocks.toString());
        // Sky above, hills below.
        assertEquals("light_blue_concrete", picture.at(0, SIZE - 1));
        assertTrue(blocks.contains("blue_ice") && blocks.contains("green_concrete") && blocks.contains("lime_terracotta"), blocks.toString());
        for (String block : blocks) assertEquals(block, GatePalette.built(block), "a block that a plain one stands in for");
    }

    @Test void aGradientBecomesAFewBandsInOrder() {
        var icon = LogoIcons.gradient();
        var picture = GatePicture.of(icon, SIZE);
        assertFalse(picture.enlarged());
        // Four bands from coral to violet, and the white triangle.
        assertEquals(Set.of("pink_wool", "pink_concrete", "magenta_terracotta", "purple_wool", "snow_block"), blocks(picture));
        assertEquals("pink_wool", picture.at(1, SIZE - 2));
        assertEquals("purple_wool", picture.at(SIZE - 2, 1));
        assertEquals("snow_block", picture.at(5, 5));
    }

    @Test void anIconWithoutAPlateKeepsItsOutline() {
        var picture = GatePicture.of(LogoIcons.noPlate(), SIZE);
        assertFalse(picture.enlarged());
        assertEquals(Set.of("green_wool", "brown_wool", "black_concrete"), blocks(picture));
        // Half as wide as tall: the crown in the middle columns, nothing beside it, the trunk over the door.
        for (int v = 0; v < SIZE; v++) for (int u : new int[]{0, 1, 2, 9, 10, 11}) assertNull(picture.at(u, v));
        assertEquals("green_wool", picture.at(5, SIZE - 1));
        assertEquals("brown_wool", picture.at(5, 3));
    }

    @Test void aSmallFigureIsEnlargedInItsOwnColours() {
        var picture = GatePicture.of(LogoIcons.smallFigure(), SIZE);
        assertTrue(picture.enlarged());
        // Version 1 had five more blocks on the sun's two edges.
        assertEquals(Set.of("cyan_concrete", "yellow_concrete", "orange_concrete"), blocks(picture));
        assertEquals("cyan_concrete", picture.at(0, SIZE - 1));
        assertEquals("orange_concrete", picture.at(SIZE / 2, SIZE / 2));
    }

    @Test void aMostlySeeThroughIconStaysMostlyEmpty() {
        var picture = GatePicture.of(LogoIcons.seeThrough(), SIZE);
        assertFalse(picture.enlarged());
        assertEquals(Set.of("cyan_terracotta", "orange_wool", "black_concrete"), blocks(picture));
        int solid = 0;
        for (int v = 0; v < SIZE; v++) for (int u = 0; u < SIZE; u++) if (picture.at(u, v) != null) solid++;
        assertTrue(solid >= 50 && solid <= 70, solid + " solid cells of 144");
        assertNull(picture.at(3, 8), "the glass is see-through");
    }

    @Test void theSameIconGivesTheSameBlocksEveryTime() {
        var first = LogoIcons.all();
        var second = LogoIcons.all();
        for (int i = 0; i < first.size(); i++) {
            String name = first.get(i).id();
            assertEquals(GatePicture.of(first.get(i).image(), SIZE).hash(), GatePicture.of(second.get(i).image(), SIZE).hash(), name);
            assertEquals(GatePicture.mainColours(first.get(i).image(), SIZE), GatePicture.mainColours(second.get(i).image(), SIZE), name);
            assertFalse(GatePicture.of(first.get(i).image(), SIZE).isEmpty(), name);
        }
        // The rules changed with package 39: a standing logo of version 1 is drawn again (HUB.md 2.5).
        assertEquals(2, GatePicture.CONVERTER);
    }

    @Test void twoMainColoursShareABlockOnlyWhenTheyAreNearlyTheSame() {
        // Two whites, a step apart: one block. A white and a mid grey whose nearest block is taken: the next one.
        assertArrayEquals(new String[]{"snow_block", "snow_block"},
                GatePicture.blocksFor(java.util.List.of(new GatePicture.Main(0xffffff, 0.6), new GatePicture.Main(0xf4f6f8, 0.4))));
        // Both reds are nearest to red wool, and they are far apart: the darker one takes its next block.
        var reds = GatePicture.blocksFor(java.util.List.of(new GatePicture.Main(0xff0000, 0.6), new GatePicture.Main(0x7a1010, 0.4)));
        assertEquals("red_wool", reds[0]);
        assertNotEquals("red_wool", reds[1]);
    }
}
