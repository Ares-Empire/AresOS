package dev.aresos.names;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import java.util.*;

/** /open resolution, including programs outside My apps. Exact names take precedence over prefixes. */
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
        // Stable IDs make every clickable choice unambiguous even for two identical displayed names.
        var byId = apps.stream().filter(app -> app.id().equals(query)).toList();
        if (!byId.isEmpty()) return byId;
        String squeezed = NameRules.squeeze(query);
        if (squeezed.isEmpty()) return List.of();
        var exact = apps.stream().filter(app -> keys(app, apps, commands).contains(squeezed)).sorted(AppSearch.BY_NAME).toList();
        if (!exact.isEmpty()) return exact;
        return apps.stream().filter(app -> keys(app, apps, commands).stream().anyMatch(key -> key.startsWith(squeezed)))
                .sorted(AppSearch.BY_NAME).toList();
    }
}
