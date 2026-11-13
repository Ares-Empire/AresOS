package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.SystemInfo;
import dev.aresos.shell.ShellClient;
import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.*;

class AppGroupTest {
    private static ShellClient.App app(String id, List<String> categories) {
        return new ShellClient.App(id, id, true, null, new SystemInfo("system", null, categories, null, null, null, null, null));
    }

    @Test void theFirstRuleThatFitsWinsAndTheStartersAreFixed() {
        assertEquals(AppGroup.GAMES, AppGroup.of("steam", List.of("Network", "FileTransfer", "Game")));
        assertEquals(AppGroup.INTERNET, AppGroup.of("discord", List.of("Network", "InstantMessaging")));
        assertEquals(AppGroup.INTERNET, AppGroup.of("mail", List.of("Office", "Network", "Email")));
        for (String category : List.of("Office", "Development", "Education", "Science", "Graphics", "AudioVideo", "Audio", "Video"))
            assertEquals(AppGroup.WORK_MEDIA, AppGroup.of("some", List.of("Qt", category)), category);
        for (var rest : List.of(List.of("System", "FileManager"), List.of("Settings"), List.of("Utility"), List.<String>of()))
            assertEquals(AppGroup.SYSTEM_TOOLS, AppGroup.of("some", rest), rest.toString());
        assertEquals(AppGroup.SYSTEM_TOOLS, AppGroup.of("some", null));
        assertEquals(AppGroup.INTERNET, AppGroup.of("browser", List.of("Game")));
        assertEquals(AppGroup.SYSTEM_TOOLS, AppGroup.of("terminal", List.of("Network")));
        assertEquals(AppGroup.SYSTEM_TOOLS, AppGroup.of("notepad", List.of("Office")));
        var okular = new AppDefinition("okular", "Okular", List.of(), "minecraft:paper", false, "helper", null, null)
                .withSystem(new SystemInfo("flatpak-system", null, List.of("Office", "Viewer"), null, null, null, null, null));
        assertEquals(AppGroup.WORK_MEDIA, AppGroup.of(okular));
        assertEquals(AppGroup.SYSTEM_TOOLS, AppGroup.of(okular.withSystem(null)));
    }

    @Test void anAppWithoutAPictureLooksLikeItsGroupAndTheStartersKeepTheirLooks() {
        var definitions = LinuxAppCatalogue.definitions(List.of(app("browser", List.of("Network")), app("terminal", null),
                app("notepad", List.of("Utility")), app("steam", List.of("Network", "Game")), app("discord", List.of("Network")),
                app("okular", List.of("Office")), app("dolphin", List.of("System")), app("bare", null), app("empty", List.of()),
                new ShellClient.App("old-helper", "Old helper", true, null)));
        assertEquals(List.of("minecraft:compass", "minecraft:command_block", "minecraft:writable_book",
                "minecraft:diamond_sword", "minecraft:ender_pearl", "minecraft:painting", "minecraft:iron_pickaxe",
                "minecraft:paper", "minecraft:paper", "minecraft:paper"), definitions.stream().map(AppDefinition::look).toList());
        for (var group : AppGroup.values()) assertTrue(group.look().matches("minecraft:[a-z_]+"), group.title());
        assertNull(definitions.getLast().system());
        assertEquals("system", definitions.get(3).system().source());
    }

    /** One table: the rule above, and the avenue, letter, concrete and colour of HUB.md 3.2 reached from its result. */
    @Test void everythingAboutAGroupIsReachedFromTheAppsGroup() {
        var steam = AppGroup.of("steam", List.of("Network", "Game"));
        assertEquals('E', steam.letter());
        assertEquals("minecraft:red_concrete", steam.concrete());
        assertEquals(0xFF6257, steam.colour());
        assertEquals(List.of(0x3AB3DA, 0xFF6257, 0xFED83D, 0xC774F2), AppGroup.clockwise().stream().map(AppGroup::colour).toList());
        // The pad builds its avenues and names clockwise from the one straight ahead.
        assertEquals(List.of(AppGroup.INTERNET, AppGroup.GAMES, AppGroup.SYSTEM_TOOLS, AppGroup.WORK_MEDIA), AppGroup.clockwise());
        for (var group : AppGroup.values()) {
            assertEquals(Optional.of(group), AppGroup.ofLetter(group.letter()));
            assertEquals(group.outward().getClockWise(), group.right());
        }
        assertEquals(Optional.empty(), AppGroup.ofLetter('n'));
        assertEquals(Optional.empty(), AppGroup.ofLetter('X'));
    }
}
