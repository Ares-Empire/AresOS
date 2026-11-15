package dev.aresos.catalogue;

import com.google.gson.*;
import dev.aresos.config.*;
import org.junit.jupiter.api.condition.EnabledOnOs;
import org.junit.jupiter.api.condition.OS;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;
import static dev.aresos.catalogue.WindowsCatalogueFixesTest.*;

class WindowsCatalogueIdentityTest {
    @TempDir Path directory;

    @Test @EnabledOnOs(value = OS.WINDOWS, disabledReason = WindowsOnly.WINDOWS_PATHS)
    void migratedDefaultNotepadReconcilesStoreAndShortcutWithoutChangingOwnerFields() throws Exception {
        Path file = directory.resolve("apps.json"), cache = directory.resolve("cache");
        String legacy = """
                [{"id":"notepad","name":"Owner notes","command":["notepad.exe"],
                  "look":"minecraft:diamond","pinned":false,"icon":"owner-art.png","ownerExtra":{"keep":42}}]
                """;
        Files.writeString(file, legacy);
        var loaded = AppsConfig.load(file);
        assertEquals(legacy, Files.readString(loaded.migrationBackup()));
        var ownerDocument = JsonParser.parseString(Files.readString(file));
        var store = new JsonObject(); store.addProperty("kind", "uwp");
        store.addProperty("key", "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"); store.addProperty("name", "Notepad");
        var shortcut = shortcut("Editor.lnk", "C:\\Windows\\System32\\notepad.exe", List.of(), "");
        // Store alone reproduces 07b; both discovery orders also need to reconcile every alias.
        for (var records : List.of(rows(store), rows(shortcut, store), rows(store, shortcut))) {
            var configured = AppsConfig.load(file).apps();
            var found = new WindowsAppCatalogue(cache, configured).decodeConfigured(records, cache);
            var merged = AppsConfig.merge(file, found);
            assertEquals(1, merged.size(), "Known Notepad alias duplicated migrated default");
            assertEquals(loaded.apps(), merged, "Discovery changed owner Notepad fields");
            assertEquals(ownerDocument, JsonParser.parseString(Files.readString(file)), "Unknown owner fields changed");
        }
    }

