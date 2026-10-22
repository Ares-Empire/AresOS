package dev.aresos.config;

import com.google.gson.*;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

public final class AppsConfig {
    private static final Gson JSON = new GsonBuilder().setPrettyPrinting().setStrictness(Strictness.STRICT).create();
    private static final List<AppDefinition> DEFAULTS = List.of(new AppDefinition(
            "notepad", "Notepad", List.of("notepad.exe"), "minecraft:writable_book", true));

    private AppsConfig() { }
    public static List<AppDefinition> defaults() { return DEFAULTS; }
    public record Loaded(List<AppDefinition> apps, Path migrationBackup) { }

    public static synchronized Loaded load(Path file) throws IOException {
        return load(file, false);
    }

    public static synchronized Loaded load(Path file, boolean linux) throws IOException {
        if (!Files.exists(file)) {
            var defaults = linux ? DEFAULTS.stream().map(AppsConfig::helperOnly).toList() : DEFAULTS;
            save(file, defaults);
            return new Loaded(defaults, null);
        }
        JsonElement original = read(file);
        if (!original.isJsonArray()) return new Loaded(parse(original.getAsJsonObject()), null);
        // Validate the entire old file before copying or writing anything.
        JsonArray entries = original.getAsJsonArray();
        var document = document(entries.deepCopy());
        parse(document);
        Path backup = file.resolveSibling(file.getFileName() + ".schema-1-" + UUID.randomUUID() + ".bak");
        Files.copy(file, backup);
        for (JsonElement element : document.getAsJsonArray("apps")) {
            JsonObject app = element.getAsJsonObject();
            app.addProperty("type", linux ? "helper" : "command");
            if (linux) app.remove("command");
        }
        write(file, document);
        return new Loaded(parse(document), backup);
    }

    private static AppDefinition helperOnly(AppDefinition app) {
        return new AppDefinition(app.id(), app.name(), List.of(), app.look(), app.pinned(), "helper", null, null);
    }

    private static JsonElement read(Path file) throws IOException {
        try (var reader = Files.newBufferedReader(file)) {
            var value = JSON.fromJson(reader, JsonElement.class);
            if (value == null || value.isJsonNull() || !(value.isJsonArray() || value.isJsonObject()))
                throw new IllegalArgumentException("Expected an app array or schema-2 document");
            return value;
        } catch (RuntimeException error) {
            throw new IOException("Invalid apps.json; original left intact: " + error.getMessage(), error);
        }
    }

    private static List<AppDefinition> parse(JsonObject document) throws IOException {
        try {
            if (!document.has("schemaVersion") || !document.get("schemaVersion").toString().equals("2"))
                throw new IllegalArgumentException("Unsupported schemaVersion (expected 2)");
            List<AppDefinition> apps = new ArrayList<>();
            for (JsonElement element : document.getAsJsonArray("apps")) {
                JsonObject app = element.getAsJsonObject();
                String id = string(app.get("id"));
                try {
                    var command = new ArrayList<String>();
                    if (app.has("command")) for (JsonElement part : app.getAsJsonArray("command")) command.add(string(part));
                    var pinned = app.get("pinned");
                    if (pinned == null || !pinned.isJsonPrimitive() || !pinned.getAsJsonPrimitive().isBoolean())
                        throw new IllegalArgumentException("pinned must be a boolean");
                    apps.add(new AppDefinition(id, string(app.get("name")), command, string(app.get("look")),
                            pinned.getAsBoolean(), optional(app, "type", "command"), optional(app, "url", null), optional(app, "icon", null), identity(app)));
                } catch (RuntimeException error) { throw new IllegalArgumentException("App " + id + ": " + error.getMessage(), error); }
            }
            validate(apps);
            return List.copyOf(apps);
        } catch (RuntimeException error) {
            throw new IOException("Invalid apps.json; original left intact: " + error.getMessage(), error);
        }
    }

