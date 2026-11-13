package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * The four groups of the hub (docs/design/HUB.md 2.2 and 3.2): which group an app belongs to, and everything about
 * a group: its title, the vanilla item an app of it looks like while it has no picture of its own, its avenue in
 * the flat home, its concrete and the colour its name is written in. This is the one table to change; the gate,
 * the pad and the places all read it from here.
 */
public enum AppGroup {
    // Text colours are the concretes' dye colours, except red and purple: those two dyes are too dark to read on
    // the dark plate (2 to 1), so their names use a lighter tint of the same hue (above 4 to 1).
    INTERNET("Internet", "minecraft:ender_pearl", Direction.NORTH, "minecraft:light_blue_concrete", 0x3AB3DA),
    GAMES("Games", "minecraft:diamond_sword", Direction.EAST, "minecraft:red_concrete", 0xFF6257),
    WORK_MEDIA("Work & Media", "minecraft:painting", Direction.WEST, "minecraft:purple_concrete", 0xC774F2),
    SYSTEM_TOOLS("System & Tools", "minecraft:iron_pickaxe", Direction.SOUTH, "minecraft:yellow_concrete", 0xFED83D);

    private static final Set<String> WORK_MEDIA_CATEGORIES = Set.of("Office", "Development", "Education", "Science",
            "Graphics", "AudioVideo", "Audio", "Video");
    private final String title;
    private final String look;
    private final Direction outward;
    private final String concrete;
    private final int colour;

    AppGroup(String title, String look, Direction outward, String concrete, int colour) {
        this.title = title;
        this.look = look;
        this.outward = outward;
        this.concrete = concrete;
        this.colour = colour;
    }

    /** The group's name as he reads it, for example "System & Tools". */
    public String title() { return title; }
    /** A vanilla item ID, as apps.json's {@code look}. */
    public String look() { return look; }
    /** The block ID of the group's concrete: the avenue's centre line, the doormats and a plain front. */
    public String concrete() { return concrete; }
    /** The group's colour for text, as RGB. */
    public int colour() { return colour; }

    /** The direction of the group's avenue, seen from home. */
    public Direction outward() { return outward; }
    /** His right as he looks along the avenue from home. A gate's columns count this way too. */
    public Direction right() { return outward.getClockWise(); }
    /** The yaw that looks along the avenue, from -180 to 180 as HUB.md 3.2 lists it. */
    public float yaw() {
        float yaw = outward.toYRot();
        return yaw > 180 ? yaw - 360 : yaw;
    }
    /** The letter that starts the names of the group's places: N, E, S or W, after its avenue's direction. */
    public char letter() { return Character.toUpperCase(outward.getName().charAt(0)); }

    /** "Outward a, sideways b, height h" (HUB.md 3.2): the block {@code home + outward x a + right x b}, h above home's y. */
    public BlockPos block(BlockPos home, int outward, int sideways, int height) {
        var right = right();
        return home.offset(this.outward.getStepX() * outward + right.getStepX() * sideways, height,
                this.outward.getStepZ() * outward + right.getStepZ() * sideways);
    }

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

    /** The group whose places start with this letter (N, E, S or W, upper case only). */
    public static Optional<AppGroup> ofLetter(char letter) {
        return Arrays.stream(values()).filter(group -> group.letter() == letter).findFirst();
    }

    /** The four groups clockwise from the avenue straight ahead: north, east, south, west. */
    public static List<AppGroup> clockwise() {
        return Direction.Plane.HORIZONTAL.stream()
                .map(direction -> Arrays.stream(values()).filter(group -> group.outward == direction).findFirst().orElseThrow())
                .toList();
    }
}
