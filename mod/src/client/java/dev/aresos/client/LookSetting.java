package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.config.LookMode;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Package 328: the look setting, {@code look = classic | click | edge} in {@link LookMode#FILE} in the game's config
 * folder, read once. Click to look ({@link ClickToLook}) and edge turning ({@link EdgeLook}) both ask it.
 */
public final class LookSetting {
    // Client thread only.
    private static LookMode mode, modeForTests;

    private LookSetting() { }

    public static LookMode mode() {
        if (modeForTests != null) return modeForTests;
        if (mode == null) mode = load();
        return mode;
    }

    private static LookMode load() {
        Path file = FabricLoader.getInstance().getConfigDir().resolve(LookMode.FILE);
        try {
            var read = LookMode.read(file);
            if (read != LookMode.CLASSIC) AresOs.LOGGER.info("AresOS: look = {} ({})", read.value(), file);
            return read;
        } catch (IOException | IllegalArgumentException error) {
            AresOs.LOGGER.warn("AresOS: {}: {}; the world looks around as before (classic)", file, error.getMessage());
            return LookMode.CLASSIC;
        }
    }

    /** Client game tests: the setting to use (null: the file's). Both prototypes start over. */
    public static void forTests(LookMode look) {
        modeForTests = look;
        ClickToLook.reset();
        EdgeLook.reset();
    }
}
