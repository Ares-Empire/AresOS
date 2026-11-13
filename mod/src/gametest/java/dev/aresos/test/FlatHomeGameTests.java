package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.HubLayout.Group;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.FlatHome;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.NaturalSpawner;
import net.minecraft.world.level.ServerExplosion;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.gamerules.GameRule;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.levelgen.FlatLevelSource;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.TagValueOutput;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Package 32. The hub tests build far from the test plots: a hub is 49 x 49 blocks and would cover other tests.
 * "Far" is measured from the test's own plot, which the test server puts at new random coordinates in every run:
 * the test world can be kept between runs, so no fixed place is known to be untouched ground.
 * Coordinates are written out as docs/design/HUB.md 3.2 states them, relative to the home block.
 */
public final class FlatHomeGameTests {
    private static final int TEN_MINUTES = 12000;
    /**
     * The control of the no-mob test must see a mob within this many ticks, counted from the moment the ground around
     * home is loaded. A slime came after 44 to 83 ticks on a quiet laptop and after 819 with other builds running,
     * when most of those ticks passed before the chunks were there.
     */
    private static final int CONTROL_LIMIT = 2400;
    /** The test server runs ticks as fast as it can; chunks load at the disk's and the other builds' pace. */
    private static final int LOAD_LIMIT = 6000;
    private static final List<GameRule<Boolean>> SWITCHES = List.of(GameRules.SPAWN_MOBS, GameRules.MOB_GRIEFING, GameRules.KEEP_INVENTORY,
            GameRules.SPAWN_PHANTOMS, GameRules.SPAWN_PATROLS, GameRules.SPAWN_WANDERING_TRADERS, GameRules.ADVANCE_TIME, GameRules.ADVANCE_WEATHER);

