package dev.aresos.zone;

import dev.aresos.config.AppDefinition;
import dev.aresos.world.HomeSites;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.AABB;

import javax.imageio.ImageIO;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class LogoBuilder {
    public record Plan(AppZone zone, Map<BlockPos, BlockState> blocks) { }
    private LogoBuilder() { }

    public static LogoPixels.Image readIcon(AppDefinition app) throws IOException {
        if (app.icon() == null) throw new IOException("No source icon. Add a local PNG icon path to this app in apps.json, then restart.");
        var source = ImageIO.read(Path.of(app.icon()).toFile());
        if (source == null) throw new IOException("Source icon is not a readable image.");
        return LogoPixels.convert(source);
    }

    public static Plan plan(ServerPlayer player, String app, LogoPixels.Image image, boolean floor) {
        var forward = player.getDirection();
        var right = forward.getClockWise();
        // Four cells leave the entire return body outside the two-cell approach, even at a block's edge.
        var origin = player.blockPosition().relative(forward, 4);
        var blocks = new LinkedHashMap<BlockPos, BlockState>();
        var all = new java.util.ArrayList<BlockPos>();
        for (int y = 0; y < image.height(); y++) for (int x = 0; x < image.width(); x++) {
            var pos = origin.relative(right, x - image.width() / 2);
            all.add(floor ? pos.below().relative(forward, image.height() - 1 - y) : pos.above(image.height() - 1 - y));
        }
        for (var pixel : image.pixels()) {
            var pos = all.get(pixel.y() * image.width() + pixel.x());
            blocks.put(pos, BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(pixel.block())).defaultBlockState());
        }
        BlockPos min = new BlockPos(all.stream().mapToInt(BlockPos::getX).min().orElseThrow(),
                all.stream().mapToInt(BlockPos::getY).min().orElseThrow(), all.stream().mapToInt(BlockPos::getZ).min().orElseThrow());
        BlockPos max = new BlockPos(all.stream().mapToInt(BlockPos::getX).max().orElseThrow(),
                all.stream().mapToInt(BlockPos::getY).max().orElseThrow(), all.stream().mapToInt(BlockPos::getZ).max().orElseThrow());
        BlockPos zoneMin, zoneMax;
        if (floor) { zoneMin = min.above(); zoneMax = max.above(2); }
        else {
            var a = min.relative(forward.getOpposite(), 1); var b = max.relative(forward.getOpposite(), 2);
            zoneMin = new BlockPos(Math.min(a.getX(), b.getX()), min.getY(), Math.min(a.getZ(), b.getZ()));
            zoneMax = new BlockPos(Math.max(a.getX(), b.getX()), max.getY(), Math.max(a.getZ(), b.getZ()));
        }
        var box = new AABB(zoneMin.getX(), zoneMin.getY(), zoneMin.getZ(), zoneMax.getX() + 1, zoneMax.getY() + 1, zoneMax.getZ() + 1);
        return new Plan(new AppZone(UUID.randomUUID().toString(), app, player.level().dimension(), zoneMin, zoneMax,
                AppZone.exit(player.level().dimension(), player.position(), box), List.copyOf(blocks.keySet())), blocks);
    }

    public static void build(ServerPlayer player, Plan plan) throws IOException {
        var level = player.level();
        var data = ZoneData.get(level.getServer());
        String conflict = data.conflict(plan.zone);
        if (conflict != null) throw new IOException(conflict);
        if (plan.blocks.isEmpty()) throw new IOException("Icon is fully transparent; no logo built.");
        if (!HomeSites.isSafe(level, plan.zone.exit().position())) throw new IOException("Stand on safe solid ground to save the exit point.");
        // Inspect the whole face and approach before placing anything, including transparent holes.
        AABB area = plan.zone.box();
        for (var pos : plan.blocks.keySet()) area = area.minmax(new AABB(pos));
        for (var pos : BlockPos.betweenClosed(BlockPos.containing(area.minX, area.minY, area.minZ),
                BlockPos.containing(area.maxX - 1, area.maxY - 1, area.maxZ - 1))) {
            if (pos.getY() < level.getMinY() || pos.getY() >= level.getMaxY() || !level.getWorldBorder().isWithinBounds(pos))
                throw new IOException("Logo would be outside the build limits or world border.");
            if (!level.getBlockState(pos).isAir())
                throw new IOException("Area isn't clear at " + pos.toShortString() + ". No blocks changed. Clear the face and zone in Build mode, then retry; overwrite is not supported.");
        }
        for (var pos : plan.blocks.keySet()) if (!level.getEntities(null, new AABB(pos)).isEmpty())
            throw new IOException("An entity occupies the logo. Move it away, then retry.");
        checkNeighbors(player, plan);
        for (var block : plan.blocks.entrySet()) level.setBlockAndUpdate(block.getKey(), block.getValue());
        data.add(plan.zone);
    }

    private static void checkNeighbors(ServerPlayer player, Plan plan) throws IOException {
        var level = player.level();
        var checked = new java.util.HashSet<BlockPos>();
        // Updates can reach a circuit through an adjacent solid block. Refuse special behavior within two cells;
        // speculative placement/rollback would already have fired ticks, drops and redstone side effects.
        for (var pixel : plan.blocks.keySet()) for (int x = -2; x <= 2; x++) for (int y = -2; y <= 2; y++) for (int z = -2; z <= 2; z++) {
            if (Math.abs(x) + Math.abs(y) + Math.abs(z) > 2) continue;
            var pos = pixel.offset(x, y, z);
            if (plan.blocks.containsKey(pos) || !checked.add(pos)) continue;
            var state = level.getBlockState(pos);
            if (state.isAir()) continue;
            // Plain full blocks have no survival/support/neighbor callbacks. Unknown block behavior is refused.
            if (state.getBlock().getClass() == Block.class && state.isCollisionShapeFullBlock(level, pos)
                    && state.getFluidState().isEmpty() && !state.isRandomlyTicking() && !state.isSignalSource() && !state.hasBlockEntity()) continue;
            throw new IOException("Logo could disturb neighboring " + BuiltInRegistries.BLOCK.getKey(state.getBlock()) + " at " + pos.toShortString()
                    + ". No blocks changed. Leave two cells clear of plants, circuits, fluids and blocks with special behavior, then retry.");
        }
    }
}
