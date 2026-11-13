package dev.aresos.names;

import dev.aresos.config.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class SavedNamesTest {
    @TempDir Path temp;
    private AppDefinition app(String id, String name) {
        return new AppDefinition(id, name, List.of("fallback"), "minecraft:book", false).withMine(true);
    }

    @Test void namesSurviveRenameRemovalReturnAndUnknownFields() throws Exception {
        var file = temp.resolve("apps.json");
        AppsConfig.save(file, List.of(app("discord", "Discord"), app("other", "Discord")));
        var first = AppsConfig.assignNames(file, Set.of("help", "list", "time"));
        assertEquals(List.of("discord", "dc"), first.getFirst().names());
        assertEquals("fallback", first.getLast().names().getFirst());
        String saved = Files.readString(file).replace("\"name\": \"Discord\"", "\"name\": \"Renamed\"")
                .replace("\"schemaVersion\": 4", "\"future\": 42, \"schemaVersion\": 4");
        Files.writeString(file, saved);
        AppsConfig.mine(file, Map.of("discord", false));
        assertEquals(first.getFirst().names(), AppsConfig.assignNames(file, Set.of()).getFirst().names());
        AppsConfig.mine(file, Map.of("discord", true));
        assertEquals(first.getFirst().names(), AppsConfig.assignNames(file, Set.of()).getFirst().names());
        assertTrue(Files.readString(file).contains("\"future\": 42"));
        AppsConfig.name(file, "discord", "chat", Set.of());
        assertEquals(List.of("chat", "discord", "dc"), AppsConfig.load(file).apps().getFirst().names());
        assertThrows(java.io.IOException.class, () -> AppsConfig.name(file, "other", "chat", Set.of()));
        AppsConfig.unname(file, "chat");
        assertEquals(first.getFirst().names(), AppsConfig.load(file).apps().getFirst().names());
    }

    @Test void refusalsDoNotWriteAndRealCommandsDisplaceSavedNames() throws Exception {
        var file = temp.resolve("apps.json");
        AppsConfig.save(file, List.of(app("test", "Help").withNames(List.of("help", "chat")), app("other", "Other")));
        var assigned = AppsConfig.assignNames(file, Set.of("help"));
        assertEquals(List.of("fallback", "chat"), assigned.getFirst().names());
        String before = Files.readString(file);
        for (String name : List.of("X", "a", "1chat", "home", "help", "other"))
            assertThrows(java.io.IOException.class, () -> AppsConfig.name(file, "test", name, Set.of("help")));
        assertThrows(java.io.IOException.class, () -> AppsConfig.unname(file, "other"));
        assertThrows(java.io.IOException.class, () -> AppsConfig.unname(file, "missing"));
        assertThrows(java.io.IOException.class, () -> AppsConfig.name(file, "missing", "valid", Set.of()));
        assertEquals(before, Files.readString(file));
    }

    @Test void aDisplacedMainCanUseTheSameAppsExistingNextBestAlias() throws Exception {
        var file = temp.resolve("apps.json");
        AppsConfig.save(file, List.of(app("test", "Help").withNames(List.of("help", "fallback"))));
        assertEquals(List.of("fallback"), AppsConfig.assignNames(file, Set.of("help")).getFirst().names());
    }

    @Test void schemaThreeMigratesWithoutLosingFieldsAndNamesValidate() throws Exception {
        var file = temp.resolve("apps.json");
        String old = """
            {"schemaVersion":3,"baseline":"2026-11-13","future":true,"apps":[
            {"id":"discord","name":"Discord","command":["never"],"look":"minecraft:book","pinned":false,"mine":true,"extra":42}]}
            """;
        Files.writeString(file, old);
        var loaded = AppsConfig.load(file);
        assertEquals(old, Files.readString(loaded.migrationBackup()));
        assertEquals(List.of(), loaded.apps().getFirst().names());
        AppsConfig.assignNames(file, Set.of());
        assertTrue(Files.readString(file).contains("\"extra\": 42"));
        assertTrue(Files.readString(file).contains("\"future\": true"));
        assertThrows(IllegalArgumentException.class, () -> app("x", "X").withNames(List.of("bad-name")));
        assertThrows(IllegalArgumentException.class, () -> AppsConfig.save(file,
                List.of(app("x", "X").withNames(List.of("chat")), app("y", "Y").withNames(List.of("chat")))));
    }
}
