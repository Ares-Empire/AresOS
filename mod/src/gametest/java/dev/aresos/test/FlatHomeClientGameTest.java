package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ModeInventories;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.FlatHome;
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
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.StringTag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.ServerExplosion;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.level.storage.LevelData;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.Arrays;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Predicate;

/**
 * Package 32, in the real client: the create screen's choice, a flat home made by clicking through it, what the
 * owner sees there, and the promises about an existing save. Coordinates are the design's world coordinates
 * (docs/design/HUB.md 2.1 and 3.2), written out and not taken from the mod's own tables.
 */
public final class FlatHomeClientGameTest implements FabricClientGameTest {
    private static final BlockPos HOME = new BlockPos(0, 64, 0);
    private static final Vec3 SPOT = new Vec3(0.5, 64, 0.5);
    private static final Vec3 AWAY = new Vec3(30.5, 64, 30.5);
    private static final Vec3 PICKED = new Vec3(30.25, 64, 30.75);
    /** A paving block of the north road, far enough ahead to be seen from home. */
    private static final BlockPos EDITED = new BlockPos(1, 63, -6);
    private static final BlockPos CHANGED_BACK = new BlockPos(0, 63, -8);
    /** High enough for the whole cross at a field of view of 110, low enough for it to fill the picture. */
    private static final int ABOVE = 84;

