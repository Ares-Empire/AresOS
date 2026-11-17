package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.world.FlatHome;
import dev.aresos.world.HomeSwap;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.AlertScreen;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.util.DirectoryLock;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;

public final class HomeButton {
    private HomeButton() { }

    public static void register() {
        ScreenEvents.AFTER_INIT.register((client, screen, width, height) -> {
            if (screen instanceof TitleScreen) {
                NetherHome.cancelPendingCreation();
                boolean exists = Files.exists(client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
                Screens.getWidgets(screen).add(Button.builder(Component.translatable("aresos.home"), button -> open(client, screen))
                        .bounds(width / 2 - 100, height / 4 + 24, exists ? 64 : 200, 20).build());
                if (exists) Screens.getWidgets(screen).add(Button.builder(Component.translatable("aresos.home.new"),
                        button -> confirmNew(client, screen)).bounds(width / 2 - 32, height / 4 + 24, 132, 20).build());
            }
        });
    }

    private static void open(Minecraft client, Screen parent) {
        var source = client.getLevelSource();
        var directory = source.getBaseDir().resolve(NetherHome.SAVE_FOLDER);
        try {
            if (Files.exists(directory)) {
                NetherHome.readManifest(directory);
                if (!Files.isRegularFile(directory.resolve("level.dat")) && !Files.isRegularFile(directory.resolve("level.dat_old"))) {
                    throw new IOException("AresHub is incomplete; restore or move the save before trying again.");
                }
                client.createWorldOpenFlows().openWorld(NetherHome.SAVE_FOLDER, () -> client.gui.setScreen(parent));
                return;
            }
            client.gui.setScreen(new HomeCreateScreen(parent));
        } catch (IOException error) { showError(client, parent, error); }
    }

    /** A Nether home: the seed and the placeholder hub as chosen on the create screen. */
    static HomePlan netherPlan(long seed, boolean placeholder) {
        var request = seed == 49 ? NetherHome.DEFAULT_SITE : new NetherHome.Site(seed, 0, 64, 0, 0);
        return new HomePlan("Nether", directory -> NetherHome.writeManifest(directory, request, placeholder),
                new WorldOptions(seed, true, false), WorldPresets::createNormalWorldDimensions);
    }

    /** The flat home: the same save folder and create flow, with a flat Overworld and no structures. */
    static HomePlan flatPlan() {
        return new HomePlan("flat", NetherHome::writeFlatManifest, new WorldOptions(FlatHome.SEED, false, false),
                FlatHome::dimensions);
    }

    /** The flat home as AresHub, at once (the first start, package 48); {@code parent} shows if it cannot be made. */
    static void createFlat(Minecraft client, Screen parent) {
        createWorld(client, parent, flatPlan());
    }

    /** Makes the plan as AresHub at once, as the title screen's AresOS button always has. */
    static void createWorld(Minecraft client, Screen parent, HomePlan plan) {
        var source = client.getLevelSource();
        try {
            Files.createDirectories(source.getBaseDir());
            Path directory = Files.createDirectory(source.getBaseDir().resolve(NetherHome.SAVE_FOLDER));
            plan.create(client, directory, parent);
        } catch (IOException error) { showError(client, parent, error); }
    }

    private static void confirmNew(Minecraft client, Screen parent) {
        client.gui.setScreen(new ConfirmScreen(confirmed -> {
            if (!confirmed) { client.gui.setScreen(parent); return; }
            try {
                archive(client.getLevelSource().getBaseDir());
                client.gui.setScreen(new HomeCreateScreen(parent));
            } catch (IOException error) { showError(client, parent, error); }
        }, Component.translatable("aresos.home.new"),
                Component.literal("Keep the current AresHub save under a dated name, then choose a new world? "
                        + "You can open the old world from Singleplayer. No save is deleted."),
                Component.literal("Keep old & continue"), Component.translatable("gui.cancel")));
    }

    private static void archive(Path saves) throws IOException {
        Path current = saves.resolve(NetherHome.SAVE_FOLDER);
        try {
            if (DirectoryLock.isLocked(current)) throw new IOException("AresHub is in use. Close it before creating another world.");
        } catch (java.nio.channels.OverlappingFileLockException error) {
            throw new IOException("AresHub is in use. Close it before creating another world.", error);
        }
        Path target = HomeSwap.datedName(saves, HomeSwap.ARCHIVE_PREFIX, LocalDateTime.now());
        // No replacement option: a collision or failed rename must leave the original save alone.
        Files.move(current, target);
    }

    private static void showError(Minecraft client, Screen parent, IOException error) {
        AresOs.LOGGER.error("Cannot open AresOS home; existing save left intact", error);
        client.gui.setScreen(new AlertScreen(() -> client.gui.setScreen(parent), Component.literal("Cannot open AresOS"),
                Component.literal("AresHub could not be opened. Existing saves are kept intact. " + error.getMessage())));
    }
}
