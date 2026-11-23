package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AresOsMenuScreen;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.config.SystemInfo;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
import dev.aresos.hub.TownKeeper;
import dev.aresos.item.AppItems;
import dev.aresos.item.MyAppsGame;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.world.FlatHome;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GatePicture;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.client.gui.components.toasts.Toast;
import net.minecraft.client.gui.components.toasts.TutorialToast;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.client.tutorial.TutorialSteps;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.phys.Vec3;

import javax.imageio.ImageIO;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

public final class HomeTryoutClientGameTest implements FabricClientGameTest {
    private static final String OFF = "Build mode: Off", ON = "Build mode: On";
    private static final String LEGACY_MODEL = "command_block", TERMINAL_MODEL = "black_concrete";
    private static final String REFUSAL = "The home is protected. Press G or use Build mode in the menu to change it.";
    private static final BlockPos GROUND = HubLayout.HOME.offset(3, -1, 3);

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousTutorial = context.computeOnClient(client -> client.options.tutorialStep);
        int previousScale = context.computeOnClient(client -> client.options.guiScale().get());
        Path home = null;
        Path files = null;
        String oldConfig = System.getProperty("aresos.appsConfig");
        try {
            context.runOnClient(client -> HomeScreen.forTests(true, null));
            try (var vanilla = context.worldBuilder().adjustSettings(settings ->
                    settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL)).create()) {
                vanilla.getConnection().waitForChunksRender();
                expectVanillaTutorial(context);
            }

