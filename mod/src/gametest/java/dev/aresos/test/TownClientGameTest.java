package dev.aresos.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import dev.aresos.AresOs;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.mixin.TextDisplayAccess;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.ZoneCommands;
import dev.aresos.zone.ZoneData;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Package 36, step 3: the town keeper's first run in the real game. A fake helper sends a complete program list; a
 * new flat home is made through the title screen; when the host is in, the keeper's own triggers, its picture thread
 * and its pass build day one's logos, with their lines in his chat and the counts on the group names. Then
 * {@code /aresos app remove} and {@code /aresos hub rebuild}, typed as he types them. No screenshots (step 4 takes
 * them, in {@link TownPicturesClientGameTest}, which uses this test's helpers and runs after it).
 */
public final class TownClientGameTest implements FabricClientGameTest {
    private static final List<String> DAY_ONE = List.of("browser", "discord", "lunar-client", "notepad", "terminal");

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        var messages = new CopyOnWriteArrayList<String>();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> { if (!overlay) messages.add(message.getString()); });
        Path sockets = null;
        FakeHelper helper = null;
        ShellClient shell = null;
        try {
            Path root = Path.of("town-fixtures").toAbsolutePath();
            deleteTree(root);
            Files.createDirectories(root);
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var firstStart = AppsConfig.load(config, true).apps();
            sockets = Files.createTempDirectory("a36");
            helper = new FakeHelper(sockets);
            helper.minor = 1;
            helper.revision = "town";
            helper.entries = List.of(
                    program("terminal", "Terminal", "image", "System"),
                    program("notepad", "Notepad", "image", "Utility"),
                    program("browser", "Chrome", "image", "Network"),
                    program("lunar-client", "Lunar Client", "user", "Game"),
                    program("discord", "Discord", "flatpak-user", "Network"));
            shell = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3), Duration.ofSeconds(1),
                    Duration.ofMillis(50), Duration.ofMillis(200), Duration.ofMillis(200)));
            var connection = shell;
            // Wired as AresOs wires its own helper: the complete list goes into the apps file and on to the town.
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(firstStart);
                AppsTestAccess.aresos$startHelper(connection, true);
            });
            shell.awaitCatalogue(Duration.ofSeconds(5));
            context.waitFor(client -> mine().equals(DAY_ONE), 200);

            Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
            openCreateScreen(context, directory);
            context.clickScreenButton("aresos.home.create");
            context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
            try (TestSingleplayerContext world = new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, directory),
                    context.computeOnClient(Minecraft::getSingleplayerServer))) {
                world.getConnection().waitForChunksRender();
                // The host is in: his join asks for the town, the picture thread reads five pictures, the pass builds.
                waitForServer(context, world, server -> HubData.get(server) != null && HubData.get(server).logos().size() == 5,
                        "The town did not stand up after the host joined", 1200);
                world.getServer().runOnServer(server -> {
                    var hub = HubData.get(server);
                    check(HubLayout.LOOK.equals(hub.look()), "Not a flat home: " + hub.look());
                    var places = hub.logos().stream().collect(Collectors.toMap(HubData.Logo::app, HubData.Logo::place));
                    check(places.get("browser").startsWith("N0") && places.get("discord").startsWith("N0") && places.get("lunar-client").equals("E0L0")
                            && places.get("notepad").startsWith("S0") && places.get("terminal").startsWith("S0"), "Day one stands at " + places);
                    check(names(server).equals(List.of("INTERNET · 2", "GAMES · 1", "SYSTEM & TOOLS · 2", "WORK & MEDIA · 0")),
                            "The group names: " + names(server));
                    var saved = AresOs.apps().stream().filter(app -> places.containsKey(app.id()))
                            .collect(Collectors.toMap(AppDefinition::id, app -> String.valueOf(app.place())));
                    check(saved.equals(places), "The apps file holds other places: " + saved);
                });
                context.waitFor(client -> messages.stream().filter(line -> line.contains(" is new. It stands in ")).count() == 5, 100);
                check(messages.stream().anyMatch(line -> line.startsWith("Chrome is new. It stands in Internet, north.")), "Chat: " + messages);

                // A command that changes My apps asks the keeper again: the logo comes down a few ticks later.
                context.runOnClient(client -> client.player.connection.sendCommand("aresos app remove discord"));
                waitForServer(context, world, server -> HubData.get(server).logo("discord").isEmpty(), "Discord's logo stayed", 600);
                context.waitFor(client -> messages.contains("Discord left My apps. Its logo came down."), 100);
                world.getServer().runOnServer(server -> check(names(server).getFirst().equals("INTERNET · 1"), "Not counted: " + names(server)));

                // hub rebuild: one line for the town.
                context.runOnClient(client -> client.player.connection.sendCommand("aresos hub rebuild"));
                context.waitFor(client -> messages.contains("The town was rebuilt from the rules: 4 logos built again."), 100);
                world.getServer().runOnServer(server -> check(HubData.get(server).logos().size() == 4, "After the rebuild: " + HubData.get(server).logos()));

                // /aresos logo never waits on a picture on the server thread (review fixes 1, step B, point 3): the
                // command returns at once and builds nothing in its own tick; the gate stands a few ticks later, once
                // the picture is read. He stands on the pad, looking north.
                world.getServer().runOnServer(server -> check(run(server, world, "aresos logo terminal") == 1 && ZoneCommands.ordered(server) == 1
                        && gates(server) == 0, "The gate was built in the command's own tick"));
                waitForServer(context, world, server -> ZoneCommands.ordered(server) == 0, "The ordered gate was never built", 200);
                context.waitFor(client -> messages.stream().anyMatch(line -> line.startsWith("Built the gate of Terminal.")), 100);
                world.getServer().runOnServer(server -> check(gates(server) == 1, "No gate after its picture was read"));
                context.runOnClient(client -> client.player.connection.sendCommand("aresos logo remove terminal"));
                waitForServer(context, world, server -> gates(server) == 0, "The gate stayed", 200);
                // He moves while the picture is read: one line, nothing built.
                world.getServer().runOnServer(server -> {
                    check(run(server, world, "aresos logo terminal") == 1, "The command failed");
                    var player = world.getConnection().getServerPlayer();
                    player.teleportTo(player.getX() + 2, player.getY(), player.getZ());
                });
                waitForServer(context, world, server -> ZoneCommands.ordered(server) == 0, "The ordered gate was never dropped", 200);
                context.waitFor(client -> messages.stream().anyMatch(line -> line.startsWith("Logo refused: you moved while the picture of Terminal was read.")), 100);
                world.getServer().runOnServer(server -> {
                    check(gates(server) == 0, "A gate was built after he moved");
                    var player = world.getConnection().getServerPlayer();
                    player.teleportTo(player.getX() - 2, player.getY(), player.getZ());
                });
            }
            AresOs.LOGGER.info("36 client checks passed: the town stands up after the host joins (a complete list, the picture thread, "
                    + "the pass), its lines and counts; app remove takes a logo down; hub rebuild says one line");
        } catch (IOException error) {
            throw new RuntimeException(error);
        } finally {
            if (shell != null) shell.close();
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(previousShell);
                AppsTestAccess.aresos$setApps(previousApps);
                AresOs.generatedIcons = previousIcons;
            });
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try {
                if (helper != null) helper.close();
                if (sockets != null) deleteTree(sockets);
            } catch (IOException error) {
                AresOs.LOGGER.warn("Could not clear the fake helper's socket folder", error);
            }
        }
    }

    private static JsonObject program(String id, String name, String source, String category) {
        var entry = FakeHelper.entry(id, name, null, source);
        var categories = new JsonArray();
        categories.add(category);
        entry.add("categories", categories);
        return entry;
    }

    private static List<String> mine() {
        return AresOs.apps().stream().filter(AppDefinition::mine).map(AppDefinition::id).sorted().toList();
    }

    /** Runs a command as the host types it, on the server thread; what it returned. */
    private static int run(MinecraftServer server, TestSingleplayerContext world, String command) {
        try {
            return server.getCommands().getDispatcher().execute(command, server.createCommandSourceStack().withEntity(world.getConnection().getServerPlayer()));
        } catch (CommandSyntaxException error) {
            throw new AssertionError(command + ": " + error.getMessage(), error);
        }
    }

    /** How many gates built by hand stand in the world. */
    private static long gates(MinecraftServer server) { return ZoneData.get(server).zones().stream().filter(AppZone::isGate).count(); }

    static List<String> names(MinecraftServer server) {
        var hub = HubData.get(server);
        return hub.fixed().names().stream().map(id -> ((TextDisplayAccess) server.getLevel(hub.home().dimension()).getEntity(id)).aresos$text().getString()).toList();
    }

    /** The title screen's way to a new AresOS home; an older one is kept aside, as package 32's test does it. */
    static void openCreateScreen(ClientGameTestContext context, Path directory) {
        context.setScreen(TitleScreen::new);
        if (Files.exists(directory)) {
            context.clickScreenButton("aresos.home.new");
            context.waitForScreen(ConfirmScreen.class);
            context.clickScreenButton("Keep old & continue");
        } else context.clickScreenButton("aresos.home");
        context.waitForScreen(HomeCreateScreen.class);
    }

    static void waitForServer(ClientGameTestContext context, TestSingleplayerContext world, Predicate<MinecraftServer> done,
                                      String failure, int ticks) {
        for (int tick = 0; tick < ticks; tick++) {
            if (world.getServer().computeOnServer(done::test)) return;
            context.waitTicks(1);
        }
        throw new AssertionError(failure);
    }

    static void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        try (var paths = Files.walk(root)) {
            for (var path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
