package dev.aresos.zone;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Fallable;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.io.IOException;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * What a logo may be built next to. Placing a block updates its neighbours, and an update can travel on through
 * a solid block, so anything that could react within reach is refused before the first block changes: trying
 * and rolling back would already have fired ticks, drops and redstone.
 */
final class Neighbors {
    /** Blocks the mod itself places that are not plain: three of the gate's palette, and the hidden light. */
    private static final Set<Block> OWN = java.util.stream.Stream.concat(
            GatePalette.BLOCKS.stream().map(color -> block(color.block())), java.util.stream.Stream.of(Blocks.LIGHT))
            .collect(Collectors.toUnmodifiableSet());

    private Neighbors() { }

    static Block block(String name) { return BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(name)); }

    /**
     * Refuses when something that could react stands within {@code reach} face-steps of a cell in {@code around}.
     * Cells in {@code changing} are the build's own and are not looked at.
     */
    static void check(ServerLevel level, Set<BlockPos> changing, Collection<BlockPos> around, int reach) throws IOException {
        var checked = new HashSet<BlockPos>();
        for (var cell : around) for (int x = -reach; x <= reach; x++) for (int y = -reach; y <= reach; y++) for (int z = -reach; z <= reach; z++) {
            if (Math.abs(x) + Math.abs(y) + Math.abs(z) > reach) continue;
            var pos = cell.offset(x, y, z);
            if (changing.contains(pos) || !checked.add(pos)) continue;
            var state = level.getBlockState(pos);
            if (inert(level, pos, state)) continue;
            throw new IOException("Logo could disturb neighboring " + BuiltInRegistries.BLOCK.getKey(state.getBlock()) + " at " + pos.toShortString()
                    + ". No blocks changed. Leave two cells clear of plants, circuits, fluids and blocks with special behavior, then retry.");
        }
    }

    /** Air, a plain full block, a block the mod itself builds with, or untouched ground. Anything unknown is refused. */
    static boolean inert(ServerLevel level, BlockPos pos, BlockState state) {
        if (state.isAir()) return true;
        if (!state.getFluidState().isEmpty() || state.hasBlockEntity() || state.isSignalSource()) return false;
        if (OWN.contains(state.getBlock())) return true;
        if (!state.isCollisionShapeFullBlock(level, pos) || state.getBlock() instanceof Fallable) return false;
        // Plain full blocks have no survival, support or neighbour callbacks.
        if (state.getBlock().getClass() == Block.class && !state.isRandomlyTicking()) return true;
        return ground(level, pos, state);
    }

    /**
     * The ground the world is made of: grass, dirt, stone, netherrack and their kin. It reacts to nothing a logo
     * does next to it. Grass right under a logo turns to dirt in time, as under any block.
     */
    static boolean ground(ServerLevel level, BlockPos pos, BlockState state) {
        return state.isCollisionShapeFullBlock(level, pos) && state.getFluidState().isEmpty() && !state.hasBlockEntity()
                && (state.is(BlockTags.SUBSTRATE_OVERWORLD) || state.is(BlockTags.BASE_STONE_OVERWORLD)
                || state.is(BlockTags.BASE_STONE_NETHER) || state.is(BlockTags.NYLIUM));
    }

    /** The first entity inside one of the cells, other than a gate's sign; null when they are all free. */
    static Entity occupant(ServerLevel level, Collection<BlockPos> cells, Set<UUID> signs) {
        for (var pos : cells) {
            var inside = level.getEntities((Entity)null, new AABB(pos), entity -> !signs.contains(entity.getUUID()));
            if (!inside.isEmpty()) return inside.getFirst();
        }
        return null;
    }
}