    @GameTest(environment = "aresos-test:home")
    public void flatHomeRulesAreTheNetherOnesPlusFrozenTimeAndWeather(GameTestHelper helper) {
        var nether = new GameRules(helper.getLevel().enabledFeatures());
        NetherHome.applyRules(nether, null);
        check(nether.get(GameRules.ADVANCE_TIME) && nether.get(GameRules.ADVANCE_WEATHER), "The Nether home's rules changed");
        var rules = new GameRules(helper.getLevel().enabledFeatures());
        check(rules.get(GameRules.ADVANCE_TIME) && rules.get(GameRules.ADVANCE_WEATHER), "Fixture: the two rules are not on by default");
        FlatHome.applyRules(rules, null);
        NetherHomeGameTests.assertRules(rules);
        check(!rules.get(GameRules.ADVANCE_TIME), "The day cycle is on");
        check(!rules.get(GameRules.ADVANCE_WEATHER), "The weather cycle is on");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:home")
    public void flatWorldHasTheDesignedLayersAndNoStructures(GameTestHelper helper) {
        var server = helper.getLevel().getServer();
        var generator = FlatHome.dimensions(server.registryAccess()).overworld();
        check(FlatHome.isFlatHome(generator), "The created world is not recognised as the flat home");
        var settings = ((FlatLevelSource) generator).settings();
        // Index 0 is y -64: bedrock, 123 stone (y -63 to 59), 3 dirt (y 60 to 62), grass at y 63, nothing above.
        var layers = settings.getLayers();
        for (int y = -64; y <= 64; y++) {
            Block expected = y == -64 ? Blocks.BEDROCK : y <= 59 ? Blocks.STONE : y <= 62 ? Blocks.DIRT : y == 63 ? Blocks.GRASS_BLOCK : null;
            var state = y + 64 < layers.size() ? layers.get(y + 64) : null;
            check(expected == null ? state == null || state.isAir() : state != null && state.is(expected), "Wrong layer at y " + y + ": " + state);
        }
        check(settings.getBiome().is(Biomes.PLAINS), "Biome is not plains");
        check(settings.structureOverrides().isPresent() && settings.structureOverrides().get().size() == 0, "Structures are possible");
        check(settings.adjustGenerationSettings(settings.getBiome()).features().stream().allMatch(step -> step.size() == 0),
                "The flat world places features");
        // The test server's own world is vanilla's default flat preset: flat, but not ours.
        check(!FlatHome.isFlatHome(helper.getLevel().getChunkSource().getGenerator()), "A default flat world passes as the flat home");
        check(!FlatHome.isFlatHome(net.minecraft.world.level.levelgen.presets.WorldPresets.createNormalWorldDimensions(server.registryAccess()).overworld()),
                "A normal world passes as the flat home");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:home")
    public void fixedThingsStandWhereTheDesignPutsThem(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos home = homeAt(level, far(helper, 3000, 0));
        assertFixedThings(level, home, build(level, home));
        helper.succeed();
    }

    /**
     * The pad, the four avenues and the four names around {@code home}, as HUB.md 3.2 states them, with nothing else
     * built in the square they lie in, and a record that lists exactly these. The client test calls this for the
     * real world, where home is (0, 64, 0) and these offsets are the design's world coordinates.
     */
    public static void assertFixedThings(ServerLevel level, BlockPos home, HubData.Fixed fixed) {
        var expected = new HashMap<BlockPos, Block>();
        for (int x = -2; x <= 2; x++) for (int z = -2; z <= 2; z++) expected.put(home.offset(x, -1, z), Blocks.POLISHED_BLACKSTONE_BRICKS);
        expected.put(home.below(), Blocks.GOLD_BLOCK);
        for (int out = 3; out <= 24; out++) for (int side = -2; side <= 2; side++) {
            expected.put(home.offset(side, -1, -out), side == 0 ? Blocks.CONCRETE.lightBlue() : Blocks.POLISHED_BLACKSTONE_BRICKS);
            expected.put(home.offset(out, -1, side), side == 0 ? Blocks.CONCRETE.red() : Blocks.POLISHED_BLACKSTONE_BRICKS);
            expected.put(home.offset(side, -1, out), side == 0 ? Blocks.CONCRETE.yellow() : Blocks.POLISHED_BLACKSTONE_BRICKS);
            expected.put(home.offset(-out, -1, side), side == 0 ? Blocks.CONCRETE.purple() : Blocks.POLISHED_BLACKSTONE_BRICKS);
        }
        check(expected.size() == 25 + 4 * 22 * 5, "Fixture: expected block count is " + expected.size());
        // The whole square the hub lies in, floor and the layer above: every block is either an expected one or untouched.
        for (BlockPos pos : BlockPos.betweenClosed(home.offset(-27, -1, -27), home.offset(27, -1, 27))) {
            Block want = expected.getOrDefault(pos, Blocks.GRASS_BLOCK);
            check(level.getBlockState(pos).is(want), "Floor at " + pos.subtract(home) + " is " + level.getBlockState(pos) + ", not " + want);
            check(level.getBlockState(pos.above()).isAir(), "Something was built above the floor at " + pos.subtract(home));
        }
        check(fixed.blocks().size() == expected.size(), "Recorded " + fixed.blocks().size() + " blocks, built " + expected.size());
        for (var placed : fixed.blocks()) {
            Block want = expected.get(placed.pos());
            check(want != null && placed.block().equals(net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(want).toString()),
                    "Record does not match the build at " + placed.pos().subtract(home) + ": " + placed.block());
        }
        check(new HashSet<>(fixed.blocks().stream().map(HubData.Placed::pos).toList()).size() == fixed.blocks().size(), "A position is recorded twice");

        String[] words = {"INTERNET", "GAMES", "SYSTEM & TOOLS", "WORK & MEDIA"};
        Vec3[] places = {new Vec3(0.5, 9, -19.5), new Vec3(20.5, 9, 0.5), new Vec3(0.5, 9, 20.5), new Vec3(-19.5, 9, 0.5)};
        String[] colours = {"#3AB3DA", "#FF6257", "#FED83D", "#C774F2"};
        check(fixed.names().size() == 4 && new HashSet<>(fixed.names()).size() == 4, "Expected four different group names");
        for (int i = 0; i < 4; i++) {
            Entity name = level.getEntity(fixed.names().get(i));
            check(name instanceof Display.TextDisplay, words[i] + " is not a text display: " + name);
            Vec3 want = Vec3.atLowerCornerOf(home).add(places[i]);
            check(name.position().distanceToSqr(want) < 1.0e-6, words[i] + " hangs at " + name.position() + ", not " + want);
            CompoundTag tag = saved(level, name);
            var text = tag.getCompoundOrEmpty("text");
            check(text.getStringOr("text", "").equals(words[i]), "Wrong word: " + tag.get("text"));
            check(text.getStringOr("color", "").equalsIgnoreCase(colours[i]), "Wrong colour for " + words[i] + ": " + text.get("color"));
            check(tag.getStringOr("billboard", "").equals("vertical"), words[i] + " does not turn around the upright axis");
            check(tag.getFloatOr("view_range", 0) == 2.5f, words[i] + " is not seen from 160 blocks");
            check(tag.getIntOr("background", 0) == 0xC0000000, words[i] + " does not hang on the dark plate");
            var brightness = tag.getCompoundOrEmpty("brightness");
            check(brightness.getIntOr("sky", -1) == 15 && brightness.getIntOr("block", -1) == 15, words[i] + " is not at full brightness");
            var scale = tag.getCompoundOrEmpty("transformation").getListOrEmpty("scale");
            check(scale.size() == 3 && scale.getFloatOr(0, 0) == 3 && scale.getFloatOr(1, 0) == 3 && scale.getFloatOr(2, 0) == 3,
                    words[i] + " has scale " + scale);
        }
    }

    @GameTest(environment = "aresos-test:home")
    public void hubIsNotBuiltWhereSomethingStands(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos home = homeAt(level, far(helper, 6000, 0));
        BlockPos hisFloor = home.offset(1, -1, 0);
        BlockPos underHisBuild = home.offset(0, -1, -10);
        level.setBlockAndUpdate(hisFloor, Blocks.DIAMOND_BLOCK.defaultBlockState());
        level.setBlockAndUpdate(underHisBuild.above(), Blocks.OAK_PLANKS.defaultBlockState());
        var fixed = build(level, home);
        check(level.getBlockState(hisFloor).is(Blocks.DIAMOND_BLOCK), "A block that was not grass was replaced");
        check(level.getBlockState(underHisBuild).is(Blocks.GRASS_BLOCK) && level.getBlockState(underHisBuild.above()).is(Blocks.OAK_PLANKS),
                "The ground under a standing block was paved");
        check(fixed.blocks().stream().noneMatch(placed -> placed.pos().equals(hisFloor) || placed.pos().equals(underHisBuild)),
                "A block the mod did not place is in its record");
        check(fixed.blocks().size() == 465 - 2, "Everything else should be built: " + fixed.blocks().size());
        check(level.getBlockState(home.below()).is(Blocks.GOLD_BLOCK), "The rest of the pad is missing");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:home")
    public void explosionPolicyUsesOnlyTheHostMode(GameTestHelper helper) {
        check(HubData.protectsFromExplosions((GameType) null), "An unknown host must be protected");
        for (GameType mode : GameType.values()) {
            check(HubData.protectsFromExplosions(mode) == (mode != GameType.CREATIVE), "Wrong host policy for " + mode);
        }
        helper.succeed();
    }

    /** Server tests have no singleplayer host; the real host's Live/Build explosions are in the client test. */
    @GameTest(environment = "aresos-test:flat_hub")
    public void liveModeProtectsHubBlocksAndBuildModeDoesNot(GameTestHelper helper) {
        var level = helper.getLevel();
        var server = level.getServer();
        boolean marked = DesktopWorld.isEnabled(server);
        ServerPlayer player = join(level, "FlatHubTest");
        try {
            DesktopWorld.setEnabled(server, true);
            // At x 15, z 3 within its chunk, the west name hangs in the chunk the build loads last: the layout in which
            // a freshly loaded chunk does not show its entities yet (see build below).
            BlockPos column = far(helper, 9000, 0);
            BlockPos home = homeAt(level, new BlockPos((column.getX() & ~15) + 15, 0, (column.getZ() & ~15) + 3));
            var fixed = build(level, home);
            HubData.store(server, new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), fixed));
            player.snapTo(home.getX() + 0.5, home.getY(), home.getZ() + 0.5, 180, 0);
            BlockPos gold = home.below();
            BlockPos road = Group.N.block(home, 10, 0, -1);
            BlockPos grass = home.offset(3, -1, 3);

            check(LiveMode.isLive(player), "Fixture: the player is not in Live mode");
            check(!player.gameMode.destroyBlock(gold) && level.getBlockState(gold).is(Blocks.GOLD_BLOCK), "Live mode broke the gold block");
            check(!player.gameMode.destroyBlock(road) && level.getBlockState(road).is(Blocks.CONCRETE.lightBlue()), "Live mode broke the road");
            check(player.gameMode.destroyBlock(grass) && level.getBlockState(grass).isAir(), "Live mode could not break plain ground");
            level.setBlockAndUpdate(grass, Blocks.GRASS_BLOCK.defaultBlockState());
            // Right above the pad's corner: the pad block below and the grass diagonally below are both in reach.
            explode(level, player, Vec3.atCenterOf(home.offset(2, 0, 2)));
            check(level.getBlockState(grass).isAir(), "Fixture: the explosion did not reach the ground beside the pad");
            check(fixed.blocks().stream().allMatch(placed -> !level.getBlockState(placed.pos()).isAir()), "An explosion in Live mode broke hub blocks");
            for (UUID name : fixed.names()) {
                Entity display = level.getEntity(name);
                check(display != null && display.isAlive(), "An explosion removed a group name");
                check(!display.hurtServer(level, level.damageSources().playerAttack(player), 100) && display.isAlive(), "A group name was hit");
            }
            explode(level, player, level.getEntity(fixed.names().getFirst()).position());
            check(level.getEntity(fixed.names().getFirst()).isAlive(), "An explosion at a group name removed it");

            // Another dimension's blocks at the same coordinates are not the hub's.
            HubData.store(server, new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(Level.NETHER, home), fixed));
            check(!HubData.protectsFrom(player, gold), "The record of another dimension protects this one");
            HubData.store(server, new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), fixed));
            check(HubData.protectsFrom(player, gold), "Fixture: the record is back");

