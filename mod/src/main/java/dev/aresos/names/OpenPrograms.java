package dev.aresos.names;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import java.util.*;

/**
 * /open resolution (HUB.md 4.4), including programs outside My apps: by a saved name or the name the rules would
 * give, by the squeezed full name, or by the unique start of either. Exact names take precedence over prefixes.
 * An app ID is no key here; clicks use {@code /aresos app open <id>} instead.
 */
public final class OpenPrograms {
    private OpenPrograms() { }

    public static List<String> keys(AppDefinition app, List<AppDefinition> apps, Set<String> commands) {
        var held = new HashSet<String>();
        for (var other : apps) if (!other.id().equals(app.id())) held.addAll(other.names());
        var keys = new LinkedHashSet<>(app.names());
        keys.add(NameRules.main(NameRules.of(app), held, commands));
        keys.add(NameRules.squeeze(app.name()));
        return keys.stream().filter(key -> !key.isEmpty()).toList();
    }

    public static List<AppDefinition> find(List<AppDefinition> apps, String query, Set<String> commands) {
        return find(apps, query, commands, app -> true);
    }

    /**
     * The same lookup with the same keys (worked out against all of {@code apps}), among the apps that pass
     * {@code among} only: {@code /go} looks among his apps, so a program that is not his never hides one that is.
     */
    public static List<AppDefinition> find(List<AppDefinition> apps, String query, Set<String> commands,
                                           java.util.function.Predicate<AppDefinition> among) {
        String squeezed = NameRules.squeeze(query);
        if (squeezed.isEmpty()) return List.of();
        var candidates = apps.stream().filter(among).toList();
        var exact = candidates.stream().filter(app -> keys(app, apps, commands).contains(squeezed)).sorted(AppSearch.BY_NAME).toList();
        if (!exact.isEmpty()) return exact;
        return candidates.stream().filter(app -> keys(app, apps, commands).stream().anyMatch(key -> key.startsWith(squeezed)))
                .sorted(AppSearch.BY_NAME).toList();
    }
}
