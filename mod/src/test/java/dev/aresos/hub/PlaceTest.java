package dev.aresos.hub;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.zone.GateNumbers;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.*;

/** Places (HUB.md 3.2 and 3.3): their names, their order, and the gates GatePlan makes of them. */
class PlaceTest {
    private static final BlockPos HOME = HubLayout.HOME;

    /** A gate plan holds its exit as a saved home, whose codec needs the game's registries. */
    @BeforeAll static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    private static Place place(String name) { return Place.parse(name).orElseThrow(() -> new AssertionError("No place " + name)); }

    private static GatePlan plan(Place place) {
        return place.plan(GatePicture.plain("stone", HubLayout.SIZE), Level.OVERWORLD, HOME, "Fixture", null);
    }

    @Test void aNameGoesToItsPlaceAndBack() {
        assertEquals(new Place(AppGroup.INTERNET, 0, Place.Side.L, 0), place("N0L0"));
        assertEquals(new Place(AppGroup.SYSTEM_TOOLS, 2, Place.Side.R, 1), place("S2R1"));
        assertEquals(new Place(AppGroup.WORK_MEDIA, 1, Place.Side.R, 1), place("W1R1"));
        assertEquals(new Place(AppGroup.GAMES, 63, Place.Side.L, 17), place("E63L17"));
        assertEquals("E0L0", new Place(AppGroup.GAMES, 0, Place.Side.L, 0).name());
        assertEquals("W12R3", new Place(AppGroup.WORK_MEDIA, 12, Place.Side.R, 3).toString());
        for (var group : AppGroup.values()) Place.inOrder(group).limit(200).forEach(place -> assertEquals(Optional.of(place), Place.parse(place.name())));
        // One spelling per place, and only places that exist.
        for (String wrong : Arrays.asList(null, "", "N0L1", "N00L0", "N0L00", "N01R0", "n0l0", "N0l0", "X0L0", "N0X0", "N64L0", "N-1L0",
                " N0L0", "N0L0 ", "N0", "NL0", "N0L", "N1000L0", "N2R2N0L0"))
            assertEquals(Optional.empty(), Place.parse(wrong), wrong);
        assertThrows(IllegalArgumentException.class, () -> new Place(AppGroup.INTERNET, 1, Place.Side.L, 2));
        assertThrows(IllegalArgumentException.class, () -> new Place(AppGroup.INTERNET, Place.ROWS, Place.Side.L, 0));
        assertThrows(IllegalArgumentException.class, () -> new Place(AppGroup.INTERNET, 0, Place.Side.L, -1));
    }

    @Test void placesComeByRowThenKThenLeftBeforeRight() {
        assertEquals(List.of("N0L0", "N0R0", "N1L0", "N1R0", "N1L1", "N1R1", "N2L0", "N2R0", "N2L1", "N2R1", "N2L2", "N2R2", "N3L0"),
                Place.inOrder(AppGroup.INTERNET).limit(13).map(Place::name).toList());
        // Row r holds r + 1 places a side: rows 0 to 5 hold 42, the design's "12 logos per group" in row 5.
        assertEquals(42, Place.inOrder(AppGroup.GAMES).takeWhile(place -> place.row() <= 5).count());
        assertEquals(12, Place.inOrder(AppGroup.GAMES).filter(place -> place.row() == 5).count());
        var all = Place.inOrder(AppGroup.SYSTEM_TOOLS).toList();
        assertEquals(Place.ROWS * (Place.ROWS + 1), all.size());
        assertEquals(all.size(), new HashSet<>(all).size());
        assertEquals("S63R63", all.getLast().name());
        assertTrue(all.stream().allMatch(place -> place.group() == AppGroup.SYSTEM_TOOLS));
    }

