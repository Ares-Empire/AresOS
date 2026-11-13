package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import java.util.List;
import java.util.Set;

/**
 * The four groups of the hub (docs/design/HUB.md 2.2), worked out from a program's categories, and the vanilla
 * item an app of each group looks like while it has no picture of its own. This is the one table to change.
 */
public enum AppGroup {
    INTERNET("Internet", "minecraft:ender_pearl"),
    GAMES("Games", "minecraft:diamond_sword"),
    WORK_MEDIA("Work & Media", "minecraft:painting"),
    SYSTEM_TOOLS("System & Tools", "minecraft:iron_pickaxe");

    private static final Set<String> WORK_MEDIA_CATEGORIES = Set.of("Office", "Development", "Education", "Science",
            "Graphics", "AudioVideo", "Audio", "Video");
    private final String title;
    private final String look;

    AppGroup(String title, String look) {
        this.title = title;
        this.look = look;
    }

    public String title() { return title; }
    /** A vanilla item ID, as apps.json's {@code look}. */
    public String look() { return look; }

    /**
     * The first rule that fits wins: Game, then Network, then the Work and Media list, then everything else.
     * So Steam (Network, FileTransfer, Game) is a game. The three starters are fixed.
     */
    public static AppGroup of(String id, List<String> categories) {
        if (id.equals("browser")) return INTERNET;
        if (id.equals("terminal") || id.equals("notepad")) return SYSTEM_TOOLS;
        if (categories != null) {
            if (categories.contains("Game")) return GAMES;
            if (categories.contains("Network")) return INTERNET;
            if (categories.stream().anyMatch(WORK_MEDIA_CATEGORIES::contains)) return WORK_MEDIA;
        }
        return SYSTEM_TOOLS;
    }

    public static AppGroup of(AppDefinition app) {
        return of(app.id(), app.system() == null ? null : app.system().categories());
    }
}