    @Override
    public void runTest(ClientGameTestContext context) {
        Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
        var dimensions = new ArrayList<ResourceKey<Level>>();
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> dimensions.add(client.level.dimension()));
        var messages = new CopyOnWriteArrayList<String>();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> messages.add(message.getString()));

        openCreateScreen(context, directory);
        assertChoice(context, true);
        screenshot(context, "create-flat");
        context.clickScreenButton("Home: Flat");
        assertChoice(context, false);
        screenshot(context, "create-nether");
        context.clickScreenButton("Home: Nether");
        assertChoice(context, true);
        context.clickScreenButton("aresos.home.create");
        context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
        var save = new TestWorldSaveImpl(context, directory);
        HubData.Fixed built;
        List<BlockState> groundBefore;
        try (TestSingleplayerContext world = adopt(context, save)) {
            world.getConnection().waitForChunksRender();
            assertArrival(context, world, dimensions);
            assertNewWorld(world, directory);
            photographViews(context, world);
            assertHomeCommands(context, world, messages);
            assertRespawn(context, world);
            photographAboveInBuildMode(context, world);
            assertHostExplosions(context, world);
            groundBefore = world.getServer().computeOnServer(server -> {
                var level = server.overworld();
                var player = world.getConnection().getServerPlayer();
                check(!LiveMode.isLive(player) && !HubData.protectsFrom(player, EDITED), "Build mode still protects the road");
                check(!HubData.protectsFromExplosions(server), "Build mode still shields the hub from explosions");
                // His edit, made the way a mined block is, and a rule he changes: both must still be there after a restart.
                check(player.gameMode.destroyBlock(EDITED) && level.getBlockState(EDITED).isAir(), "Build mode could not break a road block");
                level.setBlockAndUpdate(EDITED, Blocks.DIAMOND_BLOCK.defaultBlockState());
                check(player.gameMode.destroyBlock(HOME.below()), "Build mode could not mine gold");
                check(HubData.get(server).fixed().blocks().stream().noneMatch(block -> block.pos().equals(HOME.below())),
                        "Gold remained recorded after mining");
                level.setBlockAndUpdate(HOME.below(), Blocks.GOLD_BLOCK.defaultBlockState());
                level.setBlockAndUpdate(CHANGED_BACK, Blocks.DIAMOND_BLOCK.defaultBlockState());
                level.setBlockAndUpdate(CHANGED_BACK, Blocks.CONCRETE.lightBlue().defaultBlockState());
                server.getGameRules().set(GameRules.KEEP_INVENTORY, false, server);
                server.getGameRules().set(GameRules.ADVANCE_WEATHER, true, server);
                check(level.getOverworldClockTime() == 6000, "Time moved while he was there: " + level.getOverworldClockTime());
                assertEmptyOfMobs(level);
                return ground(level);
            });
            built = world.getServer().computeOnServer(server -> HubData.get(server).fixed());
        }

        // The second start, as he does it: the AresOS button on the title screen.
        context.clickScreenButton("aresos.home");
        context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
        try (TestSingleplayerContext world = adopt(context, save)) {
            world.getConnection().waitForChunksRender();
            assertArrival(context, world, dimensions);
            context.waitTicks(10);
            photograph(context, "rejoin");
            world.getServer().runOnServer(server -> {
                var level = server.overworld();
                var player = world.getConnection().getServerPlayer();
                check(ground(level).equals(groundBefore), "The ground around home changed across a restart");
                check(level.getBlockState(EDITED).is(Blocks.DIAMOND_BLOCK), "His edit was undone");
                check(!HubData.protectsFrom(player, EDITED), "A block he changed is still treated as the mod's");
                check(player.gameMode.destroyBlock(EDITED), "He cannot break his own block in Live mode");
                level.setBlockAndUpdate(EDITED, Blocks.DIAMOND_BLOCK.defaultBlockState());
                // Live mode, as the real host: the mod's own blocks stay.
                check(HubData.protectsFromExplosions(server), "Live mode does not shield the hub from explosions");
                check(!HubData.protectsFrom(player, HOME.below()) && player.gameMode.destroyBlock(HOME.below()), "His gold regained protection after restart");
                level.setBlockAndUpdate(HOME.below(), Blocks.GOLD_BLOCK.defaultBlockState());
                check(!HubData.protectsFrom(player, CHANGED_BACK) && player.gameMode.destroyBlock(CHANGED_BACK), "Changed-back road regained protection after restart");
                level.setBlockAndUpdate(CHANGED_BACK, Blocks.CONCRETE.lightBlue().defaultBlockState());
                check(!player.gameMode.destroyBlock(HOME.offset(2, -1, 0)), "Live mode broke an untouched pad block");
                check(!player.gameMode.destroyBlock(new BlockPos(0, 63, -10)) && level.getBlockState(new BlockPos(0, 63, -10)).is(Blocks.CONCRETE.lightBlue()),
                        "Live mode broke the road's centre line");
                var hub = HubData.get(server);
                check(hub != null && hub.fixed().equals(built), "The hub's record changed across a restart");
                assertNames(level, built);
                var rules = server.getGameRules();
                check(!rules.get(GameRules.KEEP_INVENTORY) && rules.get(GameRules.ADVANCE_WEATHER), "A rule he changed was set again");
                check(!rules.get(GameRules.SPAWN_MOBS) && !rules.get(GameRules.ADVANCE_TIME) && !rules.get(GameRules.MOB_GRIEFING),
                        "Rules he did not touch changed");
                check(level.getOverworldClockTime() == 6000, "Time moved across a restart: " + level.getOverworldClockTime());
                assertEmptyOfMobs(level);
                check(NetherHome.get(server).site().equals(FlatHome.SITE), "The saved site changed");
            });
        }
        check(dimensions.size() == 2, "Expected two joins: " + dimensions);
        assertDamagedExactHome(context, save, directory, messages, built);
        assertMissingHomeData(context, save, directory, messages, built);
        AresOs.LOGGER.info("32 client checks passed: create screen choice, flat home by clicking through it, arrival on create, restart, "
                + "/aresos home and respawn, fixed things at the design's coordinates, Live protection as the real host, his edit and "
                + "his rule kept, frozen noon, no mob, missing home data opens unchanged");
    }

    /** Through "New AresOS world…" when a save stands there, as it does after the Nether tests; else through "AresOS". */
    private static void openCreateScreen(ClientGameTestContext context, Path directory) {
        try {
            boolean existed = Files.exists(directory);
            Set<Path> previous;
            try (var entries = Files.list(directory.getParent())) { previous = entries.collect(java.util.stream.Collectors.toSet()); }
            context.setScreen(TitleScreen::new);
            if (existed) {
                context.clickScreenButton("aresos.home.new");
                context.waitForScreen(ConfirmScreen.class);
                context.clickScreenButton("Keep old & continue");
            } else context.clickScreenButton("aresos.home");
            context.waitForScreen(HomeCreateScreen.class);
            if (!existed) return;
            check(!Files.exists(directory), "The old save was not moved aside");
            try (var entries = Files.list(directory.getParent())) {
                var archived = entries.filter(path -> !previous.contains(path) && path.getFileName().toString().startsWith("AresHub-")).toList();
                check(archived.size() == 1 && Files.isDirectory(archived.getFirst()), "Expected the old save under one dated name: " + archived);
            }
        } catch (IOException error) { throw new AssertionError(error); }
    }

    private static void assertChoice(ClientGameTestContext context, boolean flat) {
        context.runOnClient(client -> {
            var screen = client.gui.screen();
            check(screen instanceof HomeCreateScreen, "Not on the create screen: " + screen);
            var buttons = screen.children().stream().filter(Button.class::isInstance).map(button -> ((Button) button).getMessage().getString()).toList();
            var seeds = screen.children().stream().filter(EditBox.class::isInstance).map(EditBox.class::cast).toList();
            check(buttons.contains("Home: " + (flat ? "Flat" : "Nether")), "Wrong home choice shown: " + buttons);
            boolean netherSettings = !seeds.isEmpty() || buttons.stream().anyMatch(text -> text.startsWith("Placeholder hub")
                    || text.equals("49") || text.equals("50") || text.equals("26"));
            if (flat) check(!netherSettings, "The flat choice shows Nether settings: " + buttons);
            else check(seeds.size() == 1 && seeds.getFirst().getValue().equals("49") && buttons.contains("Placeholder hub: ON")
                    && buttons.containsAll(List.of("49", "50", "26")), "The Nether choice lost its settings: " + buttons);
        });
    }

    private static void assertArrival(ClientGameTestContext context, TestSingleplayerContext world, List<ResourceKey<Level>> dimensions) {
        check(dimensions.getLast() == Level.OVERWORLD, "The login packet did not name the Overworld: " + dimensions);
        context.runOnClient(client -> {
            check(client.level.dimension() == Level.OVERWORLD, "Client not in the Overworld");
            check(client.player.position().distanceToSqr(SPOT) < 1.0e-4, "Client is not on the home block: " + client.player.position());
            check(facesNorth(client.player.getYRot(), client.player.getXRot()), "Client does not look north, slightly up: "
                    + client.player.getYRot() + ", " + client.player.getXRot());
            check(client.gameMode.getPlayerMode() == GameType.SURVIVAL, "Client not in Live mode");
        });
        world.getServer().runOnServer(server -> {
            ServerPlayer player = world.getConnection().getServerPlayer();
            check(LiveMode.isLive(player), "Server not in Live mode");
            check(player.level().dimension() == Level.OVERWORLD && player.position().distanceToSqr(SPOT) < 1.0e-4, "Server missed home: " + player.position());
            check(facesNorth(player.getYRot(), player.getXRot()), "Server does not look north, slightly up");
            check(player.blockPosition().equals(HOME), "He does not stand in block (0, 64, 0)");
        });
    }

    private static boolean facesNorth(float yaw, float pitch) {
        return Math.abs(Mth.wrapDegrees(yaw - 180)) < 0.5 && Math.abs(pitch + 8) < 0.5;
    }

    /** Everything brief point 2 to 6 says about a world that was just created. Returns what the hub recorded. */
    private static HubData.Fixed assertNewWorld(TestSingleplayerContext world, Path directory) {
        var fixed = world.getServer().computeOnServer(server -> {
            var level = server.overworld();
            check(server.getWorldData().getLevelName().equals("AresOS"), "Wrong world name");
            check(level.getSeed() == 0, "Wrong seed: " + level.getSeed());
            check(!server.getWorldData().isAllowCommands(), "Cheats enabled");
            check(server.getWorldData().getGameType() == GameType.SURVIVAL, "World not survival");
            check(server.getWorldData().getDifficulty() == Difficulty.NORMAL, "Wrong difficulty");
            check(DesktopWorld.isEnabled(server), "Desktop marker missing");
            var rules = server.getGameRules();
            NetherHomeGameTests.assertRules(rules);
            check(!rules.get(GameRules.ADVANCE_TIME) && !rules.get(GameRules.ADVANCE_WEATHER), "Day or weather cycle is on");
            check(level.getOverworldClockTime() == 6000, "It is not noon: " + level.getOverworldClockTime());
            check(!level.isRaining() && !level.isThundering(), "The weather is not clear");

            check(FlatHome.isFlatHome(level.getChunkSource().getGenerator()), "Not the flat world");
            var structures = ((net.minecraft.world.level.levelgen.FlatLevelSource) level.getChunkSource().getGenerator()).settings().structureOverrides();
            check(structures.isPresent() && structures.get().size() == 0, "Structures are possible");
            // Columns well away from the hub: bedrock, stone to y 59, dirt to y 62, grass at y 63, nothing above, plains.
            for (int[] column : new int[][] {{100, 100}, {-333, 207}, {64, -512}}) {
                for (int y = -64; y <= 80; y++) {
                    Block expected = y == -64 ? Blocks.BEDROCK : y <= 59 ? Blocks.STONE : y <= 62 ? Blocks.DIRT : y == 63 ? Blocks.GRASS_BLOCK : Blocks.AIR;
                    var pos = new BlockPos(column[0], y, column[1]);
                    check(level.getBlockState(pos).is(expected), "Wrong layer at " + pos.toShortString() + ": " + level.getBlockState(pos));
                }
                check(level.getBiome(new BlockPos(column[0], 64, column[1])).is(Biomes.PLAINS), "Not plains at " + column[0] + ", " + column[1]);
            }

            var spawn = server.getRespawnData();
            check(spawn.dimension() == Level.OVERWORLD && spawn.pos().equals(HOME), "World spawn is not the home block: " + spawn);
            check(facesNorth(spawn.yaw(), spawn.pitch()), "World spawn does not look north: " + spawn);
            var home = NetherHome.get(server);
            check(home != null && home.hasExactHome() && home.site().equals(new NetherHome.Site(0, 0, 63, 0, 180)), "Wrong home data");
            check(home.home().dimension() == Level.OVERWORLD && home.home().position().equals(SPOT) && home.home().yaw() == 180
                    && home.home().pitch() == -8, "Wrong home: " + home.home());

            var hub = HubData.get(server);
            check(hub != null, "No hub record");
            check(hub.look().equals("flat-1"), "Wrong look: " + hub.look());
            check(hub.numbers().equals(java.util.Map.ofEntries(java.util.Map.entry("size", 12), java.util.Map.entry("depth", 3),
                    java.util.Map.entry("first", 4), java.util.Map.entry("pitch", 14), java.util.Map.entry("row0", 20),
                    java.util.Map.entry("step", 14), java.util.Map.entry("door_column", 5), java.util.Map.entry("door_width", 2),
                    java.util.Map.entry("door_height", 3), java.util.Map.entry("door_depth", 2), java.util.Map.entry("exit", 6),
                    java.util.Map.entry("road", 5))), "Wrong numbers: " + hub.numbers());
            check(hub.numbers().equals(HubLayout.numbers()), "The record's numbers are not the layout's");
            check(hub.home().equals(GlobalPos.of(Level.OVERWORLD, HOME)), "Wrong home block in the record: " + hub.home());
            FlatHomeGameTests.assertFixedThings(level, HOME, hub.fixed());
            check(level.getEntitiesOfClass(ItemEntity.class, new AABB(HOME).inflate(40)).isEmpty(), "Building littered the hub with drops");
            assertEmptyOfMobs(level);
            return hub.fixed();
        });
        try {
            check(Files.isRegularFile(directory.resolve("level.dat")), "AresHub/level.dat missing");
            check(Files.isRegularFile(directory.resolve("data/aresos/hub.dat")), "data/aresos/hub.dat was not saved with the new world");
            check(Files.isRegularFile(directory.resolve("data/aresos/nether_home.dat")), "The home data was not saved with the new world");
            check(Files.readString(directory.resolve(NetherHome.PROVISIONED)).equals("complete\n"), "Provisioning was not recorded as complete");
            check(NetherHome.readKind(directory) == NetherHome.Kind.FLAT, "The manifest does not name the flat home");
        } catch (IOException error) { throw new AssertionError(error); }
        return fixed;
    }

    /** The arrival view (HUB.md's first picture), then east, south and west from the same spot. */
    private static void photographViews(ClientGameTestContext context, TestSingleplayerContext world) {
        context.waitTicks(20);
        photograph(context, "arrival");
        String[] names = {"east", "south", "west"};
        float[] yaws = {-90, 0, 90};
        for (int i = 0; i < names.length; i++) {
            look(context, world, SPOT, yaws[i], -8);
            photograph(context, names[i]);
        }
        look(context, world, SPOT, 180, -8);
    }

    private static void look(ClientGameTestContext context, TestSingleplayerContext world, Vec3 position, float yaw, float pitch) {
        world.getServer().runOnServer(server -> world.getConnection().getServerPlayer()
                .teleportTo(server.overworld(), position.x, position.y, position.z, Set.of(), yaw, pitch, false));
        context.waitFor(client -> client.player.position().distanceToSqr(position) < 1.0e-4
                && Math.abs(Mth.wrapDegrees(client.player.getYRot() - yaw)) < 0.5 && Math.abs(client.player.getXRot() - pitch) < 0.5);
        context.waitTicks(5);
    }

    /** /aresos home info, /aresos home and /aresos home set, in Live mode and with cheats off. */
    private static void assertHomeCommands(ClientGameTestContext context, TestSingleplayerContext world, List<String> messages) {
        var before = world.getServer().computeOnServer(server -> ground(server.overworld()));
        look(context, world, AWAY, 0, 0);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home info"));
        context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("Seed: 0") && message.contains("0.500, 64.000, 0.500")
                && message.contains("minecraft:overworld") && message.contains("180.0, -8.0")));
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home"));
        context.waitFor(client -> client.player.position().distanceToSqr(SPOT) < 1.0e-4 && facesNorth(client.player.getYRot(), client.player.getXRot()));
        // Package 37: /home and the H key do what /aresos home does.
        look(context, world, AWAY, 0, 0);
        context.runOnClient(client -> client.player.connection.sendCommand("home"));
        context.waitFor(client -> client.player.position().distanceToSqr(SPOT) < 1.0e-4 && facesNorth(client.player.getYRot(), client.player.getXRot()));
        look(context, world, AWAY, 0, 0);
        context.getInput().pressKey(org.lwjgl.glfw.GLFW.GLFW_KEY_H);
        context.waitFor(client -> client.player.position().distanceToSqr(SPOT) < 1.0e-4 && facesNorth(client.player.getYRot(), client.player.getXRot()));

        look(context, world, PICKED, 137, -18);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home set"));
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> {
            var home = NetherHome.get(server).home();
            check(home.dimension() == Level.OVERWORLD && home.position().distanceToSqr(PICKED) < 1.0e-6
                    && Math.abs(home.yaw() - 137) < 0.01 && Math.abs(home.pitch() + 18) < 0.01, "home set did not record the spot: " + home);
        });
        // Back to the designed spot the same way, so the restart below arrives on the pad again.
        look(context, world, SPOT, 180, -8);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos home set"));
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> {
            var home = NetherHome.get(server).home();
            check(home.dimension() == Level.OVERWORLD && home.position().distanceToSqr(SPOT) < 1.0e-6 && facesNorth(home.yaw(), home.pitch()),
                    "home set did not record the pad again: " + home);
            check(ground(server.overworld()).equals(before), "A home command changed blocks");
            check(LiveMode.isLive(world.getConnection().getServerPlayer()), "A home command left Live mode");
            check(!server.getWorldData().isAllowCommands(), "The home commands needed cheats");
        });
    }

    private static void assertRespawn(ClientGameTestContext context, TestSingleplayerContext world) {
        look(context, world, AWAY, 0, 0);
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var transition = player.findRespawnPositionAndUseSpawnBlock(true, TeleportTransition.DO_NOTHING);
            check(transition.newLevel().dimension() == Level.OVERWORLD && transition.position().distanceToSqr(SPOT) < 1.0e-6,
                    "Respawn would miss home: " + transition.position());
            // The game's own player replacement and respawn packets; Live mode prevents a real death.
            player.connection.player = server.getPlayerList().respawn(player, false, Entity.RemovalReason.KILLED);
        });
        context.waitFor(client -> client.level.dimension() == Level.OVERWORLD && client.player.position().distanceToSqr(SPOT) < 1.0e-4
                && facesNorth(client.player.getYRot(), client.player.getXRot()));
        world.getServer().runOnServer(server -> check(LiveMode.isLive(world.getConnection().getServerPlayer()), "Respawn left Live mode"));
    }

    private static void photographAboveInBuildMode(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().setGameMode(GameType.CREATIVE));
        context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
        waitForServer(context, world, server -> {
            var player = world.getConnection().getServerPlayer();
            return player.gameMode.getGameModeForPlayer() == GameType.CREATIVE && !ModeInventories.of(player).pending();
        }, "The switch to Build mode did not finish");
        // Up first, then flying: a flying player who still stands on the ground is landed again by his own client.
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(server.overworld(), SPOT.x, ABOVE, SPOT.z, Set.of(), 180, 90, false);
            player.getAbilities().flying = true;
            player.onUpdateAbilities();
        });
        context.waitFor(client -> client.player.getAbilities().flying && Math.abs(client.player.getY() - ABOVE) < 2
                && client.player.getDeltaMovement().lengthSqr() < 1.0e-6 && Math.abs(client.player.getXRot() - 90) < 0.5);
        world.getConnection().waitForChunksRender();
        int fov = context.computeOnClient(client -> client.options.fov().get());
        context.runOnClient(client -> client.options.fov().set(110));
        // Long enough for the action-bar lines of the home commands to fade.
        context.waitTicks(70);
        photograph(context, "above-build");
        context.runOnClient(client -> client.options.fov().set(fov));
    }

    private static void assertHostExplosions(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(DesktopWorld.isHost(server, player), "Fixture: player is not the real host");
            check(!HubData.protectsFromExplosions(server), "Build host did not disable explosion protection");
            BlockPos road = new BlockPos(12, 63, 0);
            explode(server.overworld(), player, Vec3.atCenterOf(road.above()));
            check(server.overworld().getBlockState(road).isAir(), "An explosion in host Build mode spared the road");
            check(HubData.get(server).fixed().blocks().stream().noneMatch(block -> block.pos().equals(road)),
                    "An exploded block stayed in the record");
            assertNames(server.overworld(), HubData.get(server).fixed());
            player.setGameMode(GameType.SURVIVAL);
        });
        waitForMode(context, world, GameType.SURVIVAL);
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(HubData.protectsFromExplosions(server), "Live host did not enable explosion protection");
            var before = HubData.get(server).fixed();
            explode(server.overworld(), player, Vec3.atCenterOf(new BlockPos(0, 64, 12)));
            check(server.overworld().getBlockState(new BlockPos(0, 63, 12)).is(Blocks.CONCRETE.yellow()),
                    "An explosion in host Live mode broke the road");
            check(HubData.get(server).fixed().equals(before), "A Live explosion removed recorded blocks");
            player.setGameMode(GameType.CREATIVE);
        });
        waitForMode(context, world, GameType.CREATIVE);
    }

    private static void waitForMode(ClientGameTestContext context, TestSingleplayerContext world, GameType mode) {
        context.waitFor(client -> client.gameMode.getPlayerMode() == mode);
        waitForServer(context, world, server -> world.getConnection().getServerPlayer().gameMode.getGameModeForPlayer() == mode
                && !ModeInventories.of(world.getConnection().getServerPlayer()).pending(), "Mode switch did not finish: " + mode);
    }

    private static void explode(ServerLevel level, ServerPlayer player, Vec3 centre) {
        var tnt = new net.minecraft.world.entity.item.PrimedTnt(level, centre.x, centre.y, centre.z, player);
        new ServerExplosion(level, tnt, null, null, centre, 4, false, Explosion.BlockInteraction.DESTROY).explode();
    }

    /** Open real saved NBT, including a Vec3 decode with a partial value that SavedDataStorage would accept. */
    private static void assertDamagedExactHome(ClientGameTestContext context, TestWorldSaveImpl save, Path directory,
                                                List<String> messages, HubData.Fixed built) {
        Path file = directory.resolve("data/aresos/nether_home.dat");
        var respawn = new ServerPlayer.RespawnConfig(LevelData.RespawnData.of(Level.OVERWORLD,
                BlockPos.containing(AWAY), 73, 0), true);
        List<BlockState> before;
        try (var world = save.open()) {
            before = world.getServer().computeOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                player.teleportTo(server.overworld(), AWAY.x, AWAY.y, AWAY.z, Set.of(), 0, 0, false);
                player.setRespawnPosition(respawn, false);
                check(DesktopWorld.isEnabled(server), "Fixture: arrival must be enabled for the damaged-data regression");
                return ground(server.overworld());
            });
        }
        try {
            byte[] original = Files.readAllBytes(file);
            for (String damage : List.of("missing", "malformed", "partial")) {
                NbtIo.writeCompressed(readDamagedHome(file, original, damage), file);
                byte[] damaged = Files.readAllBytes(file);
                messages.clear();
                try (var world = save.open()) {
                    context.waitTicks(20);
                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer();
                        check(NetherHome.get(server) == null, damage + " exact home was accepted");
                        check(player.level().dimension() == Level.OVERWORLD && player.position().distanceToSqr(AWAY) < 0.01,
                                damage + " exact home caused arrival: " + player.level().dimension() + " " + player.position());
                        check(respawn.equals(player.getRespawnConfig()), damage + " exact home changed respawn");
                        check(DesktopWorld.isEnabled(server), damage + " exact home changed the desktop marker");
                        check(ground(server.overworld()).equals(before), damage + " exact home changed blocks");
                        check(HubData.get(server).fixed().equals(built), damage + " exact home changed the hub record");
                        assertNames(server.overworld(), built);
                        check(!server.getGameRules().get(GameRules.KEEP_INVENTORY)
                                && server.getGameRules().get(GameRules.ADVANCE_WEATHER), damage + " exact home reset rules");
                    });
                    context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("AresOS home data")
                            && message.contains("unchanged")));
                    context.runOnClient(client -> client.player.connection.sendCommand("aresos home set"));
                    world.getConnection().waitForServerboundPackets();
                    world.getServer().runOnServer(server -> check(NetherHome.get(server) == null, "home set repaired damaged data"));
                }
                check(Arrays.equals(damaged, Files.readAllBytes(file)), damage + " exact home was rewritten");
                check(Files.readString(directory.resolve(NetherHome.PROVISIONED)).equals("complete\n"), "Provisioning claim changed");
                AresOs.LOGGER.info("32 damaged flat home regression passed: {} nested home, no arrival/respawn/rebuild/write", damage);
            }
            Files.write(file, original);
        } catch (IOException error) { throw new AssertionError(error); }
    }

    private static CompoundTag readDamagedHome(Path file, byte[] original, String damage) throws IOException {
        Files.write(file, original);
        CompoundTag root = NbtIo.readCompressed(file, NbtAccounter.unlimitedHeap());
        var data = root.getCompoundOrEmpty("data");
        check(data.contains("home"), "Fixture: exact home missing before corruption");
        switch (damage) {
            case "missing" -> data.remove("home");
            case "malformed" -> data.putString("home", "unreadable");
            case "partial" -> data.getCompoundOrEmpty("home").getListOrEmpty("position").add(StringTag.valueOf("bad fourth coordinate"));
            default -> throw new AssertionError(damage);
        }
        return root;
    }

    /**
     * Brief point 8 for the flat home: a save whose home data is gone opens unchanged, with the message, and nothing
     * is built or set again. The save is left in a state unlike a new flat home first, so "unchanged" can be seen.
     */
    private static void assertMissingHomeData(ClientGameTestContext context, TestWorldSaveImpl save, Path directory,
                                              List<String> messages, HubData.Fixed built) {
        List<BlockState> groundBefore;
        try (var world = save.open()) {
            groundBefore = world.getServer().computeOnServer(server -> {
                var player = world.getConnection().getServerPlayer();
                player.setGameMode(GameType.CREATIVE);
                player.teleportTo(server.overworld(), AWAY.x, AWAY.y, AWAY.z, Set.of(), 0, 0, false);
                DesktopWorld.setEnabled(server, false);
                var rules = server.getGameRules();
                rules.set(GameRules.SPAWN_PHANTOMS, true, server);
                rules.set(GameRules.MOB_GRIEFING, true, server);
                server.setDifficulty(Difficulty.HARD, true);
                // Gold was already relinquished above. Keep the record stable while making a rebuild visible.
                check(HubData.get(server).fixed().blocks().stream().noneMatch(block -> block.pos().equals(HOME.below())),
                        "Fixture: gold is still owned before the missing-data edit");
                server.overworld().setBlockAndUpdate(HOME.below(), Blocks.EMERALD_BLOCK.defaultBlockState());
                return ground(server.overworld());
            });
        }
        try {
            check(Files.readString(directory.resolve(NetherHome.PROVISIONED)).equals("complete\n"), "The provisioning claim changed");
            Files.delete(directory.resolve("data/aresos/nether_home.dat"));
        } catch (IOException error) { throw new AssertionError(error); }
        messages.clear();
        try (var world = save.open()) {
            context.waitTicks(30);
            world.getServer().runOnServer(server -> {
                var level = server.overworld();
                var changed = new ArrayList<String>();
                if (!ground(level).equals(groundBefore)) changed.add("blocks");
                var rules = server.getGameRules();
                if (!rules.get(GameRules.SPAWN_PHANTOMS) || !rules.get(GameRules.MOB_GRIEFING) || rules.get(GameRules.KEEP_INVENTORY)
                        || !rules.get(GameRules.ADVANCE_WEATHER) || rules.get(GameRules.SPAWN_MOBS) || rules.get(GameRules.ADVANCE_TIME)) changed.add("rules");
                if (DesktopWorld.isEnabled(server)) changed.add("desktop marker");
                if (server.getWorldData().getDifficulty() != Difficulty.HARD) changed.add("difficulty");
                if (level.getOverworldClockTime() != 6000) changed.add("time");
                var hub = HubData.get(server);
                if (hub == null || !hub.fixed().equals(built)) changed.add("hub record");
                check(changed.isEmpty(), "Missing home data changed the save: " + changed);
                assertNames(level, built);
                check(NetherHome.get(server) == null, "Missing home data was silently recreated");
                var player = world.getConnection().getServerPlayer();
                check(player.position().distanceToSqr(AWAY) < 1 && player.gameMode.getGameModeForPlayer() == GameType.CREATIVE,
                        "Missing home data still moved him or changed his mode: " + player.position());
            });
            context.waitFor(client -> messages.stream().anyMatch(message -> message.contains("AresOS home data") && message.contains("unchanged")));
            // Not photograph(): that clears the chat, and the message is what this picture is for.
            screenshot(context, "missing-home-data");
            world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
        }
        check(!Files.exists(directory.resolve("data/aresos/nether_home.dat")), "Missing home data was rewritten on shutdown");
        check(Files.isRegularFile(directory.resolve("data/aresos/hub.dat")), "The hub record was lost");
    }

    /** Still the four names the world was built with, each alive, and no fifth: nothing built them a second time. */
    private static void assertNames(ServerLevel level, HubData.Fixed built) {
        for (var id : built.names()) {
            var name = level.getEntity(id);
            check(name instanceof Display.TextDisplay && name.isAlive(), "A group name is gone: " + id);
        }
        int displays = level.getEntitiesOfClass(Display.TextDisplay.class, new AABB(HOME).inflate(60)).size();
        check(displays == 4, "Expected four group names around home, found " + displays);
    }

    private static void assertEmptyOfMobs(ServerLevel level) {
        var mobs = new ArrayList<String>();
        for (Entity entity : level.getAllEntities()) if (entity instanceof Mob) mobs.add(entity.getType().toShortString() + " at " + entity.blockPosition().toShortString());
        check(mobs.isEmpty(), "Mobs in the flat home: " + mobs);
    }

    /** The floor and the two layers above it, in the square the hub lies in. */
    private static List<BlockState> ground(ServerLevel level) {
        var blocks = new ArrayList<BlockState>();
        for (BlockPos pos : BlockPos.betweenClosed(HOME.offset(-27, -1, -27), HOME.offset(27, 1, 27))) blocks.add(level.getBlockState(pos));
        return List.copyOf(blocks);
    }

    private static void waitForServer(ClientGameTestContext context, TestSingleplayerContext world, Predicate<MinecraftServer> done, String failure) {
        for (int tick = 0; tick < 200; tick++) {
            if (world.getServer().computeOnServer(done::test)) return;
            context.waitTicks(1);
        }
        throw new AssertionError(failure);
    }

    private static TestSingleplayerContext adopt(ClientGameTestContext context, TestWorldSaveImpl save) {
        // Fabric has no API for adopting a world opened by a real UI button; this wrapper only supplies test synchronization.
        return new TestSingleplayerContextImpl(context, save, context.computeOnClient(Minecraft::getSingleplayerServer));
    }

    /** A picture of the world without chat lines or toasts from the steps before it. */
    private static void photograph(ClientGameTestContext context, String name) {
        context.runOnClient(client -> {
            client.gui.hud.getChat().clearMessages(true);
            client.gui.toastManager().clear();
        });
        context.waitTicks(2);
        screenshot(context, name);
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.hubReviewDir"))));
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
