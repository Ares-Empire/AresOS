package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;

import java.util.Objects;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.stream.IntStream;
import java.util.stream.Stream;

/**
 * A place for one logo in the flat home (HUB.md 3.2): its group, its row {@code r} counted outward from 0, its side
 * as he sees it from home looking outward, and {@code k}, counted from the road (0 to r). Written {@code N0L0},
 * {@code S2R1}. Plain data: from a place to the gate's origin and facing, and so to every block through
 * {@link GatePlan}.
 */
public record Place(AppGroup group, int row, Side side, int k) {
    /** Left or right of the road, as he sees it from home looking outward. */
    public enum Side { L, R }

    /**
     * Rows 0 to 63. Far past any real town (a hundred apps fill rows 0 to 5; these are 4160 places a group, the
     * last 900 blocks out), and it keeps every coordinate small and the search for a free place finite even when
     * every place of a group is blocked.
     */
    public static final int ROWS = 64;
    private static final Pattern NAME = Pattern.compile("([A-Z])(0|[1-9][0-9]{0,2})([LR])(0|[1-9][0-9]{0,2})");

    public Place {
        Objects.requireNonNull(group, "group");
        Objects.requireNonNull(side, "side");
        if (row < 0 || row >= ROWS || k < 0 || k > row)
            throw new IllegalArgumentException("No such place: row " + row + ", k " + k);
    }

    /** The place's name, for example {@code N0L0}: as it is saved with the app and said in the chat. */
    public String name() { return "" + group.letter() + row + side + k; }

    @Override public String toString() { return name(); }

    /**
     * The place as he reads it in the chat (HUB.md 2.6), for example "Games, east, front row, left" or "Work & Media,
     * west, row 2, right, 2nd from the road": the group's title, its direction, the row counted from 1 ("front row"
     * for the first), the side as he sees it walking out from home, and, past the first logo beside the road, how
     * far from the road. The one wording of a place: {@code /apps}, {@code /go} and the commands that move logos say
     * it this way.
     */
    public String words() {
        String words = group.title() + ", " + group.outward().getSerializedName() + ", "
                + (row == 0 ? "front row" : "row " + (row + 1)) + ", " + (side == Side.L ? "left" : "right");
        return k == 0 ? words : words + ", " + ordinal(k + 1) + " from the road";
    }

    /** 2nd, 3rd, 4th … 11th, 12th, 13th … 21st, 22nd. */
    static String ordinal(int number) {
        int tens = number % 100;
        String suffix = tens >= 11 && tens <= 13 ? "th" : switch (number % 10) {
            case 1 -> "st";
            case 2 -> "nd";
            case 3 -> "rd";
            default -> "th";
        };
        return number + suffix;
    }

    /**
     * Where he stands to walk into the logo here (HUB.md 3.2): on the ground in the middle of the block {@code EXIT}
     * in front of the front layer, on the doorway's centre line, looking outward at pitch -10. The same point as the
     * exit of the gate built here, whatever its picture.
     */
    public NetherHome.Home exit(ResourceKey<Level> dimension, BlockPos home) {
        return plan(GatePicture.plain(GatePalette.name(group.concrete()), HubLayout.SIZE), dimension, home, "?", null).exit();
    }

    /** The place a name stands for; empty for anything else, including names with leading zeros. */
    public static Optional<Place> parse(String name) {
        if (name == null) return Optional.empty();
        var match = NAME.matcher(name);
        if (!match.matches()) return Optional.empty();
        var group = AppGroup.ofLetter(match.group(1).charAt(0));
        int row = Integer.parseInt(match.group(2)), k = Integer.parseInt(match.group(4));
        if (group.isEmpty() || row >= ROWS || k > row) return Optional.empty();
        return Optional.of(new Place(group.get(), row, Side.valueOf(match.group(3)), k));
    }

    /**
     * The places of a group, nearest first (HUB.md 3.3): by row, then by {@code k}, then L before R. For north:
     * N0L0, N0R0, N1L0, N1R0, N1L1, N1R1, N2L0 … It runs to the last of the {@link #ROWS} rows.
     */
    public static Stream<Place> inOrder(AppGroup group) {
        return IntStream.range(0, ROWS).boxed().flatMap(row -> IntStream.rangeClosed(0, row).boxed()
                .flatMap(k -> Stream.of(new Place(group, row, Side.L, k), new Place(group, row, Side.R, k))));
    }

    /** Outward, the front layer of the place's logo: {@code a0 = ROW0 + STEP x r}. The logo fills a0 to a0 + 2. */
    public int front() { return HubLayout.ROW0 + HubLayout.STEP * row; }

    /**
     * Sideways, the logo's column 0 (his left as he looks at its front): {@code FIRST + PITCH x k} on side R and
     * {@code -(FIRST + PITCH x k + SIZE - 1)} on side L. Column u is this plus u.
     */
    public int sideways() {
        int near = HubLayout.FIRST + HubLayout.PITCH * k;
        return side == Side.R ? near : -(near + HubLayout.SIZE - 1);
    }

    /** The gate's origin: the block of column 0, row 0 in its front layer, for a home block {@code home}. */
    public BlockPos origin(BlockPos home) { return group.block(home, front(), sideways(), 0); }

    /** Every logo faces home: he walks into it looking outward, along the group's avenue. */
    public Direction facing() { return group.outward(); }

    /**
     * The gate that stands here: the picture at the place's origin and facing, with its doormat in the group's
     * concrete. The picture must be {@link HubLayout#SIZE} cells a side, the size the places are laid out for.
     */
    public GatePlan plan(GatePicture picture, ResourceKey<Level> dimension, BlockPos home, String name, String shortName) {
        if (picture.size() != HubLayout.SIZE)
            throw new IllegalArgumentException("Places are laid out for logos of " + HubLayout.SIZE + ", not " + picture.size());
        return GatePlan.of(picture, dimension, origin(home), facing(), name, shortName, GatePalette.name(group.concrete()));
    }
}
