package dev.aresos.test;

import com.google.gson.JsonObject;
import dev.aresos.AresOs;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.TownPicturesClientGameTest.Program;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.GatePicture;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.Mth;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;
import org.lwjgl.glfw.GLFW;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Package 37, step 3: getting around the town as he sees it, in pictures under
 * {@code reviews/37-getting-around/screenshots}. A fake helper lists day one's five programs with Mail and Spotify,
 * with the icons package 36's picture test draws; a new flat home is made through the title screen, and the town builds
 * seven logos. Then, each typed or pressed as he does it: {@code /go mail} to Mail's door in Internet's second row;
 * the H key from there; {@code /apps} with the places; the town from above before and after
 * {@code /aresos app swap chrome lunar}, a swap across two groups; and a swap refused by his torch on Discord's
 * doormat, with its line. The window is half his laptop's screen, as in package 36's pictures.
 *
 * Last in the list, so no other package's pictures are renumbered.
 */
public final class GettingAroundClientGameTest implements FabricClientGameTest {
    private static final List<Program> PROGRAMS = Stream.concat(TownPicturesClientGameTest.DAY_ONE.stream(),
            Stream.of(TownPicturesClientGameTest.MAIL, TownPicturesClientGameTest.SPOTIFY)).toList();
    /** Over the town, a little north of home so that Internet's second row is in the picture too. */
    private static final Vec3 ABOVE = new Vec3(0.5, 124, -8.5);

