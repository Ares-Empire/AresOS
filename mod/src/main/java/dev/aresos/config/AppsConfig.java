package dev.aresos.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.Strictness;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.UUID;

public final class AppsConfig {
    private static final Gson JSON = new GsonBuilder().setPrettyPrinting().setStrictness(Strictness.STRICT).create();
    private static final List<AppDefinition> DEFAULTS = List.of(new AppDefinition(
            "notepad", "Notepad", List.of("notepad.exe"), "minecraft:writable_book", true));

    private AppsConfig() { }

    public static List<AppDefinition> defaults() {
        return DEFAULTS;
    }

    public record Loaded(List<AppDefinition> apps, Path brokenBackup) { }

    public static Loaded load(Path file) throws IOException {
        if (!Files.exists(file)) {
            save(file, DEFAULTS);
            return new Loaded(DEFAULTS, null);
        }
        List<AppDefinition> apps;
        try (var reader = Files.newBufferedReader(file)) {
            JsonArray array = JSON.fromJson(reader, JsonElement.class).getAsJsonArray();
            apps = new ArrayList<>();
            for (JsonElement element : array) {
                JsonObject app = element.getAsJsonObject();
                // Require every field, including pinned, rather than silently accepting typos as defaults.
                List<String> command = new ArrayList<>();
                for (JsonElement part : app.getAsJsonArray("command")) {
                    command.add(string(part));
                }
                JsonElement pinned = app.get("pinned");
                if (!pinned.isJsonPrimitive() || !pinned.getAsJsonPrimitive().isBoolean()) {
                    throw new IllegalArgumentException("pinned must be a boolean");
                }
                apps.add(new AppDefinition(string(app.get("id")), string(app.get("name")), command,
                        string(app.get("look")), pinned.getAsBoolean()));
            }
            validate(apps);
        } catch (RuntimeException malformed) {
            Path backup = file.resolveSibling(file.getFileName() + ".broken-" + UUID.randomUUID());
            // Copy before replacing: if backup or replacement fails, the owner's original survives.
            Files.copy(file, backup);
            save(file, DEFAULTS);
            return new Loaded(DEFAULTS, backup);
        }
        return new Loaded(List.copyOf(apps), null);
    }

    private static String string(JsonElement value) {
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString()) {
            throw new IllegalArgumentException("Expected a string");
        }
        return value.getAsString();
    }

    private static void validate(List<AppDefinition> apps) {
        var ids = new HashSet<String>();
        for (AppDefinition app : apps) {
            if (!ids.add(app.id())) {
                throw new IllegalArgumentException("Duplicate app id: " + app.id());
            }
        }
    }

    public static void save(Path file, List<AppDefinition> apps) throws IOException {
        validate(apps);
        Path target = file.toAbsolutePath();
        Files.createDirectories(target.getParent());
        Path temporary = Files.createTempFile(target.getParent(), "apps-", ".tmp");
        try {
            Files.writeString(temporary, JSON.toJson(apps) + System.lineSeparator());
            try {
                Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException unsupported) {
                Files.move(temporary, target, StandardCopyOption.REPLACE_EXISTING);
            }
        } finally {
            Files.deleteIfExists(temporary);
        }
    }
}
