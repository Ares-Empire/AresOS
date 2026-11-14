package dev.aresos.hub;

import dev.aresos.zone.AppZone;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.Level;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/** The seal on the town's records (review fixes 1, point 1), on world folders of its own. */
class TownSealTest {
    private static final long SEED = 4242L;
    private static final GlobalPos HOME = GlobalPos.of(Level.OVERWORLD, new BlockPos(0, 64, 0));

    @BeforeAll static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    private static HubData.TownFile town(String... apps) {
        var logos = new java.util.ArrayList<HubData.Logo>();
        int x = 0;
        for (var app : apps) {
            var at = new BlockPos(x += 20, 64, -20);
            logos.add(new HubData.Logo(app, "N0R0", "ab".repeat(32), 1, app, Optional.empty(), "zone-" + app,
                    new AppZone.Gate(List.of(new AppZone.Placed(at, "minecraft:red_concrete")), List.of(), Optional.of(UUID.randomUUID()))));
        }
        return new HubData.TownFile(HOME, logos);
    }

    /** A level.dat as the game writes it: the level data under "Data", with its LastPlayed. */
    private static void levelDat(Path world, long lastPlayed) throws IOException {
        var data = new CompoundTag();
        data.putLong("LastPlayed", lastPlayed);
        data.putString("LevelName", "Test");
        var root = new CompoundTag();
        root.put("Data", data);
        NbtIo.writeCompressed(root, world.resolve("level.dat"));
    }

    @Test void aSealWrittenWithLevelDatHoldsUntilLevelDatIsWrittenWithoutIt(@TempDir Path world) throws IOException {
        var town = town("chrome", "discord");
        assertFalse(TownSeal.sealed(world, SEED, town), "no level.dat, no seal");
        levelDat(world, 1_000L);
        assertFalse(TownSeal.sealed(world, SEED, town), "no seal");
        TownSeal.write(world, new TownSeal.Seal(1_000L, SEED, TownSeal.fingerprint(town)));
        assertEquals(OptionalLong.of(1_000L), TownSeal.lastPlayed(world));
        assertTrue(TownSeal.sealed(world, SEED, town), "saved together");
        assertFalse(TownSeal.sealed(world, SEED + 1, town), "another world's seed");

        // The records read back from town.dat give the same fingerprint as the ones the seal was written for.
        var saved = HubData.TownFile.CODEC.encodeStart(NbtOps.INSTANCE, town).getOrThrow();
        assertTrue(TownSeal.sealed(world, SEED, HubData.TownFile.CODEC.parse(NbtOps.INSTANCE, saved).getOrThrow()), "the same records read again");

        // A town.dat restored from a backup or copied from another world: other records, the same home.
        assertFalse(TownSeal.sealed(world, SEED, town("chrome")), "a town.dat of fewer logos");
        assertFalse(TownSeal.sealed(world, SEED, town("chrome", "discord", "mail")), "a town.dat of more logos");

        // An older mod or plain Minecraft saved the world since (or the game stopped between the two writes):
        // level.dat has another LastPlayed and no seal was written for it.
        levelDat(world, 2_000L);
        assertFalse(TownSeal.sealed(world, SEED, town), "level.dat written without the seal");
        assertEquals(Optional.empty(), TownSeal.holding(world));
    }

    /** Review fixes 2, point 1: when the seal is checked, and what an empty town file is worth. */
    @Test void theTownTrustsAFileOnlyWhileItsSealOrTheLackOfOneShowsThatNothingElseStands(@TempDir Path world) throws IOException {
        var empty = new HubData.TownFile(HOME, List.of());
        // Neither a seal file nor logos: a town that never had logos.
        assertTrue(TownSeal.trusted(world, SEED, empty), "no seal, no logos");
        assertFalse(TownSeal.trusted(world, SEED, town("chrome")), "logos without a seal");

        levelDat(world, 1_000L);
        var both = town("chrome", "discord");
        TownSeal.write(world, new TownSeal.Seal(1_000L, SEED, TownSeal.fingerprint(both)));
        assertTrue(TownSeal.trusted(world, SEED, both), "the seal holds");
        // A file restored on its own that leaves out a logo the seal names, or holds none at all: the logo may stand.
        assertFalse(TownSeal.trusted(world, SEED, town("chrome")), "a subset restored");
        assertFalse(TownSeal.trusted(world, SEED, empty), "an empty file restored while the seal names logos");
        levelDat(world, 2_000L);
        assertFalse(TownSeal.trusted(world, SEED, empty), "an empty file, and a seal of logos that no longer holds");

        // The seal no longer holds (an older mod saved since), but it and the file both show an empty town of this home.
        TownSeal.write(world, new TownSeal.Seal(1_000L, SEED, TownSeal.fingerprint(empty)));
        assertTrue(TownSeal.trusted(world, SEED, empty), "both show a town without logos");
        assertFalse(TownSeal.trusted(world, SEED, town("chrome")), "an empty seal and a file with logos");
        var elsewhere = new HubData.TownFile(GlobalPos.of(Level.OVERWORLD, new BlockPos(64, 64, 0)), List.of());
        TownSeal.write(world, new TownSeal.Seal(1_000L, SEED, TownSeal.fingerprint(elsewhere)));
        assertFalse(TownSeal.trusted(world, SEED, empty), "the seal of an empty town of another home");

        // A seal file that cannot be read is a seal file: checked, and it does not hold.
        java.nio.file.Files.write(TownSeal.file(world), new byte[] {1, 2, 3});
        assertFalse(TownSeal.trusted(world, SEED, empty), "an unreadable seal");
    }

    @Test void aSealThatHoldsIsCarriedToTheNextLevelDatAndABrokenOneIsNot(@TempDir Path world) throws IOException {
        var town = town("chrome");
        levelDat(world, 1_000L);
        var seal = new TownSeal.Seal(1_000L, SEED, TownSeal.fingerprint(town));
        TownSeal.write(world, seal);
        assertEquals(Optional.of(seal), TownSeal.holding(world), "it holds before the game writes level.dat as the world opens");
        assertEquals(Optional.of(seal), TownSeal.read(world));

        // A seal written for another LastPlayed does not hold, and so is never carried over.
        TownSeal.write(world, new TownSeal.Seal(999L, SEED, TownSeal.fingerprint(town)));
        assertEquals(Optional.empty(), TownSeal.holding(world));
        assertTrue(TownSeal.read(world).isPresent());
    }
}
