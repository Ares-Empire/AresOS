package dev.aresos.test;

import net.minecraft.SharedConstants;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.presets.WorldPresets;

import java.util.ArrayList;
import java.util.Comparator;

/** Offline survey using the same noise columns and biome sampler as normal 26.2 worlds. */
public final class NetherSeedSearch {
    record Site(long seed, int x, int y, int z, int yaw, String biome, int flat, int air, int lava, double score) { }

    public static void main(String[] args) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        var registries = VanillaRegistries.createLookup();
        var generator = WorldPresets.createNormalWorldDimensions(registries).get(LevelStem.NETHER).orElseThrow().generator();
        var height = LevelHeightAccessor.create(0, 256);
        var sites = new ArrayList<Site>();
        for (long seed = 0; seed < 64; seed++) {
            var random = RandomState.create(registries, NoiseGeneratorSettings.NETHER, seed);
            for (int x = -96; x <= 96; x += 32) for (int z = -96; z <= 96; z += 32) {
                var biome = generator.getBiomeSource().getNoiseBiome(x >> 2, 10, z >> 2, random.sampler());
                if (!biome.is(Biomes.CRIMSON_FOREST) && !biome.is(Biomes.NETHER_WASTES)) continue;
                var center = generator.getBaseColumn(x, z, height, random);
                int y = -1;
                for (int h = 34; h <= 65; h++) {
                    if (center.getBlock(h).isSolid() && center.getBlock(h + 1).isAir()
                            && center.getBlock(h + 6).isAir()) { y = h; break; }
                }
                if (y < 0) continue;
                int flat = 0, air = 0;
                for (int dx = -6; dx <= 6; dx += 3) for (int dz = -6; dz <= 6; dz += 3) {
                    var column = generator.getBaseColumn(x + dx, z + dz, height, random);
                    if (column.getBlock(y).isSolid() && column.getBlock(y + 1).isAir()) flat++;
                    for (int h = 1; h <= 8; h++) if (column.getBlock(y + h).isAir()) air++;
                }
                int bestLava = 0, yaw = 0;
                int[][] directions = {{0, 1, 0}, {-1, 0, 90}, {0, -1, 180}, {1, 0, -90}};
                for (var direction : directions) {
                    int lava = 0;
                    for (int distance = 16; distance <= 64; distance += 8) for (int across = -16; across <= 16; across += 8) {
                        int sx = x + direction[0] * distance + direction[1] * across;
                        int sz = z + direction[1] * distance + direction[0] * across;
                        var column = generator.getBaseColumn(sx, sz, height, random);
                        if (column.getBlock(31).is(Blocks.LAVA) && column.getBlock(32).isAir()
                                && column.getBlock(y + 2).isAir()) lava++;
                    }
                    if (lava > bestLava) { bestLava = lava; yaw = direction[2]; }
                }
                if (bestLava < 10 || flat < 15 || air < 160) continue;
                double score = flat * 4 + air * 0.25 + bestLava * 3 - Math.hypot(x, z) * 0.1;
                sites.add(new Site(seed, x, y, z, yaw, biome.unwrapKey().orElseThrow().identifier().toString(), flat, air, bestLava, score));
            }
            System.out.println("Surveyed seed " + seed);
        }
        var refined = new ArrayList<Site>();
        for (var site : sites) {
            var random = RandomState.create(registries, NoiseGeneratorSettings.NETHER, site.seed);
            int visible = 0;
            double angle = Math.toRadians(site.yaw);
            double forwardX = -Math.sin(angle), forwardZ = Math.cos(angle);
            double eyeX = site.x + 0.5 + forwardX * 5, eyeZ = site.z + 0.5 + forwardZ * 5;
            var columns = new java.util.HashMap<Long, net.minecraft.world.level.NoiseColumn>();
            for (int distance = 16; distance <= 64; distance += 8) for (int across = -16; across <= 16; across += 8) {
                int tx = (int) Math.round(site.x + forwardX * distance + forwardZ * across);
                int tz = (int) Math.round(site.z + forwardZ * distance - forwardX * across);
                var target = generator.getBaseColumn(tx, tz, height, random);
                if (!target.getBlock(31).is(Blocks.LAVA) || !target.getBlock(32).isAir()) continue;
                boolean clear = true;
                int steps = (int) (Math.hypot(tx + 0.5 - eyeX, tz + 0.5 - eyeZ) * 2);
                for (int step = 1; step < steps; step++) {
                    double t = (double) step / steps;
                    int sx = (int) Math.floor(eyeX + (tx + 0.5 - eyeX) * t);
                    int sz = (int) Math.floor(eyeZ + (tz + 0.5 - eyeZ) * t);
                    int sy = (int) Math.floor(site.y + 2.62 + (32.5 - site.y - 2.62) * t);
                    long key = blockKey(sx, sz);
                    var column = columns.computeIfAbsent(key, ignored -> generator.getBaseColumn(sx, sz, height, random));
                    if (column.getBlock(sy).isSolid()) { clear = false; break; }
                }
                if (clear) visible++;
            }
            if (visible >= 5) {
                System.out.println("VISIBLE seed=" + site.seed + " x=" + site.x + " z=" + site.z + " rays=" + visible);
                refined.add(new Site(site.seed, site.x, site.y, site.z, site.yaw, site.biome,
                        site.flat, site.air, site.lava, site.score + visible * 10));
            }
        }
        var ranked = refined.stream().sorted(Comparator.comparingDouble(Site::score).reversed()).toList();
        var seeds = new java.util.HashSet<Long>();
        int kept = 0;
        for (var site : ranked) if (seeds.add(site.seed())) {
            System.out.println("CANDIDATE " + (++kept) + " " + site);
            if (kept == 3) break;
        }
        System.out.println("Eligible sites: " + sites.size());
        System.out.println("Eligible after visibility: " + refined.size());
    }

    private static long blockKey(int x, int z) { return ((long) x << 32) ^ (z & 0xffffffffL); }
}
