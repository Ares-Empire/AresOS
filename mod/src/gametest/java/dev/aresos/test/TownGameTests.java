package dev.aresos.test;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
import dev.aresos.hub.TownKeeper;
import dev.aresos.hub.TownSeal;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.Placing;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import dev.aresos.mixin.TextDisplayAccess;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.storage.LevelStorageSource;
import net.minecraft.world.level.storage.SavedDataStorage;

import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.Set;

/**
 * Package 36: the town's record in hub.dat and the one function every block of the hub goes through. The town test
 * is alone in its batch, because the hub's record is one per server; it builds its flat home far from every plot,
 * on new ground in every run, as the flat-home tests do, and holds the chunks it needs with a ticket of its own.
 */
public final class TownGameTests {
    private static final String BATCH = "aresos-test:town";
    /** The longest wait for the town's chunks; the test server ticks as fast as it can. */
    private static final int LOAD_TICKS = 400_000;

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }

    private static BlockState block(String name) {
        return BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(name)).defaultBlockState();
    }

    /** A drawn icon: a white ring on a dark blue plate. Nothing of a real app. */
    private static GatePicture picture() { return picture(0xff2d2f8f); }

    /** A white ring on a plate of this colour. */
    private static GatePicture picture(int plate) {
        var icon = new BufferedImage(96, 96, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 96; y++) for (int x = 0; x < 96; x++) {
            double r = Math.hypot(x - 47.5, y - 47.5);
            icon.setRGB(x, y, r > 18 && r < 32 ? 0xffffffff : plate);
        }
        return GatePicture.of(icon, HubLayout.SIZE);
    }

    private static Set<Long> chunks(BlockPos from, BlockPos to) {
        var chunks = new HashSet<Long>();
        for (int x = from.getX() >> 4; x <= to.getX() >> 4; x++)
            for (int z = from.getZ() >> 4; z <= to.getZ() >> 4; z++) chunks.add(ChunkPos.pack(x, z));
        return chunks;
    }

    private static void hold(ServerLevel level, Set<Long> chunks, boolean held) {
        for (long chunk : chunks) {
            if (held) level.getChunkSource().addTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
            else level.getChunkSource().removeTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
        }
    }

    private static boolean loaded(ServerLevel level, Set<Long> chunks) {
        return chunks.stream().allMatch(chunk -> level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) && level.areEntitiesLoaded(chunk));
    }

    private static Map<BlockPos, BlockState> snapshot(ServerLevel level, BlockPos from, BlockPos to) {
        var states = new HashMap<BlockPos, BlockState>();
        for (var pos : BlockPos.betweenClosed(from, to)) states.put(pos.immutable(), level.getBlockState(pos));
        return states;
    }

    private interface Body { void run(ServerLevel level, BlockPos home) throws IOException; }

    /** Runs the body around a home block of its own once the ground there is loaded, and puts back the server's hub record. */
    private static void inTown(GameTestHelper helper, int offset, Body body) {
        var level = helper.getLevel();
        var server = level.getServer();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(offset, 0, 0);
        var chunks = chunks(column.offset(-48, 0, -60), column.offset(48, 0, 16));
        hold(level, chunks, true);
        helper.startSequence().thenWaitUntil(() -> helper.assertTrue(loaded(level, chunks), "The town's chunks are not loaded yet")).thenExecute(() -> {
            var previous = HubData.get(server);
            try {
                BlockPos home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
                check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home);
                body.run(level, home);
            } catch (IOException error) {
                throw new AssertionError(error.getMessage(), error);
            } finally {
                if (previous != null) HubData.store(server, previous);
                hold(level, chunks, false);
            }
        }).thenSucceed();
    }

    @GameTest(environment = BATCH, maxTicks = LOAD_TICKS)
    public void aTownLogoIsBuiltRecordedAndTakenDownThroughTheOneFunction(GameTestHelper helper) {
        inTown(helper, 15000, (level, home) -> {
            var server = level.getServer();
            var fixed = FlatHub.build(level, home);
            var hub = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), fixed);
            HubData.store(server, hub);
            var discord = new AppDefinition("town-discord", "Discord", List.of("discord"), "minecraft:ender_pearl", false).withNames(List.of("towndc"));
            var picture = picture();
            var place = Place.parse("N0R0").orElseThrow();
            var plan = Town.plan(hub, discord, place, picture);
            BlockPos from = home.offset(-20, -2, -40), to = home.offset(20, 16, 2);
            var before = snapshot(level, from, to);

            Town.check(server, discord, place, picture);
            var logo = Town.build(server, discord, place, picture);

            // The world holds the plan: the logo, its niche's black back, the two lights and the doormat in Internet's colour.
            var expected = new HashMap<BlockPos, BlockState>();
            plan.blocks().forEach((pos, name) -> expected.put(pos, block(name)));
            plan.lights().forEach(pos -> expected.put(pos, Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, 15)));
            plan.doormat().forEach(pos -> expected.put(pos, Blocks.CONCRETE.lightBlue().defaultBlockState()));
            expected.forEach((pos, state) -> check(level.getBlockState(pos).is(state.getBlock()), "At " + pos.subtract(home) + ": " + level.getBlockState(pos)));
            check(plan.origin().equals(home.offset(4, 0, -20)), "N0R0 does not start where HUB.md 3.2 puts it: " + plan.origin().subtract(home));

            // hub.dat: app, place, picture, sign and zone, and every block placed with the ground the doormat replaced.
            check(logo.app().equals("town-discord") && logo.place().equals("N0R0") && logo.picture().equals(picture.hash())
                    && logo.converter() == GatePicture.CONVERTER && logo.name().equals("Discord") && logo.shortName().equals(Optional.of("towndc")),
                    "The logo's record: " + logo);
            var gate = logo.gate();
            var recorded = new HashMap<BlockPos, String>();
            gate.placed().forEach(placed -> recorded.put(placed.pos(), placed.block()));
            check(recorded.size() == expected.size() && gate.placed().size() == expected.size(), "Recorded " + recorded.size() + " blocks, placed " + expected.size());
            expected.forEach((pos, state) -> check(Placing.id(state).equals(recorded.get(pos)), "Record at " + pos.subtract(home) + ": " + recorded.get(pos)));
            check(gate.ground().size() == 8 && gate.ground().stream().allMatch(ground -> ground.block().equals("minecraft:grass_block")
                    && plan.doormat().contains(ground.pos())), "The doormat's ground: " + gate.ground());
            check(Set.copyOf(gate.grass()).equals(Set.copyOf(plan.floor())), "The grass it stands on: " + gate.grass().size());
            var sign = level.getEntity(gate.sign().orElseThrow());
            check(sign instanceof Display.TextDisplay && sign.position().equals(plan.sign().position()), "The sign: " + sign);
            check(HubData.get(server) == hub && hub.logo("town-discord").equals(Optional.of(logo)) && hub.logos().equals(List.of(logo)), "Not in the server's record");
            check(hub.blocks(level.dimension()).keySet().containsAll(recorded.keySet()) && hub.signs().contains(sign.getUUID()), "The record does not own the logo");
            var corner = plan.at(0, 0, 11);
            check(hub.logoAt(level, corner).equals(Optional.of(logo)) && hub.logoAt(level, home.below()).isEmpty(), "logoAt does not find the logo's block");
            check(hub.holds(level, corner) && hub.fixed().blocks().size() == fixed.blocks().size(), "The pad's record changed");
            // hub.dat written again in package 32's shape (as an older mod does) loses nothing: the logos are in town.dat.
            var hubDat = (net.minecraft.nbt.CompoundTag)HubData.CODEC.encodeStart(NbtOps.INSTANCE, hub).getOrThrow();
            check(!hubDat.contains("logos"), "hub.dat holds the logos: " + hubDat.keySet());
            var rewritten = HubData.CODEC.parse(NbtOps.INSTANCE, hubDat).getOrThrow();
            HubData.store(server, rewritten);
            check(HubData.get(server) == rewritten && rewritten.logos().equals(hub.logos()) && rewritten.holds(level, corner)
                    && rewritten.signs().equals(hub.signs()), "The logo did not survive hub.dat being written again");
            HubData.store(server, hub);

            // zones.dat: the trigger zone and exit, no gate and no blocks of its own; it is the town's and nothing else is.
            var zones = ZoneData.get(server).zones().stream().filter(zone -> zone.app().equals("town-discord")).toList();
            check(zones.size() == 1 && zones.getFirst().id().equals(logo.zone()), "zones: " + zones);
            var zone = zones.getFirst();
            check(zone.min().equals(plan.nicheMin()) && zone.max().equals(plan.nicheMax()) && zone.exit().equals(plan.exit())
                    && zone.blocks().isEmpty() && !zone.isGate(), "The town's zone: " + zone);
            check(HubData.town(server, zone), "The zone is not the town's");
            var his = new AppZone("his-own", "town-discord", zone.dimension(), zone.min(), zone.max(), zone.exit(), List.of());
            check(!HubData.town(server, his), "A zone of his counts as the town's");

            // Refusals change nothing: the same app twice, and another app in a place that is taken.
            var built = snapshot(level, from, to);
            refused(() -> Town.build(server, discord, place, picture), "already stands");
            var chrome = new AppDefinition("town-chrome", "Chrome", List.of("chrome"), "minecraft:ender_pearl", false);
            refused(() -> Town.build(server, chrome, place, picture), "isn't clear");
            check(snapshot(level, from, to).equals(built) && hub.logos().equals(List.of(logo)), "A refused build changed something");

            // A blocked place: something of his in the logo's box, or a floor that isn't grass under the way in.
            var n0l0 = Place.parse("N0L0").orElseThrow();
            BlockPos hisBlock = home.offset(-10, 3, -21);
            level.setBlockAndUpdate(hisBlock, Blocks.OAK_PLANKS.defaultBlockState());
            var clear = refused(() -> Town.check(server, chrome, n0l0, picture), "isn't clear");
            check(!(clear instanceof GateBuilder.NotLoaded), "A blocked place reads as not loaded");
            level.setBlockAndUpdate(hisBlock, Blocks.AIR.defaultBlockState());
            Town.check(server, chrome, n0l0, picture);
            var n1l0 = Place.parse("N1L0").orElseThrow();
            BlockPos hisFloor = home.offset(-10, -1, -30);
            level.setBlockAndUpdate(hisFloor, Blocks.STONE.defaultBlockState());
            refused(() -> Town.check(server, chrome, n1l0, picture), "isn't untouched grass");
            level.setBlockAndUpdate(hisFloor, Blocks.GRASS_BLOCK.defaultBlockState());
            Town.check(server, chrome, n1l0, picture);

            // He changes one of its blocks in Build mode: from then on it is his, and the record lets go of it.
            level.setBlockAndUpdate(corner, Blocks.DIAMOND_BLOCK.defaultBlockState());
            check(!hub.holds(level, corner), "A block he changed is still the mod's");
            var left = hub.logo("town-discord").orElseThrow().gate().placed();
            check(left.size() == expected.size() - 1 && left.stream().noneMatch(placed -> placed.pos().equals(corner)), "The record kept a block he changed");

            // Taken down: the world as it was, except what he changed; no sign, no zone, no record.
            var removal = Town.remove(server, "town-discord");
            check(removal.removed() == expected.size() - 1 && removal.kept() == 0, "Removal: " + removal);
            for (var cell : before.entrySet()) {
                if (cell.getKey().equals(corner)) continue;
                check(level.getBlockState(cell.getKey()).equals(cell.getValue()), "After removal " + cell.getKey().subtract(home)
                        + " is " + level.getBlockState(cell.getKey()) + ", was " + cell.getValue());
            }
            check(level.getBlockState(corner).is(Blocks.DIAMOND_BLOCK), "What he changed did not stay");
            check(sign.isRemoved() && ZoneData.get(server).zones().stream().noneMatch(other -> other.id().equals(logo.zone())), "The sign or the zone stayed");
            check(hub.logos().isEmpty() && !HubData.town(server, zone) && !hub.blocks(level.dimension()).containsKey(plan.at(1, 1, 1)), "The record stayed");
            refused(() -> Town.remove(server, "town-discord"), "No logo");
            level.setBlockAndUpdate(corner, Blocks.AIR.defaultBlockState());

            // Review fixes 1, step B, point 2: a sign or a zone is taken down only while it is what the town made. He
            // edits the sign's text: it is his and stays; the logo's blocks and its zone still come down.
            var signed = Town.build(server, discord, place, picture);
            var edited = (Display.TextDisplay)level.getEntity(signed.gate().sign().orElseThrow());
            ((TextDisplayAccess)edited).aresos$setText(Component.literal("Discord\n/mine"));
            var withHisSign = Town.remove(server, "town-discord");
            check(withHisSign.removed() == expected.size() && !edited.isRemoved() && hub.logos().isEmpty()
                    && ZoneData.get(server).zones().stream().noneMatch(other -> other.id().equals(signed.zone())),
                    "His edited sign: " + withHisSign + ", taken away " + edited.isRemoved());
            for (var pos : expected.keySet()) check(level.getBlockState(pos).equals(before.get(pos)), "Around his sign " + pos.subtract(home) + " is " + level.getBlockState(pos));
            edited.discard();

            // Reused IDs: a zone of hisDisplay took the logo's zone ID (its box, another app) and a text display of hisDisplay, higher
            // up, the sign's ID. Neither is the town's; both stay, and the logo's blocks come down.
            var reused = Town.build(server, discord, place, picture);
            var townZone = ZoneData.get(server).zones().stream().filter(other -> other.id().equals(reused.zone())).findFirst().orElseThrow();
            check(HubData.town(server, townZone), "The rebuilt logo's zone is not the town's");
            ZoneData.get(server).remove(other -> other.id().equals(reused.zone()));
            var hisZone = new AppZone(reused.zone(), "his-app", townZone.dimension(), townZone.min(), townZone.max(), townZone.exit(), List.of());
            ZoneData.get(server).add(hisZone);
            check(!HubData.town(server, hisZone), "A zone of his with the logo's zone ID counts as the town's");
            var signId = reused.gate().sign().orElseThrow();
            var townSign = level.getEntity(signId);
            townSign.discard();
            var hisDisplay = EntityType.create(EntityTypes.TEXT_DISPLAY, TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), new CompoundTag()),
                    level, EntitySpawnReason.COMMAND).orElseThrow();
            hisDisplay.setUUID(signId);
            hisDisplay.snapTo(townSign.getX(), townSign.getY() + 4, townSign.getZ(), 0, 0);
            check(level.addFreshEntity(hisDisplay) && level.getEntity(signId) == hisDisplay, "Fixture: his display with the sign's ID");
            var withHisIds = Town.remove(server, "town-discord");
            boolean stayed = !hisDisplay.isRemoved() && ZoneData.get(server).zones().contains(hisZone);
            ZoneData.get(server).remove(other -> other.equals(hisZone));
            hisDisplay.discard();
            check(stayed && withHisIds.removed() == expected.size() && hub.logos().isEmpty(), "His zone or display with the logo's IDs: " + withHisIds + ", stayed " + stayed);
            for (var pos : expected.keySet()) check(level.getBlockState(pos).equals(before.get(pos)), "With his IDs " + pos.subtract(home) + " is " + level.getBlockState(pos));
        });
    }

    /**
     * The rule of the one function, cell by cell: untouched ground (air, grass or dirt with air above) or the mod's own
     * recorded block that is still that block. Built in the test's own plot.
     */
    @GameTest(environment = "aresos-test:desktop")
    public void theOneFunctionChangesOnlyUntouchedGroundOrTheBlockItRecorded(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos a = helper.absolutePos(new BlockPos(1, 2, 1)), b = a.east(2), c = b.east(2);
        for (var pos : List.of(a, b, c)) { level.setBlockAndUpdate(pos, Blocks.AIR.defaultBlockState()); level.setBlockAndUpdate(pos.above(), Blocks.AIR.defaultBlockState()); }
        var stone = Blocks.STONE.defaultBlockState();

        // Air, then grass and dirt with nothing on them, are untouched; the change says what stood there.
        check(Placing.set(level, a, null, stone).equals(Optional.of(new Placing.Change(a, "minecraft:stone", "minecraft:air"))), "Air was refused");
        level.setBlockAndUpdate(b, Blocks.GRASS_BLOCK.defaultBlockState());
        check(Placing.set(level, b, null, stone).map(Placing.Change::before).equals(Optional.of("minecraft:grass_block")), "Open grass was refused");
        level.setBlockAndUpdate(c, Blocks.DIRT.defaultBlockState());
        check(Placing.set(level, c, null, stone).isPresent(), "Open dirt was refused");
        // His: grass with something on it, and any other block.
        level.setBlockAndUpdate(b, Blocks.GRASS_BLOCK.defaultBlockState());
        level.setBlockAndUpdate(b.above(), Blocks.OAK_PLANKS.defaultBlockState());
        check(Placing.set(level, b, null, stone).isEmpty() && level.getBlockState(b).is(Blocks.GRASS_BLOCK), "Grass under his block was paved");
        level.setBlockAndUpdate(b.above(), Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(b, Blocks.DIAMOND_BLOCK.defaultBlockState());
        check(Placing.set(level, b, null, stone).isEmpty() && level.getBlockState(b).is(Blocks.DIAMOND_BLOCK), "His block was replaced");

        // A recorded block is changed only while it is still that block.
        check(Placing.set(level, a, "minecraft:gold_block", Blocks.AIR.defaultBlockState()).isEmpty() && level.getBlockState(a).is(Blocks.STONE),
                "A block other than the recorded one was removed");
        check(Placing.set(level, a, "minecraft:stone", Blocks.AIR.defaultBlockState()).isPresent() && level.getBlockState(a).isAir(), "The recorded block was not removed");
        check(Placing.set(level, a, "minecraft:stone", stone).isEmpty() && level.getBlockState(a).isAir(), "A recorded block that is gone was put back");

        // A light is still the mod's only at full level and dry.
        var light = Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, 15);
        check(Placing.still(light, "minecraft:light") && !Placing.still(light.setValue(LightBlock.LEVEL, 3), "minecraft:light")
                && !Placing.still(light.setValue(LightBlock.WATERLOGGED, true), "minecraft:light") && !Placing.still(stone, "minecraft:light"), "The light rule");
        check(Placing.state("minecraft:no_such_block").isAir() && Placing.state("minecraft:gold_block").is(Blocks.GOLD_BLOCK), "Recorded IDs");
        for (var pos : List.of(a, b, c)) level.setBlockAndUpdate(pos, Blocks.AIR.defaultBlockState());
        helper.succeed();
    }

    private static final String KEEP_BATCH = "aresos-test:town_keep";

    /** One app of the fake program list, in a group of his choosing (the saved {@code group}), with one short name or none. */
    private static AppDefinition app(String id, String name, String shortName, AppGroup group, boolean pinned, boolean mine) {
        return new AppDefinition(id, name, List.of(id), "minecraft:ender_pearl", pinned).withMine(mine)
                .withNames(shortName == null ? List.of() : List.of(shortName)).withSpot(null, group.key());
    }

    /** The keeping test's world outside the town: the fake apps file, the drawn pictures, what was saved. */
    private static final class Fake {
        final List<AppDefinition> apps = new ArrayList<>();
        final GatePicture ring = picture();
        final Map<String, GatePicture> pictures = new HashMap<>();
        final List<Map<String, AppsConfig.Spot>> saves = new ArrayList<>();
        final TownKeeper keeper = new TownKeeper();
        HubData previous;
        BlockPos home, planks;
        Set<Long> far = Set.of();
        /** The start of every app ID of this test's town. */
        String prefix = "keep-";

        /**
         * Removes the trigger zones of this test's apps. The test world is kept between runs, and a run that failed
         * half way leaves its town's zones in it; other tests expect zones.dat to hold only their own.
         */
        void clearZones(MinecraftServer server) { ZoneData.get(server).remove(zone -> zone.app().startsWith(prefix)); }

        boolean zoneLeft(MinecraftServer server) { return ZoneData.get(server).zones().stream().anyMatch(zone -> zone.app().startsWith(prefix)); }

        TownKeeper.Pass pass(MinecraftServer server) { return pass(server, true); }

        /** One pass, saving places into the fake file as {@code AresOs.saveSpots} does into the real one. */
        TownKeeper.Pass pass(MinecraftServer server, boolean complete) {
            return keeper.keep(server, new TownKeeper.Programs(apps, complete), app -> Optional.of(pictures.getOrDefault(app.id(), ring)), spots -> {
                saves.add(spots);
                apps.replaceAll(app -> spots.containsKey(app.id()) ? app.withSpot(spots.get(app.id()).place(), spots.get(app.id()).group()) : app);
            });
        }

        void change(String id, java.util.function.UnaryOperator<AppDefinition> how) { apps.replaceAll(app -> app.id().equals(id) ? how.apply(app) : app); }
        AppDefinition get(String id) { return apps.stream().filter(app -> app.id().equals(id)).findFirst().orElseThrow(); }
    }

    private static String place(MinecraftServer server, String app) {
        return HubData.get(server).logo(app).map(HubData.Logo::place).orElse("none");
    }

    /**
     * HUB.md 3.4 with a fake program list and drawn pictures: never on an incomplete list or in a town of other rules;
     * the first build (pinned first); a pass in step that changes nothing; hub.dat written again by an older mod; the
     * refusal and explosion rules; a newcomer; a blocked place; a place changing hands; a logo renewed; a removal his
     * torch refuses; a light he changed; a place that is not loaded, built once it is. Its own batch and ground.
     */
    @GameTest(environment = KEEP_BATCH, maxTicks = LOAD_TICKS)
    public void theTownKeepsInStepWithHisApps(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(17000, 0, 0);
        var near = chunks(column.offset(-48, 0, -60), column.offset(48, 0, 16));
        var fake = new Fake();
        hold(level, near, true);
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> keeping(fake, level, near, false, () -> keepingNear(fake, level, column)))
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, fake.far), "The far place is not loaded yet"))
                .thenExecute(() -> keeping(fake, level, near, true, () -> keepingFar(fake, level)))
                .thenSucceed();
    }

    private interface Part { void run() throws IOException; }

    /** Runs a part; after the last one, or when one fails, puts back the server's hub record and lets go of the chunks. */
    private static void keeping(Fake fake, ServerLevel level, Set<Long> near, boolean last, Part part) {
        boolean done = false;
        try {
            part.run();
            done = true;
        } catch (IOException error) {
            throw new AssertionError(error.getMessage(), error);
        } finally {
            if (last || !done) {
                if (!done) fake.clearZones(level.getServer());
                if (fake.previous != null) HubData.store(level.getServer(), fake.previous);
                hold(level, near, false);
                hold(level, fake.far, false);
            }
        }
    }

    private static void keepingNear(Fake fake, ServerLevel level, BlockPos column) throws IOException {
        var server = level.getServer();
        fake.previous = HubData.get(server);
        BlockPos home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
        check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home);
        fake.home = home;
        fake.clearZones(server);
        var hub = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), FlatHub.build(level, home));
        HubData.store(server, hub);
        var before = snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2));
        fake.apps.addAll(List.of(
                app("keep-discord", "Discord", "discord", AppGroup.INTERNET, false, true),
                app("keep-chrome", "Chrome", "chrome", AppGroup.INTERNET, true, true),
                app("keep-gone", "Gone App", null, AppGroup.INTERNET, false, true).withAbsent(true).withSpot("N1R0", "internet"),
                app("keep-far", "Far", null, AppGroup.INTERNET, false, true).withSpot("N40L0", "internet"),
                app("keep-spotify", "Spotify", "spotify", AppGroup.WORK_MEDIA, false, false),
                app("keep-mail", "Mail", "mail", AppGroup.INTERNET, false, false)));

        // Never on an incomplete list; never in a town that other rules built.
        var none = fake.pass(server, false);
        check(none.lines().isEmpty() && !none.pending() && hub.logos().isEmpty() && fake.saves.isEmpty(), "An incomplete list changed the town");
        var other = new HubData("flat-0", HubLayout.numbers(), hub.home(), hub.fixed());
        HubData.store(server, other);
        check(fake.pass(server).lines().isEmpty() && other.logos().isEmpty() && fake.saves.isEmpty(), "A town of other rules was kept by these");
        HubData.store(server, hub);

        // The first build: pinned first, so Chrome gets N0L0 although Discord comes first in the file. The far place
        // is not loaded: its build waits, nothing is said about it, its place stays saved.
        var first = fake.pass(server);
        // A first build says one line, whatever the count (review fixes 1, step B, point 6).
        check(first.lines().equals(List.of("The town is built: 2 logos. /apps lists them.")), "First build: " + first.lines());
        check(place(server, "keep-chrome").equals("N0L0") && place(server, "keep-discord").equals("N0R0") && hub.logos().size() == 2, "Day one: " + hub.logos());
        check(first.pending() && first.pictures().isEmpty(), "The far place's build does not wait: " + first);
        check("N0L0".equals(fake.get("keep-chrome").place()) && "N0R0".equals(fake.get("keep-discord").place())
                && "N1R0".equals(fake.get("keep-gone").place()) && "N40L0".equals(fake.get("keep-far").place())
                && "internet".equals(fake.get("keep-chrome").group()), "Saved places: " + fake.apps);

        // In step: nothing changes, nothing is said, nothing is saved.
        int saves = fake.saves.size();
        var again = fake.pass(server);
        check(again.lines().isEmpty() && fake.saves.size() == saves && hub.logos().size() == 2, "A pass in step changed something: " + again.lines());

        // hub.dat written again in package 32's shape (an older mod changed a pad block): the town is still known, and
        // nothing is built a second time one place on.
        var rewritten = HubData.CODEC.parse(NbtOps.INSTANCE, HubData.CODEC.encodeStart(NbtOps.INSTANCE, hub).getOrThrow()).getOrThrow();
        HubData.store(server, rewritten);
        var afterRewrite = fake.pass(server);
        check(afterRewrite.lines().isEmpty() && HubData.get(server).logos().size() == 2 && fake.saves.size() == saves, "After hub.dat was written again: " + afterRewrite.lines());

        // Protection: the refusal names a town logo; explosions spare it in Build mode too, the pad only outside it.
        var town = HubData.get(server);
        var logoBlock = town.logo("keep-chrome").orElseThrow().gate().placed().getFirst().pos();
        check(town.refusal(level, logoBlock).startsWith("The logo of Chrome is part of the town and protected."), "Refusal: " + town.refusal(level, logoBlock));
        check(town.refusal(level, home.below()).startsWith("The home pad and roads are protected.") && town.refusal(level, home.offset(30, -1, 30)) == null, "The pad's refusal");
        check(town.sparesFromExplosion(level, logoBlock, true) && town.sparesFromExplosion(level, logoBlock, false)
                && !town.sparesFromExplosion(level, home.below(), true) && town.sparesFromExplosion(level, home.below(), false)
                && !town.sparesFromExplosion(level, home.offset(30, -1, 30), false), "What explosions spare");

        // A newcomer joins My apps.
        fake.change("keep-spotify", app -> app.withMine(true));
        var joined = fake.pass(server);
        check(joined.lines().equals(List.of("Spotify is new. It stands in Work & Media, west. /spotify opens it.")) && place(server, "keep-spotify").equals("W0L0"),
                "A newcomer: " + joined.lines());

        // A missing trigger zone (review fixes 1, step B, point 5): a mod of packages 33 to 35 took Spotify's away with
        // `zone remove`. A pass puts it back as the town made it and says nothing; a zone of his in its place keeps it
        // out, said once, and stays; once his zone is gone, the next pass puts the doorway back.
        var spotifyLogo = HubData.get(server).logo("keep-spotify").orElseThrow();
        var doorway = ZoneData.get(server).zones().stream().filter(zone -> zone.id().equals(spotifyLogo.zone())).findFirst().orElseThrow();
        ZoneData.get(server).remove(zone -> zone.id().equals(spotifyLogo.zone()));
        var restored = fake.pass(server);
        check(restored.lines().isEmpty() && ZoneData.get(server).zones().contains(doorway), "The missing zone: " + restored.lines());
        ZoneData.get(server).remove(zone -> zone.id().equals(spotifyLogo.zone()));
        var hisZone = new AppZone("keep-his-zone", "keep-his", doorway.dimension(), doorway.min(), doorway.max(), doorway.exit(), List.of());
        ZoneData.get(server).add(hisZone);
        var claimed = fake.pass(server);
        check(claimed.lines().equals(List.of("The logo of Spotify opens nothing: its doorway's zone is gone and a zone of yours is in its place."))
                && ZoneData.get(server).zones().contains(hisZone) && ZoneData.get(server).zones().stream().noneMatch(zone -> zone.id().equals(spotifyLogo.zone())),
                "A zone of his in the doorway's place: " + claimed.lines());
        check(fake.pass(server).lines().isEmpty(), "The missing doorway was said twice");
        ZoneData.get(server).remove(zone -> zone.equals(hisZone));
        var back = fake.pass(server);
        check(back.lines().isEmpty() && ZoneData.get(server).zones().contains(doorway), "The doorway after his zone went: " + back.lines());

        // A blocked place: his planks in N1L0's box. Mail stands one place on, in the place the absent app remembered.
        var n1l0 = Town.plan(town, fake.get("keep-mail"), Place.parse("N1L0").orElseThrow(), fake.ring);
        fake.planks = n1l0.at(1, 3, 3);
        level.setBlockAndUpdate(fake.planks, Blocks.OAK_PLANKS.defaultBlockState());
        fake.change("keep-mail", app -> app.withMine(true));
        var blocked = fake.pass(server);
        check(blocked.lines().equals(List.of("Mail is new. It stands in Internet, north. /mail opens it.",
                "N1L0 is blocked by something of yours, so Mail stands at N1R0.")), "A blocked place: " + blocked.lines());
        check(place(server, "keep-mail").equals("N1R0") && level.getBlockState(fake.planks).is(Blocks.OAK_PLANKS) && fake.get("keep-gone").place() == null,
                "His planks, or the remembered place");

        // A place changing hands (package 37's swap): both come down, then both are built, in one pass.
        fake.change("keep-chrome", app -> app.withSpot("N1R0", app.group()));
        fake.change("keep-mail", app -> app.withSpot("N0L0", app.group()));
        var swapped = fake.pass(server);
        check(swapped.lines().equals(List.of("Chrome moved to Internet, north. /chrome opens it.", "Mail moved to Internet, north. /mail opens it.")),
                "A swap: " + swapped.lines());
        check(place(server, "keep-chrome").equals("N1R0") && place(server, "keep-mail").equals("N0L0"), "After the swap");

        // Renewed in place: a new picture and a new name, one line.
        fake.pictures.put("keep-spotify", picture(0xff8f2d2d));
        fake.change("keep-spotify", app -> app("keep-spotify", "Spotify Music", "spotify", AppGroup.WORK_MEDIA, false, true).withSpot(app.place(), app.group()));
        var renewed = fake.pass(server);
        var spotify = HubData.get(server).logo("keep-spotify").orElseThrow();
        check(renewed.lines().equals(List.of("The logo of Spotify Music was renewed.")) && spotify.place().equals("W0L0")
                && spotify.picture().equals(fake.pictures.get("keep-spotify").hash()) && spotify.name().equals("Spotify Music")
                && level.getEntity(spotify.gate().sign().orElseThrow()) instanceof Display.TextDisplay, "Renewed: " + renewed.lines() + " " + spotify);

        // A removal his torch refuses: Chrome's logo stays, said once; it comes down once the torch is gone.
        var chromePlan = Town.plan(HubData.get(server), fake.get("keep-chrome"), Place.parse("N1R0").orElseThrow(), fake.ring);
        BlockPos torch = chromePlan.doormat().getFirst().above();
        level.setBlockAndUpdate(torch, Blocks.TORCH.defaultBlockState());
        fake.change("keep-chrome", app -> app.withAbsent(true));
        var stays = fake.pass(server);
        check(stays.lines().size() == 1 && stays.lines().getFirst().startsWith("The logo of Chrome stays: ") && stays.lines().getFirst().contains("torch"),
                "A refused removal: " + stays.lines());
        check(place(server, "keep-chrome").equals("N1R0") && level.getBlockState(torch).is(Blocks.TORCH), "The logo or his torch went");
        check(fake.pass(server).lines().isEmpty(), "The refusal was said twice");
        level.setBlockAndUpdate(torch, Blocks.AIR.defaultBlockState());
        var gone = fake.pass(server);
        check(gone.lines().equals(List.of("Chrome is no longer installed. Its logo came down; its place is kept for its return.")), "Chrome gone: " + gone.lines());
        check(place(server, "keep-chrome").equals("none") && "N1R0".equals(fake.get("keep-chrome").place()), "Chrome's place is not remembered");

        // A light he changed is his and stays, however he changed it and even when he changed it back (review fixes 1,
        // step B, point 1): the record lets go of it the moment its state changes, without anyone asking. One light
        // goes 15 -> 3 -> 15, the other wet -> dry; both are as the mod placed them again when Mail leaves. Neither holds
        // the logo up (the orchestrator's decision 2).
        var mailPlan = Town.plan(HubData.get(server), fake.get("keep-mail"), Place.parse("N0L0").orElseThrow(), fake.ring);
        BlockPos light = mailPlan.lights().getFirst(), wet = mailPlan.lights().getLast();
        var full = Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, 15);
        level.setBlockAndUpdate(light, full.setValue(LightBlock.LEVEL, 3));
        level.setBlockAndUpdate(light, full);
        level.setBlockAndUpdate(wet, full.setValue(LightBlock.WATERLOGGED, true));
        level.setBlockAndUpdate(wet, full);
        var mailRecord = HubData.get(server).logo("keep-mail").orElseThrow().gate().placed();
        check(!wet.equals(light) && mailRecord.stream().noneMatch(placed -> placed.pos().equals(light) || placed.pos().equals(wet))
                && !HubData.get(server).blocks(level.dimension()).containsKey(light) && !HubData.get(server).blocks(level.dimension()).containsKey(wet),
                "A light he changed and changed back is still in the record");
        fake.change("keep-mail", app -> app.withMine(false));
        var left = fake.pass(server);
        check(left.lines().equals(List.of("Mail left My apps. Its logo came down.")), "Mail left: " + left.lines());
        check(level.getBlockState(light).equals(full) && level.getBlockState(wet).equals(full), "His lights did not stay: " + level.getBlockState(light) + ", " + level.getBlockState(wet));
        var area = new HashSet<BlockPos>(mailPlan.space());
        area.addAll(mailPlan.floor());
        area.addAll(mailPlan.doormat());
        area.addAll(mailPlan.blocks().keySet());
        area.remove(light);
        area.remove(wet);
        for (var pos : area) check(level.getBlockState(pos).equals(before.get(pos)), "After Mail left " + pos.subtract(home) + " is " + level.getBlockState(pos));
        level.setBlockAndUpdate(light, Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(wet, Blocks.AIR.defaultBlockState());

        // The far place: still waiting. Its chunks are loaded next, with a ticket of this test's own.
        var farPlan = Town.plan(HubData.get(server), fake.get("keep-far"), Place.parse("N40L0").orElseThrow(), fake.ring);
        fake.far = chunks(farPlan.origin().offset(-24, 0, -24), farPlan.origin().offset(24, 0, 24));
        check(!loaded(level, fake.far) && place(server, "keep-far").equals("none") && fake.pass(server).pending(), "The far place is loaded or built");
        hold(level, fake.far, true);
    }

    private static void keepingFar(Fake fake, ServerLevel level) {
        var server = level.getServer();
        var far = fake.pass(server);
        // Its logo stands; the north road to it (step 3) still waits for the ground between, which nobody loaded.
        var hub = HubData.get(server);
        int middle = (HubLayout.avenueEnd(5) + HubLayout.avenueEnd(38)) / 2;
        BlockPos road = AppGroup.INTERNET.block(hub.home().pos(), middle, 0, -1);
        boolean between = level.hasChunkAt(road) && level.areEntitiesLoaded(ChunkPos.pack(road));
        check(far.lines().equals(List.of("Far stands in Internet, north.")) && far.pending() && !between && place(server, "keep-far").equals("N40L0"),
                "When its place is loaded: " + far.lines() + " pending " + far.pending() + ", the road's ground between loaded " + between
                        + ", hub blocks " + hub.fixed().blocks().size());

        // Everything leaves My apps: the town comes down and nothing of it is left; no road waits any more.
        fake.apps.replaceAll(app -> app.withMine(false));
        var empty = fake.pass(server);
        check(empty.lines().size() == 3 && !empty.pending() && HubData.get(server).logos().isEmpty(), "Taking the town down: " + empty.lines());
        check(!fake.zoneLeft(server), "A zone of the town stayed");
        level.setBlockAndUpdate(fake.planks, Blocks.AIR.defaultBlockState());
    }

    private static final String REBUILD_BATCH = "aresos-test:town_rebuild";

    /**
     * Step 3 in one town of its own: a fresh flat home whose apps file already holds places (another world's) gets
     * that town, said in one line; roads that grow with their group and never shrink, and only over untouched grass;
     * the counts on the group names; a logo drawn by an older converter and a changed short name, renewed in place;
     * and {@code hub rebuild} with a block he changed inside a logo.
     */
    @GameTest(environment = REBUILD_BATCH, maxTicks = LOAD_TICKS)
    public void roadsCountsRenewalsAndRebuildInAFreshFlatHome(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(19000, 0, 0);
        var near = chunks(column.offset(-80, 0, -80), column.offset(80, 0, 80));
        var fake = new Fake();
        fake.prefix = "re-";
        hold(level, near, true);
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> keeping(fake, level, near, true, () -> stepThree(fake, level, column)))
                .thenSucceed();
    }

    private static String text(ServerLevel level, java.util.UUID entity) {
        return ((dev.aresos.mixin.TextDisplayAccess) level.getEntity(entity)).aresos$text().getString();
    }

    private static List<String> names(ServerLevel level, HubData hub) {
        return hub.fixed().names().stream().map(id -> text(level, id)).toList();
    }

    /** Whether the avenue of a group is paved and recorded at this outward index, all five blocks. */
    private static boolean paved(ServerLevel level, HubData hub, AppGroup group, int outward) {
        for (int sideways = -2; sideways <= 2; sideways++) {
            var pos = group.block(hub.home().pos(), outward, sideways, -1);
            if (!Placing.id(level.getBlockState(pos)).equals(sideways == 0 ? group.concrete() : HubLayout.PAVING) || !hub.holds(level, pos)) return false;
        }
        return true;
    }

    private static boolean grass(ServerLevel level, HubData hub, AppGroup group, int outward) {
        for (int sideways = -2; sideways <= 2; sideways++)
            if (!level.getBlockState(group.block(hub.home().pos(), outward, sideways, -1)).is(Blocks.GRASS_BLOCK)) return false;
        return true;
    }

    private static void stepThree(Fake fake, ServerLevel level, BlockPos column) throws IOException {
        var server = level.getServer();
        fake.previous = HubData.get(server);
        BlockPos home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
        check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home);
        fake.clearZones(server);
        var hub = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), FlatHub.build(level, home));
        HubData.store(server, hub);
        check(names(level, hub).equals(List.of("INTERNET", "GAMES", "SYSTEM & TOOLS", "WORK & MEDIA")), "A new flat home's names: " + names(level, hub));

        // Point 6: a new world gets the same town. The apps file brings places from another world, not the ones a first
        // build would give (Discord left of Chrome, Lunar Client in the second row). Six changes are said in one line.
        fake.apps.addAll(List.of(
                app("re-chrome", "Chrome", "chrome", AppGroup.INTERNET, true, true).withSpot("N0R0", "internet"),
                app("re-discord", "Discord", "discord", AppGroup.INTERNET, false, true).withSpot("N0L0", "internet"),
                app("re-lunar", "Lunar Client", "lunar", AppGroup.GAMES, false, true).withSpot("E1L0", "games"),
                app("re-terminal", "Terminal", "terminal", AppGroup.SYSTEM_TOOLS, true, true).withSpot("S0R0", "system_tools"),
                app("re-notepad", "Notepad", null, AppGroup.SYSTEM_TOOLS, false, true).withSpot("S0L0", "system_tools"),
                app("re-spotify", "Spotify", "spotify", AppGroup.WORK_MEDIA, false, true).withSpot("W0R0", "work_media"),
                app("re-mail", "Mail", "mail", AppGroup.INTERNET, false, false).withSpot("N2L1", "internet")));
        var first = fake.pass(server);
        check(first.lines().equals(List.of("The town is built: 6 logos. /apps lists them.")) && !first.pending(), "A fresh home: " + first.lines());
        for (var app : fake.apps) if (app.mine()) check(place(server, app.id()).equals(app.place()), app.id() + " stands at " + place(server, app.id()));
        check(fake.saves.isEmpty(), "A place was given out again: " + fake.saves);

        // Point 2: the counts. Point 1: the east road reaches row 1; the others end where package 32 ended them.
        check(names(level, hub).equals(List.of("INTERNET \u00b7 2", "GAMES \u00b7 1", "SYSTEM & TOOLS \u00b7 2", "WORK & MEDIA \u00b7 1")),
                "The counts: " + names(level, hub));
        for (int outward = 3; outward <= HubLayout.avenueEnd(1); outward++) check(paved(level, hub, AppGroup.GAMES, outward), "East road at " + outward);
        check(grass(level, hub, AppGroup.GAMES, HubLayout.avenueEnd(1) + 1), "The east road is paved too far");
        check(paved(level, hub, AppGroup.INTERNET, 24) && grass(level, hub, AppGroup.INTERNET, 25), "The north road changed without a reason");

        // A road grows with its group, over untouched grass only: his cobblestone on the way stays, its grass unpaved.
        BlockPos cobble = AppGroup.INTERNET.block(home, 30, 1, 0);
        level.setBlockAndUpdate(cobble, Blocks.COBBLESTONE.defaultBlockState());
        fake.change("re-mail", app -> app.withMine(true));
        var joined = fake.pass(server);
        check(joined.lines().equals(List.of("Mail stands in Internet, north. /mail opens it.")) && place(server, "re-mail").equals("N2L1"), "Mail: " + joined.lines());
        for (int outward = 25; outward <= HubLayout.avenueEnd(2); outward++)
            if (outward != 30) check(paved(level, hub, AppGroup.INTERNET, outward), "North road at " + outward);
        check(level.getBlockState(cobble).is(Blocks.COBBLESTONE) && level.getBlockState(cobble.below()).is(Blocks.GRASS_BLOCK) && !hub.holds(level, cobble.below()),
                "The road went under his cobblestone");
        check(grass(level, hub, AppGroup.INTERNET, HubLayout.avenueEnd(2) + 1), "The north road is paved too far");
        check(text(level, hub.fixed().names().getFirst()).equals("INTERNET \u00b7 3"), "A join is not counted");

        // ... and never shrinks: Mail leaves, its road stays.
        fake.change("re-mail", app -> app.withMine(false));
        var left = fake.pass(server);
        check(left.lines().equals(List.of("Mail left My apps. Its logo came down.")), "Mail left: " + left.lines());
        for (int outward = 25; outward <= HubLayout.avenueEnd(2); outward++)
            if (outward != 30) check(paved(level, hub, AppGroup.INTERNET, outward), "The north road shrank at " + outward);
        check(text(level, hub.fixed().names().getFirst()).equals("INTERNET \u00b7 2"), "A leave is not counted");

        // Point 4: a logo drawn by another converter is renewed in place by itself.
        var chrome = hub.logo("re-chrome").orElseThrow();
        hub.remove("re-chrome");
        hub.add(new HubData.Logo(chrome.app(), chrome.place(), chrome.picture(), GatePicture.CONVERTER - 1, chrome.name(), chrome.shortName(),
                chrome.zone(), chrome.gate()));
        var converted = fake.pass(server);
        check(converted.lines().equals(List.of("The logo of Chrome was renewed.")) && hub.logo("re-chrome").orElseThrow().converter() == GatePicture.CONVERTER
                && place(server, "re-chrome").equals("N0R0"), "Another converter: " + converted.lines());

        // Point 5: the sign's second line follows the main short name.
        check(text(level, hub.logo("re-chrome").orElseThrow().gate().sign().orElseThrow()).equals("Chrome\n/chrome"), "Chrome's sign");
        fake.change("re-chrome", app -> app.withNames(List.of("web", "chrome")));
        var renamed = fake.pass(server);
        var signed = hub.logo("re-chrome").orElseThrow();
        check(renamed.lines().equals(List.of("The logo of Chrome was renewed.")) && signed.shortName().equals(Optional.of("web"))
                && text(level, signed.gate().sign().orElseThrow()).equals("Chrome\n/web") && signed.place().equals("N0R0"), "A new short name: " + renamed.lines());
        check(fake.pass(server).lines().isEmpty(), "A pass in step changed something");

        // Point 3: hub rebuild. His glass in place of a block of Discord's logo stays his; Discord cannot stand in N0L0
        // again and goes one place on; every other logo is built again where it stood; his cobblestone stays.
        var discord = hub.logo("re-discord").orElseThrow();
        var plan = Town.plan(hub, fake.get("re-discord"), Place.parse("N0L0").orElseThrow(), fake.ring);
        BlockPos glass = plan.blocks().keySet().stream().filter(pos -> pos.getY() == home.getY() + 6).findFirst().orElseThrow();
        level.setBlockAndUpdate(glass, Blocks.GLASS.defaultBlockState());
        check(!hub.holds(level, glass) && discord.gate().placed().stream().anyMatch(block -> block.pos().equals(glass)), "Fixture: the glass");
        var zones = hub.logos().stream().map(HubData.Logo::zone).toList();
        var rebuilt = fake.keeper.rebuild(server, new TownKeeper.Programs(fake.apps, true), app -> Optional.of(fake.ring), spots -> {
            fake.saves.add(spots);
            fake.apps.replaceAll(app -> spots.containsKey(app.id()) ? app.withSpot(spots.get(app.id()).place(), spots.get(app.id()).group()) : app);
        });
        check(rebuilt.lines().size() == 3 && rebuilt.lines().get(0).equals("The town was rebuilt from the rules: 5 logos built again, 1 moved.")
                && rebuilt.lines().get(1).startsWith("The logo of Discord came down to be renewed but cannot stand at N0L0 again: ")
                && rebuilt.lines().get(2).equals("N0L0 is blocked by something of yours, so Discord stands at N1L0."), "Rebuild: " + rebuilt.lines());
        check(level.getBlockState(glass).is(Blocks.GLASS) && level.getBlockState(cobble).is(Blocks.COBBLESTONE), "His glass or cobblestone went");
        check(place(server, "re-discord").equals("N1L0") && "N1L0".equals(fake.get("re-discord").place()), "Discord one place on");
        for (var app : List.of("re-chrome", "re-lunar", "re-terminal", "re-notepad", "re-spotify"))
            check(place(server, app).equals(fake.get(app).place()), app + " moved in the rebuild");
        check(hub.logos().stream().map(HubData.Logo::zone).noneMatch(zones::contains), "A logo was not built again");
        check(text(level, hub.fixed().names().getFirst()).equals("INTERNET \u00b7 2"), "The rebuild's count");

        // The town comes down: one line for six, and nothing of it is left but his things.
        fake.apps.replaceAll(app -> app.withMine(false));
        var empty = fake.pass(server);
        check(empty.lines().equals(List.of("The town changed: 6 logos taken down. /apps lists where your apps stand.")) && hub.logos().isEmpty(),
                "Taking the town down: " + empty.lines());
        check(!fake.zoneLeft(server), "A zone of the town stayed");
        check(names(level, hub).equals(List.of("INTERNET \u00b7 0", "GAMES \u00b7 0", "SYSTEM & TOOLS \u00b7 0", "WORK & MEDIA \u00b7 0")), "Empty: " + names(level, hub));
        level.setBlockAndUpdate(glass, Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(cobble, Blocks.AIR.defaultBlockState());
    }

    private static final String SEAL_BATCH = "aresos-test:town_seal";

    /**
     * Review fixes 1 (points 1 to 4) and 2 (point 1) through the world's own files: a normal save is sealed when the
     * world is read again; a whole-world copy, opened as the game opens a world, stays sealed; an earlier town.dat put
     * back alone (a subset of the logos that stand, or none) freezes the whole town, which then builds, removes and
     * paves nothing for any app, and a save does not seal it; a hub.dat of another home, an unreadable town.dat and
     * one with overlapping records are refused and kept, and the town does nothing in that world; the review's
     * scenario (an older mod saved the world after he rebuilt a block of a logo with the same block) freezes the
     * town, so that block stays, a newcomer gets no logo, {@code hub rebuild} refuses, a save and reopen stay frozen,
     * and {@code hub trust} from a source that is not the host is refused; trust lets the pass run and the next save
     * renews the seal; a town.dat restored from a backup, or one moved away, is unsealed; an empty town whose seal
     * shows an empty town needs no trust. Between the first save and the rest, the town goes on from its records read
     * back from the files (step B, point 7). Its own batch and ground; the copies are made beside the test world and
     * removed.
     */
    @GameTest(environment = SEAL_BATCH, maxTicks = LOAD_TICKS)
    public void theTownTrustsItsRecordsOnlyWhileTheWorldWasSavedWithThem(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(21000, 0, 0);
        var near = chunks(column.offset(-48, 0, -60), column.offset(48, 0, 16));
        var fake = new Fake();
        fake.prefix = "seal-";
        hold(level, near, true);
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> keeping(fake, level, near, true, () -> sealing(fake, level, column)))
                .thenSucceed();
    }

    /** A world's files read as the game reads them when the world opens: a data storage of their own. */
    private static SavedDataStorage storage(MinecraftServer server, Path world) {
        return new SavedDataStorage(world.resolve(LevelResource.DATA.id()), server.getFixerUpper(), server.registryAccess());
    }

    /** The hub of a world's files as the world opens, joined to its town: sealed, frozen or refused. */
    private static HubData reopen(MinecraftServer server, Path world) {
        var hub = HubData.open(storage(server, world), world, TownSeal.seed(server));
        check(hub != null, "No hub.dat in " + world);
        return hub;
    }

    /** A copy of the world as a whole, of the files the town reads: level.dat and data/aresos. */
    private static Path copy(Path world, Path to) throws IOException {
        var data = to.resolve("data").resolve("aresos");
        Files.createDirectories(data);
        Files.copy(world.resolve("level.dat"), to.resolve("level.dat"));
        try (var files = Files.list(world.resolve("data").resolve("aresos"))) {
            for (var file : files.toList()) Files.copy(file, data.resolve(file.getFileName()));
        }
        return to;
    }

    /** The game opens a copied world: it writes level.dat before any server runs on it, as Minecraft.doWorldLoad does. */
    private static void opened(MinecraftServer server, Path copies, String name) throws IOException {
        try (var access = LevelStorageSource.createDefault(copies).createAccess(name)) {
            access.saveDataTag(server.getWorldData());
        }
    }

    /** An older mod or plain Minecraft saves the world: level.dat with another LastPlayed and no seal; town.dat as it was. */
    private static void olderModSaves(LevelStorageSource.LevelStorageAccess access, long lastPlayed) throws IOException {
        var data = access.getUnfixedDataTag(false);
        access.saveLevelData(data.set("LastPlayed", data.createLong(lastPlayed)));
    }

    /** Rewrites a world's town.dat on disk, its records as the game saved them ("data", "logos"). */
    private static void rewrite(Path world, java.util.function.Consumer<net.minecraft.nbt.ListTag> logos) throws IOException {
        var file = HubData.townFile(world);
        var saved = NbtIo.readCompressed(file, net.minecraft.nbt.NbtAccounter.uncompressedQuota());
        var list = saved.getCompoundOrEmpty("data").getListOrEmpty("logos");
        check(!list.isEmpty(), "Fixture: no logos in " + file);
        logos.accept(list);
        NbtIo.writeCompressed(saved, file);
    }

    /** The trigger zones of this test's apps. */
    private static List<AppZone> zones(MinecraftServer server) {
        return ZoneData.get(server).zones().stream().filter(zone -> zone.app().startsWith("seal-")).toList();
    }

    private static final String FREEZE = "This world was opened without the town's records since its last visit, so the town builds and removes nothing. ";

    private static void sealing(Fake fake, ServerLevel level, BlockPos column) throws IOException {
        var server = level.getServer();
        fake.previous = HubData.get(server);
        BlockPos home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
        check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home);
        fake.home = home;
        fake.clearZones(server);
        HubData hub = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), FlatHub.build(level, home));
        HubData.store(server, hub);
        // Day one: Chrome alone; Discord joins My apps after the first save.
        fake.apps.addAll(List.of(app("seal-chrome", "Chrome", "chrome", AppGroup.INTERNET, true, true),
                app("seal-discord", "Discord", "discord", AppGroup.INTERNET, false, false)));
        fake.pass(server);
        check(place(server, "seal-chrome").equals("N0L0") && hub.logos().size() == 1, "Day one: " + hub.logos());
        Path world = server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
        long seed = TownSeal.seed(server);
        Path copies = Files.createTempDirectory(world.getParent(), "aresos-town-seal");
        BlockPos his = null;
        boolean done = false;
        try {
            // The town.dat of a save with Chrome alone: the earlier file that review fixes 2 puts back.
            server.saveAllChunks(true, true, true);
            byte[] chromeOnly = Files.readAllBytes(HubData.townFile(world));
            fake.change("seal-discord", app -> app.withMine(true));
            fake.pass(server);
            check(place(server, "seal-discord").equals("N0R0"), "Discord joined: " + hub.logos());

            // A normal save writes level.dat, the seal and town.dat together; the world read again is sealed.
            server.saveAllChunks(true, true, true);
            var seal = TownSeal.read(world).orElseThrow(() -> new AssertionError("No seal after a save"));
            check(TownSeal.lastPlayed(world).equals(OptionalLong.of(seal.lastPlayed())) && seal.seed() == seed, "The seal " + seal + " for " + TownSeal.lastPlayed(world));
            var reopened = reopen(server, world);
            check(reopened.refusal().isEmpty() && !reopened.frozen() && reopened.logos().equals(hub.logos()), "Read again after a save: " + reopened.logos());
            byte[] backup = Files.readAllBytes(HubData.townFile(world));

            // A whole-world copy, opened in the game: the game writes level.dat first, the seal follows it.
            var copy = copy(world, copies.resolve("copy"));
            opened(server, copies, "copy");
            check(TownSeal.holding(copy).isPresent(), "The copy's seal was not carried to its new level.dat");
            var copied = reopen(server, copy);
            check(copied.refusal().isEmpty() && !copied.frozen() && copied.logos().equals(hub.logos()), "A whole-world copy: " + copied.logos());

            // Review fixes 2, point 1: the earlier town.dat (Chrome alone) put back while Discord's logo stands. The town
            // cannot tell Discord from a new app, so the whole town is frozen: a pass builds no second Discord logo and
            // takes nothing down, and Discord's blocks, sign and zone stay as they are.
            var subset = copy(world, copies.resolve("subset"));
            Files.write(HubData.townFile(subset), chromeOnly);
            var restored = reopen(server, subset);
            check(restored.refusal().isEmpty() && restored.frozen() && restored.logos().size() == 1 && restored.logo("seal-discord").isEmpty(),
                    "A subset restored: frozen " + restored.frozen() + ", " + restored.logos());
            var discordSign = hub.logo("seal-discord").orElseThrow().gate().sign().orElseThrow();
            var discordText = text(level, discordSign);
            var zonesBefore = zones(server);
            var area = snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2));
            HubData.store(server, restored);
            check(TownKeeper.notice(server).equals(Optional.of(FREEZE + "Look over its logo, then type /aresos hub trust.")), "The freeze's line: " + TownKeeper.notice(server));
            var subsetPass = fake.pass(server);
            check(subsetPass.lines().isEmpty() && !subsetPass.pending() && restored.logos().size() == 1 && snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2)).equals(area)
                    && zones(server).equals(zonesBefore) && level.getEntity(discordSign) instanceof Display.TextDisplay && text(level, discordSign).equals(discordText),
                    "A subset restored changed something: " + subsetPass.lines() + " " + restored.logos());
            HubData.store(server, hub);

            // Review fixes 1, step B, point 7: the town goes on from the records read back from the saved files. A pass
            // on them builds nothing twice and says nothing; a renewal takes the old logo down by its reloaded sign and
            // zone IDs, so one sign and one zone stand for it afterwards.
            HubData.store(server, reopened);
            hub = reopened;
            var inStep = fake.pass(server);
            check(inStep.lines().isEmpty() && HubData.get(server) == reopened && reopened.logos().size() == 2 && zones(server).equals(zonesBefore),
                    "A pass on the records read back: " + inStep.lines());
            var oldChrome = reopened.logo("seal-chrome").orElseThrow();
            fake.pictures.put("seal-chrome", picture(0xff2d8f2d));
            var renewedChrome = fake.pass(server);
            var newChrome = reopened.logo("seal-chrome").orElseThrow();
            check(renewedChrome.lines().equals(List.of("The logo of Chrome was renewed.")) && level.getEntity(oldChrome.gate().sign().orElseThrow()) == null
                    && level.getEntity(newChrome.gate().sign().orElseThrow()) instanceof Display.TextDisplay
                    && ZoneData.get(server).zones().stream().filter(zone -> zone.app().equals("seal-chrome")).map(AppZone::id).toList().equals(List.of(newChrome.zone())),
                    "Renewed from the records read back: " + renewedChrome.lines());
            // Saved again, so the files hold the town as it stands for what follows.
            server.saveAllChunks(true, true, true);

            // hub.dat of another home beside this town.dat: refused, kept as it is, and the town does nothing.
            var other = copy(world, copies.resolve("other"));
            var elsewhere = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home.east(64)), hub.fixed());
            var file = new net.minecraft.nbt.CompoundTag();
            file.put("data", HubData.CODEC.encodeStart(NbtOps.INSTANCE, elsewhere).getOrThrow());
            NbtIo.writeCompressed(NbtUtils.addCurrentDataVersion(file), other.resolve("data").resolve("aresos").resolve("hub.dat"));
            byte[] town = Files.readAllBytes(HubData.townFile(other));
            var otherStorage = storage(server, other);
            var refused = HubData.open(otherStorage, other, seed);
            check(refused.refusal().orElse("").startsWith("it was saved for a home at ") && refused.logos().isEmpty(), "Another home: " + refused.refusal());
            otherStorage.saveAndJoin();
            check(Arrays.equals(town, Files.readAllBytes(HubData.townFile(other))), "A town.dat of another home was written over");
            // ... an unreadable one ...
            var broken = copy(world, copies.resolve("broken"));
            Files.write(HubData.townFile(broken), new byte[] {1, 2, 3});
            var brokenStorage = storage(server, broken);
            check(HubData.open(brokenStorage, broken, seed).refusal().equals(Optional.of("it cannot be read")), "An unreadable town.dat");
            brokenStorage.saveAndJoin();
            check(Arrays.equals(new byte[] {1, 2, 3}, Files.readAllBytes(HubData.townFile(broken))), "An unreadable town.dat was written over");
            // ... and one whose records overlap (a logo recorded twice), written to disk and opened (review fixes 2).
            var overlapping = copy(world, copies.resolve("overlapping"));
            rewrite(overlapping, logos -> logos.add(logos.getFirst().copy()));
            byte[] overlap = Files.readAllBytes(HubData.townFile(overlapping));
            var overlapStorage = storage(server, overlapping);
            var twice = HubData.open(overlapStorage, overlapping, seed);
            check(twice.refusal().orElse("").startsWith("two logos are recorded for seal-") && twice.logos().isEmpty(), "Overlapping records on disk: " + twice.refusal());
            overlapStorage.saveAndJoin();
            check(Arrays.equals(overlap, Files.readAllBytes(HubData.townFile(overlapping))), "A town.dat with overlapping records was written over");
            HubData.store(server, refused);
            area = snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2));
            fake.change("seal-discord", app -> app.withMine(false));
            var nothing = fake.pass(server);
            check(nothing.lines().isEmpty() && !nothing.pending() && snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2)).equals(area),
                    "A refused town changed something: " + nothing.lines());
            var notice = TownKeeper.notice(server).orElse("");
            check(notice.startsWith("The town's file " + HubData.townFile(world) + " does not fit this world (it was saved for a home at ")
                    && notice.endsWith("To start the town afresh, close the world and move that file out of the world's folder."), "The refusal's line: " + notice);
            fake.change("seal-discord", app -> app.withMine(true));
            HubData.store(server, hub);

            // The review's scenario. He takes a block of Discord's logo away and builds his own of the same block there;
            // this mod lets go of it at once, an older mod (packages 32 to 35) does not know town.dat and saves the world
            // without the seal.
            var recorded = hub.logo("seal-discord").orElseThrow().gate().placed().getFirst();
            his = recorded.pos();
            level.setBlockAndUpdate(his, Blocks.AIR.defaultBlockState());
            level.setBlockAndUpdate(his, Placing.state(recorded.block()));
            check(!hub.holds(level, his), "His block is still the town's");
            var access = ((dev.aresos.mixin.ServerStorageAccess)server).aresos$storageSource();
            olderModSaves(access, seal.lastPlayed() + 1);
            var older = reopen(server, world);
            check(older.frozen() && older.logo("seal-discord").orElseThrow().gate().placed().contains(recorded), "The older mod's world: frozen " + older.frozen());
            HubData.store(server, older);
            var freeze = FREEZE + "Look over its 2 logos, then type /aresos hub trust.";
            check(TownKeeper.notice(server).equals(Optional.of(freeze)), "The freeze's line: " + TownKeeper.notice(server));

            // Frozen, the town changes nothing in the world for any app (review fixes 2, point 2): Discord leaves, Chrome
            // gets a new name and picture, and Mail is new. Nothing comes down, nothing is renewed, Mail gets no logo,
            // no road is paved and his block stays.
            var logos = older.logos();
            zonesBefore = zones(server);
            area = snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2));
            fake.change("seal-discord", app -> app.withMine(false));
            fake.change("seal-chrome", app -> app("seal-chrome", "Chrome Browser", "chrome", AppGroup.INTERNET, true, true).withSpot(app.place(), app.group()));
            fake.pictures.put("seal-chrome", picture(0xff8f2d2d));
            fake.apps.add(app("seal-mail", "Mail", "mail", AppGroup.INTERNET, false, true));
            var frozen = fake.pass(server);
            check(frozen.lines().isEmpty() && !frozen.pending() && frozen.pictures().isEmpty() && older.logos().equals(logos) && place(server, "seal-mail").equals("none")
                    && zones(server).equals(zonesBefore) && snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2)).equals(area),
                    "A frozen town changed something: " + frozen.lines() + " " + older.logos());
            // hub rebuild refuses with the freeze's line.
            var rebuilt = fake.keeper.rebuild(server, new TownKeeper.Programs(fake.apps, true), app -> Optional.of(fake.pictures.getOrDefault(app.id(), fake.ring)), spots -> { });
            check(rebuilt.lines().equals(List.of(freeze)) && older.logos().equals(logos) && snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2)).equals(area),
                    "A rebuild while frozen: " + rebuilt.lines());

            // /aresos hub trust from a source that is not the host is refused where it is parsed: the server's own
            // source, and a player who is not the host (the test server is no singleplayer game, so it has no host).
            var guest = new net.minecraft.server.level.ServerPlayer(server, level, new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "Guest"),
                    net.minecraft.server.level.ClientInformation.createDefault());
            for (var source : List.of(server.createCommandSourceStack(), server.createCommandSourceStack().withEntity(guest))) {
                check(!dev.aresos.hub.HubCommands.hub().build().canUse(source), "hub's requirement let a source that is not the host through");
                boolean ran;
                try {
                    server.getCommands().getDispatcher().execute("aresos hub trust", source);
                    ran = true;
                } catch (com.mojang.brigadier.exceptions.CommandSyntaxException notParsed) {
                    ran = false;
                }
                check(!ran && HubData.get(server).frozen(), "hub trust ran for a source that is not the host");
            }

            // Saved and opened again without trust: still frozen, the seal was not renewed.
            var sealBefore = Files.readAllBytes(TownSeal.file(world));
            server.saveAllChunks(true, true, true);
            check(Arrays.equals(sealBefore, Files.readAllBytes(TownSeal.file(world))) && reopen(server, world).frozen(), "A save while frozen sealed the town");

            // An empty town.dat put back while the logos stand: frozen too, nothing is built, and a save does not seal it.
            var emptied = copy(world, copies.resolve("emptied"));
            rewrite(emptied, net.minecraft.nbt.ListTag::clear);
            var empty = reopen(server, emptied);
            check(empty.refusal().isEmpty() && empty.frozen() && empty.logos().isEmpty(), "An empty town.dat restored: frozen " + empty.frozen());
            HubData.store(server, empty);
            check(TownKeeper.notice(server).equals(Optional.of(FREEZE + "Its records hold no logo: look the town over, then type /aresos hub trust.")),
                    "The freeze's line with no logo: " + TownKeeper.notice(server));
            var emptyPass = fake.pass(server);
            check(emptyPass.lines().isEmpty() && empty.logos().isEmpty() && zones(server).equals(zonesBefore) && snapshot(level, home.offset(-40, -2, -45), home.offset(40, 16, 2)).equals(area),
                    "An empty town.dat restored built something: " + emptyPass.lines());
            server.saveAllChunks(true, true, true);
            var savedEmpty = reopen(server, world);
            check(Arrays.equals(sealBefore, Files.readAllBytes(TownSeal.file(world))) && savedEmpty.frozen() && savedEmpty.logos().isEmpty(), "A save sealed the empty town.dat");
            HubData.store(server, older);

            // He looks the logos over (the block he wants to keep, he changes: it is his) and trusts the records. The
            // pass runs: Discord comes down, Chrome is renewed and Mail gets a logo.
            level.setBlockAndUpdate(his, Blocks.DIAMOND_BLOCK.defaultBlockState());
            check(TownKeeper.trust(server).equals(Optional.of("The town trusts its records again and keeps their 2 logos in step with your apps. Anything of a logo"
                    + " they do not hold is yours from now on, and the town may build that app a logo of its own."))
                    && !HubData.get(server).frozen() && TownKeeper.trust(server).isEmpty() && TownKeeper.notice(server).isEmpty(), "Trust");
            var trusted = fake.pass(server);
            check(trusted.lines().containsAll(List.of("Discord left My apps. Its logo came down.", "The logo of Chrome Browser was renewed."))
                    && trusted.lines().stream().anyMatch(line -> line.startsWith("Mail ")), "After trust: " + trusted.lines());
            check(level.getBlockState(his).is(Blocks.DIAMOND_BLOCK) && place(server, "seal-discord").equals("none") && !place(server, "seal-mail").equals("none"),
                    "His diamond, Discord's logo or Mail's: " + place(server, "seal-mail"));
            // The next save renews the seal.
            server.saveAllChunks(true, true, true);
            check(!reopen(server, world).frozen() && reopen(server, world).logos().size() == 2, "The seal was not renewed after trust");

            // town.dat restored from the backup taken after the first save, into a copy of this world: unsealed.
            var fromBackup = copy(world, copies.resolve("restored"));
            Files.write(HubData.townFile(fromBackup), backup);
            var backedUp = reopen(server, fromBackup);
            check(backedUp.refusal().isEmpty() && backedUp.frozen() && backedUp.logo("seal-discord").isPresent(), "A town.dat from a backup: frozen " + backedUp.frozen());
            // town.dat moved out of the world's folder (to start afresh, review fixes 2, point 5): the seal still names
            // logos, so the town is frozen once more and asks for trust.
            var movedAway = copy(world, copies.resolve("moved"));
            Files.delete(HubData.townFile(movedAway));
            var withoutFile = reopen(server, movedAway);
            check(withoutFile.refusal().isEmpty() && withoutFile.frozen() && withoutFile.logos().isEmpty(), "town.dat moved away: frozen " + withoutFile.frozen());

            // The end: everything leaves. A town with no logos and no seal needs no trust, nor one whose seal shows an
            // empty town of this home after an older mod saved the world.
            fake.apps.replaceAll(app -> app.withMine(false));
            fake.pass(server);
            check(HubData.get(server).logos().isEmpty() && !fake.zoneLeft(server), "Taking the town down");
            server.saveAllChunks(true, true, true);
            var noSeal = copy(world, copies.resolve("empty"));
            Files.delete(TownSeal.file(noSeal));
            check(!reopen(server, noSeal).frozen() && reopen(server, noSeal).refusal().isEmpty(), "A town with no logos was not taken as its own");
            copy(world, copies.resolve("older"));
            try (var olderAccess = LevelStorageSource.createDefault(copies).createAccess("older")) {
                olderModSaves(olderAccess, TownSeal.lastPlayed(world).orElseThrow() + 1);
            }
            check(TownSeal.holding(copies.resolve("older")).isEmpty() && !reopen(server, copies.resolve("older")).frozen(), "An empty town saved by an older mod was frozen");
            done = true;
        } finally {
            if (his != null) level.setBlockAndUpdate(his, Blocks.AIR.defaultBlockState());
            try (var paths = Files.walk(copies)) {
                for (var path : paths.sorted(java.util.Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
            }
            // This test saves the world on purpose, and a failed check stops the test server without its last save. So
            // a failed run must not leave its town in the saved files: every later town of the kept test world would be
            // refused (a town.dat of another home with logos). Its records go (its blocks stay on its own ground, as
            // any failed run's do), the previous hub comes back, and the world is saved once more.
            if (!done) {
                var current = HubData.get(server);
                if (current != null) for (var logo : current.logos()) current.remove(logo.app());
                fake.clearZones(server);
                if (fake.previous != null) HubData.store(server, fake.previous);
                server.saveAllChunks(true, true, true);
            }
        }
    }

    private interface Action { void run() throws IOException; }

    /** Runs an action that must refuse with a message containing {@code words}, and returns the refusal. */
    private static IOException refused(Action action, String words) {
        try { action.run(); }
        catch (IOException expected) {
            check(expected.getMessage().contains(words), "Refused for another reason: " + expected.getMessage());
            return expected;
        }
        throw new AssertionError("Not refused: expected \"" + words + "\"");
    }
}
