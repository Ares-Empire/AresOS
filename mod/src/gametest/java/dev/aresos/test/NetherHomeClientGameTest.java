package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.AlertScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

public final class NetherHomeClientGameTest implements FabricClientGameTest {
    @Override
    public void runTest(ClientGameTestContext context) {
        Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
        // Preserve prior dev saves and keep repeated test runs independent, with no recursive deletion.
        if (Files.exists(directory)) {
            try { Files.move(directory, directory.resolveSibling("AresHub-test-backup-" + java.util.UUID.randomUUID())); }
            catch (IOException error) { throw new AssertionError(error); }
        }
        var firstDimensions = new ArrayList<net.minecraft.resources.ResourceKey<Level>>();
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> firstDimensions.add(client.level.dimension()));
        context.setScreen(TitleScreen::new);
        context.takeScreenshot(TestScreenshotOptions.of("title-button").withDestinationDir(homeDir()));
        context.clickScreenButton("aresos.home");
        context.waitForScreen(dev.aresos.client.HomeCreateScreen.class);
        context.clickScreenButton("aresos.home.create");
        context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
        var server = context.computeOnClient(Minecraft::getSingleplayerServer);
        // Fabric exposes no API for adopting a world opened by a real UI button; these wrappers only supply test synchronization.
        var save = new TestWorldSaveImpl(context, directory);
        try (TestSingleplayerContext world = new TestSingleplayerContextImpl(context, save, server)) {
            world.getConnection().waitForChunksRender();
            assertArrival(context, world, firstDimensions);
            world.getServer().runOnServer(s -> {
                check(s.getWorldData().getLevelName().equals("AresOS"), "Wrong world name");
                check(s.overworld().getSeed() == NetherHome.DEFAULT_SITE.seed(), "Wrong seed");
                check(!s.getWorldData().isAllowCommands(), "Cheats enabled");
                check(s.getWorldData().getGameType() == GameType.SURVIVAL, "World not survival");
                check(s.getWorldData().getDifficulty() == Difficulty.NORMAL, "Wrong difficulty");
                check(DesktopWorld.isEnabled(s), "Desktop marker missing");
                NetherHomeGameTests.assertRules(s.getGameRules());
                NetherHomeGameTests.assertHub(s.getLevel(Level.NETHER), NetherHome.DEFAULT_SITE);
                check(s.getLevel(Level.NETHER).getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class,
                        net.minecraft.world.phys.AABB.encapsulatingFullBlocks(NetherHome.DEFAULT_SITE.floor().offset(-8, 0, -8),
                                NetherHome.DEFAULT_SITE.floor().offset(9, 11, 9))).isEmpty(), "Building littered the hub with drops");
                var player = world.getConnection().getServerPlayer();
                var respawn = player.findRespawnPositionAndUseSpawnBlock(false, TeleportTransition.DO_NOTHING);
                check(respawn.newLevel().dimension() == Level.NETHER && !respawn.missingRespawnBlock(), "Respawn missed Nether anchor");
                check(respawn.position().distanceToSqr(Vec3.atCenterOf(NetherHome.DEFAULT_SITE.anchor())) < 12, "Respawn missed anchor site");
            });
            context.waitTicks(10);
            context.takeScreenshot(TestScreenshotOptions.of("arrival").withDestinationDir(homeDir()));
            photographAbove(context, world, NetherHome.DEFAULT_SITE, "hub-above", homeDir());
            // A deliberately edited block must survive reopen; neither joins nor startup may rebuild the hub.
            world.getServer().runOnServer(s -> {
                var player = world.getConnection().getServerPlayer();
                player.level().setBlockAndUpdate(NetherHome.DEFAULT_SITE.floor().offset(2, 0, 0), Blocks.DIAMOND_BLOCK.defaultBlockState());
                player.setGameMode(GameType.CREATIVE);
                player.getInventory().clearContent();
                player.teleportTo(s.overworld(), 400, 80, 400, Set.of(), 90, 30, false);
            });
        }
        context.clickScreenButton("aresos.home");
        context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
        try (TestSingleplayerContext world = new TestSingleplayerContextImpl(context, save,
                context.computeOnClient(Minecraft::getSingleplayerServer))) {
            world.getConnection().waitForChunksRender();
            assertArrival(context, world, firstDimensions);
            world.getServer().runOnServer(s -> {
                check(s.getLevel(Level.NETHER).getBlockState(NetherHome.DEFAULT_SITE.floor().offset(2, 0, 0)).is(Blocks.DIAMOND_BLOCK), "Hub rebuilt on reopen");
                check(NetherHome.get(s).site().equals(NetherHome.DEFAULT_SITE), "Saved site changed");
            });
            context.takeScreenshot(TestScreenshotOptions.of("rejoin").withDestinationDir(homeDir()));
        }
        check(firstDimensions.size() == 2, "Expected two real home joins: " + firstDimensions);
        check(Files.isRegularFile(directory.resolve("level.dat")), "AresHub/level.dat missing");
        int visible49 = photographCandidate(context, NetherHome.DEFAULT_SITE, "01-seed-49", 209.84458247200067);
        int visible50 = photographCandidate(context, new NetherHome.Site(50, -32, 38, 0, -90), "02-seed-50", 217.05);
        int visible26 = photographCandidate(context, new NetherHome.Site(26, 64, 43, 96, 0), "03-seed-26", 230.21223591851523);
        check(209.84458247200067 + visible49 * 10 > 217.05 + visible50 * 10
                && 209.84458247200067 + visible49 * 10 > 230.21223591851523 + visible26 * 10, "Default is not the best full-generation candidate");
        check(visible49 >= 5 && visible50 >= 5 && visible26 >= 5, "Candidate lacks a visible lava ocean");
        testSaveCollision(context, directory);
        AresOs.LOGGER.info("04 client checks passed: real title button creation and reload, Nether in first login packet, "
                + "Live and pins on both joins, flags, safe hub, anchor respawn, edits persist, three generated seed screenshots, existing-save refusal");
        var failures = new ArrayList<AssertionError>();
        regression(failures, "mounted Nether rejoin", () -> testMountedRejoin(context, save, firstDimensions, Level.NETHER));
        regression(failures, "mounted Overworld rejoin", () -> testMountedRejoin(context, save, firstDimensions, Level.OVERWORLD));
        regression(failures, "missing home data", () -> testMissingHomeData(context, save, directory));
        if (!failures.isEmpty()) {
            var error = new AssertionError("04b regressions failed: " + failures.size());
            failures.forEach(error::addSuppressed);
            throw error;
        }
    }

    private static void regression(List<AssertionError> failures, String name, Runnable test) {
        try {
            test.run();
            AresOs.LOGGER.info("04b regression PASSED: {}", name);
        } catch (AssertionError error) {
            AresOs.LOGGER.error("04b regression FAILED: {}", name, error);
            failures.add(error);
        }
    }

    private static void testMountedRejoin(ClientGameTestContext context, TestWorldSaveImpl save,
                                         ArrayList<net.minecraft.resources.ResourceKey<Level>> dimensions,
                                         net.minecraft.resources.ResourceKey<Level> dimension) {
        UUID vehicle;
        Vec3 position = new Vec3(128.5, 80, 128.5);
        try (var world = save.open()) {
            vehicle = world.getServer().computeOnServer(server -> {
                var level = server.getLevel(dimension);
                var player = world.getConnection().getServerPlayer();
                player.stopRiding();
                player.setGameMode(GameType.CREATIVE);
                for (int x = -2; x <= 2; x++) for (int z = -2; z <= 2; z++) for (int y = -1; y <= 3; y++) {
                    level.setBlock(BlockPos.containing(position).offset(x, y, z),
                            (y == -1 ? Blocks.STONE : Blocks.AIR).defaultBlockState(), 2);
                }
                player.teleportTo(level, position.x, position.y, position.z, Set.of(), 0, 0, false);
                var cart = EntityTypes.MINECART.create(level, EntitySpawnReason.COMMAND);
                cart.setNoGravity(true);
                cart.snapTo(position);
                check(level.addFreshEntity(cart), "Could not add saved vehicle");
                check(player.startRiding(cart, true, false), "Fixture did not mount vehicle");
                server.getPlayerList().saveAll();
                return cart.getUUID();
            });
            context.waitTicks(5);
            world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer().isPassenger(), "Fixture dismounted before saving"));
        }
        try (var world = save.open()) {
            try {
                context.waitTicks(30);
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(!player.isPassenger() && player.level().dimension() == Level.NETHER
                            && player.position().distanceToSqr(NetherHome.DEFAULT_SITE.arrival()) < 0.1,
                            "Saved " + dimension.identifier() + " vehicle overrode hub arrival after 30 ticks: passenger="
                                    + player.isPassenger() + ", dimension=" + player.level().dimension() + ", position=" + player.position());
                    var source = server.getLevel(dimension);
                    source.getChunkAt(BlockPos.containing(position));
                    source.waitForEntities(net.minecraft.world.level.ChunkPos.containing(BlockPos.containing(position)), 0);
                    var cart = source.getEntity(vehicle);
                    check(cart != null && cart.position().distanceToSqr(position) < 0.01 && !cart.isVehicle(),
                            "Saved vehicle was lost, moved, or remounted in " + dimension.identifier());
                    if (dimension != Level.NETHER) check(server.getLevel(Level.NETHER).getEntity(vehicle) == null,
                            "Overworld vehicle was recreated in Nether");
                });
                assertArrival(context, world, dimensions);
                world.getConnection().waitForChunksRender();
                context.takeScreenshot(TestScreenshotOptions.of("04b-mounted-" + dimension.identifier().getPath()).withDestinationDir(homeDir().resolve("04b")));
            } finally {
                // A failing rejoin must not leave a saved mount that poisons the next independent case.
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    player.stopRiding();
                    var home = NetherHome.DEFAULT_SITE.arrival();
                    player.teleportTo(server.getLevel(Level.NETHER), home.x, home.y, home.z, Set.of(), 0, 20, false);
                });
            }
        }
    }

    private static void testMissingHomeData(ClientGameTestContext context, TestWorldSaveImpl save, Path directory) {
        var messages = new CopyOnWriteArrayList<String>();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> messages.add(message.getString()));
        List<BlockState> blocks;
        try (var world = save.open()) {
            blocks = world.getServer().computeOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                player.stopRiding();
                player.setGameMode(GameType.CREATIVE);
                player.teleportTo(server.overworld(), 20, 200, 20, Set.of(), 0, 0, false);
                DesktopWorld.setEnabled(server, false);
                var rules = server.getGameRules();
                rules.set(GameRules.SPAWN_MOBS, true, server);
                rules.set(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER, 12, server);
                rules.set(GameRules.MOB_GRIEFING, true, server);
                rules.set(GameRules.KEEP_INVENTORY, false, server);
                rules.set(GameRules.SPAWN_PHANTOMS, true, server);
                rules.set(GameRules.SPAWN_PATROLS, true, server);
                rules.set(GameRules.SPAWN_WANDERING_TRADERS, true, server);
                server.setDifficulty(Difficulty.HARD, true);
                server.getLevel(Level.NETHER).setBlockAndUpdate(NetherHome.DEFAULT_SITE.floor().offset(2, 0, 0), Blocks.EMERALD_BLOCK.defaultBlockState());
                return hubSnapshot(server.getLevel(Level.NETHER));
            });
        }
        try {
            check(Files.readString(directory.resolve(NetherHome.PROVISIONED)).equals("complete\n"), "Provisioning completion was not recorded separately");
            Files.delete(directory.resolve("data/aresos/nether_home.dat"));
        }
        catch (IOException error) { throw new AssertionError(error); }
        try (var world = save.open()) {
            context.waitTicks(30);
            assertMissingHomeUnchanged(world, blocks, false);
            context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("AresOS home data") && message.contains("unchanged")));
            context.takeScreenshot(TestScreenshotOptions.of("04b-missing-home-data").withDestinationDir(homeDir().resolve("04b")));
            world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
        }
        // Old releases and incomplete backups can lack both files. A manifest alone must never grant a build.
        try { Files.delete(directory.resolve(NetherHome.PROVISIONED)); }
        catch (IOException error) { throw new AssertionError(error); }
        messages.clear();
        try (var world = save.open()) {
            context.waitTicks(30);
            assertMissingHomeUnchanged(world, blocks, true);
            context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("AresOS home data") && message.contains("unchanged")));
            context.takeScreenshot(TestScreenshotOptions.of("04b-legacy-missing-home-data").withDestinationDir(homeDir().resolve("04b")));
        }
        check(!Files.exists(directory.resolve("data/aresos/nether_home.dat")), "Missing data rewritten on shutdown");
    }

    private static void assertMissingHomeUnchanged(TestSingleplayerContext world, List<BlockState> blocks, boolean desktopEnabled) {
        world.getServer().runOnServer(server -> {
            var changed = new ArrayList<String>();
            if (!blocks.equals(hubSnapshot(server.getLevel(Level.NETHER)))) changed.add("hub blocks");
            var rules = server.getGameRules();
            if (!rules.get(GameRules.SPAWN_MOBS) || rules.get(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER) != 12
                    || !rules.get(GameRules.MOB_GRIEFING) || rules.get(GameRules.KEEP_INVENTORY)
                    || !rules.get(GameRules.SPAWN_PHANTOMS) || !rules.get(GameRules.SPAWN_PATROLS)
                    || !rules.get(GameRules.SPAWN_WANDERING_TRADERS)) changed.add("gamerules");
            if (DesktopWorld.isEnabled(server) != desktopEnabled) changed.add("desktop marker");
            if (server.getWorldData().getDifficulty() != Difficulty.HARD) changed.add("difficulty");
            check(changed.isEmpty(), "Missing home data changed existing save: " + changed);
            check(NetherHome.get(server) == null, "Missing home data silently recreated");
            var player = world.getConnection().getServerPlayer();
            check(player.level().dimension() == Level.OVERWORLD, "Missing data forced hub arrival");
            check(player.gameMode.getGameModeForPlayer() == GameType.CREATIVE, "Missing data changed player mode");
        });
    }

    private static List<BlockState> hubSnapshot(net.minecraft.server.level.ServerLevel level) {
        var blocks = new ArrayList<BlockState>();
        for (BlockPos pos : BlockPos.betweenClosed(NetherHome.DEFAULT_SITE.floor().offset(-8, -1, -8),
                NetherHome.DEFAULT_SITE.floor().offset(8, NetherHome.CEILING, 8))) {
            blocks.add(level.getBlockState(pos));
        }
        return List.copyOf(blocks);
    }

    private static void assertArrival(ClientGameTestContext context, TestSingleplayerContext world,
                                      ArrayList<net.minecraft.resources.ResourceKey<Level>> dimensions) {
        check(dimensions.getLast() == Level.NETHER, "First login dimension was not Nether: " + dimensions);
        context.runOnClient(client -> {
            check(client.level.dimension() == Level.NETHER, "Client not in Nether");
            check(client.player.position().distanceToSqr(NetherHome.DEFAULT_SITE.arrival()) < 0.1, "Client missed hub");
            check(Math.abs(net.minecraft.util.Mth.wrapDegrees(client.player.getYRot() - NetherHome.DEFAULT_SITE.yaw())) < 1, "Wrong view direction");
            check(client.gameMode.getPlayerMode() == GameType.SURVIVAL, "Client not in Live");
            check(client.player.getInventory().getItem(0).is(AppItems.APP), "Pinned app missing");
        });
        world.getServer().runOnServer(s -> {
            ServerPlayer player = world.getConnection().getServerPlayer();
            check(LiveMode.isLive(player), "Server not in Live");
            check(player.position().distanceToSqr(NetherHome.DEFAULT_SITE.arrival()) < 0.1, "Server missed hub");
            check(player.getRespawnConfig().respawnData().pos().equals(NetherHome.DEFAULT_SITE.anchor()), "Anchor spawn missing");
        });
    }

    private static int photographCandidate(ClientGameTestContext context, NetherHome.Site site, String name, double noiseScore) {
        int visible;
        try (var world = context.worldBuilder().setUseConsistentSettings(false).adjustSettings(settings -> {
            settings.setSeed(Long.toString(site.seed()));
            settings.setGameMode(WorldCreationUiState.SelectedGameMode.CREATIVE);
        }).create()) {
            world.getServer().runOnServer(server -> {
                var nether = server.getLevel(Level.NETHER);
                var biome = nether.getBiome(site.floor().above());
                check(biome.is(net.minecraft.world.level.biome.Biomes.CRIMSON_FOREST)
                        || biome.is(net.minecraft.world.level.biome.Biomes.NETHER_WASTES), "Candidate biome changed: " + biome);
                var player = world.getConnection().getServerPlayer();
                player.setGameMode(GameType.SPECTATOR);
                player.teleportTo(nether, site.arrival().x, site.arrival().y, site.arrival().z, Set.of(), site.yaw(), 20, false);
            });
            world.getConnection().waitForChunksRender();
            visible = world.getServer().computeOnServer(server -> visibleLava(world.getConnection().getServerPlayer(), site));
            AresOs.LOGGER.info("Full-generation seed {}: visible lava rays={}, noise score={}, final score={}",
                    site.seed(), visible, noiseScore, noiseScore + visible * 10);
            context.waitTicks(100);
            context.runOnClient(client -> {
                client.gui.hud.getChat().clearMessages(true);
                client.gui.toastManager().clear();
            });
            context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.seedReviewDir"))));
        }
        return visible;
    }

    private static int visibleLava(ServerPlayer player, NetherHome.Site site) {
        double angle = Math.toRadians(site.yaw());
        double dx = -Math.sin(angle), dz = Math.cos(angle);
        Vec3 eye = site.arrival().add(0, 1.62, 0);
        int visible = 0;
        for (int distance = 16; distance <= 64; distance += 8) for (int across = -16; across <= 16; across += 8) {
            BlockPos lava = new BlockPos((int) Math.round(site.x() + dx * distance + dz * across), 31,
                    (int) Math.round(site.z() + dz * distance - dx * across));
            if (!player.level().getBlockState(lava).is(Blocks.LAVA)) continue;
            var hit = player.level().clip(new net.minecraft.world.level.ClipContext(eye, Vec3.atCenterOf(lava.above()),
                    net.minecraft.world.level.ClipContext.Block.COLLIDER, net.minecraft.world.level.ClipContext.Fluid.NONE, player));
            if (hit.getType() == net.minecraft.world.phys.HitResult.Type.MISS) visible++;
        }
        return visible;
    }

    private static void photographAbove(ClientGameTestContext context, TestSingleplayerContext world, NetherHome.Site site, String name, Path directory) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.setGameMode(GameType.SPECTATOR);
            player.teleportTo(server.getLevel(Level.NETHER), site.x() + 0.5, site.y() + 7.3, site.z() + 0.5, Set.of(), 180, 90, false);
        });
        world.getConnection().waitForChunksRender();
        int previousFov = context.computeOnClient(client -> client.options.fov().get());
        context.runOnClient(client -> client.options.fov().set(110));
        context.waitTicks(4);
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(directory));
        context.runOnClient(client -> client.options.fov().set(previousFov));
    }

    private static void testSaveCollision(ClientGameTestContext context, Path directory) {
        try {
            Path backup = directory.resolveSibling("AresHub-created-test-" + java.util.UUID.randomUUID());
            Files.move(directory, backup);
            Files.createDirectory(directory);
            Path sentinel = directory.resolve("owners-save.txt");
            Files.writeString(sentinel, "Keep this save intact");
            context.setScreen(TitleScreen::new);
            context.clickScreenButton("aresos.home");
            context.waitForScreen(AlertScreen.class);
            check(Files.readString(sentinel).equals("Keep this save intact"), "Existing save overwritten");
            check(!Files.exists(directory.resolve(NetherHome.MANIFEST)), "Existing save adopted");
            Files.writeString(directory.resolve(NetherHome.MANIFEST), "version=1\nseed=49\nx=-64\ny=56\nz=32\n");
            context.setScreen(TitleScreen::new);
            context.clickScreenButton("aresos.home");
            context.waitForScreen(AlertScreen.class);
            check(Files.readString(sentinel).equals("Keep this save intact"), "Malformed manifest overwrote existing save");
            Files.delete(directory.resolve(NetherHome.MANIFEST));
            NetherHome.writeManifest(directory, NetherHome.DEFAULT_SITE);
            context.setScreen(TitleScreen::new);
            context.clickScreenButton("aresos.home");
            context.waitForScreen(AlertScreen.class);
            check(!Files.exists(directory.resolve("level.dat")), "Incomplete save was silently replaced");
            Files.delete(directory.resolve(NetherHome.MANIFEST));
            Files.delete(sentinel);
            Files.delete(directory);
            Files.move(backup, directory);
            context.setScreen(TitleScreen::new);
        } catch (IOException error) { throw new AssertionError(error); }
    }

    private static Path homeDir() { return Path.of(System.getProperty("aresos.homeReviewDir")); }
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