    @Test @EnabledOnOs(value = OS.WINDOWS, disabledReason = WindowsOnly.POWERSHELL)
    void nativeCmdShortcutsWithDifferentRawQuotingRemainTwoApps() throws Exception {
        Path menu = directory.resolve("menu"), cache = directory.resolve("cache"), config = directory.resolve("apps.json");
        Files.createDirectories(menu);
        String setup = "$s=New-Object -ComObject WScript.Shell;";
        for (var fixture : Map.of("Quoted", "/d /c echo \"one&ver\"", "Unquoted", "/d /c echo one&ver").entrySet()) {
            setup += "$l=$s.CreateShortcut('" + menu.resolve(fixture.getKey() + ".lnk").toAbsolutePath().toString().replace("'", "''")
                    + "');$l.TargetPath=Join-Path $env:SystemRoot 'System32\\cmd.exe';$l.Arguments='" + fixture.getValue() + "';$l.Save();";
        }
        var process = new ProcessBuilder("powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                Base64.getEncoder().encodeToString(setup.getBytes(StandardCharsets.UTF_16LE))).redirectErrorStream(true).start();
        assertTrue(process.waitFor(20, TimeUnit.SECONDS));
        assertEquals(0, process.exitValue(), new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
        var found = new WindowsAppCatalogue(cache, List.of(menu), new JsonArray()).listApps();
        assertEquals(2, found.size(), "Raw cmd quoting silently dropped a distinct shortcut");
        assertNotEquals(found.get(0).id(), found.get(1).id());
        assertEquals(found.get(0).launchIdentity().arguments(), found.get(1).launchIdentity().arguments(),
                "Fixture must demonstrate equal parsed argv despite different raw command lines");
        assertEquals(Set.of("/d /c echo \"one&ver\"", "/d /c echo one&ver"),
                found.stream().map(app -> app.launchIdentity().rawArguments()).collect(java.util.stream.Collectors.toSet()));
        AppsConfig.save(config, found);
        var reloaded = AppsConfig.load(config).apps();
        var rediscovered = new WindowsAppCatalogue(cache, reloaded, List.of(menu), new JsonArray()).listApps();
        assertEquals(reloaded, AppsConfig.merge(config, rediscovered), "Reload changed or duplicated shortcut IDs");
    }

    @Test void repurposedNotepadEntriesNeverAbsorbKnownAliases() throws Exception {
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        var store = new JsonObject(); store.addProperty("kind", "uwp");
        store.addProperty("key", "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"); store.addProperty("name", "Notepad");
        var stale = new WindowsLaunchIdentity("", List.of(), "", store.get("key").getAsString(), "");
        for (var owner : List.of(
                new AppDefinition("notepad", "Repurposed", List.of("other.exe"), "minecraft:diamond", true),
                new AppDefinition("notepad", "Document", List.of("notepad.exe", "owner.txt"), "minecraft:diamond", false),
                new AppDefinition("notepad", "Custom executable", List.of("C:\\Tools\\notepad.exe"), "minecraft:book", true),
                new AppDefinition("notepad", "Website", List.of(), "minecraft:paper", false, "url", "https://example.test", null),
                new AppDefinition("notepad", "Changed shortcut", List.of("explorer.exe", "C:\\Menu\\Changed.lnk"),
                        "minecraft:book", true, "command", null, "owner.png", stale))) {
            AppsConfig.save(config, List.of(owner));
            var found = new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(rows(store), cache);
            var merged = AppsConfig.merge(config, found);
            assertEquals(2, merged.size(), "Repurposed Notepad swallowed Store launch: " + owner.command());
            assertEquals(owner, merged.getFirst());
            assertNotEquals("notepad", merged.get(1).id());
        }
    }

    @Test void ambiguousConfiguredArgvKeepsBothRawLaunchesAndDiagnoses() throws Exception {
        var owner = new AppDefinition("owner", "Owner", List.of("C:\\Tools\\app.exe", "one&ver"), "minecraft:diamond", true);
        var quoted = shortcut("Quoted.lnk", owner.command().getFirst(), List.of("one&ver"), "");
        var unquoted = quoted.deepCopy(); unquoted.addProperty("key", "Unquoted.lnk");
        unquoted.addProperty("launch", "C:\\FixtureMenu\\Unquoted.lnk"); unquoted.addProperty("arguments", "one&ver");
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        AppsConfig.save(config, List.of(owner));
        var catalogue = new WindowsAppCatalogue(cache, List.of(owner));
        var merged = AppsConfig.merge(config, catalogue.decodeConfigured(rows(quoted, unquoted), cache));
        assertEquals(3, merged.size(), "Ambiguous parsed argv absorbed distinct raw launches");
        assertEquals(owner, merged.getFirst());
        assertTrue(catalogue.diagnostics().stream().anyMatch(message -> message.contains("Ambiguous raw") && message.contains("owner")));
    }

    @Test void legacyMetadataWithoutRawArgumentsCannotGuessAnAlias() throws Exception {
        var alias = shortcut("New.lnk", "C:\\Tools\\app.exe", List.of("one&ver"), "");
        var identity = new WindowsLaunchIdentity("C:\\Tools\\app.exe", List.of("one&ver"), "", "");
        var owner = new AppDefinition("owner", "Owner", List.of("explorer.exe", "C:\\Menu\\Gone.lnk"),
                "minecraft:diamond", true, "command", null, null, identity);
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        AppsConfig.save(config, List.of(owner));
        var reloaded = AppsConfig.load(config).apps();
        assertEquals(List.of(owner), reloaded, "07b metadata must remain readable");
        var catalogue = new WindowsAppCatalogue(cache, reloaded);
        assertEquals(2, AppsConfig.merge(config, catalogue.decodeConfigured(rows(alias), cache)).size());
        assertTrue(catalogue.diagnostics().stream().anyMatch(message -> message.contains("Ambiguous raw") && message.contains("owner")));
    }

    @Test void oneParsedShellCandidateIsStillInsufficientToProveEquivalence() throws Exception {
        var owner = new AppDefinition("owner", "Owner", List.of("C:\\Windows\\System32\\cmd.exe", "/d", "/c", "echo", "one&ver"), "minecraft:book", true);
        var row = shortcut("Quoted.lnk", owner.command().getFirst(), owner.command().subList(1, 5), "");
        row.addProperty("arguments", "/d /c echo \"one&ver\"");
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        AppsConfig.save(config, List.of(owner));
        var catalogue = new WindowsAppCatalogue(cache, List.of(owner));
        assertEquals(2, AppsConfig.merge(config, catalogue.decodeConfigured(rows(row), cache)).size());
        assertFalse(catalogue.diagnostics().isEmpty());
    }

    @Test void savedRawIdentitySelectsOnlyItsAliasAfterOriginalDisappears() throws Exception {
        Path config = directory.resolve("apps.json"), cache = directory.resolve("cache");
        var original = shortcut("Original.lnk", "C:\\Windows\\System32\\cmd.exe", List.of("/d", "/c", "echo", "one&ver"), "");
        original.addProperty("arguments", "/d /c echo \"one&ver\"");
        var owner = WindowsAppCatalogue.decode(rows(original), cache).getFirst().withPinned(true);
        AppsConfig.save(config, List.of(owner));
        var alias = original.deepCopy(); alias.addProperty("key", "Alias.lnk"); alias.addProperty("launch", "C:\\Menu\\Alias.lnk");
        var other = original.deepCopy(); other.addProperty("key", "Other.lnk"); other.addProperty("launch", "C:\\Menu\\Other.lnk");
        other.addProperty("arguments", "/d /c echo one&ver");
        var loaded = AppsConfig.load(config).apps();
        var found = new WindowsAppCatalogue(cache, loaded).decodeConfigured(rows(other, alias), cache);
        var merged = AppsConfig.merge(config, found);
        assertEquals(2, merged.size(), "Saved raw identity lost or duplicated a launch");
        assertEquals(owner, merged.getFirst(), "Original ID/command changed after alias removal");
        assertEquals("/d /c echo one&ver", merged.get(1).launchIdentity().rawArguments());
    }
}
