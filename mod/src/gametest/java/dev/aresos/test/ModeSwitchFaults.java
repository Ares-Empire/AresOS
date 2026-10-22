package dev.aresos.test;

import java.util.UUID;

/** A one-shot test failure after vanilla has already changed the game mode. */
public final class ModeSwitchFaults {
    public static UUID failAfterModeChange;
    private ModeSwitchFaults() { }
}
