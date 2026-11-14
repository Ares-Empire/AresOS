package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.zone.GateNumbers;
import net.minecraft.core.BlockPos;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The hub's numbers (docs/design/HUB.md 3.1 and 3.2), as data. A restyle changes values here; nothing in this class
 * touches a world or a registry. The four groups, with their avenues and colours, are {@link AppGroup}; the gate's
 * own numbers live in {@link GateNumbers}, so a gate built by hand and a gate of the town are the same size.
 */
public final class HubLayout {
    private HubLayout() { }

    /** Which rules built a hub; saved with it so a later change is noticed. */
    public static final String LOOK = "flat-1";

    public static final int SIZE = GateNumbers.SIZE;
    public static final int DEPTH = GateNumbers.DEPTH;
    public static final int FIRST = 4;
    public static final int PITCH = 14;
    public static final int ROW0 = 20;
    public static final int STEP = 14;
    /** The doorway: columns 5 and 6, heights 0 to 2, two blocks deep. */
    public static final int DOOR_COLUMN = GateNumbers.doorLeft(SIZE);
    public static final int DOOR_WIDTH = GateNumbers.DOOR_WIDTH;
    public static final int DOOR_HEIGHT = GateNumbers.DOOR_HEIGHT;
    public static final int DOOR_DEPTH = GateNumbers.NICHE_DEPTH;
    public static final int EXIT = GateNumbers.EXIT;
    public static final int ROAD = 5;

    /** The block he stands in. "Height 0" is this block's y; the floor is the layer below it. */
    public static final BlockPos HOME = new BlockPos(0, 64, 0);
    public static final float HOME_YAW = 180;
    public static final float HOME_PITCH = -8;

    /** The pad reaches this far from the home block on every side (5 x 5). */
    public static final int PAD_REACH = 2;
    public static final int AVENUE_START = 3;
    public static final String PAVING = "minecraft:polished_blackstone_bricks";
    public static final String HOME_MARK = "minecraft:gold_block";

    public static final int NAME_OUTWARD = 20;
    public static final int NAME_HEIGHT = 9;
    /**
     * 2.5, not the design's 3: with its count a name is up to 103 text pixels wide ("SYSTEM & TOOLS · 14"), which
     * at 3 is 7.7 blocks in the 7 blocks between the two front logos, so its last digit hid inside the logo.
     */
    public static final float NAME_SCALE = 2.5f;
    /** Text displays are seen from 64 blocks times this: 160 blocks. */
    public static final float NAME_VIEW_RANGE = 2.5f;
    /**
     * The plate behind a name, as ARGB: black at three quarters. On the game's default plate (black at one quarter)
     * the names hung over a noon sky at a contrast of 1.4 to 2.5 to 1; light blue on sky blue was the worst.
     */
    public static final int NAME_BACKGROUND = 0xC0000000;

    /** The table of HUB.md 3.1, as it is saved with a hub. */
    public static Map<String, Integer> numbers() {
        var numbers = new LinkedHashMap<String, Integer>();
        numbers.put("size", SIZE);
        numbers.put("depth", DEPTH);
        numbers.put("first", FIRST);
        numbers.put("pitch", PITCH);
        numbers.put("row0", ROW0);
        numbers.put("step", STEP);
        numbers.put("door_column", DOOR_COLUMN);
        numbers.put("door_width", DOOR_WIDTH);
        numbers.put("door_height", DOOR_HEIGHT);
        numbers.put("door_depth", DOOR_DEPTH);
        numbers.put("exit", EXIT);
        numbers.put("road", ROAD);
        return numbers;
    }

    /** The last outward index an avenue is paved to when its group's farthest row in use is {@code row}. */
    public static int avenueEnd(int row) {
        return ROW0 + STEP * row + 4;
    }
}