    private static String optional(JsonObject app, String key, String fallback) {
        return app.has(key) ? string(app.get(key)) : fallback;
    }
    private static WindowsLaunchIdentity identity(JsonObject app) {
        if (!app.has("launchIdentity")) return null;
        var value = app.getAsJsonObject("launchIdentity");
        var arguments = new ArrayList<String>();
        for (var argument : value.getAsJsonArray("arguments")) arguments.add(string(argument));
        return new WindowsLaunchIdentity(string(value.get("target")), arguments,
                string(value.get("workingDirectory")), string(value.get("aumid")), optional(value, "rawArguments", null));
    }
    private static String string(JsonElement value) {
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString())
            throw new IllegalArgumentException("Expected a string");
        return value.getAsString();
    }
    private static void validate(List<AppDefinition> apps) {
        var ids = new HashSet<String>();
        for (var app : apps) if (!ids.add(app.id())) throw new IllegalArgumentException("Duplicate app id: " + app.id());
    }
    private static JsonObject document(JsonArray entries) {
        var document = new JsonObject();
        document.addProperty("schemaVersion", 2);
        document.add("apps", entries);
        return document;
    }
    public static synchronized void save(Path file, List<AppDefinition> apps) throws IOException {
        validate(apps);
        write(file, document(JSON.toJsonTree(apps).getAsJsonArray()));
    }

    /** Preserve owner fields, including unknown optional fields, when adding apps or changing pins. */
    public static synchronized List<AppDefinition> merge(Path file, List<AppDefinition> discovered) throws IOException {
        validate(discovered);
        load(file);
        var document = read(file).getAsJsonObject();
        var existing = new ArrayList<>(parse(document));
        for (var app : discovered) {
            int match = -1;
            for (int i = 0; i < existing.size(); i++) {
                var old = existing.get(i);
                if (old.id().equals(app.id())) {
                    match = i;
                    break;
                }
            }
            if (match >= 0) {
                // Refresh only our cache paths: moving the game folder must not strand old absolute paths.
                var oldIcon = existing.get(match).icon();
                var entry = document.getAsJsonArray("apps").get(match).getAsJsonObject();
                if (app.launchIdentity() != null) entry.add("launchIdentity", JSON.toJsonTree(app.launchIdentity()));
                if (oldIcon == null || autoIcon(oldIcon)) {
                    if (app.icon() == null) entry.remove("icon");
                    else entry.addProperty("icon", app.icon());
                }
            } else {
                existing.add(app.withPinned(false));
                document.getAsJsonArray("apps").add(JSON.toJsonTree(app.withPinned(false)));
            }
        }
        var result = parse(document);
        writeIfChanged(file, document);
        return result;
    }

    private static boolean autoIcon(String icon) {
        return icon.replace('\\', '/').toLowerCase(Locale.ROOT).contains("/aresos-runtime/discovery/sources/");
    }

    public static synchronized List<AppDefinition> pins(Path file, Map<String, Boolean> changes) throws IOException {
        var document = read(file).getAsJsonObject();
        var apps = parse(document);
        for (String id : changes.keySet()) if (apps.stream().noneMatch(app -> app.id().equals(id)))
            throw new IOException("Unknown app id while saving pins: " + id);
        for (var element : document.getAsJsonArray("apps")) {
            var app = element.getAsJsonObject();
            String id = string(app.get("id"));
            if (changes.containsKey(id)) app.addProperty("pinned", changes.get(id));
        }
        writeIfChanged(file, document);
        return parse(document);
    }
    /** Explicit downgrade recovery; preserve schema-2 edits before restoring the original bytes. */
    public static synchronized Path restoreLegacy(Path file, Path backup) throws IOException {
        Path target = file.toAbsolutePath().normalize(), original = backup.toAbsolutePath().normalize();
        if (!target.getParent().equals(original.getParent())
                || !original.getFileName().toString().startsWith(target.getFileName() + ".schema-1-")
                || !original.getFileName().toString().endsWith(".bak"))
            throw new IOException("Choose a sibling schema-1 migration backup");
        var legacy = read(original);
        if (!legacy.isJsonArray()) throw new IOException("Backup is not a package-01 app array");
        parse(document(legacy.getAsJsonArray()));
        parse(read(target).getAsJsonObject());
        Path retained = target.resolveSibling(target.getFileName() + ".schema-2-before-downgrade-" + UUID.randomUUID() + ".bak");
        Files.copy(target, retained);
        System.err.println("WARNING: restoring the schema-1 backup. Later apps, names and pins remain ONLY in " + retained);
        atomicBytes(target, Files.readAllBytes(original));
        return retained;
    }

    private static void writeIfChanged(Path file, JsonObject document) throws IOException {
        if (!read(file).equals(document)) write(file, document);
    }
    private static void write(Path file, JsonObject document) throws IOException {
        parse(document);
        atomicBytes(file.toAbsolutePath(), (JSON.toJson(document) + System.lineSeparator()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
    private static void atomicBytes(Path target, byte[] bytes) throws IOException {
        Files.createDirectories(target.getParent());
        Path temporary = Files.createTempFile(target.getParent(), "apps-", ".tmp");
        try {
            Files.write(temporary, bytes);
            // Refuse a non-atomic replacement; a failed migration must leave the original in place.
            Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(temporary); }
    }
}
