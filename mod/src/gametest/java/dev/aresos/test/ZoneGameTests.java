package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.*;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;

import java.util.List;
import java.util.UUID;

public final class ZoneGameTests {
    @GameTest
    public void dueSouthExitRoundTripsExactly(GameTestHelper helper) {
        var dimension = helper.getLevel().dimension();
        var box = new net.minecraft.world.phys.AABB(0, 1, 3, 3, 3, 6);
        var exit = AppZone.exit(dimension, new net.minecraft.world.phys.Vec3(1.5, 1, 0.5), box);
        helper.assertTrue(Float.floatToRawIntBits(exit.yaw()) == 0, "Due-south exit contains negative zero");
        var zone = new AppZone("round-trip", "fixture", dimension, new BlockPos(0, 1, 3), new BlockPos(2, 2, 5), exit, List.of());
        var encoded = AppZone.CODEC.encodeStart(net.minecraft.nbt.NbtOps.INSTANCE, zone).getOrThrow();
        helper.assertTrue(zone.equals(AppZone.CODEC.parse(net.minecraft.nbt.NbtOps.INSTANCE, encoded).getOrThrow()), "Zone did not round-trip through NBT");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void builderRefusesAtomicallyAndProtectionFollowsMode(GameTestHelper helper) {
        var server = helper.getLevel().getServer();
        DesktopWorld.setEnabled(server, true);
        var cookie = net.minecraft.server.network.CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "LogoTest"), false);
        var player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
        var connection = new net.minecraft.network.Connection(net.minecraft.network.protocol.PacketFlow.SERVERBOUND);
        new io.netty.channel.embedded.EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, player, cookie);
        ModeInventoryFixtures.registerStateReceiver(player);
        // Keep the placement and its neighbor safety margin inside the clear test chamber.
        var base = helper.absolutePos(new BlockPos(3, 2, 1));
        helper.getLevel().setBlockAndUpdate(base.below(), Blocks.STONE.defaultBlockState());
        player.snapTo(base.getX() + 0.5, base.getY(), base.getZ() + 0.5, 0, 0);
        var image = new LogoPixels.Image(2, 2, List.of(new LogoPixels.Pixel(0, 0, "red_concrete"),
                new LogoPixels.Pixel(1, 1, "blue_concrete")));
        for (float yaw : new float[]{0, 90, 180, -90}) {
            player.snapTo(base.getX() + 0.99, base.getY(), base.getZ() + 0.99, yaw, 0);
            for (boolean floor : new boolean[]{false, true}) {
                var rotated = LogoBuilder.plan(player, "fixture", image, floor);
                helper.assertTrue(!rotated.zone().touchesPlayer(player.position()), "Logo exit overlaps at yaw " + yaw);
            }
        }
        player.snapTo(base.getX() + 0.5, base.getY(), base.getZ() + 0.5, 0, 0);
        var plan = LogoBuilder.plan(player, "fixture", image, false);
        var obstruction = plan.blocks().keySet().iterator().next();
        helper.getLevel().setBlockAndUpdate(obstruction, Blocks.DIAMOND_BLOCK.defaultBlockState());
        try {
            LogoBuilder.build(player, plan);
            throw new AssertionError("Builder overwrote a non-air block");
        } catch (java.io.IOException expected) {
            helper.assertTrue(expected.getMessage().contains("Area isn't clear"), expected.getMessage());
        }
        helper.assertTrue(helper.getLevel().getBlockState(obstruction).is(Blocks.DIAMOND_BLOCK), "Obstruction changed");
        helper.assertTrue(plan.blocks().keySet().stream().filter(p -> !p.equals(obstruction)).allMatch(p -> helper.getLevel().getBlockState(p).isAir()),
                "Refused placement partially wrote blocks");
        helper.assertTrue(ZoneData.get(server).zones().stream().noneMatch(z -> z.id().equals(plan.zone().id())), "Refused logo saved a zone");
        helper.getLevel().setBlockAndUpdate(obstruction, Blocks.AIR.defaultBlockState());
        try { LogoBuilder.build(player, plan); } catch (java.io.IOException error) { throw new AssertionError(error); }
        helper.assertTrue(plan.blocks().entrySet().stream().allMatch(e -> helper.getLevel().getBlockState(e.getKey()).equals(e.getValue())), "Wrong block layout");
        player.setGameMode(GameType.SURVIVAL);
        ModeInventoryFixtures.acknowledge(player);
        helper.assertTrue(!PlayerBlockBreakEvents.BEFORE.invoker().beforeBlockBreak(helper.getLevel(), player, obstruction,
                helper.getLevel().getBlockState(obstruction), null), "Live break allowed");
        player.setGameMode(GameType.CREATIVE);
        helper.assertTrue(PlayerBlockBreakEvents.BEFORE.invoker().beforeBlockBreak(helper.getLevel(), player, obstruction,
                helper.getLevel().getBlockState(obstruction), null), "Build break denied");
        ZoneData.get(server).remove(z -> z.id().equals(plan.zone().id()));
        server.getPlayerList().remove(player);
        helper.succeed();
    }
}
