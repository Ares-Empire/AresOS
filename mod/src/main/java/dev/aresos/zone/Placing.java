package dev.aresos.zone;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;

import java.util.Optional;

/**
 * The one way the mod changes a block it builds or takes down (HUB.md 3.4): the flat home's pad and roads, the
 * town's logos and the gates he builds with {@code /aresos logo} all go through {@link #set}. The rule lives here and
 * nowhere else:
 * <ul>
 *   <li>Where the mod's record holds no block, it places only on untouched ground: air, or grass or dirt with air
 *       above it. Anything else is his. A caller may ask for less (the pad goes on grass only), never for more.</li>
 *   <li>Where the record holds a block, it replaces or removes it only while that block still stands there.</li>
 * </ul>
 * It returns what it did, which the caller records: the hub in {@code hub.dat}, a hand-built gate in
 * {@code zones.dat}. A block he changes is his for good: the hub's record forgets it the moment it changes
 * ({@code HubData.blockChanged}), and a removal skips it because it is no longer the recorded block.
 */
public final class Placing {
    /** One block the mod set: where, the block it placed and the block that stood there before, as block IDs. */
    public record Change(BlockPos pos, String block, String before) { }

    private Placing() { }

    /**
     * Sets {@code next} at {@code pos}, if the mod may. {@code recorded} is the block the mod's record says stands
     * there, or null when the record holds none. Returns the change, or empty when the block is not the mod's to
     * change: then nothing happened.
     */
    public static Optional<Change> set(ServerLevel level, BlockPos pos, String recorded, BlockState next, int flags) {
        var state = level.getBlockState(pos);
        if (recorded == null ? !untouched(level, pos, state) : !still(state, recorded)) return Optional.empty();
        if (!level.setBlock(pos, next, flags) && !state.equals(next)) return Optional.empty();
        return Optional.of(new Change(pos.immutable(), id(next), id(state)));
    }

    /** {@link #set} with every update a placed block normally causes. */
    public static Optional<Change> set(ServerLevel level, BlockPos pos, String recorded, BlockState next) {
        return set(level, pos, recorded, next, Block.UPDATE_ALL);
    }

    /** Air, or open ground the world was made of: grass or dirt with nothing standing on it. */
    public static boolean untouched(ServerLevel level, BlockPos pos, BlockState state) {
        if (state.isAir()) return true;
        return (state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.DIRT)) && level.getBlockState(pos.above()).isAir();
    }

    /**
     * True while the block in the world is the one the mod recorded: the same block, and a light still at full level
     * and dry, as the mod places them (a changed level or water in it is his edit). Other properties, such as a
     * mushroom block's faces, follow the neighbours and are not his edits.
     */
    public static boolean still(BlockState state, String recorded) {
        return id(state).equals(recorded) && (!state.is(Blocks.LIGHT)
                || state.getValue(LightBlock.LEVEL) == LightBlock.MAX_LEVEL && !state.getValue(LightBlock.WATERLOGGED));
    }

    /** A block's ID as the records save it, for example {@code minecraft:gold_block}. */
    public static String id(BlockState state) { return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString(); }

    /** The plain state of a recorded block ID; air for an ID this game does not know. */
    public static BlockState state(String id) {
        return Optional.ofNullable(Identifier.tryParse(id)).flatMap(BuiltInRegistries.BLOCK::getOptional).orElse(Blocks.AIR).defaultBlockState();
    }
}
