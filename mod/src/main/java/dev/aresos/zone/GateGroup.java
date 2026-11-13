package dev.aresos.zone;

import java.util.Optional;

/**
 * The four groups of HUB.md 2.2 with their concretes, for the doormat and for the plain front of an app without
 * an icon. This is the gate's own copy of the four colours; the table that sorts programs into groups lives with
 * the flat home.
 */
public enum GateGroup {
    INTERNET("light_blue_concrete"), GAMES("red_concrete"), WORK_AND_MEDIA("purple_concrete"),
    SYSTEM_AND_TOOLS("yellow_concrete");

    /** For an app whose group is not known. */
    public static final String UNKNOWN_CONCRETE = "light_gray_concrete";
    private final String concrete;

    GateGroup(String concrete) { this.concrete = concrete; }

    public String concrete() { return concrete; }

    /**
     * The three starter apps have fixed groups. Every other app needs the program's categories, which the mod is
     * not told yet.
     */
    public static Optional<GateGroup> ofStarter(String app) {
        return switch (app) {
            case "browser" -> Optional.of(INTERNET);
            case "terminal", "notepad" -> Optional.of(SYSTEM_AND_TOOLS);
            default -> Optional.empty();
        };
    }

    public static String concreteFor(String app) {
        return ofStarter(app).map(GateGroup::concrete).orElse(UNKNOWN_CONCRETE);
    }
}
