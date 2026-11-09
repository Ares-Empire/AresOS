package dev.aresos.catalogue;

import com.google.gson.*;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;

class WindowsCatalogueTest {
    @TempDir Path directory;
    @Test void fixtureStartMenusAndUwpProduceStableUnpinnedAppsAndRealIcons() throws Exception {
        Path user=directory.resolve("user"),common=directory.resolve("common");
        Files.createDirectories(user);Files.createDirectories(common);
        Path icon=directory.resolve("compass.ico");Files.copy(getClass().getResourceAsStream("/icons/compass.ico"),icon);
        Path targets=directory.resolve("targets"); Files.createDirectories(targets);
        Files.writeString(targets.resolve("notes.exe"),"fixture only, never executable");
        String setup="$s=New-Object -ComObject WScript.Shell;";
        for(Path root:List.of(user,common)) setup+="$l=$s.CreateShortcut('"+quote(root.resolve("Fixture Notes.lnk"))+"');$l.TargetPath='"+quote(targets.resolve("notes.exe"))+"';$l.IconLocation='"+quote(icon)+",0';$l.Save();";
        setup+="$l=$s.CreateShortcut('"+quote(user.resolve("Editor.lnk"))+"');$l.TargetPath=Join-Path $env:WINDIR 'System32\\notepad.exe';$l.IconLocation='"+quote(icon)+",0';$l.Save();";
        var process=new ProcessBuilder("powershell.exe","-NoProfile","-NonInteractive","-EncodedCommand",
                Base64.getEncoder().encodeToString(setup.getBytes(java.nio.charset.StandardCharsets.UTF_16LE))).redirectErrorStream(true).start();
        assertTrue(process.waitFor(20,TimeUnit.SECONDS));assertEquals(0,process.exitValue(),new String(process.getInputStream().readAllBytes()));
        var uwp=new JsonArray();var row=new JsonObject();row.addProperty("kind","uwp");row.addProperty("key","AresFixture_abc!App");row.addProperty("name","Fixture Store App");
        row.addProperty("icon",Base64.getEncoder().encodeToString(getClass().getResourceAsStream("/icons/sunset.png").readAllBytes()));uwp.add(row);
        var catalogue=new WindowsAppCatalogue(directory.resolve("cache"),List.of(user,common),uwp);
        var apps=catalogue.listApps();
        assertEquals(3,apps.size());assertTrue(apps.stream().noneMatch(AppDefinition::pinned));
        assertTrue(apps.stream().anyMatch(app->app.id().equals("notepad")));
        var store=apps.stream().filter(app->app.name().equals("Fixture Store App")).findFirst().orElseThrow();
        assertEquals(List.of("explorer.exe","shell:AppsFolder\\AresFixture_abc!App"),store.command());
        for(var app:apps) assertNotNull(javax.imageio.ImageIO.read(Path.of(app.icon()).toFile()));
        row.addProperty("name","Renamed Fixture Store App");
        assertEquals(apps.stream().map(AppDefinition::id).toList(),catalogue.listApps().stream().map(AppDefinition::id).toList());
    }
    /** Package 24: without a helper connection the Linux catalogue fails closed instead of returning apps. */
    @Test void linuxCatalogueWithoutAHelperFailsClosed() {
        var error = assertThrows(java.io.IOException.class, () -> new LinuxAppCatalogue().listApps());
        assertTrue(error.getMessage().contains("aresos-shell/1.0")); assertEquals("aresos-shell/1.0",LinuxAppCatalogue.PROTOCOL);
    }
    @Test void nativeShortcutIdentityIncludesArgvAndWorkingDirectory() throws Exception {
        Path root = directory.resolve("menu"), a = directory.resolve("project-a"), b = directory.resolve("project-b");
        Files.createDirectories(root); Files.createDirectories(a); Files.createDirectories(b);
        Path target = directory.resolve("python.exe"); Files.writeString(target, "fixture only, never executed");
        String setup = "$s=New-Object -ComObject WScript.Shell;";
        for (var pair : Map.of("A", a, "B", b).entrySet()) {
            setup += "$l=$s.CreateShortcut('" + quote(root.resolve(pair.getKey() + ".lnk")) + "');$l.TargetPath='" + quote(target)
                    + "';$l.Arguments='app.py \"two words\" --literal=$value';$l.WorkingDirectory='" + quote(pair.getValue()) + "';$l.Save();";
        }
        setup += "$l=$s.CreateShortcut('" + quote(root.resolve("Direct.lnk")) + "');$l.TargetPath='" + quote(target)
                + "';$l.Arguments='app.py \"two words\" --literal=$value';$l.Save();";
        powershell(setup);
        var owner = new AppDefinition("owner", "Owner command", List.of(target.toString(), "app.py", "two words", "--literal=$value"), "minecraft:diamond", true);
        Path cache = directory.resolve("aresos-runtime/discovery"), config = directory.resolve("apps.json");
        AppsConfig.save(config, List.of(owner));
        var apps = AppsConfig.merge(config, new WindowsAppCatalogue(cache, List.of(owner), List.of(root), new JsonArray()).listApps());
        assertEquals(3, apps.size(), "Native discovery lost working directories or duplicated configured argv");
        assertEquals(owner.command(), apps.getFirst().command()); assertTrue(apps.getFirst().pinned());
        var discovered = apps.stream().filter(app -> !app.id().equals("owner")).toList();
        assertEquals(Set.of(a.toString().replace('\\', '/').toLowerCase(Locale.ROOT), b.toString().replace('\\', '/').toLowerCase(Locale.ROOT)),
                discovered.stream().map(app -> app.launchIdentity().workingDirectory()).collect(java.util.stream.Collectors.toSet()));
        assertTrue(discovered.stream().allMatch(app -> app.launchIdentity().arguments().equals(owner.command().subList(1, 4))));
    }
    @Test void nativeMissingIconSourceClearsPreviousExtraction() throws Exception {
        Path source = directory.resolve("fixture.ico"), root = directory.resolve("empty-menu"), cache = directory.resolve("aresos-runtime/discovery");
        Files.copy(getClass().getResourceAsStream("/icons/compass.ico"), source); Files.createDirectories(root);
        var owner = new AppDefinition("icon-fixture", "Icon fixture", List.of(source.toString()), "minecraft:book", false);
        Path config = directory.resolve("apps.json"); AppsConfig.save(config, List.of(owner));
        var good = AppsConfig.merge(config, new WindowsAppCatalogue(cache, List.of(owner), List.of(root), new JsonArray()).listApps());
        assertNotNull(good.getFirst().icon()); Path extracted = Path.of(good.getFirst().icon()); assertTrue(Files.exists(extracted));
        Files.delete(source);
        var bad = AppsConfig.merge(config, new WindowsAppCatalogue(cache, good, List.of(root), new JsonArray()).listApps());
        assertNull(bad.getFirst().icon()); assertFalse(Files.exists(extracted));
    }
    private static void powershell(String script) throws Exception {
        var process = new ProcessBuilder("powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                Base64.getEncoder().encodeToString(script.getBytes(java.nio.charset.StandardCharsets.UTF_16LE))).redirectErrorStream(true).start();
        assertTrue(process.waitFor(20, TimeUnit.SECONDS)); assertEquals(0, process.exitValue(), new String(process.getInputStream().readAllBytes()));
    }
    private static String quote(Path path){return path.toAbsolutePath().toString().replace("'","''");}
}
