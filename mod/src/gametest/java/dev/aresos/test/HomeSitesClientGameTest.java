package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.world.HomeSites;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

public final class HomeSitesClientGameTest implements FabricClientGameTest {
    @Override
    public void runTest(ClientGameTestContext context) {
        var freshDirectories = new HashSet<Path>();
        var onStart = new AtomicReference<Consumer<MinecraftServer>>();
        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            var action = onStart.getAndSet(null);
            if (action != null) action.accept(server);
        });
        for (long seed : new long[]{-812345678901234567L, 50, 26}) {
            NetherHome.Site expected = null;
            for (int fresh = 0; fresh < 3; fresh++) {
                var initial = new AtomicReference<NetherHome.Site>();
                boolean preloaded = fresh == 1;
                onStart.set(fresh == 2 ? null : server -> {
                    var level = server.getLevel(Level.NETHER);
                    if (preloaded) generateSearchArea(level);
                    var site = find(level);
                    initial.set(site);
                    AresOs.LOGGER.info("04d startup seed={}: {}, terrain={}", seed, site, terrain(level, site));
                    assertSame(level, site, "second startup search");
                });
                TestWorldSave save;
                try (var world = context.worldBuilder().setUseConsistentSettings(false)
                        .adjustSettings(settings -> settings.setSeed(Long.toString(seed))).create()) {
                    save = world.getWorldSave();
                    var directory = world.getServer().computeOnServer(server -> server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize());
                    check(freshDirectories.add(directory), "Fresh test reused a save: " + directory);
                    if (initial.get() == null) initial.set(world.getServer().computeOnServer(server -> find(server.getLevel(Level.NETHER))));
                    var site = initial.get();
                    check(site != null, "Site search did not run");
                    if (expected == null) expected = site;
                    check(expected.equals(site), "Fresh-world search differed: expected=" + expected + ", actual=" + site);
                    world.getServer().runOnServer(server -> {
                        var level = server.getLevel(Level.NETHER);
                        generateSearchArea(level);
                        assertSame(level, site, "fully generated search");
                        assertSafe(level, site);
                    });
                    visit(context, world, site);
                    world.getServer().runOnServer(server -> {
                        var level = server.getLevel(Level.NETHER);
                        assertSame(level, site, "search after arrival ticks");
                        assertSafe(level, site);
                    });
                    AresOs.LOGGER.info("04d fresh world {}/3 seed={} PASSED: {}", fresh + 1, seed, site);
                }
                if (fresh == 0) {
                    var site = expected;
                    try (var world = save.open()) {
                        world.getServer().runOnServer(server -> {
                            var level = server.getLevel(Level.NETHER);
                            generateSearchArea(level);
                            assertSame(level, site, "rejoin search");
                            assertSafe(level, site);
                        });
                        AresOs.LOGGER.info("04d rejoin seed={} PASSED: {}", seed, site);
                    }
                }
            }
        }
        AresOs.LOGGER.info("04d deterministic site search PASSED: 3 seeds, 3 fresh worlds each, repeated searches and rejoin per seed");
    }

    private static void visit(ClientGameTestContext context, TestSingleplayerContext world, NetherHome.Site site) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.setGameMode(GameType.SPECTATOR);
            player.teleportTo(server.getLevel(Level.NETHER), site.x() + 0.5, site.y() + 1, site.z() + 0.5,
                    Set.of(), site.yaw(), 0, false);
        });
        context.waitTicks(40);
    }

    private static void generateSearchArea(ServerLevel level) {
        for (int x = -11; x <= 10; x++) for (int z = -11; z <= 10; z++) {
            var chunk = level.getChunk(x, z, ChunkStatus.FULL, true);
            check(chunk.getPersistedStatus() == ChunkStatus.FULL, "Incomplete terrain at " + x + ", " + z);
        }
    }

    private static NetherHome.Site find(ServerLevel level) {
        try {
            var site = HomeSites.find(level);
            // A search must finish generation itself; this check never loads a missing chunk.
            for (int x = -10; x <= 10; x++) for (int z = -10; z <= 10; z++) {
                check(level.getChunkSource().getChunkNow(x, z) != null, "Search scored an incomplete area at " + x + ", " + z);
            }
            return site;
        }
        catch (IOException error) { throw new AssertionError(error); }
    }

    private static void assertSame(ServerLevel level, NetherHome.Site expected, String phase) {
        var actual = find(level);
        check(expected.equals(actual), phase + " differed: expected=" + expected + ", terrain=" + terrain(level, expected)
                + ", actual=" + actual + ", terrain=" + terrain(level, actual));
    }

    private static String terrain(ServerLevel level, NetherHome.Site site) {
        return java.util.stream.IntStream.rangeClosed(0, 3).mapToObj(h ->
                level.getBlockState(site.floor().above(h)).toString()).toList().toString();
    }

    private static void assertSafe(ServerLevel level, NetherHome.Site site) {
        check(HomeSites.isSafe(level, Vec3.atBottomCenterOf(site.floor().above())), "Unsafe generated site: " + site);
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
