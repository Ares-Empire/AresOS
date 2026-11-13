package dev.aresos.config;

import com.google.gson.*;
import java.io.IOException;
import java.nio.file.*;
import java.time.LocalDate;
import java.util.*;

/**
 * config/aresos/apps.json. Schema 3 adds "My apps" (docs/design/HUB.md 3.5): {@code mine} per app, what the system
 * said about it ({@code system}), and once for the file {@code baseline}, the day the first full program list was
 * taken. Every change edits the parsed file in place, so fields this mod does not know stay where they are.
 */
public final class AppsConfig {
    public static final int SCHEMA = 3;
    private static final Gson JSON = new GsonBuilder().setPrettyPrinting().setStrictness(Strictness.STRICT).create();
    private static final List<AppDefinition> DEFAULTS = List.of(new AppDefinition(
            "notepad", "Notepad", List.of("notepad.exe"), "minecraft:writable_book", true));

    private AppsConfig() { }
    public static List<AppDefinition> defaults() { return DEFAULTS; }
    /** {@code migrationBackup} is the untouched old file when this load moved it to the current schema. */
    public record Loaded(List<AppDefinition> apps, Path migrationBackup, LocalDate baseline) { }
    /**
     * What a complete program list changed. {@code added} are the IDs the file did not know before, {@code joined}
     * the ones that became his by the rules; {@code dayOne} says this list set the baseline.
     */
    public record Merged(List<AppDefinition> apps, List<String> added, List<String> joined, LocalDate baseline,
                         boolean dayOne) { }

    public static synchronized Loaded load(Path file) throws IOException {
        return load(file, false);
    }

    public static synchronized Loaded load(Path file, boolean linux) throws IOException {
        if (!Files.exists(file)) {
            var defaults = linux ? DEFAULTS.stream().map(AppsConfig::helperOnly).toList() : DEFAULTS;
            save(file, defaults);
            return new Loaded(defaults, null, null);
        }
        JsonElement original = read(file);
        int version = version(original);
        if (version == SCHEMA) {
            var document = original.getAsJsonObject();
            return new Loaded(parse(document), null, baseline(document));
        }
        // Validate the entire old file before copying or writing anything.
        JsonObject document = version == 1 ? document(original.getAsJsonArray().deepCopy())
                : original.getAsJsonObject().deepCopy();
        parseApps(document);
        if (version == 1) for (JsonElement element : document.getAsJsonArray("apps")) {
            JsonObject app = element.getAsJsonObject();
            app.addProperty("type", linux ? "helper" : "command");
            if (linux) app.remove("command");
        }
        // His from the start: what is pinned today, and the starters. Everything else waits for the first full
        // program list (merge). Nothing else in an entry is touched.
        for (JsonElement element : document.getAsJsonArray("apps")) {
            JsonObject app = element.getAsJsonObject();
            if (!app.has("mine")) app.addProperty("mine", app.get("pinned").getAsBoolean()
                    || MyApps.STARTERS.contains(string(app.get("id"))));
        }
        document.addProperty("schemaVersion", SCHEMA);
        var apps = parse(document);
        Path backup = file.resolveSibling(file.getFileName() + ".schema-" + version + "-" + UUID.randomUUID() + ".bak");
        Files.copy(file, backup);
        write(file, document);
        return new Loaded(apps, backup, baseline(document));
    }

    private static AppDefinition helperOnly(AppDefinition app) {
        return new AppDefinition(app.id(), app.name(), List.of(), app.look(), app.pinned(), "helper", null, null);
    }

    private static JsonElement read(Path file) throws IOException {
        try (var reader = Files.newBufferedReader(file)) {
            var value = JSON.fromJson(reader, JsonElement.class);
            if (value == null || value.isJsonNull() || !(value.isJsonArray() || value.isJsonObject()))
                throw new IllegalArgumentException("Expected an app array or a schema document");
            return value;
        } catch (RuntimeException error) {
            throw new IOException("Invalid apps.json; original left intact: " + error.getMessage(), error);
        }
    }

    /** 1 for package 01's bare array, otherwise the document's schemaVersion; anything but 1 to 3 is refused. */
    private static int version(JsonElement content) throws IOException {
        if (content.isJsonArray()) return 1;
        var value = content.getAsJsonObject().get("schemaVersion");
        String text = value == null ? "" : value.toString();
        if (text.equals("2")) return 2;
        if (text.equals("3")) return SCHEMA;
        // A newer mod's file: leave it alone and say so, as every version of this mod does.
        throw new IOException("Invalid apps.json; original left intact: Unsupported schemaVersion (expected " + SCHEMA + ")");
    }

