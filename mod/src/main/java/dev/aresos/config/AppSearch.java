package dev.aresos.config;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * The search box of the Apps screen (docs/design/HUB.md 2.4): it looks in a program's name and in what the system
 * said its generic name and keywords are, so "mail" or "pdf" finds the right program.
 */
public final class AppSearch {
    /** By name as he reads it; the ID settles two programs with the same name. */
    public static final Comparator<AppDefinition> BY_NAME = Comparator
            .comparing((AppDefinition app) -> app.name().toLowerCase(Locale.ROOT)).thenComparing(AppDefinition::id);

    private AppSearch() { }

    /** The programs the query finds, by name. An empty query finds every program. */
    public static List<AppDefinition> find(List<AppDefinition> apps, String query) {
        return apps.stream().filter(app -> matches(app, query)).sorted(BY_NAME).toList();
    }

    /** Every word of the query must be part of the name, the generic name or a keyword; upper and lower case are one. */
    public static boolean matches(AppDefinition app, String query) {
        String text = text(app);
        for (String word : query.toLowerCase(Locale.ROOT).split("\\s+"))
            if (!word.isEmpty() && !text.contains(word)) return false;
        return true;
    }

    private static String text(AppDefinition app) {
        var text = new StringBuilder(app.name());
        for (String name : app.names()) text.append('\n').append(name);
        var system = app.system();
        if (system != null) {
            if (system.genericName() != null) text.append('\n').append(system.genericName());
            // One line each, so a word never matches across two fields.
            if (system.keywords() != null) for (String keyword : system.keywords()) text.append('\n').append(keyword);
        }
        return text.toString().toLowerCase(Locale.ROOT);
    }
}
