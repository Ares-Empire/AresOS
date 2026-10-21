package dev.aresos.test;

import dev.aresos.world.NetherHome;
import dev.aresos.world.HomeSites;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RespawnAnchorBlock;
import net.minecraft.world.level.gamerules.GameRules;

public final class NetherHomeGameTests {
    @GameTest(environment = "aresos-test:home")
    public void homeSafetyChecksStandingBodyWithoutEditingBlocks(GameTestHelper helper) {
        var level = helper.getLevel();
        var feet = helper.absolutePos(new BlockPos(4, 3, 4));
        for (BlockPos pos : BlockPos.betweenClosed(feet.offset(-1, -1, -1), feet.offset(1, 2, 1))) {
            level.setBlock(pos, (pos.getY() == feet.getY() - 1 ? Blocks.STONE : Blocks.AIR).defaultBlockState(), 2);
        }
        var arrival = net.minecraft.world.phys.Vec3.atBottomCenterOf(feet);
        check(HomeSites.isSafe(level, arrival), "Safe solid-ground pocket refused");
        level.setBlock(feet.below(), Blocks.AIR.defaultBlockState(), 2);
        check(!HomeSites.isSafe(level, arrival), "Flying position accepted");
        level.setBlock(feet.below(), Blocks.STONE.defaultBlockState(), 2);
        for (var hazard : new net.minecraft.world.level.block.Block[]{Blocks.LAVA, Blocks.FIRE, Blocks.SOUL_FIRE, Blocks.STONE}) {
            for (var pos : new BlockPos[]{feet, feet.above()}) {
                // Fire removes itself immediately without a valid support, even before a game tick.
                level.setBlock(pos.east(), Blocks.OAK_PLANKS.defaultBlockState(), 2);
                if (hazard == Blocks.SOUL_FIRE) level.setBlock(pos.below(), Blocks.SOUL_SOIL.defaultBlockState(), 2);
                level.setBlock(pos, hazard.defaultBlockState(), 2);
                check(level.getBlockState(pos).is(hazard), "Hazard fixture did not survive placement");
                check(!HomeSites.isSafe(level, arrival), "Unsafe body accepted: " + hazard + " at " + pos);
                check(level.getBlockState(pos).is(hazard), "Safety check changed a block");
                level.setBlock(pos, Blocks.AIR.defaultBlockState(), 2);
                level.setBlock(pos.east(), Blocks.AIR.defaultBlockState(), 2);
                level.setBlock(feet, Blocks.AIR.defaultBlockState(), 2);
                level.setBlock(feet.below(), Blocks.STONE.defaultBlockState(), 2);
            }
        }
        level.setBlock(feet.east(), Blocks.LAVA.defaultBlockState(), 2);
        check(!HomeSites.isSafe(level, arrival.add(0.4, 0, 0)), "Fractional body overlapping lava accepted");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:home", maxTicks = 80)
    public void hubSealsLavaAndKeepsSafeAir(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos center = helper.absolutePos(new BlockPos(8, 3, 8));
        var site = new NetherHome.Site(56, center.getX(), center.getY(), center.getZ(), 180);
        // Adversarial hillside and ceiling sources must stay outside the air pocket after fluid ticks.
        for (int x = -9; x <= 9; x++) for (int z = -9; z <= 9; z++) for (int y = 0; y <= 11; y++) {
            level.setBlock(center.offset(x, y, z), Blocks.LAVA.defaultBlockState(), 2);
        }
        NetherHome.build(level, site);
        helper.runAtTickTime(60, () -> {
            assertHub(level, site);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:home")
    public void desktopCreationRules(GameTestHelper helper) {
        var rules = new GameRules(helper.getLevel().enabledFeatures());
        NetherHome.applyRules(rules, null);
        assertRules(rules);
        helper.succeed();
    }

    public static void assertRules(GameRules rules) {
        check(!rules.get(GameRules.SPAWN_MOBS), "Natural mobs enabled");
        check(rules.get(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER) == 0, "Fire ticking enabled");
        check(!rules.get(GameRules.MOB_GRIEFING), "Mob griefing enabled");
        check(rules.get(GameRules.KEEP_INVENTORY), "Keep inventory disabled");
        check(!rules.get(GameRules.SPAWN_PHANTOMS), "Insomnia spawns enabled");
        check(!rules.get(GameRules.SPAWN_PATROLS), "Patrol spawns enabled");
        check(!rules.get(GameRules.SPAWN_WANDERING_TRADERS), "Trader spawns enabled");
    }

    public static void assertHub(net.minecraft.server.level.ServerLevel level, NetherHome.Site site) {
        var floor = site.floor();
        for (int x = -8; x <= 8; x++) for (int z = -8; z <= 8; z++) {
            for (int y = -1; y <= NetherHome.CEILING; y++) {
                BlockPos pos = floor.offset(x, y, z);
                var state = level.getBlockState(pos);
                boolean shell = Math.abs(x) == 8 || Math.abs(z) == 8 || y == NetherHome.CEILING;
                if (y == -1 || (y == 0 && !NetherHome.isPool(x, z)) || (y > 0 && shell)) {
                    check(state.isSolidRender() || state.is(Blocks.GLASS), "Unsealed hub at " + pos);
                    check(state.getFluidState().isEmpty(), "Fluid in safety shell at " + pos);
                } else if (y == 0) {
                    check(state.is(Blocks.LAVA) && state.getFluidState().isSource(), "Trash pool missing at " + pos);
                } else if (y == 1 && Math.abs(x) == 6 && Math.abs(z) == 6) {
                    check(state.is(Blocks.LANTERN), "Corner light missing");
                } else if (!pos.equals(site.anchor())) {
                    check(state.isAir(), "Unsafe air pocket at " + pos + ": " + state);
                }
            }
        }
        check(level.getBlockState(site.anchor()).is(Blocks.RESPAWN_ANCHOR), "Anchor missing");
        check(level.getBlockState(site.anchor()).getValue(RespawnAnchorBlock.CHARGE) == 4, "Anchor not fully charged");
        check(level.getBlockState(floor).is(Blocks.POLISHED_BLACKSTONE), "Polished floor missing");
        check(level.getBlockState(floor.offset(6, 0, 6)).is(Blocks.GOLD_BLOCK), "Gold accent missing");
        check(level.getBlockState(floor.offset(7, 0, 0)).is(Blocks.GILDED_BLACKSTONE), "Gilded edge missing");
        for (int x = 3; x <= 6; x++) for (int z = 2; z <= 5; z++) {
            if (!NetherHome.isPool(x, z)) check(level.getBlockState(floor.offset(x, 0, z)).is(Blocks.POLISHED_BLACKSTONE_BRICKS), "Pool edge missing");
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
