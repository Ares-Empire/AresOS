package dev.aresos.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;

/** The survey's flat-ground, air-pocket, lava-view and distance scoring on fully generated terrain. */
public final class HomeSites {
    private HomeSites() { }

    private record Candidate(NetherHome.Site site, double score) { }

    public static NetherHome.Site find(ServerLevel level) throws IOException {
        // Features can write into adjacent chunks. Finish them in a fixed order, including a halo,
        // before promoting the entire sampled area (-160..160) to FULL or reading any scores.
        for (int x = -11; x <= 11; x++) for (int z = -11; z <= 11; z++) {
            level.getChunk(x, z, ChunkStatus.FEATURES, true);
        }
        for (int x = -10; x <= 10; x++) for (int z = -10; z <= 10; z++) {
            level.getChunk(x, z, ChunkStatus.FULL, true);
        }
        var candidates = new ArrayList<Candidate>();
        for (int x = -96; x <= 96; x += 16) for (int z = -96; z <= 96; z += 16) {
            for (int y = 33; y <= 110; y++) {
                var floor = new BlockPos(x, y, z);
                if (!level.getBlockState(floor).isSolid() || !level.getBlockState(floor.above()).isAir()
                        || !level.getBlockState(floor.above(2)).isAir()) continue;
                int flat = 0, air = 0;
                for (int dx = -6; dx <= 6; dx += 3) for (int dz = -6; dz <= 6; dz += 3) {
                    var sample = floor.offset(dx, 0, dz);
                    if (level.getBlockState(sample).isSolid() && level.getBlockState(sample.above()).isAir()) flat++;
                    for (int h = 1; h <= 8; h++) if (level.getBlockState(sample.above(h)).isAir()) air++;
                }
                int bestLava = 0;
                float yaw = 0;
                int[][] directions = {{0, 1, 0}, {-1, 0, 90}, {0, -1, 180}, {1, 0, -90}};
                for (var direction : directions) {
                    int lava = 0;
                    for (int distance = 16; distance <= 64; distance += 8) for (int across = -16; across <= 16; across += 8) {
                        var sample = new BlockPos(x + direction[0] * distance + direction[1] * across, 31,
                                z + direction[1] * distance + direction[0] * across);
                        if (level.getBlockState(sample).is(Blocks.LAVA) && level.getBlockState(sample.above()).isAir()
                                && level.getBlockState(sample.atY(y + 2)).isAir()) lava++;
                    }
                    if (lava > bestLava) { bestLava = lava; yaw = direction[2]; }
                }
                double score = flat * 4 + air * 0.25 + bestLava * 3 - Math.hypot(x, z) * 0.1;
                candidates.add(new Candidate(new NetherHome.Site(level.getSeed(), x, y, z, yaw), score));
            }
        }
        candidates.sort(Comparator.comparingDouble(Candidate::score).reversed()
                .thenComparingInt(candidate -> candidate.site.x())
                .thenComparingInt(candidate -> candidate.site.z())
                .thenComparingInt(candidate -> candidate.site.y()));
        for (var candidate : candidates) {
            if (isSafe(level, Vec3.atBottomCenterOf(candidate.site.floor().above()))) return candidate.site;
        }
        // An unusual seed may have no sampled ledge. Search nearby columns without carving or placing blocks.
        for (int radius = 0; radius <= 128; radius += 4) for (int x = -radius; x <= radius; x += 4) {
            for (int z = -radius; z <= radius; z += 4) {
                if (Math.abs(x) != radius && Math.abs(z) != radius) continue;
                for (int y = 33; y <= 120; y++) {
                    if (isSafe(level, new Vec3(x + 0.5, y + 1, z + 0.5))) return new NetherHome.Site(level.getSeed(), x, y, z, 0);
                }
            }
        }
        throw new IOException("No safe natural arrival found near (0, 0). Save kept intact; no blocks were changed.");
    }

    public static boolean isSafe(ServerLevel level, Vec3 feet) {
        BlockPos pos = BlockPos.containing(feet);
        if (!level.getWorldBorder().isWithinBounds(pos) || pos.getY() <= level.getMinY() || pos.getY() + 2 >= level.getMaxY()) return false;
        BlockPos below = pos.below();
        if (!level.getBlockState(below).isFaceSturdy(level, below, Direction.UP)
                || level.getBlockState(below).is(Blocks.MAGMA_BLOCK)) return false;
        var body = new AABB(feet.x - 0.3, feet.y, feet.z - 0.3, feet.x + 0.3, feet.y + 1.8, feet.z + 0.3);
        for (BlockPos cell : BlockPos.betweenClosed(BlockPos.containing(body.minX, body.minY, body.minZ),
                BlockPos.containing(body.maxX, body.maxY, body.maxZ))) {
            if (!level.getFluidState(cell).isEmpty() || level.getBlockState(cell).is(BlockTags.FIRE)) return false;
        }
        return level.noCollision(body);
    }
}
