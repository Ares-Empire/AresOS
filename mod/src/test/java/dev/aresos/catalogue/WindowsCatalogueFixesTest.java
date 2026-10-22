package dev.aresos.catalogue;

import com.google.gson.*;
import dev.aresos.config.*;
import dev.aresos.icon.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class WindowsCatalogueFixesTest {
    @TempDir Path directory;

    @Test void earlierAliasKeepsExistingIdAndOwnerCommand() throws Exception {
        Path cache = directory.resolve("aresos-runtime/discovery"), file = directory.resolve("apps.json");
        var b = shortcut("B.lnk", "C:\\Tools\\notes.exe", List.of("a file.txt"), "");
        var first = WindowsAppCatalogue.decode(rows(b), cache);
        // Exercise the package-07 config without identity metadata, too.
        var old = first.getFirst();
        var owner = new AppDefinition(old.id(), "Owner name", old.command(), "minecraft:diamond", true);
        AppsConfig.save(file, List.of(owner));
        var a = shortcut("A.lnk", "C:\\Tools\\notes.exe", List.of("a file.txt"), "");
        var found = new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(rows(a, b), cache);
        var merged = AppsConfig.merge(file, found);
        assertEquals(List.of(owner.id()), merged.stream().map(AppDefinition::id).toList(), "Earlier alias duplicated a known app");
        assertEquals(owner.command(), merged.getFirst().command());
        assertEquals(owner.name(), merged.getFirst().name());
        assertEquals(owner.look(), merged.getFirst().look()); assertTrue(merged.getFirst().pinned());
        // Once reconciled, identity must survive even if the old shortcut disappears.
        var reloaded = AppsConfig.load(file).apps();
        var renamed = new WindowsAppCatalogue(cache, reloaded).decodeConfigured(rows(a), cache);
        assertEquals(1, AppsConfig.merge(file, renamed).size());
    }

    @Test void configuredCommandWithArgumentsRetainsOwnerArgv() throws Exception {
        var owner = new AppDefinition("owner-notes", "Owner", List.of("C:\\Tools\\notes.exe", "a file.txt", "--literal=$value"), "minecraft:book", true);
        var row = shortcut("Notes.lnk", "c:\\tools\\NOTES.exe", owner.command().subList(1, 3), "");
        Path cache = directory.resolve("cache"), file = directory.resolve("apps.json");
        AppsConfig.save(file, List.of(owner));
        var found = new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(rows(row), cache);
        var merged = AppsConfig.merge(file, found);
        assertEquals(1, merged.size(), "Configured argv was duplicated");
        assertEquals(owner, merged.getFirst());
    }

    @Test void identicalTargetAndArgumentsWithDifferentDirectoriesRemainTwoApps() throws Exception {
        var a = shortcut("A.lnk", "C:\\Tools\\python.exe", List.of("app.py"), "C:\\Projects\\A");
        var b = shortcut("B.lnk", "C:\\Tools\\python.exe", List.of("app.py"), "C:\\Projects\\B");
        var apps = WindowsAppCatalogue.decode(rows(a, b), directory.resolve("cache"));
        assertEquals(2, apps.size(), "Working directory silently dropped an app");
        assertNotEquals(apps.get(0).id(), apps.get(1).id());
    }

    @Test void failedConfiguredExtractionInvalidatesOwnedSourceAndGeneratedModel() throws Exception {
        Path cache = directory.resolve("aresos-runtime/discovery"), file = directory.resolve("apps.json"), pack = directory.resolve("pack");
        var owner = new AppDefinition("notes", "Notes", List.of("missing-fixture.exe"), "minecraft:book", true);
        AppsConfig.save(file, List.of(owner));
        var row = new JsonObject(); row.addProperty("kind", "configured"); row.addProperty("key", owner.id());
        row.addProperty("icon", Base64.getEncoder().encodeToString(getClass().getResourceAsStream("/icons/compass.png").readAllBytes()));
        var good = AppsConfig.merge(file, new WindowsAppCatalogue(cache, List.of(owner)).decodeConfigured(rows(row), cache));
        assertEquals(Set.of("notes"), IconPack.generate(pack, good, new PixelIconConverter()));
        Path source = Path.of(good.getFirst().icon()); assertTrue(Files.exists(source));
        row.add("icon", JsonNull.INSTANCE);
        var bad = AppsConfig.merge(file, new WindowsAppCatalogue(cache, good).decodeConfigured(rows(row), cache));
        assertNull(bad.getFirst().icon(), "Failed refresh retained configured cache path");
        assertFalse(Files.exists(source), "Failed refresh retained generated source");
        assertTrue(IconPack.generate(pack, bad, new PixelIconConverter()).isEmpty());
        assertFalse(Files.exists(pack.resolve("assets/aresos/items/apps/notes.json")));
        assertFalse(Files.exists(pack.resolve("assets/aresos/textures/item/apps/notes.png")));
        var custom = new AppDefinition("notes", "Custom", owner.command(), owner.look(), true, "command", null, "owner-art.png");
        AppsConfig.save(file, List.of(custom));
        var customResult = new WindowsAppCatalogue(cache, List.of(custom)).decodeConfigured(rows(row), cache);
        assertEquals("owner-art.png", AppsConfig.merge(file, customResult).getFirst().icon());
    }

    @Test void ambiguousConfiguredMatchesKeepEveryOwnerEntryAndDiagnose() throws Exception {
        var a = new AppDefinition("owner-a", "A", List.of("C:\\Tools\\app.exe", "--work"), "minecraft:book", true);
        var b = new AppDefinition("owner-b", "B", a.command(), "minecraft:diamond", false);
        Path cache = directory.resolve("cache"), file = directory.resolve("apps.json");
        AppsConfig.save(file, List.of(a, b));
        var catalogue = new WindowsAppCatalogue(cache, List.of(a, b));
        var found = catalogue.decodeConfigured(rows(shortcut("App.lnk", a.command().getFirst(), List.of("--work"), "")), cache);
        assertEquals(List.of(a, b), AppsConfig.merge(file, found));
        assertEquals(1, catalogue.diagnostics().size());
        assertTrue(catalogue.diagnostics().getFirst().contains("owner-a"));
        assertTrue(catalogue.diagnostics().getFirst().contains("owner-b"));
    }

    @Test void distinctAumidsAndSameNamedMenuEntriesAreNotDropped() throws Exception {
        var a = shortcut("App.lnk", "C:\\Tools\\app.exe", List.of(), "");
        var b = a.deepCopy(); b.addProperty("launch", "C:\\CommonMenu\\App.lnk"); b.addProperty("aumid", "Fixture!Other");
        var apps = WindowsAppCatalogue.decode(rows(a, b), directory.resolve("cache"));
        assertEquals(2, apps.size()); assertNotEquals(apps.get(0).id(), apps.get(1).id());
    }

    static JsonObject shortcut(String name, String target, List<String> arguments, String cwd) {
        var row = new JsonObject(); row.addProperty("kind", "shortcut"); row.addProperty("key", name); row.addProperty("name", name);
        row.addProperty("launch", "C:\\FixtureMenu\\" + name); row.addProperty("target", target);
        row.addProperty("arguments", String.join(" ", arguments.stream().map(s -> "\"" + s.replace("\"", "\\\"") + "\"").toList()));
        row.add("argv", new Gson().toJsonTree(arguments)); row.addProperty("workingDirectory", cwd); row.addProperty("aumid", "");
        return row;
    }
    static JsonArray rows(JsonObject... rows) { var array = new JsonArray(); for (var row : rows) array.add(row); return array; }
}
