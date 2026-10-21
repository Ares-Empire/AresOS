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
        assertNull(result.brokenBackup());
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
    void brokenFileIsBackedUpByteForByteBeforeDefaults() throws Exception {
        Path file = directory.resolve("apps.json");
        String broken = "[{ definitely broken\n";
        Files.writeString(file, broken);
        var result = AppsConfig.load(file);
        assertEquals(broken, Files.readString(result.brokenBackup()));
        assertEquals(AppsConfig.defaults(), result.apps());
        assertEquals(AppsConfig.defaults(), AppsConfig.load(file).apps());
    }

    @Test
    void repeatedFailuresKeepEveryBackup() throws Exception {
        Path file = directory.resolve("apps.json");
        Files.writeString(file, "null");
        var first = AppsConfig.load(file);
        Files.writeString(file, "{}");
        var second = AppsConfig.load(file);
        assertNotEquals(first.brokenBackup(), second.brokenBackup());
        assertEquals("null", Files.readString(first.brokenBackup()));
        assertEquals("{}", Files.readString(second.brokenBackup()));
    }

    @Test
    void invalidFieldsAndDuplicateIdsRecoverWithoutDiscardingOriginal() throws Exception {
        Path file = directory.resolve("apps.json");
        String valid = "{\"id\":\"test\",\"name\":\"Test\",\"command\":[\"test.exe\"],"
                + "\"look\":\"minecraft:paper\",\"pinned\":true}";
        for (String broken : List.of("[" + valid + "," + valid + "]",
                "[" + valid.replace("[\"test.exe\"]", "[]") + "]",
                "[" + valid.replace("true", "\"true\"") + "]",
                "[" + valid.replace("minecraft:paper", "other:paper") + "]",
                "[" + valid.replace("\"name\":\"Test\",", "") + "]")) {
            Files.writeString(file, broken);
            var result = AppsConfig.load(file);
            assertEquals(AppsConfig.defaults(), result.apps());
            assertEquals(broken, Files.readString(result.brokenBackup()));
        }
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
