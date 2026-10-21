package dev.aresos.config;

import java.util.List;

public record AppDefinition(String id, String name, List<String> command, String look, boolean pinned) {
    public AppDefinition {
        if (id == null || !id.matches("[a-z0-9_-]+") || name == null || name.isBlank()
                || command == null || command.isEmpty()
                || command.stream().anyMatch(part -> part == null || part.isEmpty() || part.indexOf('\0') >= 0)
                || look == null || !look.matches("minecraft:[a-z0-9_./-]+")) {
            throw new IllegalArgumentException("Invalid app definition");
        }
        command = List.copyOf(command);
    }
}
