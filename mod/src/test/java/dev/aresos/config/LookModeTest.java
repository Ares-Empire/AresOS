package dev.aresos.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class LookModeTest {
    @TempDir Path dir;

    @Test void noFileNoLineOrAnEmptyValueIsClassic() throws IOException {
        Path file = dir.resolve("settings.properties");
        assertEquals(LookMode.CLASSIC, LookMode.read(file));
        Files.writeString(file, "# nothing set\nother = 1\n");
        assertEquals(LookMode.CLASSIC, LookMode.read(file));
        Files.writeString(file, "look =\n");
        assertEquals(LookMode.CLASSIC, LookMode.read(file));
    }

    @Test void theOwnersLineTurnsOnClickToLook() throws IOException {
        Path file = dir.resolve("settings.properties");
        for (String line : new String[] {"look = click", "look=click", "  look = Click  ", "look: CLICK"}) {
            Files.writeString(file, line + "\n");
            assertEquals(LookMode.CLICK, LookMode.read(file), line);
        }
        Files.writeString(file, "look = classic\n");
        assertEquals(LookMode.CLASSIC, LookMode.read(file));
    }

    @Test void anUnknownValueIsRefusedWithTheKnownOnes() throws IOException {
        Path file = dir.resolve("settings.properties");
        Files.writeString(file, "look = sideways\n");
        var error = assertThrows(IllegalArgumentException.class, () -> LookMode.read(file));
        assertTrue(error.getMessage().contains("sideways") && error.getMessage().contains("classic, click"),
                error.getMessage());
    }

    @Test void eachModeIsItsOwnWord() {
        for (var mode : LookMode.values()) assertEquals(mode, LookMode.parse(mode.value()));
        assertEquals("click", LookMode.CLICK.value());
    }
}
