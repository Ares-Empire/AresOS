package dev.aresos.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import dev.aresos.AresOs;
import dev.aresos.client.WorldSaves;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.FakeSupervisor;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Package 46's measurement, on the laptop only: {@code mod/dev/client-test.sh -PmeasureSaves} (otherwise it does
 * nothing). How long a requested save takes in a flat home with a town of 40 test apps (package 41's mix: 6 Internet,
 * 3 Games, 3 Work & Media, 28 System & Tools), at the product's render distance 8 and simulation distance 5:
 * right after joining the home again, after a 60-second glide over new ground (package 41's route and speed: 1.08
 * blocks a tick, north 15 s, south 30 s, north 15 s, about 21 blocks up), and after the same glide over that ground
 * again. Each {@code ms} is the mod's own answer, through the real lifecycle client and {@link WorldSaves}.
 * The times go to the log as "46 save time" lines.
 */
public final class SaveTimesClientGameTest implements FabricClientGameTest {
    private static final int APPS = 40;
    private static final double STEP = 1.08;

    @Override public void runTest(ClientGameTestContext context) {
        if (!Boolean.getBoolean("aresos.measureSaves")) {
            AresOs.LOGGER.info("46 save times not measured (mod/dev/client-test.sh -PmeasureSaves measures them)");
            return;
        }
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        int previousRender = context.computeOnClient(client -> client.options.renderDistance().get());
        int previousSimulation = context.computeOnClient(client -> client.options.simulationDistance().get());
        var times = new ArrayList<String>();
        Path root = Path.of("save-times-fixtures").toAbsolutePath();
        Path sockets = null;
        FakeHelper helper = null;
        ShellClient shell = null;
        try {
            TownClientGameTest.deleteTree(root);
            Files.createDirectories(root);
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var firstStart = AppsConfig.load(config, true).apps();
            sockets = Files.createTempDirectory("a46m");
            helper = new FakeHelper(sockets);
            helper.minor = 1;
            helper.revision = "save-times";
            helper.entries = programs();
            shell = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3), Duration.ofSeconds(1),
                    Duration.ofMillis(50), Duration.ofMillis(200), Duration.ofMillis(200)));
            var connection = shell;
            context.runOnClient(client -> {
                client.options.renderDistance().set(8);
                client.options.simulationDistance().set(5);
                AppsTestAccess.aresos$setApps(firstStart);
                AppsTestAccess.aresos$startHelper(connection, true);
            });
            shell.awaitCatalogue(Duration.ofSeconds(5));
            context.waitFor(client -> AresOs.apps().stream().filter(app -> app.mine()).count() == APPS, 400);

            Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
            TownClientGameTest.openCreateScreen(context, directory);
            context.clickScreenButton("aresos.home.create");
            context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
            try (TestSingleplayerContext world = new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, directory),
                    context.computeOnClient(Minecraft::getSingleplayerServer))) {
                world.getConnection().waitForChunksRender();
                TownClientGameTest.waitForServer(context, world, server -> HubData.get(server) != null
                        && HubData.get(server).logos().size() == APPS, "The town of " + APPS + " did not stand up", 2400);
                context.waitTicks(100);
            }

            // Joining the home again, as at every start of the desktop.
            try (var supervisor = new FakeSupervisor(sockets.resolve("d.sock"));
                 var lifecycle = supervisor.client(WorldSaves.INSTANCE);
                 TestSingleplayerContext world = new TestWorldSaveImpl(context, directory).open()) {
                lifecycle.start();
                world.getConnection().waitForChunksRender();
                context.waitTicks(100);
                times.add(save(context, world, supervisor, 1, "right after joining"));
                // Upwards, then the three legs at full flying speed; every tick one step, as package 41's glide.
                for (int lap = 1; lap <= 2; lap++) {
                    glide(context, world);
                    times.add(save(context, world, supervisor, 1 + lap, lap == 1 ? "after a 60 s glide over new ground"
                            : "after the same glide over that ground again"));
                }
            }
            AresOs.LOGGER.info("46 save times (render 8, simulation 5, {} apps): {}", APPS, String.join("; ", times));
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            if (shell != null) shell.close();
            context.runOnClient(client -> {
                client.options.renderDistance().set(previousRender);
                client.options.simulationDistance().set(previousSimulation);
                AppsTestAccess.aresos$setShell(previousShell);
                AppsTestAccess.aresos$setApps(previousApps);
                AresOs.generatedIcons = previousIcons;
            });
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try {
                if (helper != null) helper.close();
                if (sockets != null) TownClientGameTest.deleteTree(sockets);
            } catch (IOException error) {
                AresOs.LOGGER.warn("Could not clear the measurement's socket folder", error);
            }
        }
    }

    /** One requested save; its answer's ms with the loaded chunk count, as one log line. */
    private static String save(ClientGameTestContext context, TestSingleplayerContext world, FakeSupervisor supervisor, int id,
                               String when) throws IOException {
        int chunks = world.getServer().computeOnServer(server -> world.getConnection().getServerLevel().getChunkSource().getLoadedChunksCount());
        supervisor.save(id, "backup");
        context.waitFor(client -> !supervisor.answers(id).isEmpty(), 2400);
        JsonObject answer = supervisor.answers(id).getFirst();
        if (!answer.get("ok").getAsBoolean()) throw new AssertionError("Not saved " + when + ": " + answer);
        String line = when + ": " + answer.get("ms").getAsLong() + " ms (" + chunks + " chunks loaded)";
        AresOs.LOGGER.info("46 save time {}", line);
        return line;
    }

    /** Package 41's route: up about 21 blocks, north 15 s, south 30 s, north 15 s, 1.08 blocks every tick. */
    private static void glide(ClientGameTestContext context, TestSingleplayerContext world) {
        Vec3 start = world.getServer().computeOnServer(server -> world.getConnection().getServerPlayer().position());
        double x = start.x, y = start.y + 21, z = start.z;
        int[] legs = {300, 600, 300};
        double[] directions = {-1, 1, -1};
        for (int leg = 0; leg < legs.length; leg++) {
            float yaw = directions[leg] < 0 ? 180 : 0;
            for (int tick = 0; tick < legs[leg]; tick++) {
                z += directions[leg] * STEP;
                double nextZ = z;
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    player.getAbilities().flying = true;
                    player.teleportTo(player.level(), x, y, nextZ, Set.of(), yaw, 0, false);
                });
                context.waitTick();
            }
        }
        context.waitTicks(40);
    }

    /** 40 programs in package 41's proportions; categories put them in the four groups. */
    private static List<JsonObject> programs() {
        var groups = new String[][] {{"web", "Network", "6"}, {"game", "Game", "3"}, {"media", "Graphics", "3"},
                {"tool", "Utility", "28"}};
        var rows = new ArrayList<JsonObject>();
        for (var group : groups) {
            for (int i = 1; i <= Integer.parseInt(group[2]); i++) {
                var entry = FakeHelper.entry(group[0] + String.format("%02d", i), "Test " + group[0] + " " + i, null, "user");
                var categories = new JsonArray();
                categories.add(group[1]);
                entry.add("categories", categories);
                rows.add(entry);
            }
        }
        return rows;
    }
}
