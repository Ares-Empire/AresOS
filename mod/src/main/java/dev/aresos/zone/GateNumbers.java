package dev.aresos.zone;

/**
 * The gate's numbers (HUB.md 3.1 and 3.2), in one place. {@link #SIZE} is the one number that makes every logo
 * wider and taller; 10, 14 and 16 work as well as 12 (the owner's choice, 2026-11-13). The door keeps its size.
 */
public final class GateNumbers {
    /** Logo width and height in blocks. Even, so the two door columns sit in the middle. */
    public static final int SIZE = 12;
    /** Logo thickness in blocks. */
    public static final int DEPTH = 3;
    /** The doorway: 2 wide, 3 high and 2 deep, cut into the bottom middle. One block of the logo stays behind it. */
    public static final int DOOR_WIDTH = 2, DOOR_HEIGHT = 3, NICHE_DEPTH = 2;
    /** The exit block is this many blocks in front of the front layer. */
    public static final int EXIT = 6;
    /** He looks at the door, slightly up. */
    public static final float EXIT_PITCH = -10;
    /** The doormat: the floor under the niche and this many rows in front of it. */
    public static final int DOORMAT_FRONT = 2;
    /** The sign's lower edge above the logo's top, its scale and its widest line in text pixels. */
    public static final double SIGN_GAP = 0.5;
    public static final float SIGN_SCALE = 4;
    public static final int SIGN_LINE_WIDTH = 120;
    /**
     * The sign's plate, as ARGB: three quarters black, as in the design's drawing. On the game's own quarter-black
     * plate the white name is hard to read against a bright sky.
     */
    public static final int SIGN_BACKGROUND = 0xC0000000;
    /** A text display is drawn up to 64 blocks away times this. */
    public static final float SIGN_VIEW_RANGE = 160 / 64f;
    /** The two hidden light blocks stand this many columns in from each edge. */
    public static final int LIGHT_INSET = 2;

    private GateNumbers() { }

    /** The left one of the two door columns, counted from his left as he looks at the front. */
    public static int doorLeft(int size) { return size / 2 - 1; }

    public static void checkSize(int size) {
        if (size < DOOR_WIDTH + 4 || size % 2 != 0)
            throw new IllegalArgumentException("A gate's size must be even and at least " + (DOOR_WIDTH + 4) + ": " + size);
    }
}
