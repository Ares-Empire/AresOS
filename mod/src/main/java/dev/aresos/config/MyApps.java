package dev.aresos.config;

import java.util.Set;

/** The rules of "My apps" that need no game (docs/design/HUB.md 2.4): who is a starter, and who joins by itself. */
public final class MyApps {
    /** The image's reviewed starters. The IDs are fixed, so the schema move knows them while no helper answers. */
    public static final Set<String> STARTERS = Set.of("browser", "terminal", "notepad");

    private MyApps() { }

    public static boolean starter(String id, SystemInfo system) {
        return STARTERS.contains(id) || "image".equals(source(system));
    }

    /** Day one, when the first full program list arrives: the starters and what he installed himself. */
    public static boolean dayOne(String id, SystemInfo system) {
        String source = source(system);
        return starter(id, system) || "user".equals(source) || "flatpak-user".equals(source);
    }

    /**
     * After day one a program that newly appears joins by itself unless it came with the image or the system.
     * One whose origin is not known does not join: he can add it with a click, and an app nobody asked for in
     * the inventory is the worse mistake.
     */
    public static boolean joinsLater(SystemInfo system) {
        String source = source(system);
        return source != null && !source.equals("image") && !source.equals("system");
    }

    private static String source(SystemInfo system) { return system == null ? null : system.source(); }
}
