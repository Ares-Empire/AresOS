package dev.aresos.zone;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.decoration.BlockAttachedEntity;
import net.minecraft.world.level.block.AmethystBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Fallable;
import net.minecraft.world.level.block.FenceBlock;
import net.minecraft.world.level.block.HalfTransparentBlock;
import net.minecraft.world.level.block.IronBarsBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.TintedGlassBlock;
import net.minecraft.world.level.block.TransparentBlock;
import net.minecraft.world.level.block.WallBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.io.IOException;
import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

/**
 * What a logo may be built next to. Placing a block updates its neighbours, and an update can travel on through
 * a solid block, so anything that could react within reach is refused before the first block changes: trying
 * and rolling back would already have fired ticks, drops and redstone.
 */
final class Neighbors {
    private static final Set<String> REMOVAL_CALLBACKS = Set.of("canSurvive", "updateShape", "neighborChanged",
            "updateIndirectNeighbourShapes", "onPlace", "affectNeighborsAfterRemoval", "tick", "randomTick");

    private static final ClassValue<Boolean> STABLE_ON_REMOVAL = new ClassValue<>() {
        @Override protected Boolean computeValue(Class<?> type) {
            // BlockBehaviour's defaults are no-ops (canSurvive returns true). Inspect every subclass so an
            // unfamiliar override cannot inherit permission just because it extends an ordinary slab or pillar.
            for (Class<?> owner = type; owner != BlockBehaviour.class; owner = owner.getSuperclass())
                for (var method : owner.getDeclaredMethods()) {
                    if (!REMOVAL_CALLBACKS.contains(method.getName())) continue;
                    // Verified in 26.2: these updateShape implementations only schedule water when wet and
                    // recompute connections/corners. The fluid guard below excludes the scheduling branch.
                    if (method.getName().equals("updateShape") && (owner == SlabBlock.class || owner == StairBlock.class
                            || owner == WallBlock.class || owner == FenceBlock.class || owner == IronBarsBlock.class)) continue;
                    return false;
                }
            return true;
        }
    };

    private Neighbors() { }

    static Block block(String name) { return BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(name)); }

    /** Every block inspected, plus the full boxes used for entity queries. No world access. */
    static Set<BlockPos> footprint(Collection<BlockPos> around, int reach) {
        var cells = new LinkedHashSet<BlockPos>();
        for (var cell : around) for (int x = -reach; x <= reach; x++) for (int y = -reach; y <= reach; y++) for (int z = -reach; z <= reach; z++)
            if (Math.abs(x) + Math.abs(y) + Math.abs(z) <= reach || Math.max(Math.max(Math.abs(x), Math.abs(y)), Math.abs(z)) <= 1)
                cells.add(cell.offset(x, y, z));
        return cells;
    }

    /**
     * Refuses when something that could react stands within {@code reach} face-steps of a cell in {@code around}.
     * Cells in {@code changing} are the build's own and are not looked at.
     */
    static void check(ServerLevel level, Set<BlockPos> changing, Collection<BlockPos> around, int reach) throws IOException {
        check(level, changing, around, reach, false);
    }

    /** Retained blocks need no full-cube shape, but must survive neighbour updates without side effects. */
    static void checkRemoval(ServerLevel level, Set<BlockPos> changing) throws IOException {
        check(level, changing, changing, 2, true);
    }

    private static void check(ServerLevel level, Set<BlockPos> changing, Collection<BlockPos> around, int reach, boolean removal) throws IOException {
        var signs = signs(level.getServer());
        var owned = owned(level);
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
            if (inert(level, pos, state, ours) || removal && stableOnRemoval(state)) continue;
            throw new IOException("Logo could disturb neighboring " + BuiltInRegistries.BLOCK.getKey(state.getBlock()) + " at " + pos.toShortString()
                    + ". No blocks changed. Leave two cells clear of plants, circuits, fluids and blocks with special behavior, then retry.");
        }
    }

    /** The signs of every gate the mod built: by hand ({@code zones.dat}) and in the town ({@code hub.dat}). */
    static Set<UUID> signs(net.minecraft.server.MinecraftServer server) {
        var signs = new HashSet<>(ZoneData.get(server).signs());
        var hub = dev.aresos.hub.HubData.get(server);
        if (hub != null) signs.addAll(hub.signs());
        return signs;
    }

    /** Every block the mod recorded in this dimension: gates built by hand, and the flat home's pad, roads and town. */
    private static java.util.Map<BlockPos, String> owned(ServerLevel level) {
        var owned = ZoneData.get(level.getServer()).gateBlocks(level.dimension());
        var hub = dev.aresos.hub.HubData.get(level.getServer());
        if (hub != null) owned.putAll(hub.blocks(level.dimension()));
        return owned;
    }

    private static boolean stableOnRemoval(BlockState state) {
        // A light needs no support and survives anywhere, so nothing hangs on its neighbours: a gate's light that he
        // changed (its level, or water in it) is his and stays, and it must not hold the gate up (package 36). Water he
        // put in it already runs out on its open sides and only reaches the freed cells too; package 33 treats the
        // lights it still owns the same way (inert, below).
        if (state.is(Blocks.LIGHT)) return true;
        return state.getFluidState().isEmpty() && !state.hasBlockEntity() && !state.isSignalSource()
                && !state.isRandomlyTicking() && !(state.getBlock() instanceof Fallable)
                && STABLE_ON_REMOVAL.get(state.getBlock().getClass());
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
        if ((type == Block.class || type == AmethystBlock.class || type == HalfTransparentBlock.class
                || type == TransparentBlock.class || type == TintedGlassBlock.class) && !state.isRandomlyTicking()) return true;
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