            mode(player, GameType.CREATIVE);
            check(!DesktopWorld.isHost(server, player) && HubData.protectsFromExplosions(server),
                    "A creative guest with no identifiable host disabled explosion protection");
            check(player.gameMode.destroyBlock(gold), "Build mode could not break gold");
            check(HubData.get(server).fixed().blocks().stream().noneMatch(block -> block.pos().equals(gold)),
                    "Mining did not immediately remove gold from the record");
            level.setBlockAndUpdate(gold, Blocks.GOLD_BLOCK.defaultBlockState());
            check(player.gameMode.destroyBlock(road) && level.getBlockState(road).isAir(), "Build mode could not break the road");
            // A replacement changed back to the original concrete is still his.
            level.setBlockAndUpdate(road, Blocks.DIAMOND_BLOCK.defaultBlockState());
            level.setBlockAndUpdate(road, Blocks.CONCRETE.lightBlue().defaultBlockState());
            BlockPos replaced = Group.W.block(home, 10, 0, -1);
            level.setBlockAndUpdate(replaced, Blocks.DIAMOND_BLOCK.defaultBlockState());
            level.setBlockAndUpdate(replaced, Blocks.CONCRETE.purple().defaultBlockState());
            check(HubData.get(server).fixed().blocks().stream().noneMatch(block -> block.pos().equals(replaced)),
                    "Replacing a block did not immediately remove its record");
            // An observed mismatch must also be forgotten, even when it predates this in-memory record.
            BlockPos stale = home.offset(3, -1, 3);
            var observed = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home),
                    new HubData.Fixed(List.of(new HubData.Placed(stale, "minecraft:gold_block")), List.of()));
            check(!observed.holds(level, stale) && observed.fixed().blocks().isEmpty() && observed.isDirty(),
                    "An observed mismatch was not persistently forgotten");
            level.setBlockAndUpdate(stale, Blocks.GOLD_BLOCK.defaultBlockState());
            check(!observed.holds(level, stale), "An observed mismatch regained ownership");
            explode(level, player, Vec3.atCenterOf(Group.S.block(home, 10, 0, 0)));
            check(level.getBlockState(Group.S.block(home, 10, 0, -1)).is(Blocks.CONCRETE.yellow()), "A creative guest let an explosion break the road");
            check(level.getEntity(fixed.names().get(2)).isAlive(), "An explosion in Build mode removed a group name");

            mode(player, GameType.SURVIVAL);
            check(HubData.protectsFromExplosions(server), "Live mode does not shield the hub from explosions");
            check(!HubData.protectsFrom(player, road), "A block he changed in Build mode is still treated as the mod's");
            check(!HubData.protectsFrom(player, gold) && player.gameMode.destroyBlock(gold), "His gold regained protection in Live");
            check(!HubData.protectsFrom(player, replaced) && player.gameMode.destroyBlock(replaced), "Changed-back concrete regained protection");
            check(player.gameMode.destroyBlock(road) && level.getBlockState(road).isAir(), "Live mode could not break his own block");
            var remaining = HubData.get(server).fixed();
            check(remaining.names().equals(fixed.names()) && remaining.blocks().size() < fixed.blocks().size(), "The record did not relinquish edits");
            check(remaining.blocks().stream().allMatch(block -> HubData.get(server).holds(level, block.pos())), "An exploded block stayed recorded");

            DesktopWorld.setEnabled(server, false);
            check(!HubData.protectsFrom(player, gold), "Protection outlives the desktop marker");
            helper.succeed();
        } finally {
            server.getPlayerList().remove(player);
            DesktopWorld.setEnabled(server, marked);
        }
    }

    @GameTest(environment = "aresos-test:home")
    public void homeIsBuiltOnlyInANewWorldAndOnlyOnce(GameTestHelper helper) {
        try { provisioningRules(); }
        catch (IOException error) { throw new AssertionError(error); }
        helper.succeed();
    }

    private static void provisioningRules() throws IOException {
        Path root = Files.createTempDirectory("aresos-flat-home-test");
        try {
            Path empty = Files.createDirectory(root.resolve("no-manifest"));
            check(NetherHome.startPlan(empty, false, true) == NetherHome.Start.NOTHING, "A save without a manifest would be provisioned");

            Path flat = Files.createDirectory(root.resolve("flat"));
            NetherHome.writeFlatManifest(flat);
            check(NetherHome.readKind(flat) == NetherHome.Kind.FLAT, "Flat manifest not read as flat");
            check(NetherHome.readManifest(flat).equals(FlatHome.SITE), "Flat manifest lost its site: " + NetherHome.readManifest(flat));
            check(refused(() -> NetherHome.writeFlatManifest(flat)), "An existing manifest was overwritten");
            check(NetherHome.startPlan(flat, false, true) == NetherHome.Start.PROVISION, "A new flat world would not be provisioned");
            // An existing save: with its home data nothing happens, without it only the message.
            check(NetherHome.startPlan(flat, true, false) == NetherHome.Start.NOTHING, "A provisioned save would be touched");
            check(NetherHome.startPlan(flat, true, true) == NetherHome.Start.NOTHING, "A save with home data would be provisioned again");
            check(NetherHome.startPlan(flat, false, false) == NetherHome.Start.MISSING_DATA, "Missing home data in an existing save is not reported");
            // The claim is written before the first block and never cleared; with it, nothing is ever built again.
            Files.writeString(flat.resolve(NetherHome.PROVISIONED), "started\n");
            check(refused(() -> NetherHome.startPlan(flat, false, true)), "A claimed save would be provisioned a second time");
            check(NetherHome.startPlan(flat, false, false) == NetherHome.Start.MISSING_DATA, "A claimed save without data is not reported");
            Files.delete(flat.resolve(NetherHome.PROVISIONED));
            Files.createDirectories(flat.resolve("data/aresos"));
            Files.writeString(flat.resolve("data/aresos/nether_home.dat"), "unreadable");
            check(refused(() -> NetherHome.startPlan(flat, false, true)), "A save with unreadable home data would be rebuilt");

            Path nether = Files.createDirectory(root.resolve("nether"));
            NetherHome.writeManifest(nether, NetherHome.DEFAULT_SITE, true);
            check(NetherHome.readKind(nether) == NetherHome.Kind.NETHER, "A Nether manifest is no longer read as Nether");
            check(!Files.readString(nether.resolve(NetherHome.MANIFEST)).contains("home="), "The Nether manifest gained a key");
            Path unknown = Files.createDirectory(root.resolve("unknown"));
            Files.writeString(unknown.resolve(NetherHome.MANIFEST), "version=1\nseed=0\nx=0\ny=63\nz=0\nyaw=180.0\nhome=moon\n");
            check(refused(() -> NetherHome.readKind(unknown)), "An unknown home kind was accepted");

            // The create flow refuses any folder that already holds a world or a claim, and a second creation of the same one.
            int[] runs = {0};
            Path existing = Files.createDirectory(root.resolve("existing"));
            Files.writeString(existing.resolve("level.dat"), "his world");
            check(refused(() -> NetherHome.createNewWorld(existing, () -> runs[0]++)), "An existing world would be created over");
            Path claimed = Files.createDirectory(root.resolve("claimed"));
            Files.writeString(claimed.resolve(NetherHome.PROVISIONED), "complete\n");
            check(refused(() -> NetherHome.createNewWorld(claimed, () -> runs[0]++)), "A claimed folder would be created over");
            check(runs[0] == 0, "A refused creation still ran");
            Path fresh = Files.createDirectory(root.resolve("fresh"));
            try {
                NetherHome.createNewWorld(fresh, () -> runs[0]++);
                check(runs[0] == 1, "A fresh folder was not created in");
                check(refused(() -> NetherHome.createNewWorld(fresh, () -> runs[0]++)) && runs[0] == 1, "The same world was created twice");
            } finally {
                NetherHome.cancelPendingCreation();
            }
        } finally {
            try (var paths = Files.walk(root)) {
                for (Path path : paths.sorted(java.util.Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    /**
     * Ten minutes of game time with the owner standing at home in Live mode under the flat home's rules: no mob may
     * appear. The control runs first, in the same place with the same player: with mob spawning on, a mob appears
     * (the test world is vanilla's default flat world, plains in daylight, where animals spawn on the grass and
     * slimes in any light). So the empty ten minutes are the rules' doing and not a world that could never spawn
     * anything. Alone in its test environment, because it changes the server's rules, and far from the test plots.
     */
    @GameTest(environment = "aresos-test:flat_home", maxTicks = LOAD_LIMIT + CONTROL_LIMIT + TEN_MINUTES + 40)
    public void noMobAppearsInTenMinutes(GameTestHelper helper) {
        var level = helper.getLevel();
        var server = level.getServer();
        var rules = server.getGameRules();
        Map<GameRule<Boolean>, Boolean> before = new HashMap<>();
        for (var rule : SWITCHES) before.put(rule, rules.get(rule));
        int fire = rules.get(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER);
        boolean marked = DesktopWorld.isEnabled(server);
        ServerPlayer player = join(level, "FlatHomeMobs");
        // Mobs spawn within 128 blocks of a player; anything in this box is this test's.
        AABB[] area = {null};
        // Runs on every way out, pass or fail: the test world, its rules included, can be kept for the next run.
        Runnable restore = () -> {
            for (var rule : SWITCHES) rules.set(rule, before.get(rule), server);
            rules.set(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER, fire, server);
            if (area[0] != null) mobs(level, area[0]).forEach(Entity::discard);
            server.getPlayerList().remove(player);
            DesktopWorld.setEnabled(server, marked);
        };
        BlockPos home;
        try {
            DesktopWorld.setEnabled(server, true);
            home = homeAt(level, far(helper, 0, 8000));
            area[0] = new AABB(home).inflate(200, 400, 200);
            player.teleportTo(level, home.getX() + 0.5, home.getY(), home.getZ() + 0.5, Set.of(), 180, 0, false);
            // Nothing ticks a test player's connection, so the chunk map would go on loading the place where he joined.
            level.getChunkSource().move(player);
            check(LiveMode.isLive(player), "Fixture: the player is not in Live mode");
            check(mobs(level, area[0]).isEmpty(), "Fixture: mobs already live around the new home");
            // The control: a world that spawns mobs. The monsters rule is set last, because only it refreshes the
            // level's cached "monsters may spawn" flag, which also depends on the mobs rule.
            rules.set(GameRules.SPAWN_MOBS, true, server);
            rules.set(GameRules.SPAWN_MONSTERS, true, server);
        } catch (RuntimeException | Error error) {
            restore.run();
            throw error;
        }
        long[] loadedAt = {-1};
        long[] quietSince = {-1};
        helper.onEachTick(() -> {
            try {
                long tick = helper.getTick();
                if (quietSince[0] < 0) {
                    var appeared = mobs(level, area[0]);
                    if (appeared.isEmpty()) {
                        if (loadedAt[0] < 0 && loaded(level, home)) loadedAt[0] = tick;
                        if (loadedAt[0] < 0 && tick >= LOAD_LIMIT) throw new AssertionError("Fixture: the ground around home did not load within "
                                + LOAD_LIMIT + " ticks. " + spawningState(level, home, player));
                        if (loadedAt[0] >= 0 && tick - loadedAt[0] >= CONTROL_LIMIT) throw new AssertionError("Control: no mob appears here even"
                                + " with mob spawning on, so ten quiet minutes would prove nothing. " + spawningState(level, home, player));
                        return;
                    }
                    AresOs.LOGGER.info("32 no-mob control: with mob spawning on, {} appeared within {} ticks", describe(appeared), tick);
                    FlatHome.applyRules(rules, server);
                    appeared.forEach(Entity::discard);
                    quietSince[0] = tick;
                } else if (tick >= quietSince[0] + TEN_MINUTES) {
                    check(!player.isRemoved() && player.level() == level && player.blockPosition().closerThan(home, 2),
                            "Fixture: the player is not at home: " + player.position());
                    check(LiveMode.isLive(player), "Fixture: the player left Live mode");
                    var spawning = level.getChunkSource().getLastSpawnState();
                    check(spawning != null && spawning.getSpawnableChunkCount() > 0, "Fixture: no chunk near the player counts for spawning");
                    check(server.getWorldData().getDifficulty() != net.minecraft.world.Difficulty.PEACEFUL, "Fixture: the world is peaceful");
                    NetherHomeGameTests.assertRules(rules);
                    var appeared = mobs(level, area[0]);
                    check(appeared.isEmpty(), appeared.size() + " mob(s) appeared within ten minutes under the flat home's rules: " + describe(appeared));
                    restore.run();
                    helper.succeed();
                }
            } catch (AssertionError error) {
                restore.run();
                // The test runner reports its own exception type from a tick callback, and no Error.
                helper.fail(error.getMessage());
            }
        });
    }

    /** True once mobs can live in every direction from home, six chunks out: the spawner has its ground. */
    private static boolean loaded(ServerLevel level, BlockPos home) {
        for (int x = -96; x <= 96; x += 96) for (int z = -96; z <= 96; z += 96) {
            if (!level.isPositionEntityTicking(home.offset(x, 0, z))) return false;
        }
        return true;
    }

    /** Why the control saw nothing: what the game's spawner looks at, and whether it can place an animal here at all. */
    private static String spawningState(ServerLevel level, BlockPos home, ServerPlayer player) {
        var rules = level.getGameRules();
        var state = level.getChunkSource().getLastSpawnState();
        BlockPos spot = home.offset(40, 0, 0);
        int all = 0;
        for (Entity entity : level.getAllEntities()) if (entity instanceof Mob) all++;
        int probes = 0;
        for (int i = 0; i < 20 && probes == 0; i++) {
            NaturalSpawner.spawnCategoryForPosition(MobCategory.CREATURE, level, spot);
            probes = level.getEntitiesOfClass(Mob.class, new AABB(spot).inflate(40, 4, 40)).size();
        }
        return "game time " + level.getGameTime() + ", spawn_mobs " + rules.get(GameRules.SPAWN_MOBS) + ", spawn_monsters "
                + rules.get(GameRules.SPAWN_MONSTERS) + ", difficulty " + level.getDifficulty() + ", players in the level " + level.players().size()
                + ", player at " + player.blockPosition().toShortString() + " in " + player.gameMode.getGameModeForPlayer()
                + ", nearest player to the spot " + (level.getNearestPlayer(spot.getX(), spot.getY(), spot.getZ(), -1, false) != null)
                + ", chunks counted for spawning " + (state == null ? "none" : state.getSpawnableChunkCount() + " with " + state.getMobCategoryCounts())
                + ", spot ticks entities " + level.isPositionEntityTicking(spot) + ", may spawn in its chunk "
                + level.canSpawnEntitiesInChunk(net.minecraft.world.level.ChunkPos.containing(spot)) + ", light " + level.getRawBrightness(spot, 0)
                + ", ground " + level.getBlockState(spot.below()) + ", biome " + level.getBiome(spot).getRegisteredName()
                + ", mobs in the whole world " + all + ", animals a direct spawn call placed " + probes;
    }

    private static List<Mob> mobs(ServerLevel level, AABB area) {
        return level.getEntitiesOfClass(Mob.class, area);
    }

    private static String describe(List<Mob> mobs) {
        return mobs.stream().limit(8).map(mob -> mob.getType().toShortString() + " at " + mob.blockPosition().toShortString()).toList().toString();
    }

    private static HubData.Fixed build(ServerLevel level, BlockPos home) {
        HubData.Fixed fixed;
        try { fixed = FlatHub.build(level, home); }
        catch (IOException error) { throw new AssertionError(error); }
        // A chunk loaded in this tick shows its entities only after the server has run that chunk's queued promotion,
        // which it does before the next tick or during the next chunk load. Until then a name added to the chunk
        // loaded last is in the world but cannot be looked up, so run what is queued, as the server itself would.
        for (int task = 0; task < 10000 && level.getChunkSource().pollTask(); task++) { }
        return fixed;
    }

    /** A column this far from the test's own plot: new ground in every run, out of reach of the plots and of each other. */
    private static BlockPos far(GameTestHelper helper, int x, int z) {
        return helper.absolutePos(BlockPos.ZERO).offset(x, 0, z);
    }

    /** A home block on the test world's own untouched grass in that column. */
    private static BlockPos homeAt(ServerLevel level, BlockPos column) {
        level.getChunkAt(column);
        BlockPos home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
        check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home
                + ": " + level.getBlockState(home.below()) + " under " + level.getBlockState(home));
        return home;
    }

    /**
     * A real player in survival whose connection answers mode switches, joined while the world is unmarked, as the
     * mode tests join theirs. The game's mock player reports creative whatever it is set to, and a marked world
     * refuses a switch that the client cannot acknowledge.
     */
    private static ServerPlayer join(ServerLevel level, String name) {
        var server = level.getServer();
        DesktopWorld.setEnabled(server, false);
        var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), name), false);
        var player = new ServerPlayer(server, level, cookie.gameProfile(), cookie.clientInformation());
        var connection = new Connection(PacketFlow.SERVERBOUND);
        new io.netty.channel.embedded.EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, player, cookie);
        ModeInventoryFixtures.registerStateReceiver(player);
        player.setGameMode(GameType.SURVIVAL);
        check(player.gameMode.getGameModeForPlayer() == GameType.SURVIVAL, "Fixture: the player did not join in survival");
        return player;
    }

    private static void mode(ServerPlayer player, GameType mode) {
        check(ModeInventoryFixtures.switchAndAcknowledge(player, mode) && player.gameMode.getGameModeForPlayer() == mode,
                "Fixture: the player did not switch to " + mode);
    }

    private static void explode(ServerLevel level, ServerPlayer player, Vec3 centre) {
        var tnt = new net.minecraft.world.entity.item.PrimedTnt(level, centre.x, centre.y, centre.z, player);
        new ServerExplosion(level, tnt, null, null, centre, 4, false, Explosion.BlockInteraction.DESTROY).explode();
    }

    private static CompoundTag saved(ServerLevel level, Entity entity) {
        var output = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
        entity.saveWithoutId(output);
        return output.buildResult();
    }

    private interface Action { void run() throws IOException; }

    private static boolean refused(Action action) {
        try { action.run(); return false; }
        catch (IOException expected) { return true; }
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
