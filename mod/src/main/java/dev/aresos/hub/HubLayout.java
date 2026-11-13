package dev.aresos.hub;

import net.minecraft.core.BlockPos;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The hub's numbers and its four groups (docs/design/HUB.md 3.1 and 3.2), as data.
 * A restyle changes values here; nothing in this class touches a world or a registry.
 */
public final class HubLayout {
    private HubLayout() { }

    /** Which rules built a hub; saved with it so a later change is noticed. */
    public static final String LOOK = "flat-1";

    public static final int SIZE = 12;
    public static final int DEPTH = 3;
    public static final int FIRST = 4;
    public static final int PITCH = 14;
    public static final int ROW0 = 20;
    public static final int STEP = 14;
    /** The doorway: columns 5 and 6, heights 0 to 2, two blocks deep. */
    public static final int DOOR_COLUMN = 5;
    public static final int DOOR_WIDTH = 2;
    public static final int DOOR_HEIGHT = 3;
    public static final int DOOR_DEPTH = 2;
    public static final int EXIT = 6;
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
    public static final float NAME_SCALE = 3;
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

    /** One avenue and its apps. Outward and right are seen from home; yaw looks outward. */
    public enum Group {
        N("Internet", 0, -1, 1, 0, 180, "minecraft:light_blue_concrete", 0x3AB3DA),
        // Text colours are the concretes' dye colours, except red and purple: those two dyes are too dark to read
        // on the dark plate (2 to 1), so their names use a lighter tint of the same hue (above 4 to 1).
        E("Games", 1, 0, 0, 1, -90, "minecraft:red_concrete", 0xFF6257),
        S("System & Tools", 0, 1, -1, 0, 0, "minecraft:yellow_concrete", 0xFED83D),
        W("Work & Media", -1, 0, 0, -1, 90, "minecraft:purple_concrete", 0xC774F2);

        private final String title;
        private final int outwardX, outwardZ, rightX, rightZ;
        private final float yaw;
        private final String concrete;
        private final int colour;

        Group(String title, int outwardX, int outwardZ, int rightX, int rightZ, float yaw, String concrete, int colour) {
            this.title = title;
            this.outwardX = outwardX;
            this.outwardZ = outwardZ;
            this.rightX = rightX;
            this.rightZ = rightZ;
            this.yaw = yaw;
            this.concrete = concrete;
            this.colour = colour;
        }

        /** The group's name as he reads it, for example "System & Tools". */
        public String title() { return title; }
        public float yaw() { return yaw; }
        /** The block ID of the group's concrete: the avenue's centre line and, later, the doormats. */
        public String concrete() { return concrete; }
        /** The group's colour for text, as RGB. */
        public int colour() { return colour; }

        /** "Outward a, sideways b, height h": the block {@code home + outward x a + right x b}, h above home's y. */
        public BlockPos block(BlockPos home, int outward, int sideways, int height) {
            return home.offset(outwardX * outward + rightX * sideways, height, outwardZ * outward + rightZ * sideways);
        }
    }
}