    /** One row of the worked table of HUB.md 3.2: the logo's box, the niche, the exit point and the yaw. */
    private static void worked(String name, BlockPos min, BlockPos max, Set<Integer> nicheX, Set<Integer> nicheZ, Vec3 exit, float yaw) {
        var place = place(name);
        var plan = plan(place);
        assertEquals(place.facing(), plan.outward(), name);
        assertEquals(place.origin(HOME), plan.origin(), name);
        var blocks = plan.blocks().keySet();
        assertEquals(min, blocks.stream().reduce(BlockPos::min).orElseThrow(), name + " box");
        assertEquals(max, blocks.stream().reduce(BlockPos::max).orElseThrow(), name + " box");
        // A plain front fills all 12 x 12 x 3 but the open niche.
        assertEquals(12 * 12 * 3 - 2 * 3 * 2, blocks.size(), name);
        assertEquals(nicheX, range(plan.nicheMin().getX(), plan.nicheMax().getX()), name + " niche x");
        assertEquals(nicheZ, range(plan.nicheMin().getZ(), plan.nicheMax().getZ()), name + " niche z");
        assertEquals(64, plan.nicheMin().getY(), name);
        assertEquals(66, plan.nicheMax().getY(), name);
        assertEquals(exit, plan.exit().position(), name + " exit");
        assertEquals(yaw, plan.exit().yaw(), name + " yaw");
        assertEquals(place.group().yaw(), plan.exit().yaw(), name);
        assertEquals(-10f, plan.exit().pitch(), name);
        assertEquals(Level.OVERWORLD, plan.exit().dimension(), name);
        // The sign: on the doorway's centre line over the front layer, six blocks on from the exit, its lower edge at height 12.5.
        var outward = Vec3.atLowerCornerOf(place.facing().getUnitVec3i());
        assertEquals(exit.add(outward.scale(GateNumbers.EXIT)).add(0, 12.5, 0), plan.sign().position(), name + " sign");
        assertEquals("Fixture", plan.sign().name());
        // The doormat is the group's concrete, as the gate names blocks.
        assertEquals(place.group().concrete(), "minecraft:" + plan.doormatBlock(), name);
    }

    private static Set<Integer> range(int a, int b) {
        return IntStream.rangeClosed(Math.min(a, b), Math.max(a, b)).boxed().collect(Collectors.toSet());
    }

    @Test void dayOneAndW1R1StandWhereTheDesignWorkedThemOut() {
        // Chrome, Discord, Lunar Client, Terminal, Notepad.
        worked("N0L0", new BlockPos(-15, 64, -22), new BlockPos(-4, 75, -20), Set.of(-10, -9), Set.of(-20, -21), new Vec3(-9.0, 64, -13.5), 180);
        worked("N0R0", new BlockPos(4, 64, -22), new BlockPos(15, 75, -20), Set.of(9, 10), Set.of(-20, -21), new Vec3(10.0, 64, -13.5), 180);
        worked("E0L0", new BlockPos(20, 64, -15), new BlockPos(22, 75, -4), Set.of(20, 21), Set.of(-10, -9), new Vec3(14.5, 64, -9.0), -90);
        worked("S0L0", new BlockPos(4, 64, 20), new BlockPos(15, 75, 22), Set.of(9, 10), Set.of(20, 21), new Vec3(10.0, 64, 14.5), 0);
        worked("S0R0", new BlockPos(-15, 64, 20), new BlockPos(-4, 75, 22), Set.of(-10, -9), Set.of(20, 21), new Vec3(-9.0, 64, 14.5), 0);
        worked("W1R1", new BlockPos(-36, 64, -29), new BlockPos(-34, 75, -18), Set.of(-34, -35), Set.of(-23, -24), new Vec3(-27.5, 64, -23.0), 90);

        // The rest of HUB.md 3.2 on N0L0: its origin, the light blocks and the doormat.
        var chrome = plan(place("N0L0"));
        assertEquals(new BlockPos(-15, 64, -20), chrome.origin());
        assertEquals(Direction.NORTH, chrome.outward());
        assertEquals(new Vec3(-9.0, 76.5, -19.5), chrome.sign().position());
        assertEquals(List.of(new BlockPos(-13, 70, -19), new BlockPos(-6, 70, -19)), chrome.lights());
        assertEquals(Set.of(new BlockPos(-10, 63, -18), new BlockPos(-9, 63, -18), new BlockPos(-10, 63, -19), new BlockPos(-9, 63, -19),
                new BlockPos(-10, 63, -20), new BlockPos(-9, 63, -20), new BlockPos(-10, 63, -21), new BlockPos(-9, 63, -21)), Set.copyOf(chrome.doormat()));
        assertEquals("light_blue_concrete", chrome.doormatBlock());
        assertEquals("yellow_concrete", plan(place("S0R0")).doormatBlock());
        // Another home block moves the whole town with it.
        assertEquals(new BlockPos(85, 70, -60), place("N0L0").origin(new BlockPos(100, 70, -40)));
        assertThrows(IllegalArgumentException.class, () -> place("N0L0").plan(GatePicture.plain("stone", 14), Level.OVERWORLD, HOME, "Big", null));
    }

