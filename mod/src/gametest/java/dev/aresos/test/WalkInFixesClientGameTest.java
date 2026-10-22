package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.config.AppDefinition;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.*;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.util.*;
import java.util.concurrent.*;

public final class WalkInFixesClientGameTest implements FabricClientGameTest {
    private static final int Y = 150;

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var calls = new CopyOnWriteArrayList<List<String>>();
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(command -> {
            calls.add(List.copyOf(command)); return CompletableFuture.completedFuture(null);
        }));
        var errors = new ArrayList<AssertionError>();
        try {
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(
                    new AppDefinition("seam-a", "A", List.of("a.exe"), "minecraft:book", false),
                    new AppDefinition("seam-b", "B", List.of("b.exe"), "minecraft:paper", false))));
            try (var world = context.worldBuilder().create()) {
                world.getServer().runOnServer(server -> {
                    var level = world.getConnection().getServerLevel();
                    for (int x = -4; x <= 8; x++) for (int z = -4; z <= 8; z++)
                        level.setBlockAndUpdate(new BlockPos(x, Y - 1, z), Blocks.STONE.defaultBlockState());
                    DesktopWorld.setEnabled(server, true);
                    world.getConnection().getServerPlayer().setGameMode(net.minecraft.world.level.GameType.SURVIVAL);
                    var data = ZoneData.get(server);
                    for (int i = 0; i < 2; i++) {
                        var min = new BlockPos(i * 2, Y, 2);
                        var max = min.offset(1, 1, 3);
                        data.add(new AppZone("seam-" + i, i == 0 ? "seam-a" : "seam-b", level.dimension(), min, max,
                                AppZone.exit(level.dimension(), new Vec3(i * 2 + 0.5, Y, -1.5), new net.minecraft.world.phys.AABB(min)), List.of()));
                    }
                });
                move(context, world, new Vec3(3, Y, -1.5));
                int before = calls.size();
                // B remains intersected throughout B -> A+B -> B -> A+B -> B.
                for (double x : new double[]{2.4, 2.0, 2.4, 2.0, 2.4}) move(context, world, new Vec3(x, Y, 3.5));
                long b = calls.subList(before, calls.size()).stream().filter(c -> c.equals(List.of("b.exe"))).count();
                long a = calls.subList(before, calls.size()).stream().filter(c -> c.equals(List.of("a.exe"))).count();
                try {
                    check(b == 1 && a == 2, "Seam entry counts: A=" + a + ", B=" + b + " (expected A=2, B=1)");
                    move(context, world, new Vec3(3, Y, -1.5));
                    move(context, world, new Vec3(2.4, Y, 3.5));
                    check(calls.stream().filter(c -> c.equals(List.of("b.exe"))).count() == 2, "B did not rearm after real exit");
                    AresOs.LOGGER.info("08b seam regression passed");
                } catch (AssertionError error) { errors.add(error); AresOs.LOGGER.error("08b seam regression failed", error); }

                move(context, world, new Vec3(3, Y, -1.5));
                move(context, world, new Vec3(0.5, Y, 3.5));
                context.runOnClient(client -> {
                    var screen = new InventoryScreen(client.player);
                    client.gui.setScreen(screen);
                    boolean previous = client.options.pauseOnLostFocus;
                    try {
                        client.options.pauseOnLostFocus = true;
                        ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(false);
                        ((MinecraftTestAccess)client).aresos$setLastActiveTime(0);
                        ((MinecraftTestAccess)client).aresos$pauseIfInactive();
                        ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
                        ((MinecraftTestAccess)client).aresos$pauseIfInactive();
                        check(client.gui.screen() == screen, "Delayed focus return replaced inventory");
                    } finally { client.options.pauseOnLostFocus = previous; }
                });
                world.getConnection().waitForServerboundPackets();
                context.waitTicks(8);
                try {
                    context.runOnClient(client -> {
                        check(client.player.position().distanceToSqr(new Vec3(0.5, Y, -1.5)) < 0.01,
                                "Delayed focus return lost zone teleport while inventory was open");
                        check(client.gui.screen() instanceof InventoryScreen, "Return teleport closed inventory");
                    });
                    AresOs.LOGGER.info("08b delayed-focus regression passed");
                } catch (AssertionError error) { errors.add(error); AresOs.LOGGER.error("08b delayed-focus regression failed", error); }
                if (errors.isEmpty()) context.takeScreenshot(net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions
                        .of("08b-return-inventory").withDestinationDir(java.nio.file.Path.of(System.getProperty("aresos.logoReviewDir"))));
                context.runOnClient(client -> client.gui.setScreen(null));
            }
            if (!errors.isEmpty()) {
                var failure = new AssertionError("08b client regressions failed: " + errors.size());
                errors.forEach(failure::addSuppressed);
                throw failure;
            }
        } finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps);
                AresOsClient.replaceLauncher(previousLauncher);
                AresOsClient.FOCUS_RETURN.reset();
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
        }
    }

    private static void move(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(player.level(), point.x, point.y, point.z, Set.of(), 0, 0, false);
            player.setDeltaMovement(Vec3.ZERO);
        });
        context.waitFor(client -> client.player.position().distanceToSqr(point) < 0.01);
        context.waitTicks(5);
    }

    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
