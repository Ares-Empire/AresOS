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
        assertEquals(List.of(twin), OpenPrograms.find(apps, "second-browser", Set.of()));
        assertEquals(List.of(), OpenPrograms.find(apps, "unknown", Set.of()));
        assertEquals(List.of(), OpenPrograms.find(apps, "!!!", Set.of()));
    }
}
