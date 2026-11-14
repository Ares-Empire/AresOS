package dev.aresos.hub;

import dev.aresos.zone.AppZone;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.Level;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/** The town's record (HUB.md 3.5): hub.dat as package 32 made it, the standing logos in town.dat, and files written before the town. */
class HubDataTest {
    private static final BlockPos HOME = new BlockPos(0, 64, 0);

    @BeforeAll static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    private static HubData.Fixed pad() {
        return new HubData.Fixed(List.of(new HubData.Placed(HOME.below(), "minecraft:gold_block")), List.of(UUID.randomUUID()));
    }

    private static HubData.Logo logo(String app, String place, BlockPos at, String zone) {
        var gate = new AppZone.Gate(List.of(new AppZone.Placed(at, "minecraft:red_concrete"), new AppZone.Placed(at.above(), "minecraft:light"),
                new AppZone.Placed(at.below(), "minecraft:yellow_concrete")),
                List.of(new AppZone.Placed(at.below(), "minecraft:grass_block")), Optional.of(UUID.randomUUID()), List.of(at.below().east()));
        return new HubData.Logo(app, place, "ab".repeat(32), 1, app.toUpperCase(), Optional.of(app), zone, gate);
    }

    private static HubData hub(List<HubData.Logo> logos) {
        return new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(Level.OVERWORLD, HOME), pad(), logos);
    }

    @Test void aFileWrittenBeforeTheTownLoadsWithoutLogos() {
        var old = (CompoundTag)HubData.CODEC.encodeStart(NbtOps.INSTANCE, hub(List.of())).getOrThrow();
        old.remove("logos");
        var loaded = HubData.CODEC.parse(NbtOps.INSTANCE, old).getOrThrow();
        assertEquals(List.of(), loaded.logos());
        assertEquals(pad().blocks(), loaded.fixed().blocks());
        assertEquals(Map.of(HOME.below(), "minecraft:gold_block"), loaded.blocks(Level.OVERWORLD));
    }

    @Test void standingLogosRoundTripThroughTownDatWithEverythingPlacedForThem() {
        var discord = logo("discord", "N0R0", new BlockPos(9, 64, -20), "zone-discord");
        var lunar = new HubData.Logo("lunar", "E0L0", "cd".repeat(32), 1, "Lunar Client", Optional.empty(), "zone-lunar",
                new AppZone.Gate(List.of(new AppZone.Placed(new BlockPos(20, 64, -9), "minecraft:black_concrete")), List.of(), Optional.empty()));
        var file = new HubData.TownFile(GlobalPos.of(Level.OVERWORLD, HOME), List.of(discord, lunar));
        var saved = (CompoundTag)HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, file).getOrThrow();
        var loaded = HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, saved).getOrThrow();
        assertEquals(List.of(discord, lunar), loaded.logos);
        assertEquals(saved, HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, loaded).getOrThrow(), "saved again it is the same file");
        var first = saved.getListOrEmpty("logos").getCompoundOrEmpty(0);
        for (String field : List.of("app", "place", "picture", "converter", "name", "short_name", "zone", "gate"))
            assertTrue(first.contains(field), "a logo saves " + field);
        assertFalse(saved.getListOrEmpty("logos").getCompoundOrEmpty(1).contains("short_name"), "no short name, no field");
        assertTrue(saved.contains("home"), "town.dat names the home it belongs to");
    }

    /**
     * The orchestrator's decision 1: a mod of packages 32 to 35 rewrites hub.dat in its own shape and drops what it
     * does not know. hub.dat holds nothing of the town, so the hub read back from such a file, joined to town.dat,
     * knows every logo and every block of it.
     */
    @Test void hubDatKeepsPackage32sShapeSoAnOlderModsRewriteLosesNothingOfTheTown() {
        var discord = logo("discord", "N0R0", new BlockPos(9, 64, -20), "zone-discord");
        var hub = hub(List.of(discord));
        var hubDat = (CompoundTag)HubData.CODEC.encodeStart(NbtOps.INSTANCE, hub).getOrThrow();
        assertEquals(Set.of("look", "numbers", "home", "fixed"), hubDat.keySet(), "hub.dat is package 32's shape");
        var townDat = HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, new HubData.TownFile(hub.home(), hub.logos())).getOrThrow();

        // The older mod reads hub.dat and writes it again (a pad block changed): only the four fields it knows.
        var rewritten = HubData.CODEC.parse(NbtOps.INSTANCE, hubDat).getOrThrow();
        var reloaded = HubData.CODEC.parse(NbtOps.INSTANCE, HubData.CODEC.encodeStart(NbtOps.INSTANCE, rewritten).getOrThrow()).getOrThrow();
        reloaded.adopt(HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, townDat).getOrThrow());
        assertEquals(List.of(discord), reloaded.logos());
        assertEquals(hub.blocks(Level.OVERWORLD), reloaded.blocks(Level.OVERWORLD), "every block of the town is still the mod's");
        assertEquals(Optional.of(discord), reloaded.logoOfZone("zone-discord"));
        assertEquals(hub.signs(), reloaded.signs());

        // A town file of another home is never read into this hub.
        var elsewhere = new HubData.TownFile(GlobalPos.of(Level.OVERWORLD, HOME.east(5000)), List.of(discord));
        assertThrows(IllegalArgumentException.class, () -> hub(List.of()).adopt(elsewhere));
    }

    /** Review fixes 1, point 3: the game takes what it could read of a saved file; the town's file is read whole or not at all. */
    @Test void aTownFileWithALogoItCannotReadIsNotReadInPart() {
        var file = new HubData.TownFile(GlobalPos.of(Level.OVERWORLD, HOME), List.of(logo("discord", "N0R0", new BlockPos(9, 64, -20), "zone-discord"),
                logo("chrome", "N0L0", new BlockPos(-10, 64, -20), "zone-chrome")));
        var saved = (CompoundTag)HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, file).getOrThrow();
        assertTrue(HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, saved).isSuccess());
        var logos = saved.getListOrEmpty("logos");
        logos.getCompoundOrEmpty(1).remove("zone");
        saved.put("logos", logos);
        var read = HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, saved);
        assertTrue(read.isError(), "a logo without its zone");
        assertEquals(Optional.empty(), read.resultOrPartial(error -> { }), "nothing of it is read, as the game reads saved data");
    }

    private static HubData.Logo as(HubData.Logo logo, String app, String place, String zone, AppZone.Gate gate) {
        return new HubData.Logo(app, place, logo.picture(), logo.converter(), logo.name(), logo.shortName(), zone, gate);
    }

    /**
     * Review fixes 1, point 4: a town file read from the world goes through the checks of add, and one overlap
     * refuses all of it: two logos of one app, in one place, on one block, with one sign or one zone, or a logo
     * whose blocks lie outside the place it names. The files are decoded as the game reads town.dat.
     */
    @Test void aTownFileWithOverlappingRecordsIsRefusedWholeAsAddRefusesTheLogo() {
        var discord = logo("discord", "N0R0", new BlockPos(9, 64, -20), "zone-discord");
        var chrome = logo("chrome", "N0L0", new BlockPos(-10, 64, -20), "zone-chrome");
        var gate = chrome.gate();
        var shared = new java.util.ArrayList<>(gate.placed());
        shared.add(discord.gate().placed().getFirst());
        var overlaps = new java.util.LinkedHashMap<String, HubData.Logo>();
        overlaps.put("two logos are recorded for discord", as(chrome, "discord", "N0L0", "zone-chrome", gate));
        overlaps.put("two logos are recorded at N0R0", as(chrome, "chrome", "N0R0", "zone-chrome", gate));
        overlaps.put("two records hold the block at 9, 64, -20", as(chrome, "chrome", "N0L0", "zone-chrome",
                new AppZone.Gate(shared, gate.ground(), gate.sign(), gate.grass())));
        overlaps.put("two records name the sign", as(chrome, "chrome", "N0L0", "zone-chrome",
                new AppZone.Gate(gate.placed(), gate.ground(), discord.gate().sign(), gate.grass())));
        overlaps.put("two logos name the zone zone-discord", as(chrome, "chrome", "N0L0", "zone-discord", gate));
        overlaps.put("outside its place N1L0", as(chrome, "chrome", "N1L0", "zone-chrome", gate));
        overlaps.put("stands in no place of the town: north", as(chrome, "chrome", "north", "zone-chrome", gate));
        var home = GlobalPos.of(Level.OVERWORLD, HOME);
        assertDoesNotThrow(() -> hub(List.of()).adopt(new HubData.TownFile(home, List.of(discord, chrome))), "the two as they are");
        for (var overlap : overlaps.entrySet()) {
            var saved = HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, new HubData.TownFile(home, List.of(discord, overlap.getValue()))).getOrThrow();
            var read = HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, saved).getOrThrow();
            var hub = hub(List.of());
            var refused = assertThrows(IllegalArgumentException.class, () -> hub.adopt(read), overlap.getKey());
            assertTrue(refused.getMessage().contains(overlap.getKey()), overlap.getKey() + ": " + refused.getMessage());
            assertEquals(List.of(), hub.logos(), "nothing of a refused file is read in");
            assertEquals(Map.of(HOME.below(), "minecraft:gold_block"), hub.blocks(Level.OVERWORLD));

            var standing = hub(List.of(discord));
            var added = assertThrows(IllegalArgumentException.class, () -> standing.add(overlap.getValue()), overlap.getKey());
            assertEquals(refused.getMessage(), added.getMessage(), "add refuses it for the same reason");
            assertEquals(List.of(discord), standing.logos());
        }
        // A logo recording a block of the pad, or a group name's ID as its sign.
        var pad = new java.util.ArrayList<>(gate.placed());
        pad.add(new AppZone.Placed(HOME.below(), "minecraft:gold_block"));
        assertThrows(IllegalArgumentException.class, () -> hub(List.of()).adopt(new HubData.TownFile(home,
                List.of(as(chrome, "chrome", "N0L0", "zone-chrome", new AppZone.Gate(pad, gate.ground(), gate.sign(), gate.grass()))))));
    }

    @Test void theRecordKnowsEveryLogoByAppZoneBlockAndSign() {
        var discord = logo("discord", "N0R0", new BlockPos(9, 64, -20), "zone-discord");
        var hub = hub(List.of(discord));
        assertEquals(Optional.of(discord), hub.logo("discord"));
        assertEquals(Optional.of(discord), hub.logoOfZone("zone-discord"));
        assertEquals(Optional.empty(), hub.logoOfZone("zone-of-his-own"));
        assertEquals(Set.of(discord.gate().sign().orElseThrow()), hub.signs());
        var blocks = hub.blocks(Level.OVERWORLD);
        assertEquals(4, blocks.size(), "the pad's block and the logo's three");
        assertEquals("minecraft:light", blocks.get(new BlockPos(9, 65, -20)));
        assertFalse(blocks.containsKey(new BlockPos(10, 63, -20)), "the grass under a logo is not the mod's block");
        assertEquals(Map.of(), hub.blocks(Level.NETHER));

        // One logo an app, and no block in two records; a refusal changes nothing.
        assertThrows(IllegalArgumentException.class, () -> hub.add(logo("discord", "N1L0", new BlockPos(30, 64, -40), "zone-2")));
        assertThrows(IllegalArgumentException.class, () -> hub.add(logo("chrome", "N0L0", new BlockPos(9, 64, -20), "zone-3")));
        assertThrows(IllegalArgumentException.class, () -> hub.add(logo("chrome", "N0L0", HOME, "zone-4")),
                "a block of the pad");
        assertEquals(List.of(discord), hub.logos());
        assertFalse(hub.isDirty() || hub.townChanged());

        var chrome = logo("chrome", "N0L0", new BlockPos(-10, 64, -20), "zone-chrome");
        hub.add(chrome);
        assertTrue(hub.townChanged(), "town.dat is written for a new logo");
        assertFalse(hub.isDirty(), "hub.dat is not: it holds nothing of the town");
        assertEquals(List.of(discord, chrome), hub.logos());
        assertEquals(7, hub.blocks(Level.OVERWORLD).size());
        assertEquals(Optional.of(discord), hub.remove("discord"));
        assertEquals(Optional.empty(), hub.remove("discord"));
        assertEquals(List.of(chrome), hub.logos());
        assertEquals(4, hub.blocks(Level.OVERWORLD).size());
        assertFalse(hub.blocks(Level.OVERWORLD).containsKey(new BlockPos(9, 64, -20)));
    }
}
