package dev.aresos.names;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class NameRulesTest {
    private static final Set<String> VANILLA = Set.of("help", "list", "time");
    private static NameRules.Program app(String id, String name, String desktop, String exec) {
        return new NameRules.Program(id, name, exec, desktop, null);
    }

    @ParameterizedTest(name = "{1} → {4}")
    @CsvSource(delimiter = '|', textBlock = """
        browser|Chrome||google-chrome|chrome,browser
        terminal|Terminal||foot|terminal,term
        notepad|Notepad||kwrite|notepad
        discord|Discord|com.discordapp.Discord|flatpak|discord,dc
        lunarclient|Lunar Client|lunarclient|LunarClient.AppImage|lunar
        steam|Steam|steam|bazzite-steam|steam
        steambpm|Steam Big Picture Mode|bazzite-steam-bpm|bazzite-steam-bpm|steambpm
        lutris|Lutris|net.lutris.Lutris|lutris|lutris
        protonplus|ProtonPlus|com.vysp3r.ProtonPlus|flatpak|protonplus
        firefox|Firefox|org.mozilla.firefox|flatpak|firefox,ff
        connect|KDE Connect|org.kde.kdeconnect.app|kdeconnect-app|connect
        krdc|KRDC|org.kde.krdc|krdc|krdc
        kate|Kate|org.kde.kate|kate|kate
        okular|Okular|org.kde.okular|flatpak|okular
        gwenview|Gwenview|org.kde.gwenview|flatpak|gwenview
        haruna|Haruna|org.kde.haruna|flatpak|haruna
        dolphin|Dolphin|org.kde.dolphin|dolphin|dolphin,files
        konsole|Konsole|org.kde.konsole|konsole|konsole
        kwrite|KWrite|org.kde.kwrite|kwrite|kwrite
        kcalc|KCalc|org.kde.kcalc|flatpak|kcalc
        spectacle|Spectacle|org.kde.spectacle|spectacle|spectacle
        disks|Disks|org.gnome.DiskUtility|gnome-disks|disks
        settings|KDE System Settings|kdesystemsettings|systemsettings|settings
        monitor|System Monitor|org.kde.plasma-systemmonitor|plasma-systemmonitor|monitor
        bbrew|Bold Brew|bbrew|xdg-terminal-exec|bbrew
        btrfs|Btrfs Assistant|btrfs-assistant|btrfs-assistant-launcher|btrfs
        helpcenter|Help Center|org.kde.khelpcenter|khelpcenter|khelpcenter
        code|Visual Studio Code|com.visualstudio.code|code|code,vscode
        telegram|Telegram Desktop|org.telegram.desktop|flatpak|telegram,tg
        obs|OBS Studio|com.obsproject.Studio|obs|obs
        vlc|VLC media player|org.videolan.VLC|vlc|vlc
        gimp|GNU Image Manipulation Program|org.gimp.GIMP|gimp|gimp
        heroic|Heroic Games Launcher|com.heroicgameslauncher.hgl|heroic|heroic
        yelp|Help|org.gnome.Yelp|yelp|yelp
        input|Input Remapper|input-remapper|input-remapper|input
        indicator|KDE Connect Indicator|org.kde.kdeconnect.nonplasma|kdeconnect-indicator|nonplasma
        force|Force Restart Waydroid|force-restart-waydroid|force-restart-waydroid|force
        """)
    void workedListAndFollowingExamples(String id, String name, String desktop, String exec, String expected) {
        assertEquals(List.of(expected.split(",")), NameRules.assign(app(id, name, desktop, exec), Set.of(), VANILLA));
    }

    @Test void wordAndExecutableCleaning() {
        assertEquals("cremebrulee42", NameRules.squeeze("Crème BRÛLÉE! 42"));
        assertEquals(List.of("lunar"), NameRules.words("The Google Lunar-Client [beta (64)] / 42"));
        assertEquals(List.of("browser", "editor"), NameRules.words("Browser Editor"));
        assertEquals("chrome", NameRules.cleanProgram("/usr/bin/google-chrome-stable"));
        assertEquals("foo", NameRules.cleanProgram("C:\\Apps\\bazzite-gnome-plasma-foo42.exe"));
        assertEquals("gimp", NameRules.cleanDesktop("org.gimp.GIMP.desktop"));
        assertEquals("orgtest", NameRules.cleanDesktop("org.test"));
        for (String wrapper : List.of("flatpak", "env", "sh", "bash", "python", "python3", "pkexec", "sudo",
                "xdg-open", "xdg-terminal-exec", "gtk-launch")) assertEquals("", NameRules.cleanProgram(wrapper));
        for (String suffix : List.of("appimage", "sh", "py", "bin", "exe", "x86_64"))
            assertEquals("lunarclient", NameRules.cleanProgram("LunarClient." + suffix));
        for (String suffix : List.of("stable", "bin", "gtk", "qt", "gui", "app", "launcher", "wrapper", "desktop", "client"))
            assertEquals("foo", NameRules.cleanProgram("foo-" + suffix));
    }

    @Test void validityAndReservation() {
        for (String bad : List.of("", "a", "1abc", "Upper", "has space", "x-y", "éé", "abcdefghijklmnopq"))
            assertFalse(NameRules.valid(bad), bad);
        assertTrue(NameRules.valid("a2")); assertTrue(NameRules.valid("abcdefghijklmnop"));
        for (String reserved : List.of("help", "list", "time", "aresos", "home", "go", "open", "apps")) {
            assertTrue(NameRules.reserved(reserved, VANILLA));
            assertFalse(NameRules.free(reserved, Set.of(), VANILLA));
            var p = app("test", reserved, "fallback", "fallback");
            assertEquals("fallback", NameRules.main(p, Set.of(), VANILLA));
        }
        assertFalse(NameRules.free("chat", Set.of("chat"), VANILLA));
        assertTrue(NameRules.free("chat", Set.of(), VANILLA));
    }

    @Test void clashesUseNextCandidateThenNumbers() {
        var steam = app("steam", "Steam", "steam", "steam");
        assertEquals("steam3", NameRules.main(steam, Set.of("steam", "steam2"), VANILLA));
        assertEquals("lunarclient", NameRules.main(app("lunar", "Lunar Client", "lunarclient", "LunarClient.AppImage"),
                Set.of("lunar"), VANILLA));
        assertEquals(List.of("discord"), NameRules.assign(app("discord", "Discord", "com.discordapp.Discord", "flatpak"),
                Set.of("dc"), VANILLA));
        assertEquals("abcdefghijklmn2", NameRules.main(app("test", "abcdefghijklmn", null, null),
                Set.of("abcdefghijklmn"), VANILLA));
        assertEquals("abcdefghijklmno2", NameRules.main(app("test", "abcdefghijklmnop", null, null),
                Set.of("abcdefghijklmnop"), VANILLA));
        assertEquals("app2", NameRules.main(app("test", "42", null, null), Set.of(), VANILLA));
    }

    @Test void startersFirstAndJoiningOrderNotAlphabetic() {
        var later = app("later", "Browser", null, null);
        var starter = app("browser", "Chrome", null, null);
        var first = app("first", "Same", null, null);
        var second = app("second", "Same", null, null);
        var order = NameRules.order(List.of(later, first, starter, second));
        assertEquals(List.of(starter, later, first, second), order);
        var held = new HashSet<String>();
        var assigned = new LinkedHashMap<String, List<String>>();
        for (var program : order) {
            var names = NameRules.assign(program, held, VANILLA);
            held.addAll(names); assigned.put(program.id(), names);
        }
        assertEquals(List.of("chrome", "browser"), assigned.get("browser"));
        assertEquals(List.of("browser2"), assigned.get("later"));
        assertEquals(List.of("same"), assigned.get("first"));
        assertEquals(List.of("same2"), assigned.get("second"));
    }

    @Test void tableMatchesAnyIdentityAndOnlyTheFirstRow() {
        assertEquals(List.of("strange", "dc"), NameRules.assign(
                new NameRules.Program("x", "Strange", "org.mozilla.firefox", null, "discord"), Set.of(), VANILLA));
        assertEquals(List.of("minecraft", "mc"), NameRules.assign(app("x", "Minecraft", null, "minecraft-launcher"), Set.of(), VANILLA));
        assertEquals(List.of("qbittorrent", "qbit"), NameRules.assign(app("x", "qBittorrent", "org.qbittorrent.qbittorrent", "flatpak"), Set.of(), VANILLA));
        assertEquals(List.of("thunderbird", "mail"), NameRules.assign(app("x", "Thunderbird", "org.mozilla.thunderbird", "flatpak"), Set.of(), VANILLA));
    }
}
