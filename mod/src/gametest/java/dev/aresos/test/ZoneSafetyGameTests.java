package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.*;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ServerExplosion;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.util.List;
import java.util.UUID;

public final class ZoneSafetyGameTests {
    private static ServerPlayer join(GameTestHelper helper) {
        var server = helper.getLevel().getServer();
        DesktopWorld.setEnabled(server, true);
        var cookie = net.minecraft.server.network.CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "SafetyTest"), false);
        var player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
        var connection = new net.minecraft.network.Connection(net.minecraft.network.protocol.PacketFlow.SERVERBOUND);
        new io.netty.channel.embedded.EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, player, cookie);
        var base = helper.absolutePos(new BlockPos(3, 2, 1));
        helper.getLevel().setBlockAndUpdate(base.below(), Blocks.STONE.defaultBlockState());
        player.snapTo(base.getX() + 0.5, base.getY(), base.getZ() + 0.5, 0, 0);
        return player;
    }

    private static LogoBuilder.Plan plan(ServerPlayer player) {
        return LogoBuilder.plan(player, "fixture", new LogoPixels.Image(1, 2,
                List.of(new LogoPixels.Pixel(0, 0, "red_wool"), new LogoPixels.Pixel(0, 1, "blue_wool"))), false);
    }

    private static void leave(ServerPlayer player) {
        var server = player.level().getServer();
        ZoneData.get(server).remove(z -> z.app().equals("fixture"));
        server.getPlayerList().remove(player);
    }

    @GameTest(environment = "aresos-test:desktop")
    public void cactusBehindWallIsPreservedAndBuildRefused(GameTestHelper helper) {
        var player = join(helper);
        var plan = plan(player);
        var level = helper.getLevel();
        var cactus = plan.blocks().keySet().stream().min(java.util.Comparator.comparingInt(BlockPos::getY)).orElseThrow().south();
        level.setBlockAndUpdate(cactus.below(2), Blocks.STONE.defaultBlockState());
        level.setBlockAndUpdate(cactus.below(), Blocks.SAND.defaultBlockState());
        level.setBlockAndUpdate(cactus, Blocks.CACTUS.defaultBlockState());
        helper.assertTrue(level.getBlockState(cactus).canSurvive(level, cactus), "Invalid cactus fixture");
        boolean refused;
        try { LogoBuilder.build(player, plan); refused = false; }
        catch (IOException expected) { refused = true; }
        boolean wasRefused = refused;
        helper.runAtTickTime(5, () -> {
            try {
                helper.assertTrue(wasRefused, "Builder accepted a wall that invalidates neighboring cactus");
                helper.assertTrue(level.getBlockState(cactus).is(Blocks.CACTUS), "Neighboring cactus was destroyed");
                helper.assertTrue(plan.blocks().keySet().stream().allMatch(p -> level.getBlockState(p).isAir()), "Refused build wrote blocks");
                helper.assertTrue(ZoneData.get(level.getServer()).zones().stream().noneMatch(z -> z.id().equals(plan.zone().id())), "Refused build saved zone");
                helper.succeed();
            } finally { leave(player); }
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void disjointZoneWallCannotObstructSavedExit(GameTestHelper helper) {
        var player = join(helper);
        try {
            var plan = plan(player);
            var wall = plan.blocks().keySet().stream().min(java.util.Comparator.comparingInt(BlockPos::getY)).orElseThrow();
            var min = wall.offset(5, 0, 0);
            var box = new net.minecraft.world.phys.AABB(min).expandTowards(0, 1, 0);
            var existing = new AppZone(UUID.randomUUID().toString(), "fixture", player.level().dimension(), min, min.above(),
                    AppZone.exit(player.level().dimension(), Vec3.atBottomCenterOf(wall), box), List.of());
            var data = ZoneData.get(player.level().getServer());
            data.add(existing);
            helper.assertTrue(!existing.box().intersects(plan.zone().box()), "Triggers overlap in fixture");
            try {
                LogoBuilder.build(player, plan);
                throw new AssertionError("New wall obstructed a saved exit despite disjoint triggers");
            } catch (IOException expected) {
                helper.assertTrue(expected.getMessage().toLowerCase().contains("exit"), expected.getMessage());
            }
            helper.assertTrue(plan.blocks().keySet().stream().allMatch(p -> player.level().getBlockState(p).isAir()), "Exit refusal wrote blocks");
            helper.assertTrue(data.zones().equals(List.of(existing)), "Exit refusal changed saved zones");
            helper.succeed();
        } finally { leave(player); }
    }

    @GameTest(environment = "aresos-test:desktop")
    public void explosionsPreserveLogosInLive(GameTestHelper helper) { explosions(helper, GameType.SURVIVAL); }

    @GameTest(environment = "aresos-test:desktop")
    public void explosionsPreserveLogosInBuild(GameTestHelper helper) { explosions(helper, GameType.CREATIVE); }

    private static void explosions(GameTestHelper helper, GameType mode) {
        var player = join(helper);
        try {
            var plan = plan(player);
            try { LogoBuilder.build(player, plan); } catch (IOException error) { throw new AssertionError(error); }
            player.setGameMode(mode);
            var level = helper.getLevel();
            var pixel = plan.blocks().keySet().iterator().next();
            var control = pixel.south();
            // These are real server explosions, sharing the same destruction path as TNT, beds/anchors and creepers.
            for (String source : List.of("TNT", "bed/anchor", "creeper")) {
                level.setBlockAndUpdate(control, plan.blocks().get(pixel));
                var entity = source.equals("TNT") ? new net.minecraft.world.entity.item.PrimedTnt(level, pixel.getX(), pixel.getY(), pixel.getZ(), player)
                        : source.equals("creeper") ? new net.minecraft.world.entity.monster.Creeper(net.minecraft.world.entity.EntityTypes.CREEPER, level) : null;
                var damage = entity == null ? level.damageSources().badRespawnPointExplosion(Vec3.atCenterOf(pixel)) : null;
                new ServerExplosion(level, entity, damage, null, Vec3.atCenterOf(control), 4, false, Explosion.BlockInteraction.DESTROY).explode();
                helper.assertTrue(level.getBlockState(control).isAir(), "Explosion did not destroy unprotected control: " + source);
                helper.assertTrue(plan.blocks().entrySet().stream().allMatch(e -> level.getBlockState(e.getKey()).equals(e.getValue())),
                        source + " explosion destroyed logo in " + mode);
            }
            if (mode == GameType.CREATIVE) {
                helper.assertTrue(player.gameMode.destroyBlock(pixel), "Build mode mining denied after explosions");
                helper.assertTrue(level.getBlockState(pixel).isAir(), "Build mode mining left logo pixel");
            }
            helper.succeed();
        } finally { leave(player); }
    }
}
