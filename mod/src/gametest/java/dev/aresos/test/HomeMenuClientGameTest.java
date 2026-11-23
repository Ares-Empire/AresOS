package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AppsScreen;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.AresOsMenuScreen;
import dev.aresos.client.FirstStart;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.client.HomeRecoveryScreen;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.HomeSwitch;
import dev.aresos.client.HomeWorkingScreen;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.shell.FakeHelper;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.HomeSwap;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.narration.ScreenNarrationCollector;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.options.OptionsScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Stream;

/**
 * Package 48: the AresOS menu instead of the game menu in the home screen, "Start a new home…" from one home to the next
 * without the title screen, and the first start that makes the flat home without showing the title screen.
 *
 * <p>The first start makes the flat home this test then works in. The new home's switch is checked three ways: Cancel
 * changes nothing; flat to a Nether home with seed 50 keeps the old home (with a block placed just before) under a
 * dated name and never sets a title screen; a failure injected at the second rename brings him back to the old home
 * with a chat line. The test leaves the saves as it found them.
 */
public final class HomeMenuClientGameTest implements FabricClientGameTest {
    /** A world made and opened twice, with the Nether site search in between, at the test's tick rate. */
    private static final int SWITCH_TICKS = 6000;
    private static final String HINT = "G switches Live and Build · E opens the inventory and Apps…";

    private static SwitchSaveChecks switchSaves;

