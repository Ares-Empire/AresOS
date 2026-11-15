package dev.aresos.zone;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class GatePaletteTest {
    @Test void holdsTheWallsBlocksAndTheTwelveNewOnes() {
        assertEquals(60, GatePalette.BLOCKS.size());
        assertEquals(60, GatePalette.BLOCKS.stream().map(LogoPixels.Color::block).distinct().count());
        for (int i = 0; i < LogoPixels.PALETTE.size(); i++)
            assertEquals(LogoPixels.PALETTE.get(i).block(), GatePalette.BLOCKS.get(i).block());
        assertEquals(java.util.List.of("red_mushroom_block", "emerald_block", "lapis_block", "amethyst_block", "snow_block",
                        "iron_block", "polished_diorite", "smooth_stone", "smooth_sandstone", "honeycomb_block",
                        "prismarine_bricks", "blue_ice"),
                GatePalette.BLOCKS.subList(48, 60).stream().map(LogoPixels.Color::block).toList());
        assertTrue(GatePalette.BLOCKS.stream().anyMatch(color -> color.block().equals(GatePalette.BLACK)));
    }

    @Test void aPlainBlockIsNearestToItsOwnColourAndStandsInForAPatternedOne() {
        // Plain: the dyed 48, and of the twelve the three with one flat colour.
        var plain = new java.util.ArrayList<String>();
        for (var color : GatePalette.BLOCKS) if (GatePalette.plain(color.block())) plain.add(color.block());
        assertEquals(51, plain.size());
        assertEquals(java.util.List.of("snow_block", "smooth_sandstone", "blue_ice"), plain.subList(48, 51));
        // Seven patterned blocks are never built: the plain block nearest to their own colour is (within 0.06).
        var standIns = Map.of("red_mushroom_block", "red_wool", "emerald_block", "lime_wool", "lapis_block", "blue_concrete",
                "iron_block", "white_concrete", "polished_diorite", "white_concrete", "smooth_stone", "white_concrete",
                "honeycomb_block", "yellow_concrete");
        for (var color : GatePalette.BLOCKS) {
            String built = standIns.getOrDefault(color.block(), color.block());
            assertEquals(built, GatePalette.built(color.block()), color.block());
            assertEquals(built, GatePalette.nearest(color.rgb()), color.block());
        }
        // Two keep their place: no plain block is near amethyst's violet or prismarine's sea green.
        for (String block : new String[]{"amethyst_block", "prismarine_bricks"}) {
            assertFalse(GatePalette.plain(block));
            assertEquals(block, GatePalette.built(block));
        }
        assertEquals(0.06, GatePalette.PATTERN);
        assertThrows(IllegalArgumentException.class, () -> GatePalette.plain("stone"));
        assertThrows(IllegalArgumentException.class, () -> GatePalette.built("stone"));
    }

    @Test void referenceColoursKeepTheirHue() {
        // Pure red and the well-known reds stay red, in a plain block: red wool stands in for the spotted red
        // mushroom block. Plain RGB distance made them orange.
        for (int red : new int[]{0xff0000, 0xea4335, 0xe60023}) {
            assertEquals("red_wool", GatePalette.nearest(red));
            assertEquals("orange_concrete", LogoPixels.nearest(0xff0000), "the wall's match is not this package's to change");
        }
        var expected = Map.ofEntries(
                Map.entry(0xfbbc05, "yellow_wool"), Map.entry(0x34a853, "lime_concrete"), Map.entry(0x4285f4, "blue_ice"),
                // A bright green stays green instead of turning cyan; lime wool stands in for the emerald block.
                Map.entry(0x1db954, "lime_wool"), Map.entry(0x25d366, "lime_wool"),
                // No block is this blue-purple; it comes out blue (HUB.md 2.3).
                Map.entry(0x5865f2, "blue_wool"),
                Map.entry(0xffffff, "snow_block"), Map.entry(0x000000, "black_concrete"),
                // A light grey stays grey instead of the pinkish white terracotta; white concrete (a light grey)
                // stands in for polished diorite.
                Map.entry(0xc0c0c0, "white_concrete"), Map.entry(0x808080, "light_gray_concrete"),
                // Yellow concrete stands in for the honeycomb block.
                Map.entry(0xff9900, "yellow_concrete"), Map.entry(0xff6600, "orange_wool"),
                Map.entry(0x9146ff, "purple_wool"), Map.entry(0x0000ff, "blue_wool"), Map.entry(0xffff00, "yellow_wool"));
        expected.forEach((rgb, block) -> assertEquals(block, GatePalette.nearest(rgb), String.format("0x%06x", rgb)));
    }

    @Test void theNextNearestBlocksFollowInOrderWithoutThePatternedOnes() {
        for (int rgb : new int[]{0xff0000, 0xffffff, 0x1db954, 0x808080, 0x5865f2}) {
            var order = GatePalette.nearestFirst(rgb);
            assertEquals(GatePalette.nearest(rgb), order.getFirst());
            assertEquals(order.size(), order.stream().distinct().count());
            // The 51 plain blocks and the two patterned ones that are still built.
            assertEquals(53, order.size());
            for (String block : order) assertEquals(block, GatePalette.built(block));
        }
        assertEquals(java.util.List.of("red_wool", "orange_concrete"), GatePalette.nearestFirst(0xff0000).subList(0, 2));
    }

    @Test void oklabMatchesItsPublishedReferenceValues() {
        // White is (1, 0, 0); pure red is (0.628, 0.225, 0.126) in Ottosson's tables.
        assertArrayEquals(new double[]{1, 0, 0}, GatePalette.oklab(0xffffff), 1e-3);
        assertArrayEquals(new double[]{0.628, 0.225, 0.126}, GatePalette.oklab(0xff0000), 1e-3);
        assertEquals(0, GatePalette.distance(0x123456, 0x123456), 1e-12);
        assertEquals(1, GatePalette.distance(0x000000, 0xffffff), 1e-3);
    }
}