    /**
     * Everything a gate needs for itself: the three spaces that must be air (its box, the layer in front, the way
     * in out to the exit block), the floor under it, the doormat with its ring, the walkway and the light blocks.
     */
    private static Set<BlockPos> claim(GatePlan plan) {
        var claim = new LinkedHashSet<BlockPos>(plan.space());
        claim.addAll(plan.floor());
        claim.addAll(plan.doormatSurround());
        claim.addAll(plan.walkway());
        claim.addAll(plan.lights());
        claim.add(BlockPos.containing(plan.exit().position()));
        claim.add(BlockPos.containing(plan.exit().position()).below());
        return claim;
    }

    @Test void placesNeverCollideInTheFirstSixRows() {
        var places = new ArrayList<Place>();
        for (var group : AppGroup.values()) Place.inOrder(group).takeWhile(place -> place.row() <= 5).forEach(places::add);
        assertEquals(4 * 42, places.size());

        // The pad and the four roads paved to their longest (row 5 in use), seen from above.
        record Column(int x, int z) { }
        var paved = new HashSet<Column>();
        for (int x = -HubLayout.PAD_REACH; x <= HubLayout.PAD_REACH; x++) for (int z = -HubLayout.PAD_REACH; z <= HubLayout.PAD_REACH; z++)
            paved.add(new Column(HOME.getX() + x, HOME.getZ() + z));
        for (var group : AppGroup.values()) for (int outward = HubLayout.AVENUE_START; outward <= HubLayout.avenueEnd(5); outward++)
            for (int sideways = -HubLayout.ROAD / 2; sideways <= HubLayout.ROAD / 2; sideways++) {
                var block = group.block(HOME, outward, sideways, -1);
                paved.add(new Column(block.getX(), block.getZ()));
            }

        var owner = new HashMap<BlockPos, Place>();
        var plans = new HashMap<Place, GatePlan>();
        for (var place : places) {
            var plan = plan(place);
            plans.put(place, plan);
            for (var pos : claim(plan)) {
                var other = owner.put(pos, place);
                assertNull(other, place + " and " + other + " both need " + pos.toShortString());
                assertFalse(paved.contains(new Column(pos.getX(), pos.getZ())), place + " reaches into the pad or a road at " + pos.toShortString());
            }
        }
        // A name hangs over its own gate only, and two names never sweep into each other as they turn to face him.
        double reach = (GateNumbers.SIGN_LINE_WIDTH + 2) * 0.025 * GateNumbers.SIGN_SCALE;
        for (var place : places) {
            var plan = plans.get(place);
            for (var pos : plan.signSpace()) {
                var other = owner.get(pos);
                assertTrue(other == null || other.equals(place), place + "'s name hangs into " + other + " at " + pos.toShortString());
            }
            for (var neighbour : places) if (!neighbour.equals(place)) {
                var a = plan.sign().position();
                var b = plans.get(neighbour).sign().position();
                assertTrue(Math.hypot(a.x - b.x, a.z - b.z) >= reach, place + " and " + neighbour + " names can touch");
            }
        }
        // An exit point has five clear blocks between it and the back of the row before (HUB.md 3.2).
        for (var group : AppGroup.values()) for (int row = 1; row <= 5; row++) {
            var exit = BlockPos.containing(plans.get(new Place(group, row, Place.Side.L, 0)).exit().position());
            var back = plans.get(new Place(group, row - 1, Place.Side.L, 0)).at(GateNumbers.DEPTH - 1, 0, 0);
            var outward = group.outward();
            int between = (exit.getX() - back.getX()) * outward.getStepX() + (exit.getZ() - back.getZ()) * outward.getStepZ() - 1;
            assertEquals(5, between, group + " row " + row);
        }
    }
}
