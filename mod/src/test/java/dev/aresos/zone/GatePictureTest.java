package dev.aresos.zone;

import org.junit.jupiter.api.Test;

import java.awt.image.BufferedImage;
import java.util.function.IntBinaryOperator;

import static org.junit.jupiter.api.Assertions.*;

/** HUB.md 3.6 with icons drawn here, pixel by pixel, for every size the owner was offered. */
class GatePictureTest {
    private static final int[] SIZES = {10, 12, 14, 16};
    private static final int CLEAR = 0, RED = 0xffff0000, WHITE = 0xffffffff, BLUE = 0xff2d2f8f, GREEN = 0xff5ea919;

    private static BufferedImage draw(int width, int height, IntBinaryOperator argb) {
        var image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) image.setRGB(x, y, argb.applyAsInt(x, y));
        return image;
    }

    /** A red ring: see-through inside and outside. */
    private static BufferedImage ring() {
        return draw(120, 120, (x, y) -> {
            double d = Math.hypot(x + 0.5 - 60, y + 0.5 - 60);
            return d <= 60 && d >= 30 ? RED : CLEAR;
        });
    }

    /** A blue plate with a see-through margin and a white square of the given size in its middle. */
    private static BufferedImage plate(int figure) {
        return draw(128, 128, (x, y) -> {
            if (x < 8 || y < 8 || x >= 120 || y >= 120) return CLEAR;
            return Math.abs(x + 0.5 - 64) < figure / 2.0 && Math.abs(y + 0.5 - 64) < figure / 2.0 ? WHITE : BLUE;
        });
    }

    private static boolean opening(int size, int u, int v) {
        int left = GateNumbers.doorLeft(size);
        return v < 3 && (u == left || u == left + 1);
    }

    private static void assertDoor(GatePicture picture) {
        int size = picture.size(), left = GateNumbers.doorLeft(size);
        assertEquals(size / 2 - 1, left);
        for (int v = 0; v < 3; v++) {
            assertNull(picture.at(left, v)); assertNull(picture.at(left + 1, v));
            assertNotNull(picture.at(left - 1, v), "left post"); assertNotNull(picture.at(left + 2, v), "right post");
        }
        for (int u = left - 1; u <= left + 2; u++) assertNotNull(picture.at(u, 3), "bar over the door");
    }

    private static String text(GatePicture picture) {
        var text = new StringBuilder();
        for (int v = picture.size() - 1; v >= 0; v--) {
            for (int u = 0; u < picture.size(); u++) {
                String block = picture.at(u, v);
                text.append(block == null ? '.' : block.equals("red_wool") ? 'R' : block.equals(GatePalette.BLACK) ? '#' : '?');
            }
            text.append('\n');
        }
        return text.toString();
    }

    @Test void aRingKeepsItsOutlineAndGetsADoor() {
        assertEquals("""
                ....RRRR....
                ..RRRRRRRR..
                .RRRRRRRRRR.
                .RRR....RRR.
                RRR......RRR
                RRR......RRR
                RRR......RRR
                RRR......RRR
                .RRR####RRR.
                .RRRR..RRRR.
                ..RRR..RRR..
                ....R..R....
                """, text(GatePicture.of(ring(), 12)));
        for (int size : SIZES) {
            var picture = GatePicture.of(ring(), size);
            assertFalse(picture.enlarged());
            assertDoor(picture);
            for (int corner : new int[]{0, size - 1}) { assertNull(picture.at(corner, 0)); assertNull(picture.at(corner, size - 1)); }
            assertNull(picture.at(size / 2, size / 2), "the hole stays open");
            assertEquals("red_wool", picture.at(size / 2, size - 1));
            for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
                assertEquals(picture.at(u, v), picture.at(size - 1 - u, v), "mirror at " + u + "," + v);
        }
    }

    @Test void aSmallFigureOnAPlainPlateIsEnlargedAndThePlateFillsThePicture() {
        for (int size : SIZES) {
            var picture = GatePicture.of(plate(32), size);
            assertTrue(picture.enlarged());
            assertDoor(picture);
            int white = 0;
            for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) {
                if (opening(size, u, v)) continue;
                assertNotNull(picture.at(u, v), "the plate fills " + u + "," + v);
                if (picture.at(u, v).equals("snow_block")) white++;
            }
            for (int corner : new int[]{0, size - 1}) assertEquals("blue_concrete", picture.at(corner, size - 1));
            assertEquals("snow_block", picture.at(size / 2, size / 2));
            // Left whole, the square would cover 8% of the picture; enlarged it covers about four cells in ten.
            assertTrue(white > size * size / 3, white + " white cells of " + size * size);
        }
    }

    /**
     * Step 2's square is centred on the figure to the half pixel (package 39b, 39's review N5). An upright white bar 10
     * pixels wide (43 to 52) and 29 high gets a square of 35, whose left edge falls on a half pixel. Rounded to the
     * whole pixel, as converter 1 did, the square sat half a pixel to the right, and the bar, the same left and right,
     * was not so in the cells.
     */
    @Test void anEnlargedFigureIsCentredToTheHalfPixel() {
        var icon = draw(96, 96, (x, y) -> x >= 43 && x < 53 && y >= 34 && y < 63 ? WHITE : BLUE);
        var plate = GatePicture.plate(GatePicture.cut(icon));
        assertNotNull(plate, "Fixture: the bar is not taken as a figure on a plate");
        assertEquals(35, plate.side(), 1e-9, "Fixture: the square's side");
        assertEquals(48, plate.left() + plate.side() / 2, 1e-9, "The square's middle across, the bar's middle");
        assertEquals(48.5, plate.top() + plate.side() / 2, 1e-9, "The square's middle up and down, the bar's middle");
        var picture = GatePicture.of(icon, GateNumbers.SIZE);
        assertTrue(picture.enlarged());
        int size = picture.size();
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
            assertEquals(picture.at(u, v), picture.at(size - 1 - u, v), "mirror at " + u + "," + v);
    }

    @Test void otherIconsAreLeftWhole() {
        // The figure already fills the plate.
        assertFalse(GatePicture.of(plate(100), 12).enlarged());
        // The figure is under 2% of the picture.
        assertFalse(GatePicture.of(plate(10), 12).enlarged());
        // The rim has two colours.
        assertFalse(GatePicture.of(draw(128, 128, (x, y) -> Math.abs(x - 64) < 16 && Math.abs(y - 64) < 16 ? WHITE : x < 64 ? RED : BLUE), 12).enlarged());
        // One plain colour has no figure.
        assertFalse(GatePicture.of(draw(64, 64, (x, y) -> BLUE), 12).enlarged());
        // A faint glow around the plate is neither rim nor figure.
        var glow = draw(128, 128, (x, y) -> {
            if (x < 4 || y < 4 || x >= 124 || y >= 124) return CLEAR;
            if (x < 8 || y < 8 || x >= 120 || y >= 120) return 0x4dffffff;
            return Math.abs(x + 0.5 - 64) < 16 && Math.abs(y + 0.5 - 64) < 16 ? WHITE : BLUE;
        });
        assertTrue(GatePicture.of(glow, 12).enlarged());
    }

    @Test void aPictureThatIsNotSquareIsCentredAndStandsOnTheGround() {
        for (int size : SIZES) {
            var wide = GatePicture.of(draw(200, 100, (x, y) -> GREEN), size);
            assertFalse(wide.enlarged());
            assertDoor(wide);
            for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
                if (!opening(size, u, v)) assertEquals(v < size / 2, wide.at(u, v) != null, "wide at " + u + "," + v);
            assertEquals("lime_concrete", wide.at(0, 0));

            var tall = GatePicture.of(draw(100, 200, (x, y) -> GREEN), size);
            assertDoor(tall);
            // Half the width, rounded outwards to whole columns on both sides alike.
            int columns = size / 2 % 2 == 0 ? size / 2 : size / 2 + 1, first = (size - columns) / 2;
            for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
                if (!opening(size, u, v)) assertEquals(u >= first && u < first + columns, tall.at(u, v) != null, "tall at " + u + "," + v);
        }
    }

    @Test void nothingVisibleGivesAnEmptyPictureWithoutADoor() {
        for (int size : SIZES) {
            for (var icon : new BufferedImage[]{new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB),
                    draw(64, 64, (x, y) -> 0x19ffffff), draw(1, 1, (x, y) -> CLEAR)}) {
                var picture = GatePicture.of(icon, size);
                assertTrue(picture.isEmpty());
                for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) assertNull(picture.at(u, v));
            }
        }
        // Half opaque is solid.
        assertFalse(GatePicture.of(draw(64, 64, (x, y) -> 0x80ffffff), 12).isEmpty());
        // A hairline covers no half cell.
        assertTrue(GatePicture.of(draw(1, 200, (x, y) -> RED), 12).isEmpty());
    }

    @Test void theCutKeepsWhatIsAtLeastTwelvePercentOpaque() {
        IntBinaryOperator square = (x, y) -> x >= 20 && x < 40 && y >= 30 && y < 40 ? RED : CLEAR;
        var cut = GatePicture.cut(draw(64, 64, square));
        assertEquals(20, cut.getWidth()); assertEquals(10, cut.getHeight());
        assertEquals(RED, cut.getRGB(0, 0));
        // 30 of 255 is under 12%, 31 is over.
        var faint = GatePicture.cut(draw(64, 64, (x, y) -> square.applyAsInt(x, y) == RED ? RED : 0x1effffff));
        assertEquals(20, faint.getWidth()); assertEquals(10, faint.getHeight());
        var visible = GatePicture.cut(draw(64, 64, (x, y) -> square.applyAsInt(x, y) == RED ? RED : 0x1fffffff));
        assertEquals(64, visible.getWidth()); assertEquals(64, visible.getHeight());
        assertNull(GatePicture.cut(new BufferedImage(8, 8, BufferedImage.TYPE_INT_ARGB)));
    }

    @Test void aLoosePixelIsDroppedAndOneTouchingAtACornerStays() {
        for (int size : SIZES) {
            int cell = 10, side = size * cell;
            // Rows count from the top here: a 4 x 4 block in the bottom left corner, one cell touching it at its
            // corner, and one cell alone in the top right corner.
            var icon = draw(side, side, (x, y) -> {
                int u = x / cell, v = size - 1 - y / cell;
                return (u < 4 && v < 4) || (u == 4 && v == 4) || (u == size - 1 && v == size - 1) ? RED : CLEAR;
            });
            var picture = GatePicture.of(icon, size);
            assertNull(picture.at(size - 1, size - 1), "the loose cell");
            assertEquals("red_wool", picture.at(4, 4), "the cell touching at a corner");
            assertEquals("red_wool", picture.at(0, 0));
            assertNull(picture.at(5, 5));
            assertDoor(picture);
        }
        var cells = new String[]{
                "a", null, null, null,
                null, null, null, "b",
                null, null, "c", null,
                null, null, null, null};
        GatePicture.tidy(cells, 4);
        assertArrayEquals(new String[]{null, null, null, null, null, null, null, "b", null, null, "c", null, null, null, null, null}, cells);
    }

    @Test void aPlainFrontIsOneBlockWithTheDoor() {
        for (int size : SIZES) {
            var picture = GatePicture.plain("light_gray_concrete", size);
            assertDoor(picture);
            assertFalse(picture.isEmpty());
            for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
                assertEquals(opening(size, u, v) ? null : "light_gray_concrete", picture.at(u, v));
        }
    }

    @Test void oddAndTinySizesAreRefused() {
        assertThrows(IllegalArgumentException.class, () -> GatePicture.plain("stone", 11));
        assertThrows(IllegalArgumentException.class, () -> GatePicture.of(ring(), 4));
        assertDoesNotThrow(() -> GateNumbers.checkSize(GateNumbers.SIZE));
        var defaultPicture = GatePicture.of(ring(), GateNumbers.SIZE);
        assertEquals(GateNumbers.SIZE, defaultPicture.size());
        assertDoor(defaultPicture);
        assertEquals(3, GateNumbers.DEPTH);
    }

    @Test
    void theHashFollowsTheBlocksAndNothingElse() {
        var ring = GatePicture.of(ring(), 12);
        assertEquals(ring.hash(), GatePicture.of(ring(), 12).hash(), "the same icon gives the same hash");
        // The same picture from another file: a copy twice the size cuts and scales to the same cells.
        var bigger = new BufferedImage(240, 240, BufferedImage.TYPE_INT_ARGB);
        var paint = bigger.createGraphics();
        paint.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
        paint.drawImage(ring(), 0, 0, 240, 240, null);
        paint.dispose();
        var same = GatePicture.of(bigger, 12);
        boolean sameCells = true;
        for (int v = 0; v < 12; v++) for (int u = 0; u < 12; u++) sameCells &= java.util.Objects.equals(ring.at(u, v), same.at(u, v));
        assertEquals(sameCells, ring.hash().equals(same.hash()));
        var hashes = new java.util.HashSet<String>();
        for (int size : SIZES) hashes.add(GatePicture.plain("yellow_concrete", size).hash());
        hashes.add(GatePicture.plain("red_concrete", 12).hash());
        hashes.add(ring.hash());
        assertEquals(SIZES.length + 2, hashes.size(), "size, block and picture each change the hash");
        assertTrue(ring.hash().matches("[0-9a-f]{64}"));
    }
}
