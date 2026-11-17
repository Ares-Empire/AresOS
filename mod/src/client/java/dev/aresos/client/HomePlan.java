package dev.aresos.client;

import dev.aresos.world.NetherHome;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.HolderLookup;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.levelgen.WorldDimensions;
import net.minecraft.world.level.levelgen.WorldOptions;

import java.io.IOException;
import java.nio.file.Path;
import java.util.function.Function;

/**
 * A home as the create screen chose it (package 48): its manifest, its world options and its dimensions. The title
 * screen makes it as AresHub at once ({@link HomeButton}); the AresOS menu makes it in a staging folder first
 * ({@link HomeSwitch}). Both use these same settings.
 */
public record HomePlan(String kind, ManifestWriter manifest, WorldOptions options,
                       Function<HolderLookup.Provider, WorldDimensions> dimensions) {
    public interface ManifestWriter { void write(Path directory) throws IOException; }

    /**
     * Writes the manifest into {@code directory} (made by the caller, empty) and creates the world there: survival,
     * normal difficulty, cheats off, through the game's own create flow; the server provisions the home when it
     * starts. The game shows {@code parent} if it cannot start the world.
     */
    void create(Minecraft client, Path directory, Screen parent) throws IOException {
        manifest.write(directory);
        NetherHome.createNewWorld(directory, () -> client.createWorldOpenFlows().createFreshLevel(
                directory.getFileName().toString(),
                new LevelSettings("AresOS", GameType.SURVIVAL, LevelSettings.DifficultySettings.DEFAULT,
                        false, WorldDataConfiguration.DEFAULT),
                options, dimensions, parent));
    }
}