    private static List<AppDefinition> parse(JsonObject document) throws IOException {
        if (version(document) != SCHEMA)
            throw new IOException("Invalid apps.json; original left intact: Unsupported schemaVersion (expected " + SCHEMA + ")");
        var apps = parseApps(document);
        baseline(document);
        return apps;
    }

    /** The entries by today's rules, whatever the schema number says; a missing {@code mine} reads as his. */
    private static List<AppDefinition> parseApps(JsonObject document) throws IOException {
        try {
            List<AppDefinition> apps = new ArrayList<>();
            for (JsonElement element : document.getAsJsonArray("apps")) {
                JsonObject app = element.getAsJsonObject();
                String id = string(app.get("id"));
                try {
                    var command = new ArrayList<String>();
                    if (app.has("command")) for (JsonElement part : app.getAsJsonArray("command")) command.add(string(part));
                    // An entry he wrote by hand has no "mine": he wants it, as with a program he installs.
                    boolean mine = !app.has("mine") || bool(app, "mine");
                    apps.add(new AppDefinition(id, string(app.get("name")), command, string(app.get("look")),
                            bool(app, "pinned"), optional(app, "type", "command"), optional(app, "url", null),
                            optional(app, "icon", null), identity(app), mine,
                            app.has("system") ? JSON.fromJson(app.getAsJsonObject("system"), SystemInfo.class) : null));
                } catch (RuntimeException error) { throw new IllegalArgumentException("App " + id + ": " + error.getMessage(), error); }
            }
            validate(apps);
            return List.copyOf(apps);
        } catch (RuntimeException error) {
            throw new IOException("Invalid apps.json; original left intact: " + error.getMessage(), error);
        }
    }

    private static LocalDate baseline(JsonObject document) throws IOException {
        if (!document.has("baseline")) return null;
        try { return LocalDate.parse(string(document.get("baseline"))); }
        catch (RuntimeException error) {
            throw new IOException("Invalid apps.json; original left intact: baseline must be a date like 2026-11-13", error);
        }
    }

