package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.HomeSites;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.AlertScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

public final class HomeChoiceClientGameTest implements FabricClientGameTest {
    private static final long TYPED_SEED = -812345678901234567L;
    private static final Vec3 PICKED = new Vec3(20.25, 180, 20.75);

    @Override
    public void runTest(ClientGameTestContext context) {
        Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
        NetherHome.Site naturalSite;
        List<BlockState> natural;
        try (var reference = context.worldBuilder().setUseConsistentSettings(false).adjustSettings(settings ->
                settings.setSeed(Long.toString(TYPED_SEED))).create()) {
            naturalSite = reference.getServer().computeOnServer(server -> {
                try { return HomeSites.find(server.getLevel(Level.NETHER)); }
                catch (IOException error) { throw new AssertionError(error); }
            });
            natural = reference.getServer().computeOnServer(server -> snapshot(server.getLevel(Level.NETHER), naturalSite.floor(), 8, -1, 10));
        }
        archiveThroughUi(context, directory);
        context.clickScreenButton("Home: Flat");
        screenshot(context, "04c-create-default");
        context.clickScreenButton("50");
        assertCreateSettings(context, "50", false);
        context.clickScreenButton("26");
        assertCreateSettings(context, "26", false);
        context.clickScreenButton("49");
        assertCreateSettings(context, "49", true);
        context.runOnClient(client -> {
            var seed = seedBox(client);
            seed.setValue("");
            client.gui.screen().setFocused(seed);
        });
        context.getInput().typeChars(Long.toString(TYPED_SEED));
        assertCreateSettings(context, Long.toString(TYPED_SEED), false);
        screenshot(context, "04c-create-typed-no-hub");
        int audited = ProvisioningAudit.completed;
        var save = createThroughUi(context, directory);
        try (var world = adopt(context, save)) {
            world.getServer().runOnServer(server -> {
                check(server.overworld().getSeed() == TYPED_SEED, "Typed seed was not used");
                check(!server.getWorldData().isAllowCommands(), "Creation enabled cheats");
                var home = NetherHome.get(server);
                check(home.site().equals(naturalSite), "Site search was not deterministic: reference=" + naturalSite + ", provisioned=" + home.site());
                check(ProvisioningAudit.completed == audited + 1, "Placeholder OFF was not audited for block writes");
                var generated = snapshot(server.getLevel(Level.NETHER), naturalSite.floor(), 8, -1, 10);
                var differences = new TreeMap<String, Integer>();
                for (int i = 0; i < natural.size(); i++) if (!natural.get(i).equals(generated.get(i))) {
                    differences.merge(natural.get(i) + " -> " + generated.get(i), 1, Integer::sum);
                }
                AresOs.LOGGER.info("04c independent generated-world comparison (includes intervening terrain ticks): {}", differences);
                check(HomeSites.isSafe(server.getLevel(Level.NETHER), home.home().position()), "Natural arrival was unsafe");
                check(world.getConnection().getServerPlayer().position().distanceToSqr(home.home().position()) < 0.01, "Missed natural arrival");
                AresOs.LOGGER.info("04c typed seed and placeholder OFF PASSED: seed={}, natural site={}, ZERO block writes during provisioning",
                        TYPED_SEED, naturalSite);
            });
            testUnsafeAndHost(context, world);
            setPickedHome(context, world, Level.NETHER);
            testHomeGoInfoAndRespawn(context, world);
            moveAway(world);
        }
        var dimensions = new ArrayList<ResourceKey<Level>>();
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> dimensions.add(client.level.dimension()));
        try (var world = save.open()) {
            assertPickedHome(context, world, Level.NETHER);
            check(dimensions.getLast() == Level.NETHER, "Rejoin packet missed selected Nether home");
            setPickedHome(context, world, Level.OVERWORLD);
            moveAway(world);
        }
        try (var world = save.open()) {
            assertPickedHome(context, world, Level.OVERWORLD);
            check(dimensions.getLast() == Level.OVERWORLD, "Rejoin packet missed selected Overworld home");
            testActualRespawn(context, world, Level.OVERWORLD);
            AresOs.LOGGER.info("04c selected home PASSED: Nether and Overworld exact position/facing persisted through rejoin; actual respawn in both dimensions");
        }
        archiveThroughUi(context, directory);
        context.clickScreenButton("Home: Flat");
        context.clickScreenButton("50");
        context.clickScreenButton("Placeholder hub: OFF");
        assertCreateSettings(context, "50", true);
        screenshot(context, "04c-create-seed-50-hub");
        var second = createThroughUi(context, directory);
        try (var world = adopt(context, second)) {
            world.getServer().runOnServer(server -> {
                var home = NetherHome.get(server);
                var nether = server.getLevel(Level.NETHER);
                check(server.overworld().getSeed() == 50, "Quick pick seed was not used");
                check(Math.abs(home.site().x()) <= 128 && Math.abs(home.site().z()) <= 128, "New site too far from origin");
                NetherHomeGameTests.assertHub(nether, home.site());
                check(HomeSites.isSafe(nether, home.home().position()), "Seed 50 placeholder arrival unsafe");
                check(world.getConnection().getServerPlayer().position().distanceToSqr(home.home().position()) < 0.1, "Missed seed 50 arrival");
                AresOs.LOGGER.info("04c non-49 placeholder ON PASSED: seed=50, site={}", home.site());
            });
        }
        testMarkedDesktop(context);
        AresOs.LOGGER.info("04c client checks passed: seed entry/quick picks/toggle, natural blocks unchanged, safe non-49 hub, "
                + "home set/go/info without cheats, unsafe and guest refusal, exact joins and actual respawn, lossless confirmed save rename, create screenshots");
    }

    private static void testUnsafeAndHost(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var original = NetherHome.get(server).home();
            var level = server.overworld();
            prepare(level);
            player.setGameMode(GameType.CREATIVE);
            player.teleportTo(level, PICKED.x, PICKED.y, PICKED.z, Set.of(), 137, -18, false);
            var foot = BlockPos.containing(PICKED);
            for (int test = 0; test < 6; test++) {
                level.setBlock(foot.below(), (test == 0 ? Blocks.AIR : Blocks.STONE).defaultBlockState(), 2);
                level.setBlock(foot, (test == 1 ? Blocks.LAVA : test == 3 ? Blocks.FIRE : test == 5 ? Blocks.STONE : Blocks.AIR).defaultBlockState(), 2);
                level.setBlock(foot.above().east(), (test == 4 ? Blocks.OAK_PLANKS : Blocks.AIR).defaultBlockState(), 2);
                level.setBlock(foot.above(), (test == 2 ? Blocks.LAVA : test == 4 ? Blocks.FIRE : Blocks.AIR).defaultBlockState(), 2);
                if (test == 3 || test == 4) check(level.getBlockState(test == 3 ? foot : foot.above()).is(Blocks.FIRE), "Fire fixture vanished");
                var before = snapshot(level, foot, 2, -1, 3);
                check(command(server, player, "aresos home set") == 0, "Unsafe home accepted: case " + test);
                check(NetherHome.get(server).home().equals(original), "Unsafe command changed home");
                check(before.equals(snapshot(level, foot, 2, -1, 3)), "Unsafe command changed blocks");
            }
            prepare(level);
            var guest = new ServerPlayer(server, level, new GameProfile(UUID.randomUUID(), "HomeGuest"), ClientInformation.createDefault());
            guest.snapTo(PICKED.x, PICKED.y, PICKED.z, 0, 0);
            for (String action : List.of("", " set", " info")) check(command(server, guest, "aresos home" + action) == 0, "Guest used home" + action);
            check(NetherHome.get(server).home().equals(original), "Guest changed home");
            DesktopWorld.setEnabled(server, false);
            for (String action : List.of("", " set", " info")) check(command(server, player, "aresos home" + action) == 0, "Disabled desktop allowed home" + action);
            check(NetherHome.get(server).home().equals(original), "Disabled desktop changed home");
            DesktopWorld.setEnabled(server, true);
            AresOs.LOGGER.info("04c unsafe/authorization PASSED: no support, lava at feet/head, fire at feet/head, obstructed body; guest and disabled-world refusal");
        });
    }

    private static void setPickedHome(ClientGameTestContext context, TestSingleplayerContext world, ResourceKey<Level> dimension) {
        var before = world.getServer().computeOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var level = server.getLevel(dimension);
            prepare(level);
            player.setGameMode(GameType.CREATIVE);
            player.teleportTo(level, PICKED.x, PICKED.y, PICKED.z, Set.of(), 137, -18, false);
            player.setDeltaMovement(Vec3.ZERO);
            return snapshot(level, BlockPos.containing(PICKED), 2, -1, 3);
        });
        context.waitFor(client -> client.level.dimension() == dimension && client.player.position().distanceToSqr(PICKED) < 0.001);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home set"));
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> {
            var home = NetherHome.get(server).home();
            assertTarget(home, dimension);
            check(before.equals(snapshot(server.getLevel(dimension), BlockPos.containing(PICKED), 2, -1, 3)), "home set changed blocks");
            var player = world.getConnection().getServerPlayer();
            check(player.getRespawnConfig().forced(), "Exact home did not set respawn");
            check(!server.getWorldData().isAllowCommands(), "Home test used cheats");
        });
    }

    private static void testHomeGoInfoAndRespawn(ClientGameTestContext context, TestSingleplayerContext world) {
        var messages = new CopyOnWriteArrayList<String>();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> messages.add(message.getString()));
        moveAway(world);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home info"));
        context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("Seed: " + TYPED_SEED)
                && message.contains("20.250, 180.000, 20.750") && message.contains("minecraft:the_nether")));
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home"));
        context.waitFor(client -> client.level.dimension() == Level.NETHER && client.player.position().distanceToSqr(PICKED) < 0.001);
        world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer().gameMode.getGameModeForPlayer() == GameType.CREATIVE,
                "Going home unexpectedly changed Build mode"));
        testActualRespawn(context, world, Level.NETHER);
    }

    private static void testActualRespawn(ClientGameTestContext context, TestSingleplayerContext world, ResourceKey<Level> dimension) {
        moveAway(world);
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var transition = player.findRespawnPositionAndUseSpawnBlock(true, TeleportTransition.DO_NOTHING);
            check(transition.newLevel().dimension() == dimension && transition.position().equals(PICKED), "Respawn resolver missed exact home");
            // Exercise vanilla's player replacement and respawn packets; Live deliberately prevents real death.
            player.connection.player = server.getPlayerList().respawn(player, false, Entity.RemovalReason.KILLED);
        });
        context.waitFor(client -> client.level.dimension() == dimension && client.player.position().distanceToSqr(PICKED) < 0.001);
        world.getServer().runOnServer(server -> assertTarget(new NetherHome.Home(dimension,
                world.getConnection().getServerPlayer().position(), world.getConnection().getServerPlayer().getYRot(),
                world.getConnection().getServerPlayer().getXRot()), dimension));
    }

    private static void assertPickedHome(ClientGameTestContext context, TestSingleplayerContext world, ResourceKey<Level> dimension) {
        context.waitFor(client -> client.level.dimension() == dimension && client.player.position().distanceToSqr(PICKED) < 0.001);
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            assertTarget(NetherHome.get(server).home(), dimension);
            assertTarget(new NetherHome.Home(player.level().dimension(), player.position(), player.getYRot(), player.getXRot()), dimension);
            check(player.gameMode.getGameModeForPlayer() == GameType.SURVIVAL, "Rejoin did not enter Live");
        });
    }

    private static void assertTarget(NetherHome.Home home, ResourceKey<Level> dimension) {
        check(home.dimension() == dimension, "Selected home dimension changed");
        check(home.position().distanceToSqr(PICKED) < 0.000001, "Selected home lost fractional position: " + home);
        check(Math.abs(home.yaw() - 137) < 0.01 && Math.abs(home.pitch() + 18) < 0.01, "Selected home facing changed: " + home);
    }

    private static void moveAway(TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.setGameMode(GameType.CREATIVE);
            prepare(server.overworld());
            player.teleportTo(server.overworld(), 21.5, 180, 21.5, Set.of(), 0, 0, false);
        });
    }

    private static void prepare(net.minecraft.server.level.ServerLevel level) {
        var feet = BlockPos.containing(PICKED);
        for (BlockPos pos : BlockPos.betweenClosed(feet.offset(-2, -1, -2), feet.offset(2, 3, 2))) {
            level.setBlock(pos, (pos.getY() == feet.getY() - 1 ? Blocks.STONE : Blocks.AIR).defaultBlockState(), 2);
        }
    }

    private static void testMarkedDesktop(ClientGameTestContext context) {
        try (var world = context.worldBuilder().adjustSettings(settings -> settings.setAllowCommands(false)).create()) {
            world.getServer().runOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                player.setGameMode(GameType.CREATIVE);
                prepare(server.overworld());
                player.teleportTo(server.overworld(), PICKED.x, PICKED.y, PICKED.z, Set.of(), 137, -18, false);
                for (String action : List.of("", " set", " info")) check(command(server, player, "aresos home" + action) == 0, "Normal world accepted home" + action);
                check(NetherHome.get(server) == null, "Normal world acquired home data");
                DesktopWorld.setEnabled(server, true);
                check(dev.aresos.hub.HubData.get(server) == null, "A marked desktop world got the flat home's pad and roads");
                var before = snapshot(server.overworld(), BlockPos.containing(PICKED), 2, -1, 3);
                check(command(server, player, "aresos home set") == 1, "Marked desktop could not choose a home");
                assertTarget(NetherHome.get(server).home(), Level.OVERWORLD);
                check(before.equals(snapshot(server.overworld(), BlockPos.containing(PICKED), 2, -1, 3)), "Marked desktop set changed blocks");
            });
        }
    }

    private static int command(MinecraftServer server, ServerPlayer player, String command) {
        try { return server.getCommands().getDispatcher().execute(command, server.createCommandSourceStack().withEntity(player)); }
        catch (com.mojang.brigadier.exceptions.CommandSyntaxException error) { throw new AssertionError(error); }
    }

    private static void archiveThroughUi(ClientGameTestContext context, Path directory) {
        try {
            // Standalone runs also cover the archive flow without requiring any previous suite's world.
            if (!Files.exists(directory)) {
                Files.createDirectory(directory);
                Files.writeString(directory.resolve("keep.txt"), "Existing save must survive");
            }
            var before = fingerprint(directory);
            Set<Path> previous;
            try (var entries = Files.list(directory.getParent())) { previous = entries.collect(java.util.stream.Collectors.toSet()); }
            context.setScreen(TitleScreen::new);
            context.clickScreenButton("aresos.home.new");
            context.waitForScreen(ConfirmScreen.class);
            context.clickScreenButton("gui.cancel");
            check(Files.exists(directory) && fingerprint(directory).equals(before), "Cancel altered existing save");
            if (Files.isRegularFile(directory.resolve("session.lock"))) {
                try (var lock = net.minecraft.util.DirectoryLock.create(directory)) {
                    context.clickScreenButton("aresos.home.new");
                    context.clickScreenButton("Keep old & continue");
                    context.waitForScreen(AlertScreen.class);
                    check(Files.exists(directory), "Locked-save refusal moved the original");
                }
                // Windows forbids reading the locked bytes themselves until the lock has been released.
                check(fingerprint(directory).equals(before), "Locked-save refusal altered data");
                context.setScreen(TitleScreen::new);
            }
            context.clickScreenButton("aresos.home.new");
            context.clickScreenButton("Keep old & continue");
            context.waitForScreen(HomeCreateScreen.class);
            check(!Files.exists(directory), "Old save was not renamed");
            List<Path> archived;
            try (var entries = Files.list(directory.getParent())) {
                archived = entries.filter(path -> !previous.contains(path) && path.getFileName().toString().startsWith("AresHub-")).toList();
            }
            check(archived.size() == 1, "Expected one dated archive: " + archived);
            check(fingerprint(archived.getFirst()).equals(before), "Archive changed or lost save data");
            AresOs.LOGGER.info("04c save rename PASSED: {}, {} files byte-for-byte intact; cancellation also preserved save",
                    archived.getFirst().getFileName(), before.size());
        } catch (IOException error) { throw new AssertionError(error); }
    }

    private static Map<String, String> fingerprint(Path directory) throws IOException {
        var files = new TreeMap<String, String>();
        try (var paths = Files.walk(directory)) {
            for (Path file : paths.filter(Files::isRegularFile).toList()) {
                try {
                    files.put(directory.relativize(file).toString(), HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file))));
                } catch (java.security.NoSuchAlgorithmException error) { throw new AssertionError(error); }
            }
        }
        return files;
    }

    private static List<BlockState> snapshot(net.minecraft.server.level.ServerLevel level, BlockPos center, int radius, int bottom, int top) {
        var blocks = new ArrayList<BlockState>();
        for (BlockPos pos : BlockPos.betweenClosed(center.offset(-radius, bottom, -radius), center.offset(radius, top, radius))) blocks.add(level.getBlockState(pos));
        return List.copyOf(blocks);
    }

    private static TestWorldSaveImpl createThroughUi(ClientGameTestContext context, Path directory) {
        context.clickScreenButton("aresos.home.create");
        context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
        return new TestWorldSaveImpl(context, directory);
    }

    private static TestSingleplayerContext adopt(ClientGameTestContext context, TestWorldSaveImpl save) {
        return new TestSingleplayerContextImpl(context, save, context.computeOnClient(Minecraft::getSingleplayerServer));
    }

    private static EditBox seedBox(Minecraft client) {
        return client.gui.screen().children().stream().filter(EditBox.class::isInstance).map(EditBox.class::cast).findFirst().orElseThrow();
    }

    private static void assertCreateSettings(ClientGameTestContext context, String seed, boolean placeholder) {
        context.runOnClient(client -> {
            check(seedBox(client).getValue().equals(seed), "Seed field differs from selection");
            check(client.gui.screen().children().stream().filter(Button.class::isInstance).map(Button.class::cast)
                    .anyMatch(button -> button.getMessage().getString().equals("Placeholder hub: " + (placeholder ? "ON" : "OFF"))), "Wrong placeholder default/toggle");
        });
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.homeReviewDir")).resolve("04c")));
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
