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

    @Test void aSpeckBesideAThinLineIsNotShown() {
        var picture = GatePicture.of(LogoIcons.lineAndStar(), SIZE);
        assertTrue(picture.enlarged());
        assertEquals(Set.of("black_wool", "white_wool"), blocks(picture));
        // The two lines are whole: one column up the left, one row along the bottom, meeting in the corner.
        for (int u = 1; u <= 10; u++) assertEquals("white_wool", picture.at(u, 3), "the line along the bottom at " + u);
        for (int v = 3; v <= 8; v++) assertEquals("white_wool", picture.at(1, v), "the line up the left at " + v);
        // The star over the bottom line's end is under a cell wide: no line. Without this rule its cell was light too,
        // a bump on the line (and on Lunar Client's moon a star stood on the horn's tip as a second cell).
        for (int v = 0; v < SIZE; v++) for (int u = 0; u < SIZE; u++)
            if ("white_wool".equals(picture.at(u, v))) assertTrue(u == 1 || v == 3, "a light cell off the two lines: " + u + ", " + v);
    }

    @Test void aFlatIconOfSevenColoursHasNoBlockBetweenItsColours() {
        var icon = LogoIcons.sevenStripes();
        // One more than six main colours: each cell keeps its own colour, which is the colour of the stripe that
        // covers most of it. The average of all that falls into a cell gave twelve blocks, five of them between two
        // stripes (yellow terracotta, green wool, cyan wool, yellow and purple concrete).
        assertEquals(7, GatePicture.mainColours(icon, SIZE).size());
        assertEquals(Set.of("black_wool", "red_wool", "orange_wool", "yellow_wool", "lime_concrete", "light_blue_concrete", "purple_wool"),
                blocks(GatePicture.of(icon, SIZE)));
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

    /** An opaque 96 x 96 icon, one sample to a pixel at 12 x 12. */
    private static BufferedImage draw(java.util.function.IntBinaryOperator rgb) {
        var icon = new BufferedImage(96, 96, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 96; y++) for (int x = 0; x < 96; x++) icon.setRGB(x, y, 0xff000000 | rgb.applyAsInt(x, y));
        return icon;
    }

    /**
     * A colour on under 1% of the picture is no main colour (package 39b, 39's review N5): a yellow square of one cell
     * (0.7%) on an icon of red and blue halves gets no block of its own; its cell takes the nearest main colour, red.
     */
    @Test void aColourOnUnderOnePercentIsNoMainColour() {
        var icon = draw((x, y) -> x >= 8 && x < 16 && y >= 40 && y < 48 ? 0xffd800 : x < 48 ? 0xd02020 : 0x2040d0);
        var mains = GatePicture.mainColours(icon, SIZE);
        assertEquals(java.util.List.of(0x2040d0, 0xd02020), mains.stream().map(GatePicture.Main::rgb).toList(), "Main colours: " + mains);
        var picture = GatePicture.of(icon, SIZE);
        assertEquals(Set.of("blue_wool", "red_wool"), blocks(picture));
        assertEquals("red_wool", picture.at(1, 6), "The yellow square's cell");
    }

    /**
     * Noise of more than a hundred colours, every two farther apart than a colour group reaches (0.10), each on under
     * 1% of the picture (package 39b, 39's review N1). Every group falls under the 1% that makes a main colour; then
     * all of them stay, and the icon is many-coloured, each cell in a colour of its own. Before, none was left: the
     * conversion threw, and the logo got a plain front.
     */
    @Test void noiseWhoseColoursAreAllUnderOnePercentIsManyColoured() {
        // Picked from the edge of the colour space inwards, each more than 0.10 from every one before it.
        int[] colours = {
                0x000000, 0x000015, 0x150000, 0x030042, 0x001500, 0x270027, 0x330f00, 0x000078, 0x0c2130,
                0x30005d, 0x003000, 0x4e0036, 0x0000b1, 0x3f0096, 0x0000ed, 0x660000, 0x153063, 0x60006c,
                0x3c3024, 0x4e00d2, 0x004e00, 0x7e0042, 0x6f00a8, 0x7500ff, 0xffff00, 0x00ff00, 0x00429c,
                0x004b4e, 0x54365a, 0xff00ff, 0xa800ff, 0x90007e, 0x3945ff, 0x990600, 0x693900, 0x9f00bd,
                0xa8ff57, 0xffffa8, 0xffffff, 0xcf00d8, 0xae0054, 0xff00ba, 0xc00093, 0x006f00, 0xc90000,
                0x5748b4, 0x00ffa8, 0x00d800, 0xff0000, 0xff0075, 0xa5ffff, 0x036084, 0xffd500, 0x485d39,
                0x81424e, 0x815aff, 0xff6cfc, 0x0069d2, 0xc65aff, 0xa5d800, 0x009000, 0xffd5ff, 0x8a5400,
                0x00b400, 0xb7f0a5, 0x844b90, 0x00f0ed, 0xffd8ab, 0xa254c9, 0x1b87ff, 0xff9fff, 0xc94572,
                0xff6600, 0x6c7500, 0xff63ae, 0x007e63, 0xffab00, 0xc05700, 0x06d88a, 0x696675, 0xb1d8ff,
                0x9684ff, 0x0081a8, 0x93b400, 0x00cfff, 0x6f6fbd, 0xffb1c0, 0xff8484, 0xc972c9, 0xc6c66c,
                0x00a86f, 0xd88d00, 0x5aa8ff, 0xbda5ff, 0x998d00, 0x9f6c90, 0x00c0b4, 0x93cfba, 0xcf726c,
                0x7b8469, 0x5a9cba, 0xd2a88d, 0x8dab7b, 0xb196ba};
        for (int i = 0; i < colours.length; i++) for (int j = i + 1; j < colours.length; j++) {
            double[] a = GatePalette.oklab(colours[i]), b = GatePalette.oklab(colours[j]);
            assertTrue(Math.sqrt(Math.pow(a[0] - b[0], 2) + Math.pow(a[1] - b[1], 2) + Math.pow(a[2] - b[2], 2)) > 0.10,
                    "Fixture: two colours of one group");
        }
        // Each on 88 or 89 of the 9,216 samples, scattered as noise (a fixed seed: the same icon every run).
        var noise = new java.util.ArrayList<Integer>();
        for (int i = 0; i < 96 * 96; i++) noise.add(colours[i % colours.length]);
        java.util.Collections.shuffle(noise, new java.util.Random(39));
        var icon = draw((x, y) -> noise.get(y * 96 + x));
        var mains = GatePicture.mainColours(icon, SIZE);
        assertEquals(colours.length, mains.size(), "Main colours: " + mains.size());
        assertTrue(mains.stream().allMatch(main -> main.share() < 0.01), "Fixture: a colour on 1% or more");
        var picture = assertDoesNotThrow(() -> GatePicture.of(icon, SIZE));
        assertFalse(picture.isEmpty());
        assertTrue(blocks(picture).size() > 6, "Not many-coloured: " + blocks(picture));
    }
}
