package dev.aresos.zone;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.world.NetherHome;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Everything one gate consists of, worked out from a picture, a place and a facing (HUB.md 3.2). Plain data: no
 * player and no world, so the hub can plan gates for places it computes itself and tests can check every block.
 *
 * @param origin       the block of column 0, row 0 in the front layer: the gate's lower left front corner as he
 *                     looks at it. Its height is "height 0"; the floor is the layer below.
 * @param outward      the horizontal direction from him into the gate. Columns count along its clockwise side.
 * @param blocks       every solid block: the logo, the door posts and the niche's black back, by block name
 * @param doormat      the floor blocks under the niche and in front of it, laid in {@code doormatBlock}
 * @param nicheMin     the trigger zone is exactly the niche, {@code nicheMin} to {@code nicheMax}
 */
public record GatePlan(ResourceKey<Level> dimension, BlockPos origin, Direction outward, int size,
                       Map<BlockPos, String> blocks, List<BlockPos> lights, List<BlockPos> doormat, String doormatBlock,
                       BlockPos nicheMin, BlockPos nicheMax, NetherHome.Home exit, Sign sign) {
    /** The text display above the gate: its lower middle point, the app's name and, once apps have one, its short name. */
    public record Sign(Vec3 position, String name, String shortName) {
        /** A blank short name is none (null): the sign shows no second line, and its record reads back the same. */
        public Sign {
            if (shortName != null && shortName.isBlank()) shortName = null;
        }

        /** As a hand-built gate records it ({@link AppZone.Gate#signPlan}). */
        public static final Codec<Sign> CODEC = RecordCodecBuilder.create(i -> i.group(
                Vec3.CODEC.fieldOf("position").forGetter(Sign::position),
                Codec.STRING.fieldOf("name").forGetter(Sign::name),
                Codec.STRING.optionalFieldOf("short_name").forGetter(sign -> Optional.ofNullable(sign.shortName()).filter(name -> !name.isBlank()))
        ).apply(i, (position, name, shortName) -> new Sign(position, name, shortName.orElse(null))));
    }

    public static GatePlan of(GatePicture picture, ResourceKey<Level> dimension, BlockPos origin, Direction outward,
                              String name, String shortName, String doormatBlock) {
        if (outward.getAxis().isVertical()) throw new IllegalArgumentException("A gate faces sideways: " + outward);
        if (picture.isEmpty()) throw new IllegalArgumentException("An empty picture has no gate");
        int size = picture.size(), door = GateNumbers.doorLeft(size);
        var blocks = new LinkedHashMap<BlockPos, String>();
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++) {
            String block = picture.at(u, v);
            boolean opening = v < GateNumbers.DOOR_HEIGHT && u >= door && u < door + GateNumbers.DOOR_WIDTH;
            for (int along = opening ? GateNumbers.NICHE_DEPTH : 0; along < GateNumbers.DEPTH; along++)
                if (opening || block != null) blocks.put(at(origin, outward, along, u, v), opening ? GatePalette.BLACK : block);
        }
        var doormat = new ArrayList<BlockPos>();
        for (int along = -GateNumbers.DOORMAT_FRONT; along < GateNumbers.NICHE_DEPTH; along++)
            for (int u = door; u < door + GateNumbers.DOOR_WIDTH; u++) doormat.add(at(origin, outward, along, u, -1));
        var lights = List.of(at(origin, outward, -1, GateNumbers.LIGHT_INSET, size / 2),
                at(origin, outward, -1, size - 1 - GateNumbers.LIGHT_INSET, size / 2));
        // The doorway's centre line is the edge between the two door columns.
        var right = outward.getClockWise();
        var line = Vec3.atBottomCenterOf(origin).add(Vec3.atLowerCornerOf(right.getUnitVec3i()).scale(door + 0.5));
        var ahead = Vec3.atLowerCornerOf(outward.getUnitVec3i());
        var exit = new NetherHome.Home(dimension, line.subtract(ahead.scale(GateNumbers.EXIT)), yaw(outward), GateNumbers.EXIT_PITCH);
        var sign = new Sign(line.add(0, size + GateNumbers.SIGN_GAP, 0), name, shortName);
        // The niche's two opposite corners; which one is the lower depends on the facing.
        BlockPos near = at(origin, outward, 0, door, 0),
                far = at(origin, outward, GateNumbers.NICHE_DEPTH - 1, door + GateNumbers.DOOR_WIDTH - 1, GateNumbers.DOOR_HEIGHT - 1);
        return new GatePlan(dimension, origin, outward, size, java.util.Collections.unmodifiableMap(blocks), lights,
                List.copyOf(doormat), doormatBlock, BlockPos.min(near, far), BlockPos.max(near, far), exit, sign);
    }

    /**
     * The origin of a gate built for someone standing at {@code feet} and looking along {@code facing}: on his
     * ground, its front layer EXIT blocks ahead, so that the block he stands in is the exit block. The doorway's
     * centre line is a block edge; it is the one nearest to him.
     */
    public static BlockPos originInFrontOf(Vec3 feet, Direction facing, int size) {
        var right = facing.getClockWise();
        var block = BlockPos.containing(feet);
        int sign = right.getStepX() + right.getStepZ();
        long line = Math.round((right.getAxis() == Direction.Axis.X ? feet.x : feet.z) * sign);
        // Column 0's middle lies door + 0.5 columns before the line, counted along `right`.
        int column = (int)Math.floor((line - GateNumbers.doorLeft(size) - 0.5) * sign);
        var front = block.relative(facing, GateNumbers.EXIT);
        return right.getAxis() == Direction.Axis.X ? new BlockPos(column, block.getY(), front.getZ())
                : new BlockPos(front.getX(), block.getY(), column);
    }

    /** The block {@code along} layers behind the front layer (negative: in front), in column u and row v. */
    public BlockPos at(int along, int u, int v) { return at(origin, outward, along, u, v); }

    private static BlockPos at(BlockPos origin, Direction outward, int along, int u, int v) {
        return origin.relative(outward, along).relative(outward.getClockWise(), u).above(v);
    }

    /**
     * The three spaces that must be air before a gate is built (HUB.md 3.3): its whole box, the layer right in
     * front of it, and the way in from there out to the exit block.
     */
    public List<BlockPos> space() {
        var space = new ArrayList<BlockPos>();
        for (int along = -1; along < GateNumbers.DEPTH; along++) for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
            space.add(at(along, u, v));
        int door = GateNumbers.doorLeft(size);
        for (int along = -GateNumbers.EXIT; along < -1; along++) for (int v = 0; v < GateNumbers.DOOR_HEIGHT; v++)
            for (int u = door - 1; u <= door + GateNumbers.DOOR_WIDTH; u++) space.add(at(along, u, v));
        return space;
    }

    /**
     * Air for the rotating name, including its background. Text displays use 0.025 blocks per text pixel.
     * Reserve the full configured line width in every horizontal direction, since the billboard can turn.
     * A line per code point is a conservative height bound even for wrapping and explicit newlines, without
     * importing the client's font machinery into the server plan.
     */
    public List<BlockPos> signSpace() {
        double pixel = 0.025 * GateNumbers.SIGN_SCALE;
        double radius = (GateNumbers.SIGN_LINE_WIDTH + 2) * pixel / 2;
        int lines = Math.max(1, sign.name().codePointCount(0, sign.name().length()));
        if (sign.shortName() != null && !sign.shortName().isBlank()) lines += 1 + sign.shortName().codePointCount(0, sign.shortName().length());
        var min = BlockPos.containing(sign.position().add(-radius, -pixel, -radius));
        var max = BlockPos.containing(sign.position().add(radius, (lines * 10 + 1) * pixel, radius));
        var space = new ArrayList<BlockPos>();
        for (var pos : BlockPos.betweenClosed(min, max)) space.add(pos.immutable());
        return space;
    }

    /** The floor he walks on from the exit block into the niche. */
    public List<BlockPos> walkway() {
        var floor = new ArrayList<BlockPos>();
        int door = GateNumbers.doorLeft(size);
        for (int along = -GateNumbers.EXIT; along < GateNumbers.NICHE_DEPTH; along++)
            for (int u = door; u < door + GateNumbers.DOOR_WIDTH; u++) floor.add(at(along, u, -1));
        return floor;
    }

    /** The complete size by depth floor under the gate, including transparent columns and the niche. */
    public List<BlockPos> floor() {
        var floor = new ArrayList<BlockPos>();
        for (int along = 0; along < GateNumbers.DEPTH; along++) for (int u = 0; u < size; u++) floor.add(at(along, u, -1));
        return floor;
    }

    /** The floor under the doormat and its complete one-block ring, including the row behind the niche. */
    public List<BlockPos> doormatSurround() {
        var floor = new ArrayList<BlockPos>();
        int door = GateNumbers.doorLeft(size);
        for (int along = -GateNumbers.DOORMAT_FRONT - 1; along <= GateNumbers.NICHE_DEPTH; along++)
            for (int u = door - 1; u <= door + GateNumbers.DOOR_WIDTH; u++) floor.add(at(along, u, -1));
        return floor;
    }

    /** The yaw that looks along a direction, as HUB.md 3.2 lists them. */
    private static float yaw(Direction outward) {
        return switch (outward) {
            case NORTH -> 180;
            case EAST -> -90;
            case WEST -> 90;
            default -> 0;
        };
    }
}