    @Override public void runTest(ClientGameTestContext context) {
        // Package 36's opt-in look with real icons must never reach this package's pictures, which are in the repo.
        if (System.getenv("ARESOS_TOWN_LOOK") != null) {
            AresOs.LOGGER.info("37 pictures skipped: ARESOS_TOWN_LOOK is set, and these pictures go into the repo");
            return;
        }
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        int distance = context.computeOnClient(client -> client.options.renderDistance().get());
        var messages = new CopyOnWriteArrayList<String>();
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> { if (!overlay) messages.add(message.getString()); });
        Path sockets = null;
        FakeHelper helper = null;
        ShellClient shell = null;
        try {
            Path root = Path.of("getting-around-fixtures").toAbsolutePath();
            TownClientGameTest.deleteTree(root);
            Path icons = Files.createDirectories(root.resolve("icons"));
            Path folder = Files.createDirectories(Path.of(System.getProperty("aresos.goReviewDir")));
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var firstStart = AppsConfig.load(config, true).apps();
            sockets = Files.createTempDirectory("a37");
            helper = new FakeHelper(sockets);
            helper.minor = 1;
            helper.revision = "getting-around";
            var listed = new ArrayList<JsonObject>();
            for (var program : PROGRAMS) listed.add(TownPicturesClientGameTest.entry(program, icons));
            helper.entries = List.copyOf(listed);
            shell = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3), Duration.ofSeconds(1),
                    Duration.ofMillis(50), Duration.ofMillis(200), Duration.ofMillis(200)));
            var connection = shell;
            // Wired as AresOs wires its own helper: the complete list goes into the apps file and on to the town.
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(firstStart);
                AppsTestAccess.aresos$startHelper(connection, true);
            });
            shell.awaitCatalogue(Duration.ofSeconds(5));
            var ids = PROGRAMS.stream().map(Program::id).sorted().toList();
            context.waitFor(client -> TownPicturesClientGameTest.mine().equals(ids), 200);
            // The helper's pictures also become the items' pixel icons, with a loading bar: wait until it is gone.
            context.waitFor(client -> AresOs.generatedIcons.containsAll(ids), 600);
            context.waitTicks(40);
            context.waitFor(client -> client.gui.overlay() == null, 600);

            context.getInput().resizeWindow(960, 540);
            Path directory = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
            TownClientGameTest.openCreateScreen(context, directory);
            context.clickScreenButton("aresos.home.create");
            context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
            try (TestSingleplayerContext world = new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, directory),
                    context.computeOnClient(Minecraft::getSingleplayerServer))) {
                world.getConnection().waitForChunksRender();
                TownClientGameTest.waitForServer(context, world, server -> HubData.get(server) != null && HubData.get(server).logos().size() == 7,
                        "The town did not stand up after the host joined", 1200);
                context.waitFor(client -> messages.contains("The town is built: 7 logos. /apps lists them."), 200);
                var places = world.getServer().computeOnServer(TownPicturesClientGameTest::places);
                // Mail is Internet's third app: the second row. Spotify is Work & Media's only one.
                check(places.get("browser").startsWith("N0") && places.get("discord").startsWith("N0") && places.get("mail").startsWith("N1")
                        && places.get("lunar-client").equals("E0L0") && places.get("spotify").equals("W0L0")
                        && places.get("notepad").startsWith("S0") && places.get("terminal").startsWith("S0"), "The town stands at " + places);
                AresOs.LOGGER.info("37 pictures: the town stands at {}", places);
                // The game's own distance, as in package 36's pictures (set once the world is open).
                context.runOnClient(client -> {
                    client.options.renderDistance().set(TownPicturesClientGameTest.DISTANCE);
                    client.options.broadcastOptions();
                });
                context.waitTicks(60);

                go(context, world, folder, helper, messages, places);
                apps(context, world, folder, messages, places);
                swap(context, world, folder, messages, places);
                refused(context, world, folder, messages);
            }
            AresOs.LOGGER.info("37 client checks passed: /go mail stands him at Mail's exit point in Internet's second row, looking "
                    + "at its door, says nothing and opens nothing; the H key takes him back to the pad facing north; /apps names "
                    + "each place in words; a typed swap across two groups exchanges Chrome and Lunar Client with their hand-set "
                    + "groups and the counts unchanged; his torch on Discord's doormat refuses a swap with one line, nothing changed");
            AresOs.LOGGER.info("37 pictures taken: /go to a second row and its sign looking up, the H key's arrival, /apps in the chat, the town from above "
                    + "before and after a swap across two groups, the line of a refused swap");
        } catch (IOException error) {
            throw new RuntimeException(error);
        } finally {
            if (shell != null) shell.close();
            context.runOnClient(client -> {
                client.options.renderDistance().set(distance);
                AppsTestAccess.aresos$setShell(previousShell);
                AppsTestAccess.aresos$setApps(previousApps);
                AresOs.generatedIcons = previousIcons;
            });
            context.getInput().resizeWindow(854, 480);
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try {
                if (helper != null) helper.close();
                if (sockets != null) TownClientGameTest.deleteTree(sockets);
            } catch (IOException error) {
                AresOs.LOGGER.warn("Could not clear the fake helper's socket folder", error);
            }
        }
    }

    /** {@code /go mail}: Mail's door in Internet's second row, with nothing said and nothing opened; then H, home again. */
    private static void go(ClientGameTestContext context, TestSingleplayerContext world, Path folder, FakeHelper helper,
                           List<String> messages, Map<String, String> places) {
        TownPicturesClientGameTest.clearChat(context, messages);
        int launches = helper.launches.get();
        var exit = exit(world, places.get("mail"));
        check(exit.yaw() == 180 && exit.pitch() == -10, "Mail's exit faces " + exit.yaw() + ", " + exit.pitch());
        context.runOnClient(client -> client.player.connection.sendCommand("go mail"));
        context.waitFor(client -> at(client.player.position(), client.player.getYRot(), client.player.getXRot(), exit.position(), exit.yaw(), exit.pitch()), 200);
        // Arriving is not walking in: ten ticks on the spot open nothing, and a standing logo says nothing (1-7).
        context.waitTicks(10);
        check(helper.launches.get() == launches, "/go mail opened an app");
        check(messages.isEmpty(), "/go mail said: " + messages);
        TownPicturesClientGameTest.picture(context, folder, "37-go-second-row", false);
        // At the arrival pitch the sign is above the top of the screen (HUB.md 2.2, package 36's correction): six blocks
        // from a logo twelve tall it is about 58 degrees up. The same spot, looking up: the sign he reads there.
        TownPicturesClientGameTest.look(context, world, exit.position(), exit.yaw(), -45);
        check(helper.launches.get() == launches, "Looking up opened an app");
        TownPicturesClientGameTest.picture(context, folder, "37-go-second-row-sign", false);

        context.getInput().pressKey(GLFW.GLFW_KEY_H);
        context.waitFor(client -> at(client.player.position(), client.player.getYRot(), client.player.getXRot(),
                TownPicturesClientGameTest.SPOT, 180, -8), 200);
        check(helper.launches.get() == launches && messages.isEmpty(), "The H key opened an app or said: " + messages);
        TownPicturesClientGameTest.picture(context, folder, "37-home-key", false);
    }

    /** {@code /apps} at home: every row names where its logo stands, in the words of {@link Place#words()}. */
    private static void apps(ClientGameTestContext context, TestSingleplayerContext world, Path folder, List<String> messages,
                             Map<String, String> places) {
        TownPicturesClientGameTest.clearChat(context, messages);
        context.runOnClient(client -> client.player.connection.sendCommand("apps"));
        context.waitFor(client -> messages.size() >= 1 + PROGRAMS.size(), 100);
        check(messages.getFirst().equals("My apps: 7. Click one to open it."), "/apps began with " + messages);
        for (var program : PROGRAMS) {
            var app = AresOs.app(program.id());
            String row = app.name() + ": " + app.names().stream().map(name -> "/" + name).collect(Collectors.joining(", ")) + ". "
                    + Place.parse(places.get(program.id())).orElseThrow().words();
            check(messages.contains(row), "/apps has no row \"" + row + "\": " + messages);
        }
        check(messages.contains("Mail: /mail. Internet, north, row 2, left"), "Mail's row: " + messages);
        TownPicturesClientGameTest.picture(context, folder, "37-apps-chat", true);
    }

    /**
     * From above in Build mode: Chrome (Internet) and Lunar Client (Games) change places by the typed command. Each
     * takes the other's group by hand, the doormats change colour with the group, and the counts stay.
     */
    private static void swap(ClientGameTestContext context, TestSingleplayerContext world, Path folder, List<String> messages,
                             Map<String, String> places) {
        var names = world.getServer().computeOnServer(TownClientGameTest::names);
        check(names.equals(List.of("INTERNET · 3", "GAMES · 1", "SYSTEM & TOOLS · 2", "WORK & MEDIA · 1")), "The group names: " + names);
        TownPicturesClientGameTest.mode(context, world, GameType.CREATIVE);
        TownPicturesClientGameTest.hover(context, world, ABOVE, 180, 90);
        TownPicturesClientGameTest.picture(context, folder, "37-swap-before", false);

        String chrome = places.get("browser");
        TownPicturesClientGameTest.clearChat(context, messages);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos app swap chrome lunar"));
        TownClientGameTest.waitForServer(context, world, server -> {
            var now = TownPicturesClientGameTest.places(server);
            return "E0L0".equals(now.get("browser")) && chrome.equals(now.get("lunar-client"));
        }, "Chrome and Lunar Client did not change places", 200);
        String line = "Chrome now stands at Games, east, front row, left, and Lunar Client at "
                + Place.parse(chrome).orElseThrow().words() + ".";
        context.waitFor(client -> messages.contains(line), 100);
        check(messages.size() == 1, "The swap said more than its line: " + messages);
        world.getServer().runOnServer(server -> {
            var now = TownPicturesClientGameTest.places(server);
            places.forEach((app, place) -> check(app.equals("browser") || app.equals("lunar-client") || place.equals(now.get(app)),
                    app + " moved: " + now));
            check(TownClientGameTest.names(server).equals(names), "The counts changed: " + TownClientGameTest.names(server));
            // The doormats are in the new groups' colours: Chrome's in Games' red, Lunar Client's in Internet's light blue.
            check(doormat(server, "E0L0").equals("minecraft:red_concrete") && doormat(server, chrome).equals("minecraft:light_blue_concrete"),
                    "The doormats: " + doormat(server, "E0L0") + ", " + doormat(server, chrome));
        });
        check("E0L0".equals(AresOs.app("browser").place()) && "games".equals(AresOs.app("browser").group())
                && chrome.equals(AresOs.app("lunar-client").place()) && "internet".equals(AresOs.app("lunar-client").group()),
                "The apps file holds " + AresOs.app("browser") + " and " + AresOs.app("lunar-client"));
        TownPicturesClientGameTest.picture(context, folder, "37-swap-after", false);
        places.put("browser", "E0L0");
        places.put("lunar-client", chrome);
    }

    /**
     * In Live mode again, at Discord's door: his torch on Discord's doormat, and {@code /aresos app swap discord
     * spotify}. Discord's logo cannot come down, so nothing changes, in the file or the world, and one line says why.
     */
    private static void refused(ClientGameTestContext context, TestSingleplayerContext world, Path folder, List<String> messages) {
        TownPicturesClientGameTest.look(context, world, TownPicturesClientGameTest.SPOT, 180, -8);
        TownPicturesClientGameTest.mode(context, world, GameType.SURVIVAL);
        var before = world.getServer().computeOnServer(TownPicturesClientGameTest::places);
        String discord = before.get("discord");
        var exit = exit(world, discord);
        context.runOnClient(client -> client.player.connection.sendCommand("go discord"));
        context.waitFor(client -> at(client.player.position(), client.player.getYRot(), client.player.getXRot(), exit.position(), exit.yaw(), exit.pitch()), 200);
        // His torch, placed as his own blocks are: not through the town's record.
        var torch = world.getServer().computeOnServer(server -> {
            var hub = HubData.get(server);
            var place = Place.parse(discord).orElseThrow();
            var front = place.plan(GatePicture.plain(GatePalette.name(place.group().concrete()), HubLayout.SIZE), hub.home().dimension(),
                    hub.home().pos(), "?", null).doormat().getFirst().above();
            check(BuiltInRegistries.BLOCK.getKey(server.overworld().getBlockState(front.below()).getBlock()).toString().endsWith("_concrete"),
                    "No doormat under " + front.toShortString());
            server.overworld().setBlockAndUpdate(front, Blocks.TORCH.defaultBlockState());
            return front;
        });
        var file = Stream.of("discord", "spotify").map(AresOs::app).toList();
        TownPicturesClientGameTest.clearChat(context, messages);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos app swap discord spotify"));
        String start = "Nothing was swapped: Discord's logo at " + Place.parse(discord).orElseThrow().words()
                + " cannot come down. Logo could disturb neighboring minecraft:torch at ";
        context.waitFor(client -> messages.stream().anyMatch(line -> line.startsWith(start)), 100);
        check(messages.size() == 1, "The refusal said more than one line: " + messages);
        world.getServer().runOnServer(server -> {
            check(TownPicturesClientGameTest.places(server).equals(before), "The town changed: " + TownPicturesClientGameTest.places(server));
            check(server.overworld().getBlockState(torch).is(Blocks.TORCH), "His torch is gone");
        });
        check(Stream.of("discord", "spotify").map(AresOs::app).toList().equals(file), "The apps file changed");
        // From where /go put him, looking down at the torch: at the arrival pitch it is behind the chat's lines.
        TownPicturesClientGameTest.look(context, world, exit.position(), exit.yaw(), 15);
        TownPicturesClientGameTest.picture(context, folder, "37-swap-refused", true);
    }

    /** Where {@code /go} puts him for a place of this town: its exit point and facing. */
    private static NetherHome.Home exit(TestSingleplayerContext world, String place) {
        return world.getServer().computeOnServer(server -> {
            var hub = HubData.get(server);
            return Place.parse(place).orElseThrow().exit(hub.home().dimension(), hub.home().pos());
        });
    }

    /** The concrete under the first doormat block of the logo at a place. */
    private static String doormat(MinecraftServer server, String name) {
        var hub = HubData.get(server);
        var place = Place.parse(name).orElseThrow();
        var below = place.plan(GatePicture.plain(GatePalette.name(place.group().concrete()), HubLayout.SIZE), hub.home().dimension(),
                hub.home().pos(), "?", null).doormat().getFirst();
        return BuiltInRegistries.BLOCK.getKey(server.overworld().getBlockState(below).getBlock()).toString();
    }

    private static boolean at(Vec3 position, float yaw, float pitch, Vec3 target, float targetYaw, float targetPitch) {
        return position.distanceToSqr(target) < 1.0e-4 && Math.abs(Mth.wrapDegrees(yaw - targetYaw)) < 0.5 && Math.abs(pitch - targetPitch) < 0.5;
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
