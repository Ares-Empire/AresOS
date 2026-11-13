package dev.aresos.names;

import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class OpenProgramsTest {
    private AppDefinition app(String id, String name) {
        return new AppDefinition(id, name, List.of("never"), "minecraft:book", false);
    }
    @Test void exactNamesPrefixesFullNamesAndIds() {
        var chrome = app("browser", "Google Chrome").withMine(true).withNames(List.of("chrome", "browser"));
        var chromium = app("chromium", "Chromium");
        var twin = app("second-browser", "Google Chrome");
        var apps = List.of(chrome, chromium, twin);
        assertEquals(List.of(chrome), OpenPrograms.find(apps, "chrome", Set.of()));
        assertEquals(List.of(chromium, chrome), OpenPrograms.find(apps, "ch", Set.of()));
        assertEquals(List.of(chrome, twin), OpenPrograms.find(apps, "Google Chrome", Set.of()));
        assertEquals(List.of(), OpenPrograms.find(apps, "unknown", Set.of()));
        assertEquals(List.of(), OpenPrograms.find(apps, "!!!", Set.of()));
    }

    /** Review 1, finding 3: an ID gets no precedence over names; HUB.md 4.4 alone decides. */
    @Test void idsAreNoKeys() {
        var editor = app("editor", "Editor");
        var other = app("texteditor", "Editor");
        assertEquals(List.of(editor, other), OpenPrograms.find(List.of(editor, other), "editor", Set.of()));
        var talk = app("chat", "Talk");
        var discord = app("discord", "Discord").withMine(true).withNames(List.of("chat", "discord", "dc"));
        assertEquals(List.of(discord), OpenPrograms.find(List.of(talk, discord), "chat", Set.of()));
        assertEquals(List.of(), OpenPrograms.find(List.of(app("second-browser", "Google Chrome")), "second-browser", Set.of()));
    }
}
