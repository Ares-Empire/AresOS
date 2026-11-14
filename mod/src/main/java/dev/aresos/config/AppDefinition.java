package dev.aresos.config;

import java.util.List;

/**
 * One app of config/aresos/apps.json. {@code mine} says it is one of "My apps" (it has an item in the inventory);
 * {@code system} is what the system last said about it, or null when it never said anything. {@code absent}: the
 * latest complete list from the AresOS app helper did not name it, so it cannot be opened now; it keeps everything
 * else, its names and its place in My apps included, for its return.
 *
 * <p>{@code place} and {@code group} say where its logo stands in the flat home (HUB.md 3.5), as saved: the place's
 * name ({@code "N0R0"}, kept while the app is away so it can come back) and the group's key, only when he moved it to
 * another group by hand. Null when there is none. Text that names no place or group is kept but means none
 * ({@code hub.Place.parse}, {@code AppGroup.of}), so a file from a later mod is never refused for them.
 */
public record AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                            String type, String url, String icon, WindowsLaunchIdentity launchIdentity,
                            boolean mine, SystemInfo system, List<String> names, boolean absent,
                            String place, String group) {
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                         String type, String url, String icon, WindowsLaunchIdentity launchIdentity,
                         boolean mine, SystemInfo system, List<String> names, boolean absent) {
        this(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, names, absent, null, null);
    }
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                         String type, String url, String icon, WindowsLaunchIdentity launchIdentity,
                         boolean mine, SystemInfo system, List<String> names) {
        this(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, names, false);
    }
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                         String type, String url, String icon, WindowsLaunchIdentity launchIdentity,
                         boolean mine, SystemInfo system) {
        this(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, List.of());
    }
    /** Without the My-apps fields: his if it is pinned. */
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                         String type, String url, String icon, WindowsLaunchIdentity launchIdentity) {
        this(id, name, command, look, pinned, type, url, icon, launchIdentity, pinned, null);
    }
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                         String type, String url, String icon) {
        this(id, name, command, look, pinned, type, url, icon, null);
    }
    public AppDefinition(String id, String name, List<String> command, String look, boolean pinned) {
        this(id, name, command, look, pinned, "command", null, null);
    }

    public AppDefinition {
        if (id == null || !id.matches("[a-z0-9_-]+") || name == null || name.isBlank()
                || command == null
                || command.stream().anyMatch(part -> part == null || part.isEmpty() || part.indexOf('\0') >= 0)
                || look == null || !look.matches("minecraft:[a-z0-9_./-]+")
                || !("command".equals(type) || "url".equals(type) || "helper".equals(type))
                || ("command".equals(type) && command.isEmpty())
                || ("url".equals(type) && !validUrl(url))) {
            throw new IllegalArgumentException("Invalid app definition");
        }
        command = List.copyOf(command);
        names = names == null ? List.of() : List.copyOf(names);
        if (names.stream().anyMatch(nameValue -> !dev.aresos.names.NameRules.valid(nameValue))
                || new java.util.HashSet<>(names).size() != names.size())
            throw new IllegalArgumentException("Invalid or duplicate short name");
        // The hotbar holds his apps: a pinned app is always one of them.
        mine = mine || pinned;
    }

    private static boolean validUrl(String url) {
        try {
            var uri = java.net.URI.create(url);
            return ("https".equalsIgnoreCase(uri.getScheme()) || "http".equalsIgnoreCase(uri.getScheme()))
                    && uri.getHost() != null && uri.getUserInfo() == null;
        } catch (RuntimeException error) { return false; }
    }

    /** Pinning makes an app his; unpinning changes nothing else. */
    public AppDefinition withPinned(boolean value) {
        return new AppDefinition(id, name, command, look, value, type, url, icon, launchIdentity, mine || value, system, names, absent, place, group);
    }

    /** Taking an app out of My apps also unpins it: its item leaves the hotbar. */
    public AppDefinition withMine(boolean value) {
        return new AppDefinition(id, name, command, look, pinned && value, type, url, icon, launchIdentity, value, system, names, absent, place, group);
    }

    public AppDefinition withNames(List<String> value) {
        return new AppDefinition(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, value, absent, place, group);
    }

    public AppDefinition withSystem(SystemInfo value) {
        return new AppDefinition(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, value, names, absent, place, group);
    }

    /** Where its logo stands, as saved: a place's name and a group's key, each null for none. */
    public AppDefinition withSpot(String placeValue, String groupValue) {
        return new AppDefinition(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, names, absent,
                placeValue, groupValue);
    }

    public AppDefinition withAbsent(boolean value) {
        return new AppDefinition(id, name, command, look, pinned, type, url, icon, launchIdentity, mine, system, names, value, place, group);
    }
}
