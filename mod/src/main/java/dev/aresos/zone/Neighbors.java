package dev.aresos.zone;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.decoration.BlockAttachedEntity;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Fallable;
import net.minecraft.world.level.block.AmethystBlock;
import net.minecraft.world.level.block.HalfTransparentBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.io.IOException;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * What a logo may be built next to. Placing a block updates its neighbours, and an update can travel on through
 * a solid block, so anything that could react within reach is refused before the first block changes: trying
 * and rolling back would already have fired ticks, drops and redstone.
 */
final class Neighbors {
    private Neighbors() { }

    static Block block(String name) { return BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(name)); }

    /**
     * Refuses when something that could react stands within {@code reach} face-steps of a cell in {@code around}.
     * Cells in {@code changing} are the build's own and are not looked at.
     */
    static void check(ServerLevel level, Set<BlockPos> changing, Collection<BlockPos> around, int reach) throws IOException {
        var signs = ZoneData.get(level.getServer()).signs();
        var owned = ZoneData.get(level.getServer()).gateBlocks(level.dimension());
        for (var cell : around) {
            var entities = level.getEntities((Entity)null, new AABB(cell).inflate(1), entity -> !signs.contains(entity.getUUID())
                    && (entity instanceof BlockAttachedEntity || standsOn(entity, cell)));
            if (!entities.isEmpty()) {
                var entity = entities.getFirst();
                throw new IOException("Logo could disturb " + BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType())
                        + " at " + entity.blockPosition().toShortString() + ". No blocks changed. Move it away, then retry.");
            }
        }
        var checked = new HashSet<BlockPos>();
        for (var cell : around) for (int x = -reach; x <= reach; x++) for (int y = -reach; y <= reach; y++) for (int z = -reach; z <= reach; z++) {
            if (Math.abs(x) + Math.abs(y) + Math.abs(z) > reach) continue;
            var pos = cell.offset(x, y, z);
            if (changing.contains(pos) || !checked.add(pos)) continue;
            var state = level.getBlockState(pos);
            boolean ours = BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString().equals(owned.get(pos));
            if (inert(level, pos, state, ours)) continue;
            throw new IOException("Logo could disturb neighboring " + BuiltInRegistries.BLOCK.getKey(state.getBlock()) + " at " + pos.toShortString()
                    + ". No blocks changed. Leave two cells clear of plants, circuits, fluids and blocks with special behavior, then retry.");
        }
    }

    private static boolean standsOn(Entity entity, BlockPos cell) {
        var body = entity.getBoundingBox();
        return Math.abs(body.minY - (cell.getY() + 1)) < 0.01 && body.maxX > cell.getX() && body.minX < cell.getX() + 1
                && body.maxZ > cell.getZ() && body.minZ < cell.getZ() + 1;
    }

    /** Air, a plain full block, a block the mod itself builds with, or untouched ground. Anything unknown is refused. */
    static boolean inert(ServerLevel level, BlockPos pos, BlockState state, boolean ours) {
        if (state.isAir()) return true;
        // A kept light retains its fluid and has no support to lose when an adjacent logo block disappears.
        if (ours && state.is(Blocks.LIGHT)) return true;
        if (!state.getFluidState().isEmpty() || state.hasBlockEntity() || state.isSignalSource()) return false;
        if (ours) return true;
        if (!state.isCollisionShapeFullBlock(level, pos) || state.getBlock() instanceof Fallable) return false;
        // Plain full blocks have no survival, support or neighbour callbacks.
        var type = state.getBlock().getClass();
        // Checked against 26.2's classes: these two subclasses add sound/rendering, not neighbour behaviour.
        if ((type == Block.class || type == AmethystBlock.class || type == HalfTransparentBlock.class) && !state.isRandomlyTicking()) return true;
        return ground(level, pos, state);
    }

    /**
     * The ground the world is made of: grass, dirt, stone, netherrack and their kin. It reacts to nothing a logo
     * does next to it. Grass decay under a gate is recorded and conditionally restored; other decaying substrates
     * (mycelium and nylium) have no restoration record and are refused.
     */
    static boolean ground(ServerLevel level, BlockPos pos, BlockState state) {
        return state.isCollisionShapeFullBlock(level, pos) && state.getFluidState().isEmpty() && !state.hasBlockEntity()
                && (state.is(Blocks.GRASS_BLOCK) || state.getBlock().getClass() == Block.class && !state.isRandomlyTicking())
                && (state.is(BlockTags.SUBSTRATE_OVERWORLD) || state.is(BlockTags.BASE_STONE_OVERWORLD)
                || state.is(BlockTags.BASE_STONE_NETHER));
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
