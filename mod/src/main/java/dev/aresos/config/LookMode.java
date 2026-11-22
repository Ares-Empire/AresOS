package dev.aresos.config;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Locale;
import java.util.Properties;

/**
 * Package 328: how the world lets him look around in a session's desktop world. It is a test switch until the owner
 * picks one, so there is no menu button: one line in {@code config/aresos/settings.properties}, {@code look = click}.
 * No file, no line or an empty value is {@link #CLASSIC}. The game reads it once at start.
 */
public enum LookMode {
    /** Today's: the world holds the mouse and steers the camera whenever it has the focus and no app is in front. */
    CLASSIC,
    /** Prototype A (328b): the cursor is free; a click on the world or a movement key looks around until stillness. */
    CLICK;
    // 328c adds EDGE, prototype B.

    /** The settings file, relative to the game's config folder. */
    public static final String FILE = "aresos/settings.properties";
    public static final String KEY = "look";

    /** The word in the file. */
    public String value() {
        return name().toLowerCase(Locale.ROOT);
    }

    /** A value of the look line, in any case; null or blank is classic. Anything else unknown is refused. */
    public static LookMode parse(String value) {
        if (value == null || value.isBlank()) return CLASSIC;
        String word = value.strip().toLowerCase(Locale.ROOT);
        for (var mode : values()) if (mode.value().equals(word)) return mode;
        throw new IllegalArgumentException("unknown look '" + value.strip() + "' (known: "
                + String.join(", ", Arrays.stream(values()).map(LookMode::value).toList()) + ")");
    }

    /** The setting in a properties file; a missing file is classic. */
    public static LookMode read(Path file) throws IOException {
        if (!Files.exists(file)) return CLASSIC;
        var properties = new Properties();
        try (var reader = Files.newBufferedReader(file)) {
            properties.load(reader);
        }
        return parse(properties.getProperty(KEY));
    }
}
