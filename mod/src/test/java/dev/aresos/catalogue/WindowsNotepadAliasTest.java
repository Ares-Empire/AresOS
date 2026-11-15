package dev.aresos.catalogue;

import com.google.gson.*;
import dev.aresos.config.*;
import org.junit.jupiter.api.condition.EnabledOnOs;
import org.junit.jupiter.api.condition.OS;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static dev.aresos.catalogue.WindowsCatalogueFixesTest.*;

class WindowsNotepadAliasTest {
    @TempDir Path directory;

    @Test void defaultNotepadAndStoreNeverAbsorbUnrelatedNotepadExecutable() throws Exception {
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        String document = """
                {"schemaVersion":2,"ownerDocument":"keep","apps":[
                  {"id":"notepad","name":"Owner notes","command":["notepad.exe"],
                   "look":"minecraft:diamond","pinned":true,"icon":"owner-art.png","ownerExtra":{"keep":42}}]}
                """;
        // Loading moves the file to schema 3, which adds "mine" (true: pinned, and a starter) and nothing else.
        var ownerJson = JsonParser.parseString(document).getAsJsonObject().getAsJsonArray("apps").get(0).getAsJsonObject();
        ownerJson.addProperty("mine", true);
        var unrelated = shortcut("Tools Notepad.lnk", "C:\\Tools\\notepad.exe", List.of(), "");
        for (var records : List.of(rows(store(), unrelated), rows(unrelated, store()))) {
            Files.writeString(config, document);
            var owner = AppsConfig.load(config).apps().getFirst();
            var merged = AppsConfig.merge(config, new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(records, cache));
            assertEquals(2, merged.size(), "Unrelated C:\\Tools\\notepad.exe was swallowed by the Notepad alias");
            assertEquals(owner, merged.getFirst(), "Owner Notepad fields changed");
            var tools = merged.get(1);
            assertNotEquals("notepad", tools.id());
            assertEquals(List.of("explorer.exe", unrelated.get("launch").getAsString()), tools.command());
            assertEquals("c:/tools/notepad.exe", tools.launchIdentity().target());
            assertFalse(tools.pinned());
            var rediscovered = new WindowsAppCatalogue(cache, AppsConfig.load(config).apps())
                    .decodeConfigured(rows(unrelated, store()), cache);
            assertEquals(merged, AppsConfig.merge(config, rediscovered), "Rediscovery changed fields or IDs");
            var saved = JsonParser.parseString(Files.readString(config)).getAsJsonObject();
            assertEquals(ownerJson, saved.getAsJsonArray("apps").get(0), "Unknown owner fields changed");
            assertEquals("keep", saved.get("ownerDocument").getAsString());
        }
    }

    @Test @EnabledOnOs(value = OS.WINDOWS, disabledReason = WindowsOnly.WINDOWS_PATHS)
    void knownWindowsPathsResolveVariablesCaseAndDotSegments() throws Exception {
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        String windows = System.getenv().getOrDefault("WINDIR", "C:\\Windows");
        for (String target : List.of(windows + "\\notepad.exe", windows + "\\System32\\NOTEPAD.EXE",
                windows + "\\SysWOW64\\notepad.exe", "%windir%\\notepad.exe",
                "%WiNdIr%\\System32\\.\\NOTEPAD.EXE", "%WINDIR%\\SysWOW64\\notepad.exe",
                "%SystemRoot%\\System32\\..\\notepad.exe")) {
            var shortcut = shortcut("Windows Editor.lnk", target, List.of(), "");
            assertEquals("notepad", WindowsAppCatalogue.decode(rows(shortcut), cache).getFirst().id(), target);
            var owner = new AppDefinition("notepad", "Owner notes", List.of(target), "minecraft:diamond", true);
            AppsConfig.save(config, List.of(owner));
            var found = new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(rows(store(), shortcut), cache);
            assertEquals(List.of(owner), AppsConfig.merge(config, found), "Known Windows path did not reconcile: " + target);
        }
    }

    @Test void otherPathsAndLaunchModifiersStaySeparate() throws Exception {
        Path cache = directory.resolve("cache");
        for (String target : List.of("C:\\Tools\\notepad.exe", "%WINDIR%\\Tools\\notepad.exe",
                "%WINDIR%\\System32\\..\\Tools\\notepad.exe", "C:\\OtherWindows\\System32\\notepad.exe",
                "System32\\notepad.exe", "notepad.exe", "%ARESOS_UNKNOWN_NOTEPAD_ROOT%\\notepad.exe",
                "C:\\Invalid<path\\notepad.exe")) {
            var apps = WindowsAppCatalogue.decode(rows(store(), shortcut("Other.lnk", target, List.of(), "")), cache);
            assertEquals(2, apps.size(), "Unknown path treated as Windows Notepad: " + target);
            assertEquals(1, apps.stream().filter(app -> app.id().equals("notepad")).count());
        }
        for (var modified : List.of(shortcut("Document.lnk", "%WINDIR%\\notepad.exe", List.of("owner.txt"), ""),
                shortcut("Working Directory.lnk", "%WINDIR%\\notepad.exe", List.of(), "C:\\Tools"))) {
            assertEquals(2, WindowsAppCatalogue.decode(rows(store(), modified), cache).size());
        }
    }

    private static JsonObject store() {
        var row = new JsonObject(); row.addProperty("kind", "uwp");
        row.addProperty("key", "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"); row.addProperty("name", "Notepad");
        return row;
    }
}
