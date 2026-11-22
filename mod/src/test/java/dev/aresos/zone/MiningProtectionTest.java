package dev.aresos.zone;

import net.minecraft.world.level.GameType;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class MiningProtectionTest {
    @Test void liveProtectsBothOwnedAndOrdinaryBlocks() {
        String logo = "Auto-built logo protected. Press G for Build mode.";
        String pad = "The home pad and roads are protected. Press G for Build mode.";
        assertEquals(logo, WalkInZones.miningRefusal(true, GameType.SURVIVAL, () -> logo));
        assertEquals(pad, WalkInZones.miningRefusal(true, GameType.SURVIVAL, () -> pad));
        assertEquals("The home is protected. Press G or use Build mode in the menu to change it.",
                WalkInZones.miningRefusal(true, GameType.SURVIVAL, () -> null));
    }

    @Test void buildAndVanillaNeverConsultDesktopOwnership() {
        assertNull(WalkInZones.miningRefusal(true, GameType.CREATIVE, MiningProtectionTest::unexpectedLookup));
        assertNull(WalkInZones.miningRefusal(false, GameType.SURVIVAL, MiningProtectionTest::unexpectedLookup));
        assertNull(WalkInZones.miningRefusal(false, GameType.CREATIVE, MiningProtectionTest::unexpectedLookup));
    }

    private static String unexpectedLookup() { throw new AssertionError("Looked up desktop ownership"); }
}
