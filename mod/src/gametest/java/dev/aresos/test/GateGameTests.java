package dev.aresos.test;

import dev.aresos.world.DesktopWorld;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import dev.aresos.zone.LogoPixels;
import dev.aresos.zone.ZoneCommands;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.fabricmc.fabric.api.registry.FlammableBlockRegistry;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Display;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerExplosion;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Fallable;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.level.block.state.properties.SlabType;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Consumer;

import static dev.aresos.test.ChunkWaits.LOAD_TICKS;
import static dev.aresos.test.ChunkWaits.waitFor;

/** The gate: its plan against HUB.md 3.2, and building and removing it in a world. */
public final class GateGameTests {
    private static final int[] SIZES = {10, 12, 14, 16};
    /**
     * The framework's own bound for a test that waits for chunks of its own, never reached while the server ticks
     * (package 39b, as package 37's): its one wait fails by itself and releases its tickets after
     * {@link ChunkWaits#LOAD_TICKS} ticks or {@link ChunkWaits#WAIT_NANOS} on the wall clock. The test server ticks as
     * fast as it can, about 70,000 times a second when nothing else runs.
     */
    private static final int SITE_TICKS = LOAD_TICKS + 1_000;
    /** The app of zones a test puts in a gate's way. */
    private static final String BLOCKER = "gate-blocker";

    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }

    private static Block block(String name) { return BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(name)); }

    private static GatePlan plan(int size, BlockPos origin, Direction outward) {
        return GatePlan.of(GatePicture.plain("stone", size), Level.OVERWORLD, origin, outward, "Fixture", null, "light_blue_concrete");
    }

    /** One row of the day-one table in HUB.md 3.2. */
    private static void example(String place, BlockPos origin, Direction outward, BlockPos boxMin, BlockPos boxMax,
                                Set<Integer> nicheX, Set<Integer> nicheZ, Vec3 exit, float yaw) {
        var plan = plan(12, origin, outward);
        var cells = plan.blocks().keySet();
        var min = new BlockPos(cells.stream().mapToInt(BlockPos::getX).min().orElseThrow(), cells.stream().mapToInt(BlockPos::getY).min().orElseThrow(),
                cells.stream().mapToInt(BlockPos::getZ).min().orElseThrow());
        var max = new BlockPos(cells.stream().mapToInt(BlockPos::getX).max().orElseThrow(), cells.stream().mapToInt(BlockPos::getY).max().orElseThrow(),
                cells.stream().mapToInt(BlockPos::getZ).max().orElseThrow());
        check(min.equals(boxMin) && max.equals(boxMax), place + " blocks: " + min + " to " + max);
        check(cells.size() == 12 * 12 * 3 - 2 * 3 * 2, place + " block count " + cells.size());
        var niche = new TreeSet<BlockPos>();
        for (var pos : BlockPos.betweenClosed(plan.nicheMin(), plan.nicheMax())) niche.add(pos.immutable());
        check(niche.size() == 12 && niche.stream().noneMatch(cells::contains), place + " niche is not open");
        check(niche.stream().map(BlockPos::getX).collect(java.util.stream.Collectors.toSet()).equals(nicheX)
                && niche.stream().map(BlockPos::getZ).collect(java.util.stream.Collectors.toSet()).equals(nicheZ)
                && niche.stream().allMatch(pos -> pos.getY() >= 64 && pos.getY() <= 66), place + " niche: " + niche);
        // The same columns and heights one layer further back are black concrete.
        for (int u = 5; u <= 6; u++) for (int v = 0; v < 3; v++) {
            check(niche.contains(plan.at(0, u, v)) && niche.contains(plan.at(1, u, v)), place + " niche is not columns 5 and 6, heights 0 to 2");
            check(GatePalette.BLACK.equals(plan.blocks().get(plan.at(2, u, v))), place + " niche back at " + plan.at(2, u, v));
        }
        check(plan.exit().equals(new NetherHome.Home(Level.OVERWORLD, exit, yaw, -10)), place + " exit: " + plan.exit());
        check(plan.exit().position().distanceTo(Vec3.atBottomCenterOf(plan.at(0, 5, 0)).add(Vec3.atBottomCenterOf(plan.at(0, 6, 0))).scale(0.5)) == 6, place + " exit is not 5.5 in front of the face");
    }

    @GameTest
    public void planMatchesTheWorkedExamplesOfTheDesign(GameTestHelper helper) {
        example("N0L0", new BlockPos(-15, 64, -20), Direction.NORTH, new BlockPos(-15, 64, -22), new BlockPos(-4, 75, -20),
                Set.of(-10, -9), Set.of(-20, -21), new Vec3(-9.0, 64, -13.5), 180);
        example("N0R0", new BlockPos(4, 64, -20), Direction.NORTH, new BlockPos(4, 64, -22), new BlockPos(15, 75, -20),
                Set.of(9, 10), Set.of(-20, -21), new Vec3(10.0, 64, -13.5), 180);
        example("E0L0", new BlockPos(20, 64, -15), Direction.EAST, new BlockPos(20, 64, -15), new BlockPos(22, 75, -4),
                Set.of(20, 21), Set.of(-10, -9), new Vec3(14.5, 64, -9.0), -90);
        example("S0L0", new BlockPos(15, 64, 20), Direction.SOUTH, new BlockPos(4, 64, 20), new BlockPos(15, 75, 22),
                Set.of(9, 10), Set.of(20, 21), new Vec3(10.0, 64, 14.5), 0);
        example("S0R0", new BlockPos(-4, 64, 20), Direction.SOUTH, new BlockPos(-15, 64, 20), new BlockPos(-4, 75, 22),
                Set.of(-10, -9), Set.of(20, 21), new Vec3(-9.0, 64, 14.5), 0);
        example("W1R1", new BlockPos(-34, 64, -18), Direction.WEST, new BlockPos(-36, 64, -29), new BlockPos(-34, 75, -18),
                Set.of(-34, -35), Set.of(-23, -24), new Vec3(-27.5, 64, -23.0), 90);

        // The rest of HUB.md 3.2, on N0L0: sign, light blocks and doormat.
        var chrome = plan(12, new BlockPos(-15, 64, -20), Direction.NORTH);
        check(chrome.sign().position().equals(new Vec3(-9.0, 76.5, -19.5)) && chrome.sign().name().equals("Fixture") && chrome.sign().shortName() == null,
                "sign: " + chrome.sign());
        check(chrome.lights().equals(List.of(new BlockPos(-13, 70, -19), new BlockPos(-6, 70, -19))), "lights: " + chrome.lights());
        check(Set.copyOf(chrome.doormat()).equals(Set.of(new BlockPos(-10, 63, -18), new BlockPos(-9, 63, -18), new BlockPos(-10, 63, -19),
                new BlockPos(-9, 63, -19), new BlockPos(-10, 63, -20), new BlockPos(-9, 63, -20), new BlockPos(-10, 63, -21), new BlockPos(-9, 63, -21)))
                && chrome.doormat().size() == 8, "doormat: " + chrome.doormat());
        check(chrome.doormatBlock().equals("light_blue_concrete"), "doormat block");
        // The spaces that must be free: the box, one layer in front, and columns 4 to 7 out to the exit block.
        var space = Set.copyOf(chrome.space());
        check(space.size() == 12 * 12 * 4 + 4 * 3 * 5, "space size " + space.size());
        check(space.contains(new BlockPos(-15, 75, -19)) && space.contains(new BlockPos(-11, 64, -14)) && space.contains(new BlockPos(-8, 66, -18))
                && !space.contains(new BlockPos(-12, 64, -18)) && !space.contains(new BlockPos(-11, 64, -13)) && !space.contains(new BlockPos(-11, 67, -18)), "space shape");
        helper.succeed();
    }

    @GameTest
    public void everySizeKeepsTheSameDoorAndExit(GameTestHelper helper) {
        for (int size : SIZES) for (var outward : Direction.Plane.HORIZONTAL) {
            var plan = plan(size, new BlockPos(100, 70, -40), outward);
            // The trigger zone is the saved zone's box: it must be the niche whichever way the gate faces.
            var niche = new AppZone("id", "app", Level.OVERWORLD, plan.nicheMin(), plan.nicheMax(), plan.exit(), List.of()).box();
            check(niche.getYsize() == 3 && niche.getXsize() * niche.getZsize() == 4 && niche.minY == 70, size + " " + outward + " niche is not 2 x 3 x 2: " + niche);
            for (int along = 0; along < 2; along++) for (int u = size / 2 - 1; u <= size / 2; u++) for (int v = 0; v < 3; v++)
                check(niche.contains(Vec3.atCenterOf(plan.at(along, u, v))) && !plan.blocks().containsKey(plan.at(along, u, v)), size + " " + outward + " niche misses " + plan.at(along, u, v));
            check(!niche.contains(Vec3.atCenterOf(plan.at(-1, size / 2, 0))) && !niche.contains(Vec3.atCenterOf(plan.at(2, size / 2, 0))), size + " niche reaches outside the doorway");
            check(plan.blocks().size() == size * size * 3 - 12, size + " block count");
            // The niche's middle and the exit share the doorway's centre line, which is the logo's middle.
            var middle = Vec3.atLowerCornerOf(plan.at(0, 0, 0)).add(Vec3.atLowerCornerOf(plan.at(0, size - 1, 0)).add(1, 0, 1)).scale(0.5);
            var across = Vec3.atLowerCornerOf(outward.getClockWise().getUnitVec3i());
            check(Math.abs(niche.getCenter().subtract(middle).dot(across)) < 1e-9, size + " door is not in the middle");
            check(Math.abs(plan.exit().position().subtract(middle).dot(across)) < 1e-9, size + " exit is not on the centre line");
            check(Math.abs(plan.exit().position().subtract(middle).dot(Vec3.atLowerCornerOf(outward.getUnitVec3i())) + 6) < 1e-9, size + " exit distance");
            check(plan.exit().pitch() == -10 && Math.abs(Vec3.directionFromRotation(0, plan.exit().yaw()).dot(Vec3.atLowerCornerOf(outward.getUnitVec3i())) - 1) < 1e-6,
                    size + " exit does not look at the door");
            check(plan.sign().position().y == 70 + size + 0.5, size + " sign height");
            check(plan.lights().stream().allMatch(light -> light.getY() == 70 + size / 2) && plan.lights().size() == 2, size + " light height");
            check(plan.lights().contains(plan.at(-1, 2, size / 2)) && plan.lights().contains(plan.at(-1, size - 3, size / 2)), size + " light columns");
        }
        helper.succeed();
    }

    @GameTest
    public void theCommandsGateStandsSixBlocksAheadFacingHim(GameTestHelper helper) {
        for (var facing : Direction.Plane.HORIZONTAL) for (double fraction : new double[]{0.05, 0.5, 0.95}) {
            var feet = new Vec3(-7 + fraction, 64, 12 + fraction);
            var plan = plan(12, GatePlan.originInFrontOf(feet, facing, 12), facing);
            var ahead = Vec3.atLowerCornerOf(facing.getUnitVec3i());
            var across = Vec3.atLowerCornerOf(facing.getClockWise().getUnitVec3i());
            var exit = plan.exit().position();
            check(BlockPos.containing(feet).getY() == plan.origin().getY(), "gate is not on his ground");
            // The exit block is the block he stands in, and the centre line is at most half a block beside him.
            check(Math.abs(exit.subtract(Vec3.atBottomCenterOf(BlockPos.containing(feet))).dot(ahead)) < 1e-9, facing + " exit block");
            check(Math.abs(exit.subtract(feet).dot(across)) <= 0.5 + 1e-9, facing + " centre line is " + exit.subtract(feet).dot(across) + " beside him");
            check(plan.at(0, 5, 0).relative(facing, -6).equals(BlockPos.containing(exit.subtract(across.scale(0.5)))), facing + " front layer is not six blocks ahead");
        }
        helper.succeed();
    }

    @GameTest
    public void paletteBlocksAreFullAndStill(GameTestHelper helper) {
        var notPlain = new TreeSet<String>();
        var neighborCallbacks = new TreeSet<String>();
        for (int i = 0; i < GatePalette.BLOCKS.size(); i++) {
            String name = GatePalette.BLOCKS.get(i).block();
            var block = block(name);
            var state = block.defaultBlockState();
            // Inspect all sixty classes, including inherited overrides, rather than assuming the palette is inert.
            for (Class<?> type = block.getClass(); type != Block.class; type = type.getSuperclass())
                for (var method : type.getDeclaredMethods())
                    if (Set.of("updateShape", "neighborChanged", "updateIndirectNeighbourShapes", "onPlace", "affectNeighborsAfterRemoval").contains(method.getName()))
                        neighborCallbacks.add(name + ":" + method.getName());
            check(block != Blocks.AIR, name + " is not a block in this game version");
            check(state.isCollisionShapeFullBlock(EmptyBlockGetter.INSTANCE, BlockPos.ZERO) && state.getFluidState().isEmpty(), name + " is not a full block");
            check(!(block instanceof Fallable), name + " falls");
            check(!state.isRandomlyTicking() && !state.hasBlockEntity() && !state.isSignalSource(), name + " ticks, holds data or gives a signal");
            if (i >= LogoPixels.PALETTE.size()) {
                // The wall's wool burns; the twelve new blocks must not.
                var fire = FlammableBlockRegistry.getDefaultInstance().get(block);
                check(fire == null || fire.getBurnOdds() == 0 && fire.getIgniteOdds() == 0, name + " burns");
                if (block.getClass() != Block.class) notPlain.add(name + ":" + block.getClass().getSimpleName());
            }
        }
        // Three of the twelve have a class of their own: a mushroom block's faces follow its neighbours, amethyst
        // chimes when hit, blue ice is slippery to walk on. None of that moves or changes a standing logo.
        check(notPlain.equals(Set.of("red_mushroom_block:HugeMushroomBlock", "amethyst_block:AmethystBlock", "blue_ice:HalfTransparentBlock")),
                "blocks with their own class: " + notPlain);
        check(neighborCallbacks.equals(Set.of("red_mushroom_block:updateShape")), "palette neighbour callbacks: " + neighborCallbacks);
        helper.succeed();
    }

    @GameTest
    public void zonesFilesWrittenBeforeGatesStillLoad(GameTestHelper helper) throws IOException {
        // What the mod wrote before this package, copied as text from two zones.dat files of its client tests
        // (the wall's 716 protected blocks shortened to the first two).
        var wall = read("before-33-wall.snbt");
        var zones = ZoneData.CODEC.parse(NbtOps.INSTANCE, wall).getOrThrow().zones();
        check(zones.size() == 1 && zones.getFirst().app().equals("zone-notes") && zones.getFirst().blocks().equals(List.of(new BlockPos(4, 180, -1), new BlockPos(3, 180, -1)))
                && !zones.getFirst().isGate() && zones.getFirst().min().equals(new BlockPos(-15, 150, -3)) && zones.getFirst().exit().yaw() == -11.309933f, "wall zone: " + zones);
        var handMade = read("before-33-hand-made.snbt");
        var two = ZoneData.CODEC.parse(NbtOps.INSTANCE, handMade).getOrThrow().zones();
        check(two.size() == 2 && two.get(1).id().equals("seam-1") && two.get(1).blocks().isEmpty() && !two.get(1).isGate()
                && two.get(1).exit().position().equals(new Vec3(2.5, 150, -1.5)), "hand-made zones: " + two);
        // Written again they are the same data: an older mod reads what this one saves for them.
        for (var saved : List.of(wall, handMade))
            check(ZoneData.CODEC.encodeStart(NbtOps.INSTANCE, ZoneData.CODEC.parse(NbtOps.INSTANCE, saved).getOrThrow()).getOrThrow().equals(saved), "old zones changed when saved again");
        // A gate's zone keeps the old fields and adds one. Without it, it reads as a zone with protected blocks.
        var gate = new AppZone("id", "app", Level.OVERWORLD, BlockPos.ZERO, new BlockPos(1, 2, 1), new NetherHome.Home(Level.OVERWORLD, new Vec3(1, 0, -5.5), 0, -10),
                List.of(new BlockPos(3, 0, 0)), java.util.Optional.of(new AppZone.Gate(List.of(new AppZone.Placed(new BlockPos(3, 0, 0), "minecraft:stone")),
                List.of(new AppZone.Placed(new BlockPos(3, -1, 0), "minecraft:grass_block")), java.util.Optional.of(java.util.UUID.randomUUID()))));
        var encoded = (CompoundTag)AppZone.CODEC.encodeStart(NbtOps.INSTANCE, gate).getOrThrow();
        check(AppZone.CODEC.parse(NbtOps.INSTANCE, encoded).getOrThrow().equals(gate), "gate zone did not round-trip");
        check(encoded.keySet().equals(Set.of("id", "app", "dimension", "min", "max", "exit", "blocks", "gate")), "gate zone fields: " + encoded.keySet());
        encoded.remove("gate");
        var plain = AppZone.CODEC.parse(NbtOps.INSTANCE, encoded).getOrThrow();
        check(!plain.isGate() && plain.blocks().equals(gate.blocks()) && plain.exit().equals(gate.exit()), "gate zone without its gate field");
        helper.succeed();
    }

    private static CompoundTag read(String name) throws IOException {
        try (var input = GateGameTests.class.getResourceAsStream("/zones/" + name)) {
            return net.minecraft.nbt.TagParser.parseCompoundFully(new String(input.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8).strip());
        } catch (com.mojang.brigadier.exceptions.CommandSyntaxException error) { throw new IOException(error); }
    }

    /**
     * A place for one gate high above the test's own structure, where no other test builds. Each test has its
     * own height, so the sites of tests that stand side by side do not meet.
     */
    private record Site(ServerLevel level, BlockPos base, String app) {
        interface Body { void run(Site site) throws IOException; }

        /**
         * Runs the body once the site's chunks are loaded with their entities, as they are around a player, on a
         * stone floor. A gate reaches into chunks next to the test's own, which the test world loads only when asked.
         */
        static void run(GameTestHelper helper, int lift, Body body) {
            DesktopWorld.setEnabled(helper.getLevel().getServer(), true);
            var site = new Site(helper.getLevel(), helper.absolutePos(BlockPos.ZERO).above(lift), "gate-fixture-" + lift);
            site.hold(true);
            helper.startSequence().thenWaitUntil(waitFor(helper, site.level, site.chunks(), site::loaded, "The site's chunks are not loaded yet", () -> { }))
                    .thenExecute(() -> {
                try {
                    site.clear();
                    site.floor(Blocks.GRASS_BLOCK);
                    body.run(site);
                } catch (IOException error) { throw new AssertionError(error.getMessage(), error); }
                finally { site.clear(); site.hold(false); }
            }).thenSucceed();
        }

        private Set<Long> chunks() {
            var chunks = new java.util.HashSet<Long>();
            for (var pos : region()) chunks.add(ChunkPos.pack(pos));
            return chunks;
        }

        /**
         * Keeps the site's chunks loaded with a ticket of the test's own. The test framework forces the chunks of
         * every test structure and releases them when that test ends, so forcing and releasing them here would
         * take a neighbouring test's chunks away before it has started.
         */
        void hold(boolean held) { ChunkWaits.hold(level, chunks(), held); }

        boolean loaded() { return ChunkWaits.loaded(level, chunks()); }

        Iterable<BlockPos> region() { return BlockPos.betweenClosed(base.offset(-4, -3, 3), base.offset(24, 20, 20)); }

        AABB box() { return new AABB(Vec3.atLowerCornerOf(base.offset(-4, -3, 3)), Vec3.atLowerCornerOf(base.offset(25, 21, 21))); }

        void clear() {
            ZoneData.get(level.getServer()).remove(zone -> zone.app().equals(app) || zone.app().equals(BLOCKER));
            for (var pos : region()) if (!level.getBlockState(pos).isAir()) level.setBlock(pos, Blocks.AIR.defaultBlockState(), 2 | 16);
            // Signs, and whatever an explosion or a fixture left lying here.
            level.getEntities((net.minecraft.world.entity.Entity)null, box(), entity -> !(entity instanceof net.minecraft.world.entity.player.Player))
                    .forEach(net.minecraft.world.entity.Entity::discard);
        }

        void floor(Block block) {
            for (var pos : BlockPos.betweenClosed(base.offset(-4, -1, 3), base.offset(24, -1, 20))) level.setBlock(pos, block.defaultBlockState(), 2 | 16);
        }

        List<Display.TextDisplay> signs() { return level.getEntitiesOfClass(Display.TextDisplay.class, box()); }

        /** A gate facing south: he would stand at higher z and look north at it. */
        GatePlan plan(GatePicture picture) {
            return GatePlan.of(picture, level.dimension(), base.offset(0, 0, 10), Direction.NORTH, "Fixture", null, "light_blue_concrete");
        }

        Map<BlockPos, BlockState> snapshot() {
            var states = new HashMap<BlockPos, BlockState>();
            for (var pos : region()) states.put(pos.immutable(), level.getBlockState(pos));
            return states;
        }

        List<AppZone> zones() { return ZoneData.get(level.getServer()).zones().stream().filter(zone -> zone.app().equals(app)).toList(); }

        AppZone build(GatePlan plan) {
            try { return GateBuilder.build(level, app, plan); } catch (IOException error) { throw new AssertionError("Build refused: " + error.getMessage(), error); }
        }
    }

    /**
     * Red mushroom, amethyst and blue ice side by side: the three palette blocks with a class of their own. The
     * cells are given: since package 39 the converter builds red wool where the mushroom block's red is wanted
     * (HUB.md 3.6), and a gate drawn before that may still hold the mushroom block.
     */
    private static GatePicture stripes(int size) {
        var cells = new String[size * size];
        for (int v = 0; v < size; v++) for (int u = 0; u < size; u++)
            cells[v * size + u] = 3 * u < size ? "red_mushroom_block" : 3 * u < 2 * size ? "amethyst_block" : "blue_ice";
        return GatePicture.ofBlocks(cells, size);
    }

    /**
     * Review fixes 2, point 2, through {@code /aresos logo remove}'s own path ({@link GateBuilder#remove} and its line):
     * a hand-built gate records where its sign stands and what it says, and the sign is taken down only while it is
     * still that. An unedited sign goes; an edited one stays; a text display of his with the sign's ID and text at
     * another place stays; a record without the sign's place and text (packages 33 to 35, or written again by one of
     * them) leaves the sign and says so. The gate's blocks come down every time.
     */
    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void aHandBuiltSignIsTakenDownOnlyWhileItIsTheOneTheGateWasBuiltWith(GameTestHelper helper) {
        Site.run(helper, 310, site -> {
            var level = site.level();
            var server = level.getServer();
            var before = site.snapshot();
            var plan = site.plan(stripes(12));
            java.util.function.Consumer<String> blocksBack = when -> {
                for (var cell : before.entrySet()) check(level.getBlockState(cell.getKey()).equals(cell.getValue()),
                        when + ": " + cell.getKey() + " is " + level.getBlockState(cell.getKey()) + ", was " + cell.getValue());
            };

            // Unedited: the record names the sign's place and text, saved and read back whole; the sign goes.
            var unedited = site.build(plan);
            check(unedited.gate().orElseThrow().signPlan().equals(java.util.Optional.of(plan.sign())), "The sign's place and text are not recorded: " + unedited.gate());
            check(AppZone.CODEC.parse(NbtOps.INSTANCE, AppZone.CODEC.encodeStart(NbtOps.INSTANCE, unedited).getOrThrow()).getOrThrow().equals(unedited), "The record does not read back whole");
            var gone = GateBuilder.remove(server, unedited);
            check(gone.sign() == GateBuilder.SignLeft.NONE && site.signs().isEmpty() && site.zones().isEmpty()
                    && ZoneCommands.tookDown(unedited, gone).equals("Took down the gate of " + site.app() + ": " + gone.removed() + " blocks removed."),
                    "An unedited sign: " + ZoneCommands.tookDown(unedited, gone) + ", signs " + site.signs().size());
            blocksBack.accept("Unedited");

            // Edited (as /data does): his, it stays.
            var editedGate = site.build(plan);
            var edited = site.signs().getFirst();
            ((dev.aresos.mixin.TextDisplayAccess)edited).aresos$setText(net.minecraft.network.chat.Component.literal("My notice"));
            var withEdited = GateBuilder.remove(server, editedGate);
            check(withEdited.sign() == GateBuilder.SignLeft.CHANGED && !edited.isRemoved() && site.signs().equals(List.of(edited)) && site.zones().isEmpty()
                    && ZoneCommands.tookDown(editedGate, withEdited).endsWith(" blocks removed. Its sign stays: it is not the one the gate was built with, so it is yours."),
                    "An edited sign: " + ZoneCommands.tookDown(editedGate, withEdited) + ", taken away " + edited.isRemoved());
            blocksBack.accept("Edited");
            edited.discard();

            // A text display of his that took the sign's ID, with the sign's text, four blocks higher: his, it stays.
            var reusedGate = site.build(plan);
            var sign = site.signs().getFirst();
            var id = sign.getUUID();
            var his = net.minecraft.world.entity.EntityType.create(net.minecraft.world.entity.EntityTypes.TEXT_DISPLAY,
                    net.minecraft.world.level.storage.TagValueInput.create(net.minecraft.util.ProblemReporter.DISCARDING, level.registryAccess(), new CompoundTag()),
                    level, net.minecraft.world.entity.EntitySpawnReason.COMMAND).orElseThrow();
            ((dev.aresos.mixin.TextDisplayAccess)his).aresos$setText(((dev.aresos.mixin.TextDisplayAccess)sign).aresos$text());
            sign.discard();
            his.setUUID(id);
            his.snapTo(sign.getX(), sign.getY() + 4, sign.getZ(), 0, 0);
            check(level.addFreshEntity(his) && level.getEntity(id) == his, "Fixture: his display with the sign's ID");
            var withHis = GateBuilder.remove(server, reusedGate);
            check(withHis.sign() == GateBuilder.SignLeft.CHANGED && !his.isRemoved() && site.zones().isEmpty(), "His display with the sign's ID: " + withHis + ", taken away " + his.isRemoved());
            blocksBack.accept("His display");
            his.discard();

            // A record of packages 33 to 35: no place or text of its sign. Its blocks come down, the sign stays, and the
            // line says the sign is his.
            var built = site.build(plan);
            var gate = built.gate().orElseThrow();
            var older = new AppZone(built.id(), built.app(), built.dimension(), built.min(), built.max(), built.exit(), built.blocks(),
                    java.util.Optional.of(new AppZone.Gate(gate.placed(), gate.ground(), gate.sign(), gate.grass())));
            ZoneData.get(server).remove(zone -> zone.id().equals(built.id()));
            ZoneData.get(server).add(older);
            var olderSign = site.signs().getFirst();
            var withOlder = GateBuilder.remove(server, older);
            check(withOlder.sign() == GateBuilder.SignLeft.UNRECORDED && !olderSign.isRemoved() && site.zones().isEmpty()
                    && ZoneCommands.tookDown(older, withOlder).endsWith(" blocks removed. Its sign stays and is yours: this gate's record is from an older AresOS and does not say what the sign said."),
                    "An older record: " + ZoneCommands.tookDown(older, withOlder) + ", taken away " + olderSign.isRemoved());
            blocksBack.accept("An older record");
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void buildMatchesThePlanAndRemovalLeavesTheWorldAsItWas(GameTestHelper helper) {
        Site.run(helper, 40, site -> {
            var level = site.level();
            var before = site.snapshot();
            var plan = site.plan(stripes(12));
            var zone = site.build(plan);
            // The world holds exactly the plan: logo, black niche back, light blocks, doormat, and nothing else.
            var expected = new HashMap<>(before);
            plan.blocks().forEach((pos, name) -> expected.put(pos, block(name).defaultBlockState()));
            plan.lights().forEach(pos -> expected.put(pos, Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, 15)));
            plan.doormat().forEach(pos -> expected.put(pos, block("light_blue_concrete").defaultBlockState()));
            for (var cell : expected.entrySet()) {
                var state = level.getBlockState(cell.getKey());
                // A mushroom block hides the faces that touch another one; it is still that block.
                check(state.is(cell.getValue().getBlock()) && (state.equals(cell.getValue()) || state.is(Blocks.RED_MUSHROOM_BLOCK)),
                        "Block at " + cell.getKey() + " is " + state + ", planned " + cell.getValue());
            }
            check(plan.blocks().containsValue("red_mushroom_block") && plan.blocks().containsValue("amethyst_block") && plan.blocks().containsValue("blue_ice")
                    && plan.blocks().containsValue("black_concrete"), "fixture picture lost a block kind");
            for (var pos : BlockPos.betweenClosed(plan.nicheMin(), plan.nicheMax())) check(level.getBlockState(pos).isAir(), "niche is not open at " + pos);
            // The zone: exactly the niche, the planned exit, every placed block protected and recorded by ID.
            check(site.zones().equals(List.of(zone)) && zone.isGate(), "zone not saved as a gate");
            check(zone.min().equals(plan.nicheMin()) && zone.max().equals(plan.nicheMax()) && zone.exit().equals(plan.exit()), "zone box or exit differs from the plan");
            var gate = zone.gate().orElseThrow();
            var recorded = new HashMap<BlockPos, String>();
            gate.placed().forEach(placed -> recorded.put(placed.pos(), placed.block()));
            check(recorded.size() == plan.blocks().size() + 2 + 8 && Set.copyOf(zone.blocks()).equals(recorded.keySet()) && zone.blocks().size() == recorded.size(),
                    "record has " + recorded.size() + " blocks");
            plan.blocks().forEach((pos, name) -> check(("minecraft:" + name).equals(recorded.get(pos)), "record at " + pos + ": " + recorded.get(pos)));
            check(plan.lights().stream().allMatch(pos -> "minecraft:light".equals(recorded.get(pos)))
                    && plan.doormat().stream().allMatch(pos -> "minecraft:light_blue_concrete".equals(recorded.get(pos))), "lights or doormat not recorded");
            check(gate.ground().size() == 8 && gate.ground().stream().allMatch(ground -> ground.block().equals("minecraft:grass_block") && plan.doormat().contains(ground.pos())),
                    "replaced ground: " + gate.ground());
            // The sign: one text display where the plan says, which nothing can hit.
            check(site.signs().size() == 1, "signs: " + site.signs().size());
            var sign = site.signs().getFirst();
            check(sign.getUUID().equals(gate.sign().orElseThrow()) && sign.position().equals(plan.sign().position()), "sign is at " + sign.position());
            check(!sign.isPickable() && !sign.hurtServer(level, level.damageSources().generic(), 100) && sign.isAlive(), "the sign can be hit");

            var removal = GateBuilder.remove(level.getServer(), zone);
            check(removal.removed() == recorded.size() && removal.kept() == 0, "removal: " + removal);
            for (var cell : before.entrySet()) check(level.getBlockState(cell.getKey()).equals(cell.getValue()),
                    "After removal " + cell.getKey() + " is " + level.getBlockState(cell.getKey()) + ", was " + cell.getValue());
            check(site.signs().isEmpty() && site.zones().isEmpty(), "sign or zone left behind");
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void explosionsStillProtectGateBlocks(GameTestHelper helper) {
        Site.run(helper, 220, site -> {
            var level = site.level();
            var plan = site.plan(stripes(12));
            var zone = site.build(plan);
            var gate = zone.gate().orElseThrow();
            // Explosions leave the logo and the doormat alone, as they do a wall's blocks.
            var control = plan.at(-3, 3, 0);
            level.setBlockAndUpdate(control, Blocks.STONE.defaultBlockState());
            var centre = Vec3.atCenterOf(plan.at(-2, 4, 0));
            new ServerExplosion(level, null, level.damageSources().badRespawnPointExplosion(centre), null, centre, 6, false, Explosion.BlockInteraction.DESTROY).explode();
            check(level.getBlockState(control).isAir(), "explosion did not destroy the unprotected control block");
            for (var placed : gate.placed()) check(("minecraft:" + BuiltInRegistries.BLOCK.getKey(level.getBlockState(placed.pos()).getBlock()).getPath()).equals(placed.block()),
                    "explosion destroyed " + placed);
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void removalRestoresOnlyRecordedGrassThatIsNowDirt(GameTestHelper helper) {
        Site.run(helper, 250, site -> {
            var level = site.level();
            var plan = site.plan(GatePicture.plain("iron_block", 12));
            var before = site.snapshot();
            var zone = site.build(plan);
            var saved = AppZone.CODEC.parse(NbtOps.INSTANCE, AppZone.CODEC.encodeStart(NbtOps.INSTANCE, zone).getOrThrow()).getOrThrow();
            check(saved.equals(zone) && saved.gate().orElseThrow().grass().size() == 12 * 3, "grass floor record did not round-trip");
            var changed = plan.at(1, 3, -1);
            for (var pos : saved.gate().orElseThrow().grass()) if (!plan.doormat().contains(pos)) {
                // Exercise vanilla's decay, rather than accepting dirt as a restoration success.
                var state = level.getBlockState(pos);
                state.randomTick(level, pos, level.getRandom());
                check(level.getBlockState(pos).is(Blocks.DIRT), "covered grass did not decay at " + pos);
            }
            level.setBlockAndUpdate(changed, Blocks.DIAMOND_BLOCK.defaultBlockState());
            GateBuilder.remove(level.getServer(), saved);
            var expected = new HashMap<>(before);
            expected.put(changed, Blocks.DIAMOND_BLOCK.defaultBlockState());
            check(expected.equals(site.snapshot()), "removal did not restore decayed grass or changed his floor");
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void blocksHeChangedSurviveTheRemoval(GameTestHelper helper) {
        Site.run(helper, 70, site -> {
            var level = site.level();
            var before = site.snapshot();
            var plan = site.plan(GatePicture.plain("iron_block", 12));
            var zone = site.build(plan);
            BlockPos swapped = plan.at(0, 2, 7), mined = plan.at(1, 9, 4), mat = plan.doormat().getFirst(), light = plan.lights().getFirst();
            level.setBlockAndUpdate(swapped, Blocks.DIAMOND_BLOCK.defaultBlockState());
            level.setBlockAndUpdate(mined, Blocks.AIR.defaultBlockState());
            level.setBlockAndUpdate(mat, Blocks.GOLD_BLOCK.defaultBlockState());
            level.setBlockAndUpdate(light, Blocks.GLASS.defaultBlockState());
            var edits = Map.of(
                    plan.at(1, 4, 6), Blocks.STONE_SLAB.defaultBlockState().setValue(SlabBlock.TYPE, SlabType.TOP),
                    plan.at(1, 7, 8), Blocks.QUARTZ_PILLAR.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.X),
                    plan.at(1, 6, 4), Blocks.STONE_STAIRS.defaultBlockState().setValue(StairBlock.FACING, Direction.EAST).setValue(StairBlock.HALF, Half.TOP));
            edits.forEach(level::setBlockAndUpdate);
            var removal = GateBuilder.remove(level.getServer(), zone);
            check(removal.kept() == 7 && removal.removed() == zone.blocks().size() - 7, "removal: " + removal);
            var expected = new HashMap<>(before);
            expected.put(swapped, Blocks.DIAMOND_BLOCK.defaultBlockState());
            expected.put(mat, Blocks.GOLD_BLOCK.defaultBlockState());
            expected.put(light, Blocks.GLASS.defaultBlockState());
            expected.putAll(edits);
            for (var cell : expected.entrySet()) check(level.getBlockState(cell.getKey()).equals(cell.getValue()),
                    "After removal " + cell.getKey() + " is " + level.getBlockState(cell.getKey()) + ", expected " + cell.getValue());
            check(site.signs().isEmpty() && site.zones().isEmpty(), "sign or zone left behind");
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void retainedConnectionsCanChangeTheirShapeDuringRemoval(GameTestHelper helper) {
        Site.run(helper, 280, site -> {
            var level = site.level();
            var plan = site.plan(GatePicture.plain("iron_block", 12));
            var zone = site.build(plan);
            var edits = Map.of(plan.at(1, 2, 5), Blocks.COBBLESTONE_WALL.defaultBlockState(),
                    plan.at(1, 5, 7), Blocks.OAK_FENCE.defaultBlockState(),
                    plan.at(1, 8, 5), Blocks.GLASS_PANE.defaultBlockState());
            var connected = new HashMap<BlockPos, BlockState>();
            edits.forEach((pos, state) -> {
                var attached = Block.updateFromNeighbourShapes(state, level, pos);
                level.setBlockAndUpdate(pos, attached);
                connected.put(pos, attached);
            });
            var removal = GateBuilder.remove(level.getServer(), zone);
            check(removal.kept() == 3 && removal.removed() == zone.blocks().size() - 3, "connection removal: " + removal);
            edits.forEach((pos, state) -> {
                var actual = level.getBlockState(pos);
                check(actual.is(state.getBlock()) && actual.getFluidState().isEmpty(), "removed a retained connection at " + pos);
                check(!actual.equals(connected.get(pos)), "connection did not follow the removed neighbours at " + pos);
                check(actual.equals(Block.updateFromNeighbourShapes(state, level, pos)), "connection did not settle at " + pos + ": " + actual);
            });
            check(site.signs().isEmpty() && site.zones().isEmpty(), "connection removal left a sign or zone");
        });
    }

    private static void refused(Site site, String what, String message, Consumer<GatePlan> obstacle) {
        site.clear();
        site.floor(Blocks.STONE);
        var plan = site.plan(stripes(12));
        obstacle.accept(plan);
        var before = site.snapshot();
        int signs = site.signs().size();
        try {
            GateBuilder.build(site.level(), site.app(), plan);
            throw new AssertionError("Built despite " + what);
        } catch (IOException expected) {
            check(expected.getMessage().contains(message), what + " refused with: " + expected.getMessage());
        }
        for (var cell : before.entrySet()) check(site.level().getBlockState(cell.getKey()).equals(cell.getValue()), what + ": refusal changed " + cell.getKey());
        check(site.zones().isEmpty() && site.signs().size() == signs, what + ": refusal saved a zone or left a sign");
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void editedLightsKeepTheirWaterAndLevel(GameTestHelper helper) {
        Site.run(helper, 160, site -> {
            var plan = site.plan(GatePicture.plain("iron_block", 12));
            var zone = site.build(plan);
            var water = Blocks.LIGHT.defaultBlockState().setValue(LightBlock.WATERLOGGED, true);
            var dim = Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, 7);
            site.level().setBlock(plan.lights().getFirst(), water, 2);
            site.level().setBlock(plan.lights().getLast(), dim, 2);
            var removal = GateBuilder.remove(site.level().getServer(), zone);
            check(removal.kept() == 2 && removal.removed() == zone.blocks().size() - 2, "edited light removal: " + removal);
            check(site.level().getBlockState(plan.lights().getFirst()).equals(water), "waterlogged light or its water removed");
            check(site.level().getBlockState(plan.lights().getLast()).equals(dim), "dimmed light removed");
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void removalRefusesAttachmentsAndFallingBlocksBeforeChangingAnything(GameTestHelper helper) {
        Site.run(helper, 190, site -> {
            var level = site.level();
            var plan = site.plan(GatePicture.plain("iron_block", 12));
            var zone = site.build(plan);
            var top = plan.at(1, 2, 11).above();
            level.setBlockAndUpdate(top, Blocks.TORCH.defaultBlockState());
            removalRefused(site, zone, "minecraft:torch", top);
            level.setBlockAndUpdate(top, Blocks.AIR.defaultBlockState());
            // A changed pixel resting on a still-owned one is no longer part of the removal set.
            var sand = plan.at(1, 3, 7);
            level.setBlockAndUpdate(sand, Blocks.SAND.defaultBlockState());
            removalRefused(site, zone, "minecraft:sand", sand);
            level.setBlockAndUpdate(sand, Blocks.IRON_BLOCK.defaultBlockState());
            // The same slab callback is harmless dry, but schedules flowing water when waterlogged.
            var wet = Blocks.STONE_SLAB.defaultBlockState().setValue(SlabBlock.WATERLOGGED, true);
            level.setBlock(sand, wet, 2);
            removalRefused(site, zone, "minecraft:stone_slab", sand);
            level.setBlockAndUpdate(sand, Blocks.IRON_BLOCK.defaultBlockState());
            // Unknown/reactive callbacks remain a reason to refuse even on a full block.
            level.setBlockAndUpdate(sand, block("waxed_copper_bulb").defaultBlockState());
            removalRefused(site, zone, "minecraft:waxed_copper_bulb", sand);
            level.setBlockAndUpdate(sand, Blocks.IRON_BLOCK.defaultBlockState());
            var frame = new net.minecraft.world.entity.decoration.ItemFrame(level, plan.at(-1, 2, 5), Direction.SOUTH);
            check(frame.survives() && level.addFreshEntity(frame), "item frame fixture is not attached");
            removalRefused(site, zone, "minecraft:item_frame", frame.blockPosition());
            check(frame.isAlive(), "refusal removed the item frame");
            frame.discard();
            GateBuilder.remove(level.getServer(), zone);
        });
    }

    private static void removalRefused(Site site, AppZone zone, String thing, BlockPos pos) {
        var before = site.snapshot();
        var zones = site.zones();
        var signs = site.signs().stream().map(net.minecraft.world.entity.Entity::getUUID).toList();
        try {
            GateBuilder.remove(site.level().getServer(), zone);
            throw new AssertionError("Removed despite " + thing);
        } catch (IOException expected) {
            check(expected.getMessage().contains(thing) && expected.getMessage().contains(pos.toShortString()), "removal refused with: " + expected.getMessage());
        }
        check(before.equals(site.snapshot()), "refused removal changed blocks around " + thing);
        check(zones.equals(site.zones()) && signs.equals(site.signs().stream().map(net.minecraft.world.entity.Entity::getUUID).toList()), "refused removal lost the complete gate record or sign");
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void chunkBorderRefusesBeforeReadingTheUnloadedHalo(GameTestHelper helper) {
        var level = helper.getLevel();
        var chunk = new ChunkPos(10_000, 10_000);
        var origin = new BlockPos(chunk.getMinBlockX() + 1, 180, chunk.getMinBlockZ() + 8);
        var plan = plan(12, origin, Direction.NORTH);
        long key = chunk.pack();
        // A full but non-ticking chunk: its neighbours are not full chunks. Own only this ticket.
        level.getChunkSource().addTicketWithRadius(TicketType.DRAGON, chunk, 0);
        helper.startSequence().thenWaitUntil(waitFor(helper, level, Set.of(), () -> level.hasChunk(chunk.x(), chunk.z()) && level.areEntitiesLoaded(key),
                        "border chunk not loaded", () -> level.getChunkSource().removeTicketWithRadius(TicketType.DRAGON, chunk, 0)))
                .thenExecute(() -> {
                    var outside = plan.lights().getFirst().west(4);
                    var halo = ChunkPos.containing(outside);
                    try {
                        check(plan.space().stream().allMatch(pos -> ChunkPos.containing(pos).equals(chunk)), "fixture space crosses the border");
                        check(!level.hasChunk(halo.x(), halo.z()), "fixture's four-cell light halo is already loaded");
                        for (var pos : plan.walkway()) level.setBlock(pos, Blocks.STONE.defaultBlockState(), 2 | 16);
                        int chunks = level.getChunkSource().getLoadedChunksCount();
                        try {
                            GateBuilder.build(level, "gate-border", plan);
                            throw new AssertionError("built across unloaded light halo");
                        } catch (IOException expected) { check(expected.getMessage().contains("isn't loaded"), "border build: " + expected.getMessage()); }
                        check(!level.hasChunk(halo.x(), halo.z()) && chunks == level.getChunkSource().getLoadedChunksCount(), "build loaded an inspection chunk");
                        check(plan.blocks().keySet().stream().allMatch(pos -> level.getBlockState(pos).isAir()), "border build changed blocks");

                        var edge = origin.west();
                        level.setBlock(edge, Blocks.IRON_BLOCK.defaultBlockState(), 2 | 16);
                        var zone = new AppZone("gate-border", "gate-border", level.dimension(), plan.nicheMin(), plan.nicheMax(), plan.exit(), List.of(edge),
                                java.util.Optional.of(new AppZone.Gate(List.of(new AppZone.Placed(edge, "minecraft:iron_block")), List.of(), java.util.Optional.empty())));
                        ZoneData.get(level.getServer()).add(zone);
                        try {
                            GateBuilder.remove(level.getServer(), zone);
                            throw new AssertionError("removed across unloaded neighbour halo");
                        } catch (IOException expected) { check(expected.getMessage().contains("isn't loaded"), "border removal: " + expected.getMessage()); }
                        check(level.getBlockState(edge).is(Blocks.IRON_BLOCK) && ZoneData.get(level.getServer()).zones().contains(zone), "border refusal changed the gate or record");
                        check(!level.hasChunk(halo.x(), halo.z()) && chunks == level.getChunkSource().getLoadedChunksCount(), "removal loaded an inspection chunk");
                        level.setBlock(edge, Blocks.AIR.defaultBlockState(), 2 | 16);
                    } finally {
                        ZoneData.get(level.getServer()).remove(zone -> zone.id().equals("gate-border"));
                        for (var pos : plan.walkway()) level.setBlock(pos, Blocks.AIR.defaultBlockState(), 2 | 16);
                        level.getChunkSource().removeTicketWithRadius(TicketType.DRAGON, chunk, 0);
                    }
                }).thenSucceed();
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void everyRefusalChangesNothing(GameTestHelper helper) {
        Site.run(helper, 100, site -> {
            var level = site.level();
            var glass = Blocks.GLASS.defaultBlockState();
            refused(site, "a block in the logo's box", "Area isn't clear", plan -> level.setBlock(plan.at(2, 11, 11), glass, 2));
            refused(site, "an overhang through the name above the gate", "Area isn't clear",
                    plan -> level.setBlock(BlockPos.containing(plan.sign().position()).above(), Blocks.STONE.defaultBlockState(), 2));
            refused(site, "a block in a see-through part of the box", "Area isn't clear", plan -> level.setBlock(plan.at(0, 5, 1), glass, 2));
            refused(site, "a block in the layer in front", "Area isn't clear", plan -> level.setBlock(plan.at(-1, 0, 9), glass, 2));
            refused(site, "a block on the way in", "Area isn't clear", plan -> level.setBlock(plan.at(-4, 7, 2), glass, 2));
            refused(site, "a block on the exit point", "Area isn't clear", plan -> level.setBlock(plan.at(-6, 5, 1), glass, 2));
            refused(site, "a hole on the way to the door", "isn't solid", plan -> level.setBlock(plan.at(-3, 6, -1), Blocks.AIR.defaultBlockState(), 2));
            refused(site, "a hole under the niche", "isn't solid", plan -> level.setBlock(plan.at(1, 5, -1), Blocks.AIR.defaultBlockState(), 2));
            refused(site, "a torch beside the logo", "minecraft:torch", plan -> level.setBlock(plan.at(1, -2, 0), Blocks.TORCH.defaultBlockState(), 2));
            refused(site, "a dry slab beside the planned logo", "minecraft:stone_slab", plan -> level.setBlock(plan.at(3, 2, 5), Blocks.STONE_SLAB.defaultBlockState(), 2));
            refused(site, "water behind the logo", "minecraft:water", plan -> level.setBlock(plan.at(4, 3, 0), Blocks.WATER.defaultBlockState(), 2));
            refused(site, "a chest two cells behind the upper edge", "minecraft:chest", plan -> level.setBlock(plan.at(4, 6, 11), Blocks.CHEST.defaultBlockState(), 2));
            refused(site, "sand under the logo", "minecraft:sand", plan -> level.setBlock(plan.at(1, 0, -1), Blocks.SAND.defaultBlockState(), 2));
            refused(site, "ice four cells from a light block, where it would melt", "minecraft:ice", plan -> level.setBlock(plan.lights().getFirst().relative(Direction.SOUTH, 4), Blocks.ICE.defaultBlockState(), 2));
            refused(site, "an external mushroom behind a planned mushroom pixel", "minecraft:red_mushroom_block",
                    plan -> level.setBlock(plan.at(3, 0, 5), Blocks.RED_MUSHROOM_BLOCK.defaultBlockState(), 2));
            check(Blocks.ICE.defaultBlockState().getLightDampening() == 1, "ice dims light by " + Blocks.ICE.defaultBlockState().getLightDampening() + ": check how far a light block melts it");
            refused(site, "a zone across the doorway", "overlaps", plan -> ZoneData.get(level.getServer()).add(new AppZone("blocker", BLOCKER, level.dimension(),
                    plan.nicheMin(), plan.nicheMin(), AppZone.exit(level.dimension(), Vec3.atBottomCenterOf(plan.at(-4, 0, 0)), new AABB(plan.nicheMin())), List.of())));
            ZoneData.get(level.getServer()).remove(zone -> zone.id().equals("blocker"));
            refused(site, "a zone whose exit the logo would cover", "exit", plan -> ZoneData.get(level.getServer()).add(new AppZone("blocker", BLOCKER, level.dimension(),
                    plan.at(-9, 0, 0), plan.at(-9, 0, 0), AppZone.exit(level.dimension(), Vec3.atBottomCenterOf(plan.at(0, 1, 0)), new AABB(plan.at(-9, 0, 0))), List.of())));
            ZoneData.get(level.getServer()).remove(zone -> zone.id().equals("blocker"));
            refused(site, "an entity in the logo's place", "entity", plan -> {
                var stand = new net.minecraft.world.entity.decoration.ArmorStand(level, plan.at(1, 3, 0).getX() + 0.5, plan.at(1, 3, 0).getY(), plan.at(1, 3, 0).getZ() + 0.5);
                stand.setNoGravity(true);
                level.addFreshEntity(stand);
            });
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = SITE_TICKS)
    public void gatesStandOnGrassSideBySideAndTheDoormatNeedsUntouchedGround(GameTestHelper helper) {
        Site.run(helper, 130, site -> {
            var level = site.level();
            // Grass is not a plain block, and the flat home is made of it.
            site.floor(Blocks.GRASS_BLOCK);
            var first = site.build(site.plan(stripes(10)));
            check(first.gate().orElseThrow().ground().stream().allMatch(ground -> ground.block().equals("minecraft:grass_block")) && first.gate().orElseThrow().ground().size() == 8,
                    "doormat on grass: " + first.gate().orElseThrow().ground());
            // A second gate right beside the first. Only recorded positions establish ownership.
            var beside = GatePlan.of(stripes(10), level.dimension(), site.base().offset(10, 0, 10), Direction.NORTH, "Beside", "bs", "red_concrete");
            var loose = Map.of(beside.at(4, 7, 3), Blocks.AMETHYST_BLOCK,
                    beside.at(4, 9, 3), Blocks.BLUE_ICE);
            loose.forEach((pos, block) -> level.setBlock(pos, block.defaultBlockState(), 2));
            var second = site.build(beside);
            check(site.signs().size() == 2 && site.zones().size() == 2, "two gates: " + site.zones().size());
            GateBuilder.remove(level.getServer(), second);
            loose.keySet().forEach(pos -> level.setBlock(pos, Blocks.AIR.defaultBlockState(), 2));
            GateBuilder.remove(level.getServer(), first);
            for (var pos : site.region()) check(pos.getY() == site.base().getY() - 1 ? level.getBlockState(pos).is(Blocks.GRASS_BLOCK)
                    : level.getBlockState(pos).isAir(), "left behind at " + pos + ": " + level.getBlockState(pos));

            // One paving stone beside the door: the floor there may be his, so the gate is built without a doormat.
            site.clear();
            site.floor(Blocks.GRASS_BLOCK);
            var plan = site.plan(stripes(12));
            level.setBlock(plan.at(-3, 4, -1), Blocks.POLISHED_ANDESITE.defaultBlockState(), 2);
            var before = site.snapshot();
            var bare = site.build(plan);
            check(bare.gate().orElseThrow().ground().isEmpty() && plan.doormat().stream().allMatch(pos -> level.getBlockState(pos).is(Blocks.GRASS_BLOCK))
                    && plan.doormat().stream().noneMatch(bare.blocks()::contains), "doormat laid on changed ground");
            check(level.getBlockState(plan.at(0, 0, 0)).is(Blocks.RED_MUSHROOM_BLOCK), "gate not built without its doormat");
            GateBuilder.remove(level.getServer(), bare);
            for (var cell : before.entrySet()) check(level.getBlockState(cell.getKey()).equals(cell.getValue()),
                    "After removal " + cell.getKey() + " is " + level.getBlockState(cell.getKey()));
            // Paving all around the door is not ground either.
            site.clear();
            site.floor(Blocks.STONE_BRICKS);
            check(site.build(site.plan(stripes(12))).gate().orElseThrow().ground().isEmpty(), "doormat laid in a paved floor");
            for (var floor : List.of(Blocks.STONE, Blocks.DIRT)) {
                site.clear();
                site.floor(floor);
                var onFloor = site.build(site.plan(stripes(12)));
                check(onFloor.gate().orElseThrow().ground().size() == (floor == Blocks.DIRT ? 8 : 0), "doormat on " + floor);
                GateBuilder.remove(level.getServer(), onFloor);
            }
            site.clear();
            site.floor(Blocks.GRASS_BLOCK);
            var rear = plan.at(2, 5, -1);
            check(plan.doormatSurround().contains(rear), "doormat ring misses its rear row");
            level.setBlock(rear, Blocks.POLISHED_ANDESITE.defaultBlockState(), 2);
            var noRear = site.build(plan);
            check(noRear.gate().orElseThrow().ground().isEmpty() && plan.doormat().stream().noneMatch(noRear.blocks()::contains), "doormat ignored a changed rear row");
            GateBuilder.remove(level.getServer(), noRear);
            check(level.getBlockState(rear).is(Blocks.POLISHED_ANDESITE), "rear paving changed");
        });
    }
}
