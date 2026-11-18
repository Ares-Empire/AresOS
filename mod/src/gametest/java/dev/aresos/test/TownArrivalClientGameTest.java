package dev.aresos.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AresOsMenuScreen;
import dev.aresos.client.FirstStart;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.HomeSwitch;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
import dev.aresos.shell.FakeHelper;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.TitleScreen;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicBoolean;

/** Package 54: the rig's 40-app town, at first start and after the real New home (Flat) flow. Last in the suite. */
public final class TownArrivalClientGameTest implements FabricClientGameTest {
    private static final String BUILT = "The town is built: 40 logos. /apps lists them.";

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        int distance = context.computeOnClient(client -> client.options.renderDistance().get());
        Path saves = context.computeOnClient(client -> client.getLevelSource().getBaseDir().toAbsolutePath().normalize());
        Path hub = saves.resolve(NetherHome.SAVE_FOLDER);
        Path backup = saves.resolve("AresHub-test-backup-" + UUID.randomUUID());
        var before = listing(saves);
        var messages = new CopyOnWriteArrayList<String>();
        var watching = new AtomicBoolean(true);
        var stagedLogos = new AtomicBoolean();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> {
            if (watching.get() && !overlay) messages.add(message.getString());
        });
        // Observe the scheduler's own passes, without forcing chunks or running a pass from the test.
        ServerTickEvents.END_SERVER_TICK.register(new java.util.function.Consumer<net.minecraft.server.MinecraftServer>() {
            private Object lastServer;
            private int lastCount = -1;
            @Override public void accept(net.minecraft.server.MinecraftServer server) {
                if (!watching.get() || HubData.get(server) == null) return;
                var town = HubData.get(server);
                int count = town.logos().size();
                if (dev.aresos.world.DesktopWorld.saveName(server).startsWith("AresHub-new-") && count != 0) stagedLogos.set(true);
                if (lastServer == server && lastCount == count) return;
                lastServer = server;
                lastCount = count;
                var waiting = new ArrayList<String>();
                for (var app : AresOs.apps()) {
                    if (!app.mine() || app.absent() || town.logo(app.id()).isPresent() || app.place() == null) continue;
                    try { Town.check(server, Place.parse(app.place()).orElseThrow()); }
                    catch (IOException refusal) { waiting.add(app.place() + ": " + refusal.getClass().getSimpleName()); }
                }
                AresOs.LOGGER.info("54 arrival observation: {} tick {}, {} logos, waiting {}",
                        dev.aresos.world.DesktopWorld.saveName(server), server.getTickCount(), count, waiting);
            }
        }::accept);
        Path root = Path.of("town-arrival-fixtures").toAbsolutePath();
        try {
            TownClientGameTest.deleteTree(root);
            Files.createDirectories(root);
            if (Files.exists(hub)) Files.move(hub, backup);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        try (var helper = new FakeHelper(Files.createDirectories(Path.of("a54-socket")));
             var shell = helper.client(FakeHelper.fast())) {
            helper.minor = 1;
            helper.entries = programs();
            helper.revision = "town-arrival";
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var apps = AppsConfig.load(config, true).apps();
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(apps);
                AppsTestAccess.aresos$startHelper(shell, true);
                HomeScreen.forTests(true, null);
                HomeSwitch.closeFromTestTasksForTests(true);
                // The rig's view distance, enough for every logo, including the 28 tools along the south road.
                client.options.renderDistance().set(12);
                FirstStart.forTests();
            });
            shell.awaitCatalogue(Duration.ofSeconds(5));
            context.waitFor(client -> AresOs.apps().stream().filter(app -> app.mine() && !app.absent()).count() == 40, 200);
            context.setScreen(TitleScreen::new);
            context.waitFor(client -> client.player != null && client.gui.screen() == null, 6000);
            var first = arrival(context, hub, messages, "first-start");

            messages.clear();
            context.getInput().pressKey(InputConstants.KEY_ESCAPE);
            context.waitForScreen(AresOsMenuScreen.class);
            context.clickScreenButton("New home…");
            context.waitForScreen(HomeCreateScreen.class);
            context.clickScreenButton("aresos.home.create");
            context.waitForScreen(ConfirmScreen.class);
            context.clickScreenButton("Make the new home");
            for (int tick = 0; ; tick++) {
                check(tick < 6000, "New home never arrived");
                context.runOnClient(client -> HomeSwitch.runPendingCloseForTests());
                if (context.computeOnClient(client -> !HomeSwitch.busy() && client.player != null && client.gui.screen() == null)) break;
                context.waitTick();
            }
            check(NetherHome.readKind(hub) == NetherHome.Kind.FLAT, "New home was not Flat");
            var next = arrival(context, hub, messages, "new-home-flat");
            check(!stagedLogos.get(), "The hidden staging world built logos");
            check(first.equals(List.of(BUILT)) && next.equals(List.of(BUILT)), "First start said " + first + "; New home said " + next);
            AresOs.LOGGER.info("54 client checks passed: first start and New home (Flat) each built 40 logos with exactly one first-build line and no town-changed line");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            watching.set(false);
            if (context.computeOnClient(Minecraft::getSingleplayerServer) != null) adopt(context, hub).close();
            context.runOnClient(client -> {
                HomeScreen.forTests(null, null);
                HomeSwitch.closeFromTestTasksForTests(false);
                AppsTestAccess.aresos$setShell(previousShell);
                AppsTestAccess.aresos$setApps(previousApps);
                AresOs.generatedIcons = previousIcons;
                client.options.renderDistance().set(distance);
            });
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try {
                TownClientGameTest.deleteTree(hub);
                for (Path folder : listing(saves)) if (!before.contains(folder) && !folder.equals(backup)) TownClientGameTest.deleteTree(folder);
                if (Files.exists(backup)) Files.move(backup, hub);
                TownClientGameTest.deleteTree(root);
                TownClientGameTest.deleteTree(Path.of("a54-socket"));
            } catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    private static List<String> arrival(ClientGameTestContext context, Path hub, List<String> messages, String name) throws IOException {
        var world = adopt(context, hub);
        TownClientGameTest.waitForServer(context, world, server -> HubData.get(server).logos().size() == 40,
                "The 40 logos never stood", 1200);
        // Another two retry intervals catch a late line or duplicate, even after all logos stand.
        context.waitTicks(220);
        var town = messages.stream().filter(line -> line.startsWith("The town is built:") || line.startsWith("The town changed:")
                || line.contains(" is new. It stands in ")).toList();
        AresOs.LOGGER.info("54 {} chat: {}", name, town);
        context.getInput().pressKey(InputConstants.KEY_T);
        context.waitTicks(2);
        context.takeScreenshot(TestScreenshotOptions.of("54-" + name)
                .withDestinationDir(Path.of(System.getProperty("aresos.townArrivalReviewDir"))));
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        return town;
    }

    private static TestSingleplayerContextImpl adopt(ClientGameTestContext context, Path hub) {
        return new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, hub), context.computeOnClient(Minecraft::getSingleplayerServer));
    }

    private static List<Path> listing(Path saves) {
        try (var entries = Files.list(saves)) { return entries.toList(); }
        catch (IOException error) { throw new UncheckedIOException(error); }
    }

    /** Same proportions as the package 41/48 rig: 6 Internet, 3 Games, 3 Work & Media, 28 System & Tools. */
    private static List<JsonObject> programs() {
        var apps = new ArrayList<JsonObject>();
        String[] categories = {"Network", "Game", "Graphics", "Utility"};
        int[] counts = {6, 3, 3, 28};
        for (int group = 0; group < counts.length; group++) for (int i = 1; i <= counts[group]; i++) {
            var app = FakeHelper.entry("arrival-" + group + "-" + i, "Test " + categories[group] + " " + i, null, "user");
            var category = new JsonArray();
            category.add(categories[group]);
            app.add("categories", category);
            apps.add(app);
        }
        return List.copyOf(apps);
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