    private static boolean bool(JsonObject app, String key) {
        var value = app.get(key);
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isBoolean())
            throw new IllegalArgumentException(key + " must be a boolean");
        return value.getAsBoolean();
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
        document.addProperty("schemaVersion", SCHEMA);
        document.add("apps", entries);
        return document;
    }
    public static synchronized void save(Path file, List<AppDefinition> apps) throws IOException {
        validate(apps);
        write(file, document(JSON.toJsonTree(apps).getAsJsonArray()));
    }

    /** A list without origins: newly discovered starter IDs are his; other programs wait for a detailed list. */
    public static synchronized List<AppDefinition> merge(Path file, List<AppDefinition> discovered) throws IOException {
        return merge(file, discovered, false, null).apps();
    }

    /**
     * Takes in one complete program list. Owner fields, including unknown optional ones, are preserved; new
     * programs are added without a pin. What the system said about a program replaces what was saved.
     *
     * With {@code detailed} (the list says where each program came from) the My-apps rules run: the first such
     * list is day one and writes the baseline; after it a program the file did not know joins by its origin
     * ({@link MyApps}). A program the list no longer names keeps its entry and all its fields.
     */
    public static synchronized Merged merge(Path file, List<AppDefinition> discovered, boolean detailed, LocalDate today)
            throws IOException {
        validate(discovered);
        load(file);
        var document = read(file).getAsJsonObject();
        var existing = new ArrayList<>(parse(document));
        LocalDate baseline = baseline(document);
        boolean dayOne = detailed && baseline == null;
        var added = new ArrayList<String>();
        var joined = new ArrayList<String>();
        for (var app : discovered) {
            int match = -1;
            for (int i = 0; i < existing.size(); i++) {
                if (existing.get(i).id().equals(app.id())) {
                    match = i;
                    break;
                }
            }
            JsonObject entry;
            boolean mine = false;
            if (match >= 0) {
                // Refresh only our cache paths: moving the game folder must not strand old absolute paths.
                var oldIcon = existing.get(match).icon();
                mine = existing.get(match).mine();
                entry = document.getAsJsonArray("apps").get(match).getAsJsonObject();
                if (app.launchIdentity() != null) entry.add("launchIdentity", JSON.toJsonTree(app.launchIdentity()));
                if (oldIcon == null || autoIcon(oldIcon)) {
                    if (app.icon() == null) entry.remove("icon");
                    else entry.addProperty("icon", app.icon());
                }
            } else {
                var fresh = app.withMine(false);
                existing.add(fresh);
                entry = JSON.toJsonTree(fresh).getAsJsonObject();
                document.getAsJsonArray("apps").add(entry);
                added.add(app.id());
            }
            if (app.system() != null) {
                if (app.system().isEmpty()) entry.remove("system");
                else entry.add("system", JSON.toJsonTree(app.system()));
            }
            boolean starter = MyApps.STARTERS.contains(app.id());
            // A starter discovered by 1.0 is his too, but an existing false entry is his own removal.
            boolean joins = match < 0 && starter || (dayOne
                    ? MyApps.dayOne(app.id(), app.system()) && !(starter && match >= 0)
                    : detailed && match < 0 && MyApps.joinsLater(app.system()));
            if (joins && !mine) {
                entry.addProperty("mine", true);
                joined.add(app.id());
            }
        }
        if (dayOne) {
            baseline = Objects.requireNonNull(today);
            document.addProperty("baseline", baseline.toString());
        }
        var result = parse(document);
        writeIfChanged(file, document);
        return new Merged(result, List.copyOf(added), List.copyOf(joined), baseline, dayOne);
    }

    private static boolean autoIcon(String icon) {
        return icon.replace('\\', '/').toLowerCase(Locale.ROOT).contains("/aresos-runtime/discovery/sources/");
    }

    /** Pinning an app makes it his; unpinning changes nothing else. */
    public static synchronized List<AppDefinition> pins(Path file, Map<String, Boolean> changes) throws IOException {
        return edit(file, changes, "pins", (app, pinned) -> {
            app.addProperty("pinned", pinned);
            if (pinned) app.addProperty("mine", true);
        });
    }

    /** Adds apps to My apps or takes them out. Taking one out also unpins it: its item leaves the hotbar. */
    public static synchronized List<AppDefinition> mine(Path file, Map<String, Boolean> changes) throws IOException {
        return edit(file, changes, "My apps", (app, mine) -> {
            app.addProperty("mine", mine);
            if (!mine) app.addProperty("pinned", false);
        });
    }

    private static List<AppDefinition> edit(Path file, Map<String, Boolean> changes, String what,
                                            java.util.function.BiConsumer<JsonObject, Boolean> change) throws IOException {
        var document = read(file).getAsJsonObject();
        var apps = parse(document);
        for (String id : changes.keySet()) if (apps.stream().noneMatch(app -> app.id().equals(id)))
            throw new IOException("Unknown app id while saving " + what + ": " + id);
        for (var element : document.getAsJsonArray("apps")) {
            var app = element.getAsJsonObject();
            String id = string(app.get("id"));
            if (changes.containsKey(id)) change.accept(app, changes.get(id));
        }
        writeIfChanged(file, document);
        return parse(document);
    }

    /**
     * Explicit downgrade recovery: puts back the file an older mod wrote, from the backup a schema move made
     * (package 01's array, or schema 2), after keeping the current file with its later edits beside it.
     */
    public static synchronized Path restoreLegacy(Path file, Path backup) throws IOException {
        Path target = file.toAbsolutePath().normalize(), original = backup.toAbsolutePath().normalize();
        String name = original.getFileName().toString(), prefix = target.getFileName() + ".schema-";
        boolean first = name.startsWith(prefix + "1-");
        if (!target.getParent().equals(original.getParent()) || !(first || name.startsWith(prefix + "2-"))
                || !name.endsWith(".bak"))
            throw new IOException("Choose a sibling schema-1 or schema-2 migration backup");
        var legacy = read(original);
        if (first) {
            if (!legacy.isJsonArray()) throw new IOException("Backup is not a package-01 app array");
            parseApps(document(legacy.getAsJsonArray()));
        } else {
            if (!legacy.isJsonObject() || version(legacy) != 2) throw new IOException("Backup is not a schema-2 apps.json");
            parseApps(legacy.getAsJsonObject());
        }
        parse(read(target).getAsJsonObject());
        Path retained = target.resolveSibling(target.getFileName() + ".schema-" + SCHEMA + "-before-downgrade-"
                + UUID.randomUUID() + ".bak");
        Files.copy(target, retained);
        System.err.println("WARNING: restoring the older apps.json. Later apps, names, pins and My apps remain ONLY in " + retained);
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
