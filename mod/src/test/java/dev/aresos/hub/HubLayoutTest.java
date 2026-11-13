package dev.aresos.hub;

import dev.aresos.hub.HubLayout.Group;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** The coordinates of docs/design/HUB.md 3.1 and 3.2, written out as that document states them. */
class HubLayoutTest {
    private static final BlockPos HOME = HubLayout.HOME;

    @Test
    void numbersAreTheDesignTable() {
        assertEquals(new BlockPos(0, 64, 0), HOME);
        assertEquals(Map.ofEntries(Map.entry("size", 12), Map.entry("depth", 3), Map.entry("first", 4), Map.entry("pitch", 14),
                Map.entry("row0", 20), Map.entry("step", 14), Map.entry("door_column", 5), Map.entry("door_width", 2),
                Map.entry("door_height", 3), Map.entry("door_depth", 2), Map.entry("exit", 6), Map.entry("road", 5)), HubLayout.numbers());
        assertEquals("flat-1", HubLayout.LOOK);
        assertEquals(24, HubLayout.avenueEnd(0));
        assertEquals(38, HubLayout.avenueEnd(1));
    }

    @Test
    void groupsFollowTheDesignTable() {
        assertGroup(Group.N, "Internet", 180, "minecraft:light_blue_concrete");
        assertGroup(Group.E, "Games", -90, "minecraft:red_concrete");
        assertGroup(Group.S, "System & Tools", 0, "minecraft:yellow_concrete");
        assertGroup(Group.W, "Work & Media", 90, "minecraft:purple_concrete");
    }

    @Test
    void outwardAndRightAreSeenFromHome() {
        // North: outward is z - 1, right is east (x + 1). East: x + 1 and south. South: z + 1 and west. West: x - 1 and north.
        assertEquals(new BlockPos(1, 64, -1), Group.N.block(HOME, 1, 1, 0));
        assertEquals(new BlockPos(1, 64, 1), Group.E.block(HOME, 1, 1, 0));
        assertEquals(new BlockPos(-1, 64, 1), Group.S.block(HOME, 1, 1, 0));
        assertEquals(new BlockPos(-1, 64, -1), Group.W.block(HOME, 1, 1, 0));
    }

    @Test
    void avenuesRunFromOutwardThreeToTwentyFour() {
        // The floor is y 63: the first and the last centre block of each avenue, and its two edges.
        assertEquals(new BlockPos(0, 63, -3), Group.N.block(HOME, HubLayout.AVENUE_START, 0, -1));
        assertEquals(new BlockPos(0, 63, -24), Group.N.block(HOME, HubLayout.avenueEnd(0), 0, -1));
        assertEquals(new BlockPos(-2, 63, -24), Group.N.block(HOME, 24, -2, -1));
        assertEquals(new BlockPos(2, 63, -24), Group.N.block(HOME, 24, 2, -1));
        assertEquals(new BlockPos(24, 63, 2), Group.E.block(HOME, 24, 2, -1));
        assertEquals(new BlockPos(-2, 63, 24), Group.S.block(HOME, 24, 2, -1));
        assertEquals(new BlockPos(-24, 63, -2), Group.W.block(HOME, 24, 2, -1));
        assertEquals(5, HubLayout.ROAD);
    }

    @Test
    void groupNamesHangAtOutwardTwentyHeightNine() {
        assertEquals(new BlockPos(0, 73, -20), Group.N.block(HOME, HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT));
        assertEquals(new BlockPos(20, 73, 0), Group.E.block(HOME, HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT));
        assertEquals(new BlockPos(0, 73, 20), Group.S.block(HOME, HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT));
        assertEquals(new BlockPos(-20, 73, 0), Group.W.block(HOME, HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT));
        assertEquals(3f, HubLayout.NAME_SCALE);
    }

    /** Corners of day-one places from the worked table of HUB.md 3.2: they pin left and right for packages 33 and 36. */
    @Test
    void dayOnePlacesLandWhereTheDesignWorkedThemOut() {
        int left = -(HubLayout.FIRST + HubLayout.SIZE - 1);
        // N0L0 (Chrome): x -15 to -4, y 64 to 75, z -22 to -20.
        assertEquals(new BlockPos(-15, 64, -20), Group.N.block(HOME, HubLayout.ROW0, left, 0));
        assertEquals(new BlockPos(-4, 75, -22), Group.N.block(HOME, HubLayout.ROW0 + 2, left + 11, 11));
        // N0R0 (Discord): x 4 to 15.
        assertEquals(new BlockPos(4, 64, -20), Group.N.block(HOME, HubLayout.ROW0, HubLayout.FIRST, 0));
        // E0L0 (Lunar Client): x 20 to 22, z -15 to -4.
        assertEquals(new BlockPos(20, 64, -15), Group.E.block(HOME, HubLayout.ROW0, left, 0));
        assertEquals(new BlockPos(22, 64, -4), Group.E.block(HOME, HubLayout.ROW0 + 2, left + 11, 0));
        // S0L0 (Terminal): x 4 to 15, z 20 to 22. S0R0 (Notepad): x -15 to -4.
        assertEquals(new BlockPos(15, 64, 20), Group.S.block(HOME, HubLayout.ROW0, left, 0));
        assertEquals(new BlockPos(-4, 64, 20), Group.S.block(HOME, HubLayout.ROW0, HubLayout.FIRST, 0));
        // W1R1: x -36 to -34, z -29 to -18.
        int row1 = HubLayout.ROW0 + HubLayout.STEP;
        int second = HubLayout.FIRST + HubLayout.PITCH;
        assertEquals(new BlockPos(-34, 64, -18), Group.W.block(HOME, row1, second, 0));
        assertEquals(new BlockPos(-36, 64, -29), Group.W.block(HOME, row1 + 2, second + 11, 0));
    }

    private static void assertGroup(Group group, String title, float yaw, String concrete) {
        assertEquals(title, group.title());
        assertEquals(yaw, group.yaw());
        assertEquals(concrete, group.concrete());
    }
}