            var gameDir = context.computeOnClient(client -> client.gameDirectory.toPath().toAbsolutePath());
            files = Files.createTempDirectory(gameDir, "pkg327-fixtures-");
            Path icon = files.resolve("foot-before.png");
            try (var original = Objects.requireNonNull(getClass().getResourceAsStream("/fixtures/terminal/foot-before.png"))) {
                Files.copy(original, icon);
            }
            var terminal = new AppDefinition("terminal", "Terminal", List.of(), "minecraft:command_block", true,
                    "helper", null, null).withSystem(new SystemInfo("image", icon.toString(), List.of("System"),
                    "Terminal", null, "foot.desktop", "foot", false)).withSpot("S0L0", null);
            Path config = files.resolve("apps.json");
            AppsConfig.save(config, List.of(terminal));
            System.setProperty("aresos.appsConfig", config.toString());
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(List.of(terminal));
                client.gui.toastManager().clear();
                client.getTutorial().setStep(TutorialSteps.MOVEMENT);
            });

            Path saves = context.computeOnClient(client -> client.getLevelSource().getBaseDir());
            home = Files.createTempDirectory(saves, "pkg327-home-").toAbsolutePath();
            TownKeeper.preparingHome(home, true);
            openHome(context, home);
            try (var world = new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, home),
                    context.computeOnClient(Minecraft::getSingleplayerServer))) {
                world.getConnection().waitForChunksRender();
                checkOnboarding(context, gameDir);
                checkMiningAndMenu(context, world);
                checkTerminal(context, world, home, terminal, icon);
                pictureOtherStarters(context, world, home);

                context.runOnClient(client -> HomeScreen.forTests(false, null));
                expectVanillaTutorial(context);
            }
            AresOs.LOGGER.info("327 checks passed: home-only onboarding, Live mining and its action bar, menu and G mode switches, "
                    + "new-home confirmation, and automatic refresh of a standing Terminal gate and its old hotbar item");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            context.runOnClient(client -> {
                HomeScreen.forTests(null, null);
                client.getTutorial().setStep(previousTutorial);
                client.gui.toastManager().clear();
                client.options.guiScale().set(previousScale);
                client.resizeGui();
                AppsTestAccess.aresos$setApps(previousApps);
            });
            context.getInput().resizeWindow(854, 480);
            if (oldConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", oldConfig);
            try {
                if (home != null) {
                    TownKeeper.preparingHome(home, false);
                    TownClientGameTest.deleteTree(home);
                }
                if (files != null) TownClientGameTest.deleteTree(files);
            } catch (IOException error) {
                throw new UncheckedIOException(error);
            }
        }
    }

    private static void openHome(ClientGameTestContext context, Path home) throws IOException {
        NetherHome.writeFlatManifest(home);
        NetherHome.createNewWorld(home, () -> context.runOnClient(client -> client.createWorldOpenFlows().createFreshLevel(
                home.getFileName().toString(),
                new LevelSettings("Package 327 test home", GameType.SURVIVAL, LevelSettings.DifficultySettings.DEFAULT,
                        false, WorldDataConfiguration.DEFAULT), new WorldOptions(FlatHome.SEED, false, false),
                FlatHome::dimensions, new TitleScreen())));
        context.waitFor(client -> client.player != null && HomeScreen.home(client) && client.gui.screen() == null, 2400);
    }

    private static void expectVanillaTutorial(ClientGameTestContext context) {
        context.runOnClient(client -> {
            client.gui.toastManager().clear();
            client.getTutorial().setStep(TutorialSteps.MOVEMENT);
        });
        context.waitFor(client -> client.gui.toastManager().getToast(TutorialToast.class, Toast.NO_TOKEN) != null, 300);
    }

    private static void checkOnboarding(ClientGameTestContext context, Path gameDir) throws IOException {
        context.waitFor(client -> client.options.tutorialStep == TutorialSteps.NONE);
        check(Files.readAllLines(gameDir.resolve("options.txt")).contains("tutorialStep:none"),
                "The home did not save tutorialStep:none");
        context.waitTicks(120);
        context.runOnClient(client -> {
            var toasts = client.gui.toastManager();
            check(toasts.getToast(TutorialToast.class, Toast.NO_TOKEN) == null, "A tutorial toast appeared after joining the home");
            toasts.addToast(new TutorialToast(client.font, TutorialToast.Icons.MOVEMENT_KEYS,
                    Component.literal("Test hint"), Component.empty(), false));
            check(toasts.getToast(TutorialToast.class, Toast.NO_TOKEN) == null, "A tutorial toast entered the home queue");
            var id = SystemToast.SystemToastId.WORLD_ACCESS_FAILURE;
            SystemToast.add(toasts, id, Component.literal("Test system toast"), null);
            check(toasts.getToast(SystemToast.class, id) != null, "The home suppressed a system toast");
            toasts.clear();
        });
    }

    private static void checkMiningAndMenu(ClientGameTestContext context, TestSingleplayerContext world) {
        TownPicturesClientGameTest.look(context, world, Vec3.atBottomCenterOf(GROUND.above()), 0, 90);
        check(world.getServer().computeOnServer(server -> server.overworld().getBlockState(GROUND).is(Blocks.GRASS_BLOCK)),
                "The test needs ordinary grass");
        context.getInput().holdKeyFor(options -> options.keyAttack, 30);
        world.getConnection().waitForServerboundPackets();
        context.waitFor(client -> {
            var message = ((HudTestAccess) client.gui.hud).aresos$overlayMessage();
            return message != null && message.getString().equals(REFUSAL);
        });
        check(world.getServer().computeOnServer(server -> server.overworld().getBlockState(GROUND).is(Blocks.GRASS_BLOCK)),
                "Live mining removed the grass");

        openMenu(context, OFF);
        context.getInput().resizeWindow(1920, 1080);
        guiScale(context, 4);
        assertMenuFits(context, 270);
        picture(context, "327-menu-1920x1080");

        context.getInput().resizeWindow(1280, 720);
        guiScale(context, 3);
        assertMenuFits(context, 240);
        picture(context, "327-menu-smallest-gui");
        context.clickScreenButton(OFF);
        waitMode(context, GameType.CREATIVE, ON);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(null);
        context.getInput().holdKeyFor(options -> options.keyAttack, 2);
        world.getConnection().waitForServerboundPackets();
        check(world.getServer().computeOnServer(server -> server.overworld().getBlockState(GROUND).isAir()),
                "Build mode did not break the same grass block");

        context.getInput().pressKey(InputConstants.KEY_G);
        waitMode(context, GameType.SURVIVAL, null);
        openMenu(context, OFF);
        context.clickScreenButton(OFF);
        waitMode(context, GameType.CREATIVE, ON);
        context.clickScreenButton(ON);
        waitMode(context, GameType.SURVIVAL, OFF);
        context.clickScreenButton("Start a new home…");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        picture(context, "327-new-home-confirm");
        context.clickScreenButton("gui.cancel");
        context.waitForScreen(HomeCreateScreen.class);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(null);
    }

    private static void openMenu(ClientGameTestContext context, String label) {
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        waitMode(context, GameType.SURVIVAL, label);
    }

    private static void waitMode(ClientGameTestContext context, GameType mode, String label) {
        context.waitFor(client -> client.gameMode.getPlayerMode() == mode && !ModeSwitchClient.pending()
                && (label == null || client.gui.screen().children().stream().anyMatch(child ->
                child instanceof Button button && button.active && button.getMessage().getString().equals(label))));
    }

    private static void assertMenuFits(ClientGameTestContext context, int height) {
        context.runOnClient(client -> {
            var screen = client.gui.screen();
            check(screen.height == height, "The menu fixture's GUI is " + screen.height + " high");
            for (var child : screen.children()) if (child instanceof Button button) {
                check(button.getX() >= 0 && button.getRight() <= screen.width
                        && button.getY() >= 0 && button.getBottom() <= screen.height,
                        "Off-screen button " + button.getMessage().getString());
            }
        });
    }

    private static void checkTerminal(ClientGameTestContext context, TestSingleplayerContext world, Path home,
                                      AppDefinition terminal, Path icon) throws IOException {
        var before = oldTerminalGate();
        var converted = GatePicture.of(ImageIO.read(icon.toFile()), HubLayout.SIZE);
        check("gray_concrete".equals(converted.at(6, 8)), "The original Foot icon's neutral charcoal turned brown");
        var after = GateBuilder.picture(terminal, HubLayout.SIZE);
        var place = Place.parse(terminal.place()).orElseThrow();
        var plan = world.getServer().computeOnServer(server -> Town.plan(HubData.get(server), terminal, place, before));
        var eye = plan.exit();
        Vec3 position = eye.position().subtract(Vec3.atLowerCornerOf(plan.outward().getUnitVec3i()).scale(12));
        TownPicturesClientGameTest.look(context, world, position, eye.yaw(), -15);
        world.getConnection().waitForChunksRender();
        world.getServer().runOnServer(server -> {
            try { Town.build(server, terminal, place, before); }
            catch (IOException error) { throw new UncheckedIOException(error); }
            var player = world.getConnection().getServerPlayer();
            var oldItem = player.getInventory().getItem(0);
            check(terminal.id().equals(oldItem.get(AppItems.APP_ID)), "The Terminal is missing from its pinned slot");
            oldItem.set(DataComponents.ITEM_MODEL, Identifier.withDefaultNamespace(LEGACY_MODEL));
            player.inventoryMenu.broadcastChanges();
        });
        context.waitFor(client -> hasModel(client, LEGACY_MODEL));
        AresOs.LOGGER.info("327 old Terminal gate: blocks={}", blockCounts(before));
        picture(context, "327-terminal-before");

        TownKeeper.preparingHome(home, false);
        TownKeeper.listed();
        MyAppsGame.changed();
        TownClientGameTest.waitForServer(context, world, server -> HubData.get(server).logo(terminal.id())
                        .filter(logo -> logo.place().equals(terminal.place()) && logo.picture().equals(after.hash())).isPresent()
                        && server.overworld().getBlockState(plan.at(0, 0, 10)).is(Blocks.CONCRETE.black())
                        && server.overworld().getBlockState(plan.at(0, 4, 7)).is(Blocks.CONCRETE.white()),
                "The standing Terminal gate did not refresh in place", 600);
        context.waitFor(client -> hasModel(client, TERMINAL_MODEL));
        AresOs.LOGGER.info("327 new Terminal gate: blocks={}", blockCounts(after));
        picture(context, "327-terminal-after");
    }

    private static GatePicture oldTerminalGate() throws IOException {
        var resource = Objects.requireNonNull(HomeTryoutClientGameTest.class.getResourceAsStream("/fixtures/terminal/gate-v2.txt"));
        try (var reader = new BufferedReader(new InputStreamReader(resource, StandardCharsets.UTF_8))) {
            var blocks = reader.lines().toList().reversed().stream()
                    .flatMap(row -> Arrays.stream(row.split(" ")))
                    .map(block -> block.equals("-") ? null : block)
                    .toArray(String[]::new);
            return GatePicture.ofBlocks(blocks, HubLayout.SIZE);
        }
    }

    /** The two other real starter icons, when their helper-cached PNGs are provided for review. */
    private static void pictureOtherStarters(ClientGameTestContext context, TestSingleplayerContext world, Path home) {
        String directory = System.getenv("ARESOS_STARTER_ICONS");
        if (directory == null) return;
        TownKeeper.preparingHome(home, true);
        try {
            pictureStarter(context, world, directory, "browser", "Chrome", "N0L0");
            pictureStarter(context, world, directory, "notepad", "Notepad", "S0R0");
        } finally {
            TownKeeper.preparingHome(home, false);
        }
    }

    private static void pictureStarter(ClientGameTestContext context, TestSingleplayerContext world, String directory,
                                       String id, String name, String spot) {
        Path icon = Path.of(directory, id + ".png");
        check(Files.isRegularFile(icon), "Missing helper-cached icon for " + name);
        var app = new AppDefinition(id, name, List.of(), "minecraft:paper", false, "helper", null, null)
                .withSystem(new SystemInfo("image", icon.toString(), null, null, null, null, null, null));
        var picture = GateBuilder.icon(app, HubLayout.SIZE).orElseThrow();
        var place = Place.parse(spot).orElseThrow();
        var plan = world.getServer().computeOnServer(server -> Town.plan(HubData.get(server), app, place, picture));
        var eye = plan.exit();
        var position = eye.position().subtract(Vec3.atLowerCornerOf(plan.outward().getUnitVec3i()).scale(12));
        TownPicturesClientGameTest.look(context, world, position, eye.yaw(), -15);
        world.getConnection().waitForChunksRender();
        world.getServer().runOnServer(server -> {
            try { Town.build(server, app, place, picture); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        });
        AresOs.LOGGER.info("327 {} gate: hash={}, blocks={}", name, picture.hash(), blockCounts(picture));
        picture(context, "327-" + id);
    }

    private static java.util.Map<String, Integer> blockCounts(GatePicture picture) {
        var counts = new java.util.TreeMap<String, Integer>();
        for (int y = 0; y < picture.size(); y++) for (int x = 0; x < picture.size(); x++) {
            String block = picture.at(x, y);
            counts.merge(block == null ? "air" : block, 1, Integer::sum);
        }
        return counts;
    }

    private static boolean hasModel(Minecraft client, String model) {
        return Identifier.withDefaultNamespace(model).equals(client.player.getInventory().getItem(0).get(DataComponents.ITEM_MODEL));
    }

    private static void guiScale(ClientGameTestContext context, int scale) {
        context.runOnClient(client -> {
            client.options.guiScale().set(scale);
            client.resizeGui();
        });
        context.waitTicks(2);
    }

    private static void picture(ClientGameTestContext context, String name) {
        context.runOnClient(client -> {
            client.gui.hud.setOverlayMessage(Component.empty(), false);
            client.gui.hud.getChat().clearMessages(true);
            client.gui.toastManager().clear();
        });
        context.waitTicks(8);
        context.takeScreenshot(TestScreenshotOptions.of(name)
                .withDestinationDir(Path.of(System.getProperty("aresos.tryoutReviewDir"))));
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
