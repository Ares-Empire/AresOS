package dev.aresos.config;

import java.util.List;
import java.util.Set;

/**
 * What the system said about a program: the optional entry fields of aresos-shell/1.1 (docs/design/HUB.md 3.8).
 * A null field means "not known". It is saved with the app, so groups and names can be worked out while the
 * helper is down.
 */
public record SystemInfo(String source, String icon, List<String> categories, String genericName,
                         List<String> keywords, String desktopId, String execName, Boolean terminal) {
    /** Where a program came from; anything else on the wire is "not known". */
    public static final Set<String> SOURCES = Set.of("image", "system", "flatpak-system", "flatpak-user", "user");
    public static final SystemInfo UNKNOWN = new SystemInfo(null, null, null, null, null, null, null, null);

    public SystemInfo {
        if (source != null && !SOURCES.contains(source)) throw new IllegalArgumentException("Unknown app source");
        if (categories != null) categories = List.copyOf(categories);
        if (keywords != null) keywords = List.copyOf(keywords);
    }

    /** True when the system said nothing at all. */
    public boolean isEmpty() { return equals(UNKNOWN); }
}
