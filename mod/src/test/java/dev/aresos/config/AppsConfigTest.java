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

    @Test
    void failedReadDoesNotReplaceOwnersPath() throws Exception {
        Path file = directory.resolve("apps.json");
        Files.createDirectory(file);
        assertThrows(java.io.IOException.class, () -> AppsConfig.load(file));
        assertTrue(Files.isDirectory(file));
    }
}
