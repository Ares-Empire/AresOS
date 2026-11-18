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
import java.util.concurrent.atomic.AtomicReference;

/** Package 54: the rig's 40-app town, at first start and after the real New home (Flat) flow. Last in the suite. */
public final class TownArrivalClientGameTest implements FabricClientGameTest {
    private static final String BUILT = "The town is built: 40 logos. /apps lists them.";

    private record TimedLine(String text, int tick) { }

    private static final class LoadingSchedule {
        final boolean expire;
        final net.minecraft.server.MinecraftServer previous;
        volatile int first = -1;
        volatile int initial;
        volatile int completed = -1;
        volatile boolean release;

        LoadingSchedule(boolean expire, net.minecraft.server.MinecraftServer previous) {
            this.expire = expire;
            this.previous = previous;
        }

        boolean delayed(net.minecraft.server.level.ServerLevel level, net.minecraft.core.BlockPos pos) {
            var hub = HubData.get(level.getServer());
            return level.getServer() != previous && hub != null && pos.getZ() > hub.home().pos().getZ() + 16
                    && (expire ? !release : level.getServer().getTickCount() < 100);
        }

        void observe(net.minecraft.server.MinecraftServer server, int count) {
            if (server == previous) return;
            if (count > 0 && first < 0) {
                first = server.getTickCount();
                initial = count;
            }
            if (count == 40 && completed < 0) completed = server.getTickCount();
        }
    }

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
        var timed = new CopyOnWriteArrayList<TimedLine>();
        var schedule = new AtomicReference<>(new LoadingSchedule(false, null));
        var watching = new AtomicBoolean(true);
        var stagedLogos = new AtomicBoolean();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> {
            if (watching.get() && !overlay) {
                messages.add(message.getString());
                var server = Minecraft.getInstance().getSingleplayerServer();
                if (server != null) timed.add(new TimedLine(message.getString(), server.getTickCount()));
            }
        });
        // Observe the scheduler's own passes, without forcing chunks or running a pass from the test.
        ServerTickEvents.END_SERVER_TICK.register(new java.util.function.Consumer<net.minecraft.server.MinecraftServer>() {
            private Object lastServer;
            private int lastCount = -1;
            @Override public void accept(net.minecraft.server.MinecraftServer server) {
                if (!watching.get() || HubData.get(server) == null) return;
                var town = HubData.get(server);
                int count = town.logos().size();
                var currentSchedule = schedule.get();
                if (currentSchedule != null) currentSchedule.observe(server, count);
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
            TownLoading.delayed = schedule.get()::delayed;
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
            var controlled = schedule.get();
            var announced = timed.stream().filter(line -> line.text().equals(BUILT)).toList();
            check(controlled.first > 0 && controlled.first < 20 && controlled.initial > 0 && controlled.initial < 40,
                    "First start was not a controlled partial build near tick 3: " + controlled.first + ", " + controlled.initial);
            check(controlled.completed >= 100 && controlled.completed < 200 && announced.size() == 1
                            && announced.getFirst().tick() <= 200,
                    "The full first-start line missed tick 200: " + announced + ", completion " + controlled.completed);
            AresOs.LOGGER.info("54 controlled first start: {} at tick {}, 40 at tick {}, announcement {}",
                    controlled.initial, controlled.first, controlled.completed, announced);
            TownLoading.delayed = null;
            schedule.set(null);

            messages.clear();
            newHome(context);
            check(NetherHome.readKind(hub) == NetherHome.Kind.FLAT, "New home was not Flat");
            var next = arrival(context, hub, messages, "new-home-flat");
            check(!stagedLogos.get(), "The hidden staging world built logos");
            check(first.equals(List.of(BUILT)) && next.equals(List.of(BUILT)), "First start said " + first + "; New home said " + next);

            messages.clear();
            timed.clear();
            var expiring = new LoadingSchedule(true, context.computeOnClient(Minecraft::getSingleplayerServer));
            schedule.set(expiring);
            TownLoading.delayed = expiring::delayed;
            newHome(context);
            context.waitFor(client -> timed.stream().anyMatch(line -> line.text().startsWith("The town is built:")), 400);
            var partial = timed.stream().filter(line -> line.text().startsWith("The town is built:")).toList();
            int count = adopt(context, hub).getServer().computeOnServer(server -> HubData.get(server).logos().size());
            check(count > 0 && count < 40 && expiring.initial > 0 && expiring.initial < 40, "The expiry case was not partial");
            check(partial.size() == 1 && partial.getFirst().text().equals("The town is built: " + count + " logos. /apps lists them.")
                            && partial.getFirst().tick() - expiring.first >= 200 && partial.getFirst().tick() - expiring.first <= 205,
                    "The partial line did not expire 200 ticks after the first build: " + partial + ", first " + expiring.first);
            check(messages.stream().noneMatch(line -> line.startsWith("The town changed:")), "The waiting logos spoke before release");
            expiring.release = true;
            var afterExpiry = arrival(context, hub, messages, "first-build-expired");
            check(afterExpiry.equals(List.of(partial.getFirst().text(), "The town changed: " + (40 - count)
                    + " logos built. /apps lists where your apps stand.")), "After expiry: " + afterExpiry);
            AresOs.LOGGER.info("54 controlled expiry: first {} at tick {}, partial announcement {}, later builds said as a change",
                    expiring.initial, expiring.first, partial);
            AresOs.LOGGER.info("54 client checks passed: first start and New home (Flat) each built 40 logos with exactly one first-build line and no town-changed line");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            TownLoading.delayed = null;
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

    private static void newHome(ClientGameTestContext context) {
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
