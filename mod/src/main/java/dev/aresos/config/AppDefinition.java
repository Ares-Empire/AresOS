package dev.aresos.config;

import java.util.List;

public record AppDefinition(String id, String name, List<String> command, String look, boolean pinned,
                            String type, String url, String icon, WindowsLaunchIdentity launchIdentity) {
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
    }

    private static boolean validUrl(String url) {
        try {
            var uri = java.net.URI.create(url);
            return ("https".equalsIgnoreCase(uri.getScheme()) || "http".equalsIgnoreCase(uri.getScheme()))
                    && uri.getHost() != null && uri.getUserInfo() == null;
        } catch (RuntimeException error) { return false; }
    }

    public AppDefinition withPinned(boolean value) {
        return new AppDefinition(id, name, command, look, value, type, url, icon, launchIdentity);
    }
}
