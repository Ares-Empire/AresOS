package dev.aresos.test;

import dev.aresos.config.AppDefinition;
import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
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
import net.minecraft.nbt.NbtOps;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Display;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

import java.awt.image.BufferedImage;
import java.io.IOException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
    private static GatePicture picture() {
        var icon = new BufferedImage(96, 96, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 96; y++) for (int x = 0; x < 96; x++) {
            double r = Math.hypot(x - 47.5, y - 47.5);
            icon.setRGB(x, y, r > 18 && r < 32 ? 0xffffffff : 0xff2d2f8f);
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
