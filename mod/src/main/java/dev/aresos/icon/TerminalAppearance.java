package dev.aresos.icon;

import dev.aresos.config.AppDefinition;

/** Foot's light outline is part of its icon, so the built-in Terminal has its own look in the home. */
public final class TerminalAppearance {
    public static final String ITEM = "minecraft:black_concrete";
    public static final String LEGACY_ITEM = "minecraft:command_block";

    private TerminalAppearance() { }

    public static boolean usesBuiltInPicture(AppDefinition app) {
        return app.id().equals("terminal") && app.type().equals("helper") && app.icon() == null;
    }
}
