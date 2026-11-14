package dev.aresos.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class AppsConfigTest {
    @TempDir Path directory;

    @Test
    void firstStartWritesDefaults() throws Exception {
        Path file = directory.resolve("aresos/apps.json");
        var result = AppsConfig.load(file);
        assertEquals(AppsConfig.defaults(), result.apps());
        assertNull(result.migrationBackup());
        assertEquals(result.apps(), AppsConfig.load(file).apps());
        assertTrue(Files.readString(file).contains("notepad.exe"));
    }

    @Test
    void roundTripPreservesArgumentsUnicodeAndPinnedChoice() throws Exception {
        Path file = directory.resolve("apps.json");
        var apps = List.of(new AppDefinition("notes", "Notizen ✓",
                List.of("C:\\Program Files\\Notes\\notes.exe", "a file.txt", "--literal=$value"),
                "minecraft:paper", false));
        AppsConfig.save(file, apps);
        assertEquals(apps, AppsConfig.load(file).apps());
    }

    @Test
    void invalidFilesStopAndLeaveOriginalBytesIntact() throws Exception {
        Path file = directory.resolve("apps.json");
        String valid = "{\"id\":\"test\",\"name\":\"Test\",\"command\":[\"test.exe\"],"
                + "\"look\":\"minecraft:paper\",\"pinned\":true}";
        for (String broken : List.of("[{ definitely broken\n", "null", "{}", "[" + valid + "," + valid + "]",
                "[" + valid.replace("[\"test.exe\"]", "[]") + "]",
                "[" + valid.replace("true", "\"true\"") + "]",
                "[" + valid.replace("minecraft:paper", "other:paper") + "]",
                "[" + valid.replace("\"name\":\"Test\",", "") + "]")) {
            Files.writeString(file, broken);
            var error = assertThrows(java.io.IOException.class, () -> AppsConfig.load(file));
            assertTrue(error.getMessage().contains("original left intact"));
            assertEquals(broken, Files.readString(file));
            try (var files = Files.list(directory)) { assertEquals(1, files.count()); }
        }
    }

    @Test
    void package01MigrationMakesVersionedBackupAndIsIdempotent() throws Exception {
        Path file = directory.resolve("apps.json");
        String old = "[{\"id\":\"notepad\",\"name\":\"Meine Notizen\",\"command\":[\"notepad.exe\",\"a file.txt\"],"
                + "\"look\":\"minecraft:paper\",\"pinned\":false,\"ownerExtra\":42}]";
        Files.writeString(file, old);
        var loaded = AppsConfig.load(file);
        assertEquals(old, Files.readString(loaded.migrationBackup()));
        assertTrue(loaded.migrationBackup().getFileName().toString().contains("schema-1-"));
        var app = loaded.apps().getFirst();
        assertEquals("notepad", app.id()); assertEquals("Meine Notizen", app.name());
        assertEquals(List.of("notepad.exe", "a file.txt"), app.command());
        assertEquals("minecraft:paper", app.look()); assertFalse(app.pinned());
        String migrated = Files.readString(file);
        assertNull(AppsConfig.load(file).migrationBackup());
        assertEquals(migrated, Files.readString(file));
        assertTrue(migrated.contains("ownerExtra"));
        AppsConfig.pins(file, java.util.Map.of("notepad", true));
        assertTrue(Files.readString(file).contains("ownerExtra"));
    }

    @Test
    void explicitDowngradeRestoresExactBytesAndKeepsLaterEdits() throws Exception {
        Path file = directory.resolve("apps.json");
        String old = "[ {\"id\":\"notepad\",\"name\":\"Old name\",\"command\":[\"notepad.exe\"],"
                + "\"look\":\"minecraft:paper\",\"pinned\":false} ]\n";
        Files.writeString(file, old);
        var loaded = AppsConfig.load(file);
        AppsConfig.pins(file, java.util.Map.of("notepad", true));
        String current = Files.readString(file);
        Path retained = AppsConfig.restoreLegacy(file, loaded.migrationBackup());
        assertEquals(old, Files.readString(file)); assertEquals(current, Files.readString(retained));
        assertTrue(Files.readString(retained).contains("true"));
    }

    @Test
    void linuxMigrationImportsAppearanceOnlyAndKeepsCommandsInBackup() throws Exception {
        Path file = directory.resolve("apps.json");
        String legacy = new com.google.gson.Gson().toJson(AppsConfig.defaults());
        Files.writeString(file, legacy);
        var loaded = AppsConfig.load(file, true);
        assertEquals(legacy, Files.readString(loaded.migrationBackup()));
        var app = loaded.apps().getFirst();
        assertEquals("notepad", app.id()); assertEquals("helper", app.type()); assertTrue(app.command().isEmpty());
        assertTrue(app.pinned()); assertFalse(Files.readString(file).contains("notepad.exe"));
    }

    @Test
    void discoveryMergeNeverAutoPinsOrReplacesOwnerFields() throws Exception {
        Path file = directory.resolve("apps.json");
        AppsConfig.save(file, List.of(new AppDefinition("notepad", "Owner name", List.of("notepad.exe"), "minecraft:diamond", false)));
        var result = AppsConfig.merge(file, List.of(AppsConfig.defaults().getFirst(), new AppDefinition("fixture", "Fixture", List.of("fixture.exe"), "minecraft:paper", true)));
        assertEquals(2,result.size()); assertEquals("Owner name",result.getFirst().name());
        assertEquals("minecraft:diamond",result.getFirst().look()); assertTrue(result.stream().noneMatch(AppDefinition::pinned));
        String once = Files.readString(file);
        AppsConfig.merge(file,result); assertEquals(once,Files.readString(file));
        assertThrows(IllegalArgumentException.class, () -> AppsConfig.merge(file,List.of(result.getFirst(),result.getFirst())));
        assertEquals(once,Files.readString(file));
    }

    @Test
    void discoveryRefreshesOwnedCachePathsAndPreservesCustomIcons() throws Exception {
        Path file = directory.resolve("apps.json");
        var oldCache = directory.resolve("old/aresos-runtime/discovery/sources/app.png").toString();
        var newCache = directory.resolve("new/aresos-runtime/discovery/sources/app.png").toString();
        var cached = new AppDefinition("cached", "Cached", List.of("cached.exe"), "minecraft:paper", false, "command", null, oldCache);
        var custom = new AppDefinition("custom", "Custom", List.of("custom.exe"), "minecraft:paper", false, "command", null, "owner-art.png");
        AppsConfig.save(file,List.of(cached,custom));
        var found = List.of(new AppDefinition("cached", "Found", cached.command(), cached.look(), false, "command", null, newCache),
                new AppDefinition("custom", "Found", custom.command(), custom.look(), false, "command", null, newCache));
        var merged = AppsConfig.merge(file,found);
        assertEquals(newCache,merged.getFirst().icon()); assertEquals("owner-art.png",merged.get(1).icon());
        var missing = new AppDefinition("cached", "Found", cached.command(), cached.look(), false);
        assertNull(AppsConfig.merge(file,List.of(missing)).getFirst().icon());
    }

    @Test
    void websitesRoundTripAndRejectUnsafeOrInvalidTargets() throws Exception {
        Path file = directory.resolve("apps.json");
        var app = new AppDefinition("moodle","Moodle",List.of(),"minecraft:book",false,"url","https://example.test/course?id=1",null);
        AppsConfig.save(file,List.of(app)); assertEquals(List.of(app),AppsConfig.load(file).apps());
        for(String url:List.of("file:///etc/passwd","javascript:alert(1)","https:///missing","https://user:pass@example.test"))
            assertThrows(IllegalArgumentException.class,()->new AppDefinition("bad","Bad",List.of(),"minecraft:paper",false,"url",url,null));
    }

    @Test
    void emptyListIsAnIntentionalConfig() throws Exception {
        Path file = directory.resolve("apps.json");
        AppsConfig.save(file, List.of());
        assertEquals(List.of(), AppsConfig.load(file).apps());
    }

    // A Windows file as schema 2 wrote it: a pin, a renamed starter, unknown fields, launch metadata, a website.
    private static final String SCHEMA_2 = """
            {
              "schemaVersion": 2,
              "ownerNote": "keep me",
              "apps": [
                {"id": "notepad", "name": "Meine Notizen", "type": "command", "command": ["notepad.exe", "a file.txt"],
                 "look": "minecraft:paper", "pinned": false, "ownerExtra": 42},
                {"id": "paint", "name": "Paint", "type": "command", "command": ["C:\\\\Windows\\\\mspaint.exe", "--new"],
                 "look": "minecraft:brush", "pinned": true, "launchIdentity": {"target": "c:/windows/mspaint.exe",
                 "arguments": ["--new"], "workingDirectory": "", "aumid": "", "rawArguments": "--new"}},
                {"id": "calc", "name": "Calculator", "type": "command", "command": ["calc.exe"],
                 "look": "minecraft:paper", "pinned": false, "future": {"nested": [1, 2]}},
                {"id": "moodle", "name": "Moodle", "type": "url", "url": "https://example.test/course",
                 "look": "minecraft:book", "pinned": false}
              ]
            }
            """;

    private static com.google.gson.JsonObject tree(Path file) throws Exception {
        return com.google.gson.JsonParser.parseString(Files.readString(file)).getAsJsonObject();
    }

    private static AppDefinition listed(String id, String name, String source) {
        return new AppDefinition(id, name, List.of(), "minecraft:paper", false, "helper", null, null)
                .withSystem(new SystemInfo(source, null, null, null, null, null, null, null));
    }

    private static List<String> mine(List<AppDefinition> apps) {
        return apps.stream().filter(AppDefinition::mine).map(AppDefinition::id).toList();
    }

    @Test
    void schema2MovesToSchema3WithABackupLosesNothingAndCanGoBack() throws Exception {
        Path file = directory.resolve("apps.json");
        Files.writeString(file, SCHEMA_2);
        var loaded = AppsConfig.load(file);
        assertTrue(loaded.migrationBackup().getFileName().toString().startsWith("apps.json.schema-2-"));
        assertEquals(SCHEMA_2, Files.readString(loaded.migrationBackup()));
        assertNull(loaded.baseline());
        // His from the start: the starter and the pinned one. The rest waits for the first full program list.
        assertEquals(List.of("notepad", "paint"), mine(loaded.apps()));
        assertEquals(List.of("paint"), loaded.apps().stream().filter(AppDefinition::pinned).map(AppDefinition::id).toList());
        assertEquals(List.of("Meine Notizen", "Paint", "Calculator", "Moodle"), loaded.apps().stream().map(AppDefinition::name).toList());
        assertEquals(List.of("C:\\Windows\\mspaint.exe", "--new"), loaded.apps().get(1).command());
        assertEquals("--new", loaded.apps().get(1).launchIdentity().rawArguments());
        assertEquals("https://example.test/course", loaded.apps().get(3).url());

        // The file is the old one plus the schema number and "mine" per app; nothing else moved or went missing.
        var moved = tree(file);
        assertEquals(AppsConfig.SCHEMA, moved.get("schemaVersion").getAsInt());
        for (var app : moved.getAsJsonArray("apps")) assertNotNull(app.getAsJsonObject().remove("mine"));
        moved.addProperty("schemaVersion", 2);
        assertEquals(com.google.gson.JsonParser.parseString(SCHEMA_2), moved);

        String once = Files.readString(file);
        var again = AppsConfig.load(file);
        assertNull(again.migrationBackup());
        assertEquals(loaded.apps(), again.apps());
        assertEquals(once, Files.readString(file));

        // And back: the backup returns byte for byte, the schema-3 file with its later edits is kept beside it.
        AppsConfig.mine(file, java.util.Map.of("calc", true));
        Path retained = AppsConfig.restoreLegacy(file, loaded.migrationBackup());
        assertEquals(SCHEMA_2, Files.readString(file));
        assertTrue(retained.getFileName().toString().startsWith("apps.json.schema-4-before-downgrade-"));
        assertEquals(List.of("notepad", "paint", "calc"), mine(AppsConfig.load(retained).apps()));
        assertEquals(loaded.apps(), AppsConfig.load(file).apps());
        assertThrows(java.io.IOException.class, () -> AppsConfig.restoreLegacy(file, retained));
    }

    @Test
    void aBrokenOrNewerSchema2FileIsLeftUntouched() throws Exception {
        Path file = directory.resolve("apps.json");
        String duplicate = SCHEMA_2.replace("\"id\": \"calc\"", "\"id\": \"paint\"");
        for (String broken : List.of(duplicate, SCHEMA_2.replace("\"pinned\": true", "\"pinned\": \"true\""),
                SCHEMA_2.replace("\"name\": \"Paint\", ", ""), SCHEMA_2.replace("\"schemaVersion\": 2", "\"schemaVersion\": 5"),
                SCHEMA_2.replace("\"schemaVersion\": 2", "\"schemaVersion\": \"2\""),
                SCHEMA_2.replace("\"ownerExtra\": 42", "\"mine\": \"yes\""),
                SCHEMA_2.replace("\"schemaVersion\": 2", "\"schemaVersion\": 3, \"baseline\": \"tomorrow\""),
                SCHEMA_2.substring(0, SCHEMA_2.length() / 2))) {
            Files.writeString(file, broken);
            var error = assertThrows(java.io.IOException.class, () -> AppsConfig.load(file));
            assertTrue(error.getMessage().contains("original left intact"), error.getMessage());
            assertEquals(broken, Files.readString(file));
            try (var files = Files.list(directory)) { assertEquals(1, files.count(), "a backup or temporary file was left"); }
            assertThrows(java.io.IOException.class, () -> AppsConfig.merge(file, List.of(listed("new", "New", "user")),
                    true, java.time.LocalDate.of(2026, 11, 13)));
            assertThrows(java.io.IOException.class, () -> AppsConfig.mine(file, java.util.Map.of("paint", false)));
            assertEquals(broken, Files.readString(file));
        }
    }

    @Test
    void theFirstFullProgramListIsDayOneAndLaterProgramsJoinByTheirOrigin() throws Exception {
        Path file = directory.resolve("apps.json");
        // The laptop today: a schema-2 file from the 1.0 helper, Notepad pinned, plus an entry of his own.
        Files.writeString(file, """
                {"schemaVersion": 2, "apps": [
                  {"id": "terminal", "name": "Terminal", "type": "helper", "look": "minecraft:command_block", "pinned": false},
                  {"id": "notepad", "name": "Notepad", "type": "helper", "look": "minecraft:writable_book", "pinned": true},
                  {"id": "browser", "name": "Chrome", "type": "helper", "look": "minecraft:compass", "pinned": false},
                  {"id": "custom", "name": "Custom", "type": "helper", "look": "minecraft:paper", "pinned": false}]}
                """);
        assertEquals(List.of("terminal", "notepad", "browser"), mine(AppsConfig.load(file, true).apps()));
        var system = List.of(listed("browser", "Chrome", "image"), listed("com-discordapp-discord", "Discord", "flatpak-user"),
                listed("lunarclient", "Lunar Client", "user"), listed("notepad", "Notepad", "image"),
                listed("org-kde-dolphin", "Dolphin", "system"), listed("org-kde-okular", "Okular", "flatpak-system"),
                listed("steam", "Steam", "system"), listed("terminal", "Terminal", "image"));

        // A list without origins (Windows, a 1.0 helper) adds programs and decides nothing.
        var plain = AppsConfig.merge(file, system.stream().map(app -> app.withSystem(null)).toList(), false, null);
        assertEquals(List.of("terminal", "notepad", "browser"), mine(plain.apps()));
        assertEquals(5, plain.added().size());
        assertTrue(plain.joined().isEmpty());
        assertFalse(plain.dayOne());
        assertNull(plain.baseline());
        assertNull(AppsConfig.load(file).baseline());

        var day = java.time.LocalDate.of(2026, 11, 13);
        var first = AppsConfig.merge(file, system, true, day);
        assertTrue(first.dayOne());
        assertEquals(day, first.baseline());
        assertEquals(List.of("terminal", "notepad", "browser", "com-discordapp-discord", "lunarclient"), mine(first.apps()));
        assertEquals(List.of("com-discordapp-discord", "lunarclient"), first.joined());
        assertTrue(first.added().isEmpty(), "the plain list had added them already");
        assertEquals("2026-11-13", tree(file).get("baseline").getAsString());
        assertEquals(day, AppsConfig.load(file).baseline());
        assertEquals("flatpak-system", AppsConfig.load(file).apps().stream()
                .filter(app -> app.id().equals("org-kde-okular")).findFirst().orElseThrow().system().source());

        // The same list on another day changes nothing: the baseline is written once.
        String once = Files.readString(file);
        var second = AppsConfig.merge(file, system, true, day.plusDays(3));
        assertFalse(second.dayOne());
        assertEquals(day, second.baseline());
        assertTrue(second.joined().isEmpty() && second.added().isEmpty());
        assertEquals(once, Files.readString(file));

        // He takes Discord out and adds Steam. Then programs appear, and Steam and Dolphin leave the system.
        AppsConfig.mine(file, java.util.Map.of("com-discordapp-discord", false, "steam", true));
        var later = new java.util.ArrayList<>(system);
        later.removeIf(app -> app.id().equals("steam") || app.id().equals("org-kde-dolphin"));
        later.addAll(List.of(listed("new-user", "New user", "user"), listed("new-flatpak-user", "New fu", "flatpak-user"),
                listed("new-flatpak-system", "New fs", "flatpak-system"), listed("new-system", "New system", "system"),
                listed("new-image", "New image", "image"), listed("new-unknown", "New unknown", null)));
        var third = AppsConfig.merge(file, later, true, day.plusDays(5));
        assertEquals(List.of("new-user", "new-flatpak-user", "new-flatpak-system"), third.joined());
        assertEquals(6, third.added().size());
        assertEquals(List.of("terminal", "notepad", "browser", "lunarclient", "steam", "new-user", "new-flatpak-user",
                "new-flatpak-system"), mine(third.apps()), "Discord stays out, Steam stays in, system and image programs wait");
        var steam = third.apps().stream().filter(app -> app.id().equals("steam")).findFirst().orElseThrow();
        assertEquals("system", steam.system().source(), "a program the system no longer lists keeps its fields");
        assertEquals(15, third.apps().size());

        // A list without origins after day one still decides nothing.
        var windows = AppsConfig.merge(file, List.of(listed("late", "Late", "user").withSystem(null)), false, null);
        assertEquals(List.of("late"), windows.added());
        assertTrue(windows.joined().isEmpty());
        assertEquals(day, windows.baseline());
    }

    @Test
    void pinningMakesAnAppHisAndTakingItOutUnpinsIt() throws Exception {
        Path file = directory.resolve("apps.json");
        Files.writeString(file, SCHEMA_2);
        AppsConfig.load(file);
        var pinned = AppsConfig.pins(file, java.util.Map.of("calc", true));
        assertEquals(List.of("notepad", "paint", "calc"), mine(pinned));
        assertTrue(pinned.get(2).pinned());
        var unpinned = AppsConfig.pins(file, java.util.Map.of("calc", false));
        assertEquals(List.of("notepad", "paint", "calc"), mine(unpinned), "unpinning changes nothing else");
        assertFalse(unpinned.get(2).pinned());
        var removed = AppsConfig.mine(file, java.util.Map.of("paint", false, "moodle", true));
        assertEquals(List.of("notepad", "calc", "moodle"), mine(removed));
        assertTrue(removed.stream().noneMatch(AppDefinition::pinned), "an app that is not his cannot stay pinned");
        String before = Files.readString(file);
        assertThrows(java.io.IOException.class, () -> AppsConfig.mine(file, java.util.Map.of("nobody", true)));
        assertEquals(before, Files.readString(file));
        assertTrue(before.contains("ownerNote") && before.contains("ownerExtra") && before.contains("nested"));
        // An entry he writes by hand without "mine" is his; a pinned one is his whatever the file says.
        Files.writeString(file, """
                {"schemaVersion": 3, "apps": [
                  {"id": "hand", "name": "Hand", "type": "url", "url": "https://example.test/", "look": "minecraft:book", "pinned": false},
                  {"id": "odd", "name": "Odd", "type": "command", "command": ["odd.exe"], "look": "minecraft:paper", "pinned": true, "mine": false}]}
                """);
        assertEquals(List.of("hand", "odd"), mine(AppsConfig.load(file).apps()));
    }

    @Test
    void whatTheSystemSaidIsSavedReplacedAndKeptWhileNothingNewIsSaid() throws Exception {
        Path file = directory.resolve("apps.json");
        AppsConfig.save(file, List.of());
        var full = new SystemInfo("flatpak-user", "/run/user/1000/aresos/icons/discord.png", List.of("Network", "InstantMessaging"),
                "Internet Messenger", List.of("chat", "voice"), "com.discordapp.Discord.desktop", "com.discordapp.Discord", false);
        var discord = listed("discord", "Discord", "user").withSystem(full);
        var day = java.time.LocalDate.of(2026, 11, 13);
        assertEquals(full, AppsConfig.merge(file, List.of(discord), true, day).apps().getFirst().system());
        assertEquals(full, AppsConfig.load(file).apps().getFirst().system());
        var saved = tree(file).getAsJsonArray("apps").get(0).getAsJsonObject().getAsJsonObject("system");
        assertEquals(java.util.Set.of("source", "icon", "categories", "genericName", "keywords", "desktopId", "execName", "terminal"),
                saved.keySet());
        // The helper is down or speaks 1.0: nothing new is said, what was saved stays.
        assertEquals(full, AppsConfig.merge(file, List.of(discord.withSystem(null))).getFirst().system());
        var changed = new SystemInfo("flatpak-user", null, List.of("Game"), null, null, null, null, true);
        assertEquals(changed, AppsConfig.merge(file, List.of(discord.withSystem(changed)), true, day).apps().getFirst().system());
        assertNull(AppsConfig.merge(file, List.of(discord.withSystem(SystemInfo.UNKNOWN)), true, day).apps().getFirst().system());
        assertFalse(Files.readString(file).contains("\"system\""));
        assertThrows(IllegalArgumentException.class, () -> new SystemInfo("snap", null, null, null, null, null, null, null));
    }

    @Test
    void failedReadDoesNotReplaceOwnersPath() throws Exception {
        Path file = directory.resolve("apps.json");
        Files.createDirectory(file);
        assertThrows(java.io.IOException.class, () -> AppsConfig.load(file));
        assertTrue(Files.isDirectory(file));
    }

    /**
     * Package 36 saves {@code place} and {@code group} with schema 4 and no new number (HUB.md 3.5). This test was
     * first committed and run on package 35's parser unchanged, where both are fields it does not know: it reads the
     * file and every edit it makes keeps them where they are, so a mod of package 35 neither refuses nor loses them.
     */
    @Test
    void aSchema4FileWithPlacesAndGroupsIsReadAndEveryEditKeepsThem() throws Exception {
        Path file = directory.resolve("apps.json");
        try (var fixture = getClass().getResourceAsStream("/apps/schema-4-town.json")) { Files.copy(fixture, file); }
        var places = java.util.Map.of("discord", "N0R0", "spotify", "E0R0", "gimp", "W0L0", "calc", "S0R0");
        var loaded = AppsConfig.load(file, true);
        assertNull(loaded.migrationBackup(), "a schema-4 file is not moved to another schema");
        assertEquals(List.of("discord", "spotify", "gimp", "calc"), loaded.apps().stream().map(AppDefinition::id).toList());
        assertEquals(List.of("discord", "spotify", "gimp"), mine(loaded.apps()));
        assertTrue(loaded.apps().get(2).absent());

        // Every edit the mod makes while it runs: pins, My apps, a complete program list, short names.
        AppsConfig.pins(file, java.util.Map.of("spotify", true));
        AppsConfig.mine(file, java.util.Map.of("calc", true));
        AppsConfig.merge(file, List.of(listed("discord", "Discord", "flatpak-user"), listed("spotify", "Spotify", "flatpak-user"),
                listed("calc", "Calculator", "system"), listed("newapp", "New App", "user")), true, java.time.LocalDate.of(2026, 11, 14), true);
        AppsConfig.assignNames(file, java.util.Set.of("help"));
        AppsConfig.name(file, "discord", "chat", java.util.Set.of("help"));
        AppsConfig.unname(file, "chat");
        AppsConfig.mine(file, java.util.Map.of("discord", false));

        var saved = tree(file);
        assertEquals(4, saved.get("schemaVersion").getAsInt());
        var byId = new java.util.HashMap<String, com.google.gson.JsonObject>();
        for (var app : saved.getAsJsonArray("apps")) byId.put(app.getAsJsonObject().get("id").getAsString(), app.getAsJsonObject());
        places.forEach((id, place) -> assertEquals(place, byId.get(id).get("place").getAsString(), id + " lost its place"));
        assertEquals("games", byId.get("spotify").get("group").getAsString());
        assertFalse(byId.get("discord").has("group") || byId.get("newapp").has("place"));
        // The edits themselves happened.
        var after = AppsConfig.load(file, true).apps();
        assertEquals(List.of("spotify", "gimp", "calc", "newapp"), mine(after));
        assertTrue(after.stream().filter(app -> app.id().equals("gimp")).findFirst().orElseThrow().absent());
        assertFalse(after.stream().filter(app -> app.id().equals("discord")).findFirst().orElseThrow().pinned());
    }
}