    @Override public void runTest(ClientGameTestContext context) {
        Path saves = context.computeOnClient(client -> client.getLevelSource().getBaseDir().toAbsolutePath().normalize());
        Path hub = saves.resolve(NetherHome.SAVE_FOLDER);
        Path backup = saves.resolve("AresHub-test-backup-" + UUID.randomUUID());
        List<Path> made = new ArrayList<>();
        try {
            context.runOnClient(client -> HomeSwitch.closeFromTestTasksForTests(true));
            if (Files.exists(hub)) Files.move(hub, backup);
            gameMenuOutsideTheHomeScreen(context);
            titleScreenStays(context, hub);
            firstStart(context, hub);
            menu(context, hub);
            newHomeCancelled(context, saves);
            switchSaves = new SwitchSaveChecks(context);
            BlockPos marker = placeMarker(context, hub);
            Path archived = newHome(context, saves, hub);
            made.add(archived);
            made.add(failedNewHome(context, saves, hub));
            adopt(context, hub).close();
            try (var old = new TestWorldSaveImpl(context, archived).open()) {
                check(old.getServer().computeOnServer(server -> server.overworld().getBlockState(marker).is(Blocks.GOLD_BLOCK)),
                        "The dated old home lost the block placed just before New home");
            }
            made.addAll(reviewFixes(context, saves, hub));
            switchSaves.verify();
            AresOs.LOGGER.info("48 home menu checks passed: the game menu stays outside a session's desktop world, the "
                    + "title screen stays outside a session and with an AresHub there, the first start makes the flat "
                    + "home without a title screen, Esc opens the AresOS menu with its items and the world moving, Back, "
                    + "Esc, Apps and Settings come back, Apps waits for Live, Cancel changes nothing, New home keeps the "
                    + "old home under a dated name without a title screen, and a failed one brings the old home back");
            made.add(hub);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            try {
                if (switchSaves != null) switchSaves.close();
            } catch (IOException error) {
                throw new UncheckedIOException(error);
            } finally {
                switchSaves = null;
            }
            context.runOnClient(client -> {
                HomeScreen.forTests(null, null);
                HomeSwitch.failSecondRenameForTests(false);
                HomeSwitch.failuresForTests(HomeSwap.FILES, false);
                HomeSwitch.holdRecoveryOpenForTests(false);
                HomeSwitch.closeFromTestTasksForTests(false);
                ScreenLog.stop();
            });
        }
        try {
            for (Path folder : made) delete(folder);
            if (Files.exists(backup)) Files.move(backup, hub);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }

    /** Both callers share the same four-case gate, with the helper disconnected and really connected. */
    private static void gameMenuOutsideTheHomeScreen(ClientGameTestContext context) throws IOException {
        Path sockets = Files.createTempDirectory(Path.of("."), "a46gate");
        var previousShell = AresOs.shell();
        try (var world = context.worldBuilder().create();
             var helper = new FakeHelper(sockets); var shell = helper.client(FakeHelper.fast())) {
            for (boolean connected : new boolean[] {false, true}) {
                context.runOnClient(client -> AppsTestAccess.aresos$setShell(connected ? shell : null));
                if (connected) {
                    shell.start();
                    try { shell.awaitApps(java.time.Duration.ofSeconds(10)); }
                    catch (Exception error) { throw new AssertionError("The fake helper never connected", error); }
                }
                for (boolean desktop : new boolean[] {false, true}) {
                    world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, desktop));
                    context.waitFor(client -> AresOsClient.acceptsAppCommands(client) == desktop);
                    for (boolean session : new boolean[] {false, true}) {
                        context.runOnClient(client -> {
                            HomeScreen.forTests(session, null);
                            boolean home = session && desktop;
                            check(HomeScreen.home(client) == home && AresOsMenuScreen.replacesGameMenu(client) == home,
                                    "Home/menu gates disagree: session=" + session + ", desktop=" + desktop + ", helper=" + connected);
                            client.gui.setScreen(null);
                            client.pauseGame(false);
                            check(home ? client.gui.screen() instanceof AresOsMenuScreen : client.gui.screen() instanceof PauseScreen,
                                    "The shared gate opened the wrong menu: " + client.gui.screen());
                            client.gui.setScreen(null);
                        });
                    }
                }
            }
            AresOs.LOGGER.info("46/48 shared-home gate passed all eight cases: session × desktop world × helper connection");
        } finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(previousShell);
                HomeScreen.forTests(true, null);
            });
            delete(sockets);
        }
    }

    /** Outside a session, and with an AresHub there (whatever is in it), the title screen shows and nothing is made. */
    private static void titleScreenStays(ClientGameTestContext context, Path hub) throws IOException {
        context.runOnClient(client -> {
            HomeScreen.forTests(false, null);
            FirstStart.forTests();
        });
        context.setScreen(TitleScreen::new);
        context.waitTicks(5);
        context.runOnClient(client -> {
            check(client.gui.screen() instanceof TitleScreen, "Outside a session the title screen gave way to " + client.gui.screen());
            check(Screens.getWidgets(client.gui.screen()).stream().anyMatch(widget -> widget.getMessage().getString().equals("AresOS")),
                    "The title screen lost its AresOS button");
            check(client.level == null && client.getSingleplayerServer() == null, "Outside a session a world opened");
        });
        check(!Files.exists(hub), "Outside a session the first start made AresHub");

        Files.createDirectory(hub);
        Files.writeString(hub.resolve("keep.txt"), "an AresHub that is there, damaged or not");
        context.runOnClient(client -> {
            HomeScreen.forTests(true, null);
            FirstStart.forTests();
        });
        context.setScreen(TitleScreen::new);
        context.waitTicks(5);
        context.runOnClient(client -> check(client.gui.screen() instanceof TitleScreen && client.level == null,
                "With an AresHub there the first start did not leave the title screen: " + client.gui.screen()));
        try (Stream<Path> files = Files.list(hub)) {
            check(files.toList().equals(List.of(hub.resolve("keep.txt"))), "The first start touched an existing AresHub");
        }
        Files.delete(hub.resolve("keep.txt"));
        Files.delete(hub);
    }

    /** Session on and no AresHub: the flat home is made and open, and no title screen was ever set. */
    private static void firstStart(ClientGameTestContext context, Path hub) throws IOException {
        context.runOnClient(client -> {
            FirstStart.forTests();
            ScreenLog.start();
        });
        context.setScreen(TitleScreen::new);
        context.waitFor(client -> client.player != null && client.gui.screen() == null, SWITCH_TICKS);
        var screens = context.computeOnClient(client -> ScreenLog.stop());
        check(screens.stream().noneMatch(HomeMenuClientGameTest::titleScreen), "The first start set a title screen: " + screens);
        check(NetherHome.readKind(hub) == NetherHome.Kind.FLAT, "The first start did not make the flat home");
        check(Files.readString(hub.resolve(NetherHome.PROVISIONED)).equals("complete\n"), "The flat home was not provisioned");
        context.runOnClient(client -> {
            check(worldFolder(client).equals(hub), "The first start opened " + worldFolder(client));
            check(client.gameMode.getPlayerMode() == GameType.SURVIVAL, "He did not arrive in Live mode");
            check(AresOsClient.acceptsAppCommands(client), "The first home is not a desktop world");
        });
        AresOs.LOGGER.info("48 first start: screens set {}", screens);
    }

    private static void menu(ClientGameTestContext context, Path hub) {
        var home = adopt(context, hub);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.runOnClient(client -> {
            var widgets = Screens.getWidgets(client.gui.screen());
            var buttons = widgets.stream().filter(Button.class::isInstance).map(HomeMenuClientGameTest::text).toList();
            check(buttons.equals(List.of("Back to the world", "Apps…", "Settings…", "Build mode: Off", "Start a new home…")), "The AresOS menu has " + buttons);
            var lines = widgets.stream().filter(StringWidget.class::isInstance).map(HomeMenuClientGameTest::text).toList();
            check(lines.equals(List.of("AresOS", HINT)), "The AresOS menu's title and hint are " + lines);
            check(widgets.size() == buttons.size() + lines.size(), "The AresOS menu has more: " + widgets);
            check(!client.isPaused(), "The AresOS menu paused the game");
        });
        long before = home.getServer().computeOnServer(server -> server.overworld().getGameTime());
        context.waitTicks(20);
        long after = home.getServer().computeOnServer(server -> server.overworld().getGameTime());
        check(after >= before + 15, "The world stood still behind the AresOS menu: " + before + " -> " + after);

        context.getInput().pressKey(InputConstants.KEY_G);
        context.waitTicks(2);
        context.runOnClient(client -> {
            var said = ((HudTestAccess) client.gui.hud).aresos$overlayMessage();
            check(said != null && said.getString().equals("Close the menu before switching AresOS mode"),
                    "G in the AresOS menu said " + said);
            check(client.gui.screen() instanceof AresOsMenuScreen && client.gameMode.getPlayerMode() == GameType.SURVIVAL,
                    "G in the AresOS menu switched the mode or closed the menu");
        });

        context.clickScreenButton("Back to the world");
        context.waitFor(client -> client.gui.screen() == null);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitFor(client -> client.gui.screen() == null);
        // F3+Esc, focus loss and any mod ask for the game menu the same way.
        context.runOnClient(client -> {
            client.pauseGame(true);
            check(client.gui.screen() instanceof AresOsMenuScreen, "F3+Esc in the home screen opened " + client.gui.screen());
        });

        context.clickScreenButton("Apps…");
        context.waitForScreen(AppsScreen.class);
        context.clickScreenButton("gui.done");
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Settings…");
        context.waitForScreen(OptionsScreen.class);
        context.clickScreenButton("gui.done");
        context.waitForScreen(AresOsMenuScreen.class);
        reboundKeys(context);
        screenshots(context);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitFor(client -> client.gui.screen() == null);

        // Build mode: the Apps screen is Live's, so its button waits.
        mode(context, home, GameType.CREATIVE);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.runOnClient(client -> check(!button(client, "Apps…").active, "Apps… is active in Build mode"));
        reboundKeys(context);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitFor(client -> client.gui.screen() == null);
        mode(context, home, GameType.SURVIVAL);
    }

    /** Settings returns an already initialized menu; both hints must use the new bindings immediately. */
    private static void reboundKeys(ClientGameTestContext context) {
        var menu = context.computeOnClient(client -> client.gui.screen());
        // Preserve arbitrary bindings inherited from earlier tests, not just their defaults.
        String modeKey = context.computeOnClient(client -> KeyMapping.get("key.aresos.switch_mode").saveString());
        String inventoryKey = context.computeOnClient(client -> client.options.keyInventory.saveString());
        try {
            context.clickScreenButton("Settings…");
            context.waitForScreen(OptionsScreen.class);
            context.runOnClient(client -> {
                KeyMapping.get("key.aresos.switch_mode").setKey(InputConstants.Type.KEYSYM.getOrCreate(InputConstants.KEY_H));
                client.options.keyInventory.setKey(InputConstants.Type.KEYSYM.getOrCreate(InputConstants.KEY_I));
                KeyMapping.resetMapping();
            });
            context.clickScreenButton("gui.done");
            context.waitForScreen(AresOsMenuScreen.class);
            context.runOnClient(client -> {
                check(client.gui.screen() == menu, "Settings did not return the same initialized menu");
                var lines = Screens.getWidgets(menu).stream().filter(StringWidget.class::isInstance)
                        .map(HomeMenuClientGameTest::text).toList();
                check(lines.equals(List.of("AresOS", "H switches Live and Build · I opens the inventory and Apps…")),
                        "The key hint stayed stale: " + lines);
                var apps = button(client, "Apps…");
                if (!apps.active) {
                    var narration = new ScreenNarrationCollector();
                    narration.update(apps::updateNarration);
                    check(narration.collectNarrationText(true).contains("Apps open in Live mode. Use the Build mode button or press H in the world."),
                            "The Build-mode Apps tooltip did not follow the mode binding");
                }
            });
        } finally {
            context.runOnClient(client -> {
                KeyMapping.get("key.aresos.switch_mode").setKey(InputConstants.getKey(modeKey));
                client.options.keyInventory.setKey(InputConstants.getKey(inventoryKey));
                KeyMapping.resetMapping();
                client.gui.setScreen(menu);
            });
        }
    }

    /** The menu over the flat home at 1280x720 (GUI scale 2), then at the smallest GUI the game allows, 240 high. */
    private static void screenshots(ClientGameTestContext context) {
        int scale = context.computeOnClient(client -> client.options.guiScale().get());
        try {
            context.getInput().resizeWindow(1280, 720);
            guiScale(context, 2);
            screenshot(context, "48-menu-1280x720");
            guiScale(context, 3);
            context.runOnClient(client -> {
                var screen = client.gui.screen();
                check(client.getWindow().getGuiScaledHeight() == 240, "Fixture: the GUI is " + client.getWindow().getGuiScaledHeight() + " high");
                for (AbstractWidget widget : Screens.getWidgets(screen)) {
                    check(widget.getY() >= 0 && widget.getBottom() <= screen.height && widget.getX() >= 0 && widget.getRight() <= screen.width,
                            "At the smallest GUI the menu's " + text(widget) + " is off the screen");
                }
            });
            screenshot(context, "48-menu-smallest-gui");
            // What every step of New home shows, the game's loading screens included, at 1280x720.
            guiScale(context, 2);
            var menu = context.computeOnClient(client -> client.gui.screen());
            context.setScreen(() -> new HomeWorkingScreen(HomeSwitch.working()));
            screenshot(context, "48-making-your-new-home");
            context.setScreen(() -> menu);
        } finally {
            guiScale(context, scale);
            context.getInput().resizeWindow(854, 480);
        }
    }

    private static void newHomeCancelled(ClientGameTestContext context, Path saves) throws IOException {
        var before = listing(saves);
        var server = context.computeOnClient(Minecraft::getSingleplayerServer);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Start a new home…");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("Home: Flat");
        context.clickScreenButton("50");
        var choice = context.computeOnClient(client -> client.gui.screen());
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        context.clickScreenButton("gui.cancel");
        context.waitForScreen(HomeCreateScreen.class);
        context.runOnClient(client -> {
            check(client.gui.screen() == choice, "Cancel reopened the chooser instead of keeping the choices");
            check(Screens.getWidgets(client.gui.screen()).stream().anyMatch(widget -> widget.getMessage().getString()
                    .equals(Component.translatable("aresos.home.create").getString()) && widget.active), "Cancel left Create disabled");
            check(button(client, "Home: Nether") != null && client.gui.screen().children().stream()
                    .filter(EditBox.class::isInstance).map(EditBox.class::cast).anyMatch(box -> box.getValue().equals("50")),
                    "Cancel lost the home type or seed");
        });
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        context.clickScreenButton("gui.cancel");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("gui.cancel");
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Back to the world");
        context.waitTicks(5);
        context.runOnClient(client -> check(client.getSingleplayerServer() == server && client.gui.screen() == null
                && !HomeSwitch.busy(), "Cancel left the home: " + client.gui.screen()));
        check(listing(saves).equals(before), "Cancel changed the saves");
    }

    private static BlockPos placeMarker(ClientGameTestContext context, Path hub) {
        var home = adopt(context, hub);
        return home.getServer().computeOnServer(server -> {
            var player = home.getConnection().getServerPlayer();
            BlockPos pos = player.blockPosition().offset(3, 1, 3);
            player.level().setBlockAndUpdate(pos, Blocks.GOLD_BLOCK.defaultBlockState());
            return pos;
        });
    }

    /** Flat to a Nether home with seed 50, through the menu: the old home stays under a dated name. */
    private static Path newHome(ClientGameTestContext context, Path saves, Path hub) throws IOException {
        var before = listing(saves);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Start a new home…");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("Home: Flat");
        context.clickScreenButton("50");
        context.runOnClient(client -> check(client.gui.screen().children().stream().filter(EditBox.class::isInstance)
                .map(EditBox.class::cast).anyMatch(box -> box.getValue().equals("50")), "Fixture: the seed is not 50"));
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        context.runOnClient(client -> {
            String asked = client.gui.screen().getNarrationMessage().getString();
            check(asked.contains("AresOS will build a fresh home and open it. Your current home will stay in your saves."), "The confirmation asks " + asked);
            ScreenLog.start();
        });
        switchSaves.confirm(context);
        waitForSwitch(context);
        var screens = context.computeOnClient(client -> ScreenLog.stop());
        check(screens.stream().noneMatch(HomeMenuClientGameTest::titleScreen), "New home set a title screen: " + screens);

        var added = new HashSet<>(listing(saves));
        added.removeAll(before);
        check(added.size() == 1, "New home left these folders: " + added);
        Path archived = added.iterator().next();
        check(archived.getFileName().toString().matches("AresHub-\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-\\d{3}(-\\d+)?"),
                "The old home's dated name is " + archived.getFileName());
        check(NetherHome.readKind(archived) == NetherHome.Kind.FLAT, "The dated folder is not the old flat home");
        check(NetherHome.readKind(hub) == NetherHome.Kind.NETHER, "AresHub is not the new Nether home");
        HomeSwap.checkComplete(hub);
        var home = adopt(context, hub);
        check(home.getServer().computeOnServer(server -> server.overworld().getSeed()) == 50, "The new home's seed is not 50");
        context.runOnClient(client -> {
            check(worldFolder(client).equals(hub), "New home opened " + worldFolder(client));
            check(client.gameMode.getPlayerMode() == GameType.SURVIVAL, "He did not arrive in Live mode");
            check(chat(client).stream().noneMatch(line -> line.startsWith("Couldn't make the new home")), "A good switch said it failed");
        });
        long millis = context.computeOnClient(client -> HomeSwitch.lastMillisForTests());
        long gap = context.computeOnClient(client -> HomeSwitch.lastGapNanosForTests());
        AresOs.LOGGER.info("48 new home: flat to Nether 50 in {} ms (from Make the new home to the new home), no AresHub "
                + "on disk for {} µs; old home kept as {}; screens set {}", millis, gap / 1000, archived.getFileName(), screens);
        return archived;
    }

    /** A failure at the second rename: the old home has been moved, comes back and opens, with a chat line. */
    private static Path failedNewHome(ClientGameTestContext context, Path saves, Path hub) throws IOException {
        var before = listing(saves);
        var oldServer = context.computeOnClient(Minecraft::getSingleplayerServer);
        context.runOnClient(client -> HomeSwitch.failSecondRenameForTests(true));
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Start a new home…");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        context.runOnClient(client -> ScreenLog.start());
        switchSaves.confirm(context);
        waitForSwitch(context);
        context.runOnClient(client -> HomeSwitch.failSecondRenameForTests(false));
        var screens = context.computeOnClient(client -> ScreenLog.stop());
        check(screens.stream().noneMatch(HomeMenuClientGameTest::titleScreen), "A failed new home set a title screen: " + screens);

        var added = new HashSet<>(listing(saves));
        added.removeAll(before);
        check(added.size() == 1 && added.iterator().next().getFileName().toString().startsWith(HomeSwap.STAGING_PREFIX),
                "A failed new home left these folders (only its staging folder should stay): " + added);
        Path staging = added.iterator().next();
        check(NetherHome.readKind(staging) == NetherHome.Kind.FLAT, "The kept staging folder is not the flat home it made");
        check(NetherHome.readKind(hub) == NetherHome.Kind.NETHER, "AresHub is no longer the old Nether home");
        var home = adopt(context, hub);
        check(home.getServer().computeOnServer(server -> server.overworld().getSeed()) == 50, "He is not back in the old home");
        context.runOnClient(client -> {
            check(client.getSingleplayerServer() != oldServer && worldFolder(client).equals(hub), "The old home did not open again");
            check(chat(client).contains("Couldn't make the new home: it could not be moved into place (injected test failure). "
                    + "Your home is as it was."), "No chat line said why: " + chat(client));
        });
        AresOs.LOGGER.info("48 failed new home: back in the old home after {} ms; staging kept as {}; screens set {}",
                context.computeOnClient(client -> HomeSwitch.lastMillisForTests()), staging.getFileName(), screens);
        return staging;
    }

    /** Each recovery checks folder AND level name, so opening a different world cannot pass. */
    private static Set<Path> reviewFixes(ClientGameTestContext context, Path saves, Path hub) throws IOException {
        var before = listing(saves);
        String original = "Review original home";
        nameSave(hub, original);
        openSave(context, hub);

        // The replacement cannot move back to staging: the original must open from its archive, never AresHub.
        context.runOnClient(client -> HomeSwitch.failuresForTests((from, to) -> {
            if (from.equals(hub) && to.getFileName().toString().startsWith(HomeSwap.STAGING_PREFIX))
                throw new IOException("replacement restoration stuck");
            HomeSwap.FILES.move(from, to);
        }, true));
        startFlatSwitch(context);
        waitForSwitch(context);
        Path originalArchive = context.computeOnClient(HomeMenuClientGameTest::worldFolder);
        check(!originalArchive.equals(hub), "Failed replacement restoration reopened the replacement");
        assertHome(context, originalArchive, original, "Your previous home is open from the saves folder "
                + originalArchive.getFileName() + ". The new home remains in AresHub.");
        check(Files.isDirectory(hub), "The replacement should remain in AresHub");
        resetFailures(context);

        // From that fallback archive with another AresHub present: failure returns the archive, then success
        // archives the unrelated AresHub and leaves the world he was in under exactly its original name.
        context.runOnClient(client -> HomeSwitch.failuresForTests(HomeSwap.FILES, true));
        startFlatSwitch(context);
        waitForSwitch(context);
        assertHome(context, originalArchive, original, "Your previous home is open from the saves folder "
                + originalArchive.getFileName() + ". AresHub is a separate home.");
        resetFailures(context);
        var withHub = listing(saves);
        startFlatSwitch(context);
        waitForSwitch(context);
        assertHome(context, hub, "AresOS", null);
        check(Files.isDirectory(originalArchive), "New home renamed the open archive");
        var archivedCanonical = new HashSet<>(listing(saves));
        archivedCanonical.removeAll(withHub);
        check(archivedCanonical.size() == 1, "New home from an archive did not keep the existing AresHub: " + archivedCanonical);
        adopt(context, hub).close();
        openSave(context, originalArchive);
        assertHome(context, originalArchive, original, null);
        adopt(context, originalArchive).close();

        // The replacement moves back, but the old archive cannot become AresHub.
        String second = "Review second restoration";
        nameSave(hub, second);
        openSave(context, hub);
        context.runOnClient(client -> HomeSwitch.failuresForTests((from, to) -> {
            if (to.equals(hub) && !from.getFileName().toString().startsWith(HomeSwap.STAGING_PREFIX))
                throw new IOException("archive restoration stuck");
            HomeSwap.FILES.move(from, to);
        }, true));
        startFlatSwitch(context);
        waitForSwitch(context);
        Path missingHubArchive = context.computeOnClient(HomeMenuClientGameTest::worldFolder);
        check(!Files.exists(hub), "Failed archive restoration should leave AresHub missing");
        assertHome(context, missingHubArchive, second, "Your previous home is open from the saves folder "
                + missingHubArchive.getFileName() + ". AresHub is missing; the AresOS session will not find this home until it is named AresHub again.");
        resetFailures(context);

        // The other fallback case: no AresHub exists. Fail after promotion, then make a home successfully.
        context.runOnClient(client -> HomeSwitch.failuresForTests(HomeSwap.FILES, true));
        startFlatSwitch(context);
        waitForSwitch(context);
        check(!Files.exists(hub), "Recovery should restore the previous absence of AresHub");
        assertHome(context, missingHubArchive, second, "Your previous home is open from the saves folder "
                + missingHubArchive.getFileName() + ". AresHub is missing; the AresOS session will not find this home until it is named AresHub again.");
        resetFailures(context);
        var withoutHub = listing(saves);
        startFlatSwitch(context);
        waitForSwitch(context);
        assertHome(context, hub, "AresOS", null);
        var added = new HashSet<>(listing(saves));
        added.removeAll(withoutHub);
        check(added.equals(Set.of(hub)), "An archive switch without AresHub should only add AresHub: " + added);
        adopt(context, hub).close();
        openSave(context, missingHubArchive);
        assertHome(context, missingHubArchive, second, null);
        adopt(context, missingHubArchive).close();

        // A failed old-home reopen cannot release the guard or strand the working screen. Try again also
        // handles a recovery timeout, and eventually opens the named original after the fault is lifted.
        String retryName = "Review retry home";
        nameSave(hub, retryName);
        openSave(context, hub);
        byte[][] keptLevel = {null};
        context.runOnClient(client -> HomeSwitch.failuresForTests((from, to) -> {
            HomeSwap.FILES.move(from, to);
            if (to.equals(hub) && !from.getFileName().toString().startsWith(HomeSwap.STAGING_PREFIX)) {
                // Fail the real open flow, including its storage lock, rather than just calling fail() in a test.
                keptLevel[0] = Files.readAllBytes(hub.resolve("level.dat"));
                Files.writeString(hub.resolve("level.dat"), "injected unreadable level data");
            }
        }, true));
        startFlatSwitch(context);
        waitForRecovery(context);
        context.runOnClient(client -> {
            check(HomeSwitch.busy() && client.level == null, "Failed reopen dropped recovery");
            check(button(client, "Try again").active, "Recovery has no usable Try again button");
            client.gui.setScreen(new TitleScreen());
            check(client.gui.screen() instanceof HomeRecoveryScreen, "Recovery allowed the title screen");
        });
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(HomeRecoveryScreen.class);
        screenshot(context, "48-review-fix-recovery");
        check(keptLevel[0] != null, "Fixture: recovery never injected the damaged level");
        Files.write(hub.resolve("level.dat"), keptLevel[0]);
        context.runOnClient(client -> {
            HomeSwitch.failuresForTests(HomeSwap.FILES, false);
            HomeSwitch.holdRecoveryOpenForTests(true);
        });
        context.clickScreenButton("Try again");
        context.waitTicks(5);
        context.runOnClient(client -> HomeSwitch.timeoutForTests());
        waitForRecovery(context);
        context.runOnClient(client -> check(HomeSwitch.busy(), "Recovery timeout released the title-screen guard"));
        resetFailures(context);
        context.clickScreenButton("Try again");
        waitForSwitch(context);
        assertHome(context, hub, retryName, "Your home is as it was.");
        adopt(context, hub).close();

        var made = new HashSet<>(listing(saves));
        made.removeAll(before);
        AresOs.LOGGER.info("48 review fix checks passed: both restoration renames, both archive switch cases, failed reopen, recovery timeout and Try again");
        return made;
    }

    private static void nameSave(Path folder, String name) throws IOException {
        Path file = folder.resolve("level.dat");
        var data = NbtIo.readCompressed(file, NbtAccounter.unlimitedHeap());
        data.getCompoundOrEmpty("Data").putString("LevelName", name);
        NbtIo.writeCompressed(data, file);
    }

    private static void openSave(ClientGameTestContext context, Path folder) {
        context.runOnClient(client -> client.createWorldOpenFlows().openWorld(folder.getFileName().toString(),
                () -> { throw new AssertionError("Could not open fixture " + folder.getFileName()); }));
        context.waitFor(client -> client.player != null && client.gui.screen() == null, SWITCH_TICKS);
    }

    private static void startFlatSwitch(ClientGameTestContext context) {
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(AresOsMenuScreen.class);
        context.clickScreenButton("Start a new home…");
        context.waitForScreen(HomeCreateScreen.class);
        context.clickScreenButton("aresos.home.create");
        context.waitForScreen(ConfirmScreen.class);
        context.runOnClient(client -> ScreenLog.start());
        switchSaves.confirm(context);
    }

    private static void assertHome(ClientGameTestContext context, Path folder, String levelName, String recoveryText) {
        context.runOnClient(client -> {
            check(worldFolder(client).equals(folder), "Expected home folder " + folder.getFileName() + ", got " + worldFolder(client));
            check(client.getSingleplayerServer().getWorldData().getLevelName().equals(levelName),
                    "Opened the wrong world: expected level name " + levelName);
            var screens = ScreenLog.stop();
            check(screens.stream().noneMatch(HomeMenuClientGameTest::titleScreen), "Recovery set a title screen: " + screens);
            if (recoveryText != null) {
                String expected = "Couldn't make the new home: the new home did not open. " + recoveryText;
                check(chat(client).contains(expected), "Incorrect recovery chat; expected " + expected + ", got " + chat(client));
                check(chat(client).stream().filter(line -> line.startsWith("Couldn't make the new home:")).count() == 1,
                        "Recovery posted contradictory chat: " + chat(client));
            }
        });
    }

    private static void waitForRecovery(ClientGameTestContext context) {
        for (int tick = 0; tick < SWITCH_TICKS; tick++) {
            context.runOnClient(client -> {
                switchSaves.observe(client);
                HomeSwitch.runPendingCloseForTests();
            });
            if (context.computeOnClient(client -> client.gui.screen() instanceof HomeRecoveryScreen)) return;
            context.waitTick();
        }
        throw new AssertionError("A failed reopen never showed Try again");
    }

    private static void resetFailures(ClientGameTestContext context) {
        context.runOnClient(client -> {
            HomeSwitch.failuresForTests(HomeSwap.FILES, false);
            HomeSwitch.holdRecoveryOpenForTests(false);
        });
    }

    /**
     * Until the switch has ended in a home. Each tick the test runs the close the switch left for it from its own task
     * (`HomeSwitch.closeFromTestTasksForTests`): in the framework's lock-step only a test task may close a world.
     */
    private static void waitForSwitch(ClientGameTestContext context) {
        for (int tick = 0; tick < SWITCH_TICKS; tick++) {
            context.runOnClient(client -> {
                switchSaves.observe(client);
                HomeSwitch.runPendingCloseForTests();
            });
            if (context.computeOnClient(client -> !HomeSwitch.busy() && client.player != null && client.gui.screen() == null)) {
                switchSaves.arrived(context);
                return;
            }
            context.waitTick();
        }
        throw new AssertionError("New home did not end in a home within " + SWITCH_TICKS + " ticks");
    }

    private static void mode(ClientGameTestContext context, TestSingleplayerContext home, GameType mode) {
        context.getInput().pressKey(InputConstants.KEY_G);
        home.getConnection().waitForServerboundPackets();
        context.waitFor(client -> client.gameMode.getPlayerMode() == mode && !ModeSwitchClient.pending());
    }

    private static void guiScale(ClientGameTestContext context, int scale) {
        context.runOnClient(client -> {
            client.options.guiScale().set(scale);
            client.resizeGui();
        });
        context.waitTicks(2);
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.runOnClient(client -> {
            client.gui.hud.getChat().clearMessages(true);
            client.gui.hud.setOverlayMessage(Component.empty(), false);
            client.gui.toastManager().clear();
        });
        context.waitTicks(5);
        context.takeScreenshot(TestScreenshotOptions.of(name)
                .withDestinationDir(Path.of(System.getProperty("aresos.homeMenuReviewDir"))));
    }

    /** A test context for the world now open, as the framework's own would be (the menu opened it, not the test). */
    private static TestSingleplayerContext adopt(ClientGameTestContext context, Path folder) {
        return new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, folder),
                context.computeOnClient(Minecraft::getSingleplayerServer));
    }

    private static Path worldFolder(Minecraft client) {
        return client.getSingleplayerServer().getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
    }

    private static Set<Path> listing(Path saves) throws IOException {
        try (Stream<Path> entries = Files.list(saves)) {
            return Set.copyOf(entries.toList());
        }
    }

    private static boolean titleScreen(String screen) {
        return screen.equals(TitleScreen.class.getName());
    }

    private static Button button(Minecraft client, String text) {
        return Screens.getWidgets(client.gui.screen()).stream().filter(Button.class::isInstance).map(Button.class::cast)
                .filter(button -> text(button).equals(text)).findFirst()
                .orElseThrow(() -> new AssertionError("No button " + text));
    }

    private static String text(AbstractWidget widget) {
        return widget.getMessage().getString();
    }

    private static List<String> chat(Minecraft client) {
        return ((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().stream()
                .map(message -> message.content().getString()).toList();
    }

    private static void delete(Path folder) throws IOException {
        if (!Files.exists(folder)) return;
        try (Stream<Path> paths = Files.walk(folder)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
