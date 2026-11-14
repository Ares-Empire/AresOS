package dev.aresos.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.mode.ModeInventories;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import javax.imageio.ImageIO;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.geom.Ellipse2D;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

/**
 * Package 36, step 4: the town as he sees it, in pictures under {@code reviews/36-town/screenshots}. A fake helper
 * lists day one's five programs with icons this test draws; a new flat home is made through the title screen. Then,
 * in this order: his first arrival (with the chat), the arrival view, east, south and west; a program that joins while
 * he stands at home; its removal; the town from above in Build mode; a place blocked by his own hut; forty apps from
 * above, from the air and along the south road. The window is half his laptop's screen (1920 x 1080 at the game's
 * scale 4), so the chat and the hotbar are as large in the picture as on his screen.
 *
 * Every icon is this test's own drawing: a plain figure on a tile or a disc, or a bare shape. No real app's icon.
 * Last in the list, so no other package's pictures are renumbered.
 */
public final class TownPicturesClientGameTest implements FabricClientGameTest {
    /**
     * Opt-in, for looking at the town with real app icons without putting them into the repo: a folder outside the
     * repo holding {@code chrome.png}, {@code discord.png} and {@code lunar-client.png}. The arrival view and the
     * view east go to its {@code screenshots} folder, and nothing else is pictured.
     */
    private static final String LOOK = System.getenv("ARESOS_TOWN_LOOK");
    private static final Map<String, String> REAL = Map.of("browser", "chrome.png", "discord", "discord.png", "lunar-client", "lunar-client.png");

    private static final Vec3 SPOT = new Vec3(0.5, 64, 0.5);
    /** His own build in the place N1L0, whose logo would fill x -15 to -4 and z -36 to -34 (HUB.md 3.2). */
    private static final BlockPos HUT_MIN = new BlockPos(-12, 64, -37), HUT_MAX = new BlockPos(-8, 68, -33);
    /** The game's own render distance. The test client starts with 5 chunks, which fogs the far rows and the view from above. */
    private static final int DISTANCE = 12;

    private enum Plate { TILE, DISC, BARE }

    private enum Figure {
        STAR, BUBBLE, PROMPT, PAGE, NOTE, ENVELOPE, COMPASS, RING, PLAY, PLUS, BARS, DIAMOND, HEART, CLOUD, FOLDER, GEAR, BOLT,
        CLOCK, CAMERA, CHECKER, PAWN, GRID, SHIELD, ARROW, MOUNTAIN, DICE, LETTER, CODE, CHART, LOCK, GLOBE
    }

    /**
     * A program of the fixture: what the system says about it, and its drawn icon. On a tile or a disc the figure is
     * {@code fore} on {@code back}; a bare figure is {@code fore} with details in {@code back}.
     */
    private record Program(String id, String name, String source, String category, Plate plate, int back, Figure figure, int fore) { }

    /** Day one (HUB.md 2.4): the three starters and the two programs he installed himself. */
    private static final List<Program> DAY_ONE = List.of(
            new Program("terminal", "Terminal", "image", "System", Plate.TILE, 0x263238, Figure.PROMPT, 0x69f0ae),
            new Program("notepad", "Notepad", "image", "Utility", Plate.BARE, 0xd84315, Figure.PAGE, 0xfff3c4),
            new Program("browser", "Chrome", "image", "Network", Plate.BARE, 0x43a047, Figure.GLOBE, 0x1e88e5),
            new Program("lunar-client", "Lunar Client", "user", "Game", Plate.TILE, 0x161a2e, Figure.STAR, 0xffd54f),
            new Program("discord", "Discord", "flatpak-user", "Network", Plate.TILE, 0x3949ab, Figure.BUBBLE, 0xffffff));
    private static final Program SPOTIFY = new Program("spotify", "Spotify", "flatpak-user", "AudioVideo", Plate.DISC, 0xad1457, Figure.NOTE, 0xffffff);
    private static final Program MAIL = new Program("mail", "Mail", "flatpak-user", "Network", Plate.TILE, 0x29b6f6, Figure.ENVELOPE, 0xffffff);
    /** With day one and Mail these make forty: 10 Internet, 8 Games, 8 Work & Media, 14 System & Tools (HUB.md 2.2). */
    private static final List<Program> MORE = List.of(
            new Program("messenger", "Messenger", "flatpak-user", "Network", Plate.DISC, 0x00897b, Figure.BUBBLE, 0xffffff),
            new Program("feeds", "Feeds", "user", "Network", Plate.TILE, 0xf4511e, Figure.BARS, 0xffffff),
            new Program("downloads", "Downloads", "user", "Network", Plate.TILE, 0x2e7d32, Figure.ARROW, 0xffffff),
            new Program("remote-desk", "Remote Desk", "flatpak-user", "Network", Plate.TILE, 0x455a64, Figure.CODE, 0x80deea),
            new Program("cloud-sync", "Cloud Sync", "flatpak-user", "Network", Plate.BARE, 0x0277bd, Figure.CLOUD, 0x4fc3f7),
            new Program("web-radio", "Web Radio", "user", "Network", Plate.DISC, 0x6a1b9a, Figure.RING, 0xffd54f),
            new Program("vpn", "VPN", "user", "Network", Plate.BARE, 0x90caf9, Figure.SHIELD, 0x1565c0),
            new Program("chess", "Chess", "flatpak-user", "Game", Plate.TILE, 0x5d4037, Figure.PAWN, 0xffecb3),
            new Program("solitaire", "Solitaire", "flatpak-user", "Game", Plate.TILE, 0x1b5e20, Figure.HEART, 0xe53935),
            new Program("kart-racer", "Kart Racer", "user", "Game", Plate.BARE, 0xfafafa, Figure.CHECKER, 0x212121),
            new Program("block-puzzle", "Block Puzzle", "flatpak-user", "Game", Plate.TILE, 0x283593, Figure.GRID, 0xffca28),
            new Program("mines", "Mines", "user", "Game", Plate.DISC, 0x37474f, Figure.BOLT, 0xffeb3b),
            new Program("dice", "Dice", "user", "Game", Plate.BARE, 0xc62828, Figure.DICE, 0xfafafa),
            new Program("space-run", "Space Run", "flatpak-user", "Game", Plate.TILE, 0x12091f, Figure.COMPASS, 0xb388ff),
            new Program("writer", "Writer", "flatpak-user", "Office", Plate.TILE, 0x1565c0, Figure.LETTER, 0xffffff),
            new Program("sheets", "Sheets", "flatpak-user", "Office", Plate.TILE, 0x2e7d32, Figure.GRID, 0xffffff),
            new Program("slides", "Slides", "flatpak-user", "Office", Plate.TILE, 0xf9a825, Figure.CHART, 0x4e342e),
            new Program("paint", "Paint", "user", "Graphics", Plate.BARE, 0xffffff, Figure.DIAMOND, 0xec407a),
            new Program("photos", "Photos", "flatpak-user", "Graphics", Plate.TILE, 0x00838f, Figure.MOUNTAIN, 0xffffff),
            new Program("music", "Music", "flatpak-user", "Audio", Plate.TILE, 0xd81b60, Figure.NOTE, 0xffffff),
            new Program("video-player", "Video Player", "user", "Video", Plate.TILE, 0x212121, Figure.PLAY, 0xff7043),
            new Program("code-editor", "Code Editor", "flatpak-user", "Development", Plate.TILE, 0x1a237e, Figure.CODE, 0x80d8ff),
            new Program("files", "Files", "user", "Utility", Plate.BARE, 0xff8f00, Figure.FOLDER, 0xffb300),
            new Program("calculator", "Calculator", "user", "Utility", Plate.TILE, 0x546e7a, Figure.PLUS, 0xffffff),
            new Program("clock", "Clock", "user", "Utility", Plate.BARE, 0x263238, Figure.CLOCK, 0xeceff1),
            new Program("settings", "Settings", "user", "Settings", Plate.TILE, 0x78909c, Figure.GEAR, 0xffffff),
            new Program("archive", "Archive", "user", "Utility", Plate.TILE, 0x8d6e63, Figure.BARS, 0xffe0b2),
            new Program("disks", "Disks", "user", "System", Plate.DISC, 0x424242, Figure.RING, 0x90caf9),
            new Program("system-monitor", "System Monitor", "user", "System", Plate.TILE, 0x004d40, Figure.CHART, 0x69f0ae),
            new Program("screenshot", "Screenshot", "user", "Utility", Plate.TILE, 0x4527a0, Figure.CAMERA, 0xffffff),
            new Program("fonts", "Fonts", "user", "Utility", Plate.BARE, 0x3e2723, Figure.LETTER, 0x6d4c41),
            new Program("backup", "Backup", "user", "System", Plate.DISC, 0x0277bd, Figure.ARROW, 0xffffff),
            new Program("passwords", "Passwords", "flatpak-user", "Utility", Plate.TILE, 0xfdd835, Figure.LOCK, 0x263238),
            new Program("printers", "Printers", "user", "Settings", Plate.TILE, 0xb0bec5, Figure.PAGE, 0xffffff));

    @Override public void runTest(ClientGameTestContext context) {
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
            Path root = Path.of("town-pictures-fixtures").toAbsolutePath();
            TownClientGameTest.deleteTree(root);
            Path icons = Files.createDirectories(root.resolve("icons"));
            Path folder = Files.createDirectories(LOOK != null ? Path.of(LOOK, "screenshots") : Path.of(System.getProperty("aresos.townReviewDir")));
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var firstStart = AppsConfig.load(config, true).apps();
            sockets = Files.createTempDirectory("a36p");
            helper = new FakeHelper(sockets);
            helper.minor = 1;
            helper.revision = "day-one";
            var listed = new ArrayList<JsonObject>();
            for (var program : DAY_ONE) listed.add(entry(program, icons));
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
            var dayOne = DAY_ONE.stream().map(Program::id).sorted().toList();
            context.waitFor(client -> mine().equals(dayOne), 200);
            // The helper's pictures also become the items' pixel icons, and the game loads them by itself: its
            // loading bar must be gone before a button is clicked or a picture is taken.
            context.waitFor(client -> AresOs.generatedIcons.containsAll(dayOne), 600);
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
                TownClientGameTest.waitForServer(context, world, server -> HubData.get(server) != null && HubData.get(server).logos().size() == 5,
                        "The town did not stand up after the host joined", 1200);
                context.waitFor(client -> messages.stream().filter(line -> line.contains(" is new. It stands in ")).count() == 5, 200);
                var places = world.getServer().computeOnServer(TownPicturesClientGameTest::places);
                check(places.get("browser").startsWith("N0") && places.get("discord").startsWith("N0") && places.get("lunar-client").equals("E0L0")
                        && places.get("notepad").startsWith("S0") && places.get("terminal").startsWith("S0"), "Day one stands at " + places);
                AresOs.LOGGER.info("36 pictures: day one stands at {}, the names say {}", places,
                        world.getServer().computeOnServer(TownClientGameTest::names));
                // The first arrival keeps its chat: the town's lines about day one are part of what he sees then.
                if (LOOK == null) picture(context, folder, "town-first-arrival", true);
                // From here on the game's own distance. Not before the world opens: the test API's wait for the first
                // chunks did not end within its minute when the world was entered at this distance.
                context.runOnClient(client -> {
                    client.options.renderDistance().set(DISTANCE);
                    client.options.broadcastOptions();
                });
                context.waitTicks(60);
                if (LOOK != null) {
                    picture(context, folder, "town-arrival", false);
                    look(context, world, SPOT, -90, -8);
                    picture(context, folder, "town-east", false);
                    AresOs.LOGGER.info("36 pictures: the arrival view and the view east with the icons of {} are in {}", LOOK, folder);
                    return;
                }
                dayOne(context, world, folder);
                joinAndRemoval(context, world, folder, helper, listed, icons, messages);
                blocked(context, world, folder, helper, listed, icons, messages);
                forty(context, world, folder, helper, listed, icons, messages);
            }
            AresOs.LOGGER.info("36 pictures taken: the first arrival with its chat lines, the arrival view, east, south and west; Spotify "
                    + "joining at W0L0 and coming down again; the town from above in Build mode; Mail standing one place on from his "
                    + "hut in N1L0; forty apps from above, from the air and along the south road");
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

    /** The four views from the home spot (HUB.md 1). */
    private static void dayOne(ClientGameTestContext context, TestSingleplayerContext world, Path folder) {
        picture(context, folder, "town-arrival", false);
        String[] names = {"east", "south", "west"};
        float[] yaws = {-90, 0, 90};
        for (int i = 0; i < names.length; i++) {
            look(context, world, SPOT, yaws[i], -8);
            picture(context, folder, "town-" + names[i], false);
        }
    }

    /** He stands at home and looks west: Spotify is installed and its logo appears; he removes it and the grass is back. */
    private static void joinAndRemoval(ClientGameTestContext context, TestSingleplayerContext world, Path folder, FakeHelper helper,
                                       List<JsonObject> listed, Path icons, List<String> messages) throws IOException {
        clearChat(context, messages);
        list(helper, listed, icons, List.of(SPOTIFY), "spotify");
        TownClientGameTest.waitForServer(context, world, server -> "W0L0".equals(places(server).get("spotify")), "Spotify's logo did not appear at W0L0", 600);
        context.waitFor(client -> messages.stream().anyMatch(line -> line.startsWith("Spotify is new. It stands in Work & Media, west.")), 200);
        icons(context, List.of(SPOTIFY));
        picture(context, folder, "town-join", true);
        // One line about the new app: the town's. My apps keeps its own line for worlds without a town.
        check(messages.stream().noneMatch(line -> line.contains("joined My apps")), "Two lines about one new app: " + messages);

        clearChat(context, messages);
        context.runOnClient(client -> client.player.connection.sendCommand("aresos app remove spotify"));
        TownClientGameTest.waitForServer(context, world, server -> HubData.get(server).logo("spotify").isEmpty(), "Spotify's logo stayed", 600);
        context.waitFor(client -> messages.contains("Spotify left My apps. Its logo came down."), 200);
        world.getServer().runOnServer(server -> {
            // W0L0 (HUB.md 3.2): x -22 to -20, z 4 to 15. Its ground is the untouched grass again.
            for (BlockPos pos : BlockPos.betweenClosed(new BlockPos(-22, 63, 4), new BlockPos(-20, 63, 15)))
                check(server.overworld().getBlockState(pos).is(Blocks.GRASS_BLOCK) && server.overworld().getBlockState(pos.above()).isAir(),
                        "The grass is not back at " + pos.toShortString());
            check(TownClientGameTest.names(server).getLast().equals("WORK & MEDIA · 0"), "Not counted: " + TownClientGameTest.names(server));
        });
        picture(context, folder, "town-removal", true);
    }

    /** Build mode: the town from above; then his hut in N1L0, and Mail, which is installed after it, stands at N1R0. */
    private static void blocked(ClientGameTestContext context, TestSingleplayerContext world, Path folder, FakeHelper helper,
                                List<JsonObject> listed, Path icons, List<String> messages) throws IOException {
        mode(context, world, GameType.CREATIVE);
        hover(context, world, new Vec3(0.5, 114, 0.5), 180, 90);
        picture(context, folder, "town-above-build", false);

        world.getServer().runOnServer(server -> hut(server.overworld()));
        hover(context, world, new Vec3(0.5, 98, -2.5), 180, 55);
        clearChat(context, messages);
        list(helper, listed, icons, List.of(MAIL), "mail");
        TownClientGameTest.waitForServer(context, world, server -> "N1R0".equals(places(server).get("mail")), "Mail does not stand at N1R0", 600);
        context.waitFor(client -> messages.contains("N1L0 is blocked by something of yours, so Mail stands at N1R0."), 200);
        world.getServer().runOnServer(server -> check(server.overworld().getBlockState(HUT_MIN).is(Blocks.OAK_PLANKS)
                && server.overworld().getBlockState(HUT_MAX).is(Blocks.COBBLESTONE), "His hut was touched"));
        icons(context, List.of(MAIL));
        picture(context, folder, "town-blocked", true);
    }

    /** Thirty-four more programs at once: forty apps, fourteen of them in System & Tools, rows 0 to 3 (HUB.md 2.2). */
    private static void forty(ClientGameTestContext context, TestSingleplayerContext world, Path folder, FakeHelper helper,
                              List<JsonObject> listed, Path icons, List<String> messages) throws IOException {
        clearChat(context, messages);
        list(helper, listed, icons, MORE, "forty");
        TownClientGameTest.waitForServer(context, world, server -> HubData.get(server).logos().size() == 40, "Forty logos did not stand up", 1200);
        context.waitFor(client -> messages.stream().anyMatch(line -> line.startsWith("The town changed: 34 logos built.")), 200);
        world.getServer().runOnServer(server -> {
            check(TownClientGameTest.names(server).equals(List.of("INTERNET · 10", "GAMES · 8", "SYSTEM & TOOLS · 14", "WORK & MEDIA · 8")),
                    "The group names: " + TownClientGameTest.names(server));
            check(server.overworld().getBlockState(HUT_MIN).is(Blocks.OAK_PLANKS), "His hut was touched");
            AresOs.LOGGER.info("36 pictures: forty stand at {}", places(server));
        });
        icons(context, MORE);
        hover(context, world, new Vec3(0.5, 164, 0.5), 180, 90);
        picture(context, folder, "town-forty-above", false);
        // From the south-east corner, looking north-west: the fronts of Internet and Work & Media, the backs of the others.
        hover(context, world, new Vec3(62.5, 102, 62.5), 135, 31);
        // The far end of the town is nine chunks from here: give its chunks time to arrive (a picture, not a check).
        context.waitTicks(100);
        picture(context, folder, "town-forty-from-the-air", false);

        // Live mode again, at home: what he sees of the biggest group from the pad, and when he has passed its front row.
        look(context, world, SPOT, 0, -8);
        mode(context, world, GameType.SURVIVAL);
        look(context, world, SPOT, 0, -8);
        // The name of the item in his hand shows for two seconds after the switch.
        context.waitTicks(60);
        picture(context, folder, "town-forty-south", false);
        look(context, world, new Vec3(0.5, 64, 24.5), 0, -8);
        picture(context, folder, "town-forty-south-past-row-0", false);
    }

    /** The system lists more programs: the helper's list grows and it says so, as after an install. */
    private static void list(FakeHelper helper, List<JsonObject> listed, Path icons, List<Program> more, String revision) throws IOException {
        for (var program : more) listed.add(entry(program, icons));
        helper.entries = List.copyOf(listed);
        helper.revision = revision;
        helper.event("apps_changed", Map.of("revision", revision));
    }

    /**
     * The new programs' pictures also become pixel icons, a moment after the list (at most one loading every five
     * seconds), and the game then loads its resources again with a loading bar: wait until that has come and gone.
     */
    private static void icons(ClientGameTestContext context, List<Program> programs) {
        var ids = programs.stream().map(Program::id).toList();
        context.waitFor(client -> AresOs.generatedIcons.containsAll(ids), 600);
        context.waitTicks(20);
        context.waitFor(client -> client.gui.overlay() == null, 600);
    }

    private static JsonObject entry(Program program, Path icons) throws IOException {
        var entry = FakeHelper.entry(program.id(), program.name(), null, program.source());
        var categories = new JsonArray();
        categories.add(program.category());
        entry.add("categories", categories);
        Path file = LOOK != null && REAL.containsKey(program.id()) ? Path.of(LOOK, REAL.get(program.id())) : null;
        if (file == null || !Files.isRegularFile(file)) {
            file = icons.resolve(program.id() + ".png");
            ImageIO.write(draw(program), "png", file.toFile());
        }
        entry.addProperty("icon", file.toString());
        return entry;
    }

    // What the town is.

    private static List<String> mine() {
        return AresOs.apps().stream().filter(AppDefinition::mine).map(AppDefinition::id).sorted().toList();
    }

    /** Every standing logo: app to place. */
    private static Map<String, String> places(MinecraftServer server) {
        return HubData.get(server).logos().stream().collect(Collectors.toMap(HubData.Logo::app, HubData.Logo::place, (first, second) -> first, TreeMap::new));
    }

    /** A plank hut with a cobblestone roof and a door, placed as his own blocks are: not through the town's record. */
    private static void hut(ServerLevel level) {
        for (BlockPos each : BlockPos.betweenClosed(HUT_MIN, HUT_MAX)) {
            BlockPos pos = each.immutable();
            boolean wall = pos.getX() == HUT_MIN.getX() || pos.getX() == HUT_MAX.getX() || pos.getZ() == HUT_MIN.getZ() || pos.getZ() == HUT_MAX.getZ();
            boolean door = pos.getX() == -10 && pos.getZ() == HUT_MAX.getZ() && pos.getY() <= HUT_MIN.getY() + 1;
            if (pos.getY() == HUT_MAX.getY()) level.setBlockAndUpdate(pos, Blocks.COBBLESTONE.defaultBlockState());
            else if (wall && !door) level.setBlockAndUpdate(pos, Blocks.OAK_PLANKS.defaultBlockState());
        }
    }

    // Where he stands and what the picture shows.

    private static void look(ClientGameTestContext context, TestSingleplayerContext world, Vec3 position, float yaw, float pitch) {
        world.getServer().runOnServer(server -> world.getConnection().getServerPlayer()
                .teleportTo(server.overworld(), position.x, position.y, position.z, Set.of(), yaw, pitch, false));
        context.waitFor(client -> client.player.position().distanceToSqr(position) < 1.0e-4
                && Math.abs(Mth.wrapDegrees(client.player.getYRot() - yaw)) < 0.5 && Math.abs(client.player.getXRot() - pitch) < 0.5);
        context.waitTicks(5);
    }

    /** In Build mode, flying in place. Up first, then flying: a flying player on the ground is landed again by his own client. */
    private static void hover(ClientGameTestContext context, TestSingleplayerContext world, Vec3 position, float yaw, float pitch) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(server.overworld(), position.x, position.y, position.z, Set.of(), yaw, pitch, false);
            player.getAbilities().flying = true;
            player.onUpdateAbilities();
        });
        context.waitFor(client -> client.player.getAbilities().flying && client.player.position().distanceToSqr(position) < 4
                && client.player.getDeltaMovement().lengthSqr() < 1.0e-6 && Math.abs(client.player.getXRot() - pitch) < 0.5
                && Math.abs(Mth.wrapDegrees(client.player.getYRot() - yaw)) < 0.5);
        context.waitTicks(5);
    }

    private static void mode(ClientGameTestContext context, TestSingleplayerContext world, GameType mode) {
        world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().setGameMode(mode));
        context.waitFor(client -> client.gameMode.getPlayerMode() == mode);
        TownClientGameTest.waitForServer(context, world, server -> {
            var player = world.getConnection().getServerPlayer();
            return player.gameMode.getGameModeForPlayer() == mode && !ModeInventories.of(player).pending();
        }, "The switch to " + mode + " did not finish", 200);
    }

    private static void clearChat(ClientGameTestContext context, List<String> messages) {
        context.runOnClient(client -> client.gui.hud.getChat().clearMessages(true));
        messages.clear();
    }

    /**
     * One picture. With {@code chat} the lines of the last change stay in it; they fade ten seconds after they were
     * said. A list with new pictures makes the game load its item icons again a moment later, with a loading bar:
     * the picture waits until that has come and gone, and until the action bar is empty.
     */
    private static void picture(ClientGameTestContext context, Path folder, String name, boolean chat) {
        context.waitTicks(chat ? 30 : 10);
        context.waitFor(client -> client.gui.overlay() == null && ((HudTestAccess) client.gui.hud).aresos$overlayTime() == 0, 600);
        // The renderer's own word that everything loaded is drawn; the test API's wait for chunks did not end at
        // the game's own distance (see runTest).
        context.waitTicks(10);
        context.waitFor(client -> client.levelRenderer.hasRenderedAllSections(), 600);
        context.runOnClient(client -> {
            if (!chat) client.gui.hud.getChat().clearMessages(true);
            client.gui.toastManager().clear();
        });
        context.waitTicks(3);
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(folder));
    }

    // The drawings.

    /** A program's icon, 96 pixels a side, as the system would hand it over: a figure on its plate, or a bare shape. */
    private static BufferedImage draw(Program program) {
        var image = new BufferedImage(96, 96, BufferedImage.TYPE_INT_ARGB);
        var graphics = image.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        var back = new Color(program.back());
        graphics.setColor(back);
        if (program.plate() == Plate.TILE) graphics.fillRoundRect(0, 0, 96, 96, 26, 26);
        if (program.plate() == Plate.DISC) graphics.fillOval(0, 0, 96, 96);
        if (program.plate() != Plate.BARE) {
            // A figure on a plate leaves the plate's rim free, as app icons do.
            graphics.translate(48, 48);
            graphics.scale(0.62, 0.62);
            graphics.translate(-48, -48);
        }
        figure(graphics, program.figure(), new Color(program.fore()), back);
        graphics.dispose();
        return image;
    }

    /** One figure in the square from 0 to 96, in {@code fore}; its details, where it has any, in {@code accent}. */
    private static void figure(Graphics2D g, Figure figure, Color fore, Color accent) {
        g.setColor(fore);
        switch (figure) {
            case STAR -> {
                var star = new Polygon();
                for (int point = 0; point < 10; point++) {
                    double radius = point % 2 == 0 ? 46 : 19, angle = Math.PI / 5 * point - Math.PI / 2;
                    star.addPoint((int) Math.round(48 + radius * Math.cos(angle)), (int) Math.round(50 + radius * Math.sin(angle)));
                }
                g.fillPolygon(star);
            }
            case BUBBLE -> {
                g.fillRoundRect(4, 10, 88, 60, 30, 30);
                g.fillPolygon(new int[] {22, 22, 50}, new int[] {62, 92, 66}, 3);
            }
            case PROMPT -> {
                g.setStroke(new BasicStroke(15, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g.drawPolyline(new int[] {14, 46, 14}, new int[] {16, 42, 68}, 3);
                g.fillRect(52, 68, 36, 14);
            }
            case PAGE -> {
                g.fillRect(14, 0, 68, 96);
                g.setColor(accent);
                g.fillRect(14, 0, 68, 16);
                for (int line = 0; line < 3; line++) g.fillRect(24, 30 + 18 * line, line == 2 ? 30 : 48, 8);
            }
            case NOTE -> {
                g.fillOval(12, 56, 36, 30);
                g.fillRect(38, 10, 11, 62);
                g.fillPolygon(new int[] {49, 86, 86, 49}, new int[] {10, 22, 44, 32}, 4);
            }
            case ENVELOPE -> {
                g.fillRect(4, 18, 88, 60);
                g.setColor(accent);
                g.setStroke(new BasicStroke(8, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g.drawPolyline(new int[] {8, 48, 88}, new int[] {24, 54, 24}, 3);
            }
            case COMPASS -> g.fillPolygon(new int[] {48, 60, 94, 60, 48, 36, 2, 36}, new int[] {2, 36, 48, 60, 94, 60, 48, 36}, 8);
            case RING -> {
                g.setStroke(new BasicStroke(20));
                g.drawOval(14, 14, 68, 68);
            }
            case PLAY -> g.fillPolygon(new int[] {22, 88, 22}, new int[] {8, 48, 88}, 3);
            case PLUS -> {
                g.fillRect(36, 6, 24, 84);
                g.fillRect(6, 36, 84, 24);
            }
            case BARS -> { for (int bar = 0; bar < 3; bar++) g.fillRect(8, 14 + 26 * bar, 80, 16); }
            case DIAMOND -> {
                g.fillPolygon(new int[] {48, 94, 48, 2}, new int[] {2, 48, 94, 48}, 4);
                g.setColor(accent);
                g.fillPolygon(new int[] {48, 66, 48, 30}, new int[] {30, 48, 66, 48}, 4);
            }
            case HEART -> {
                g.fillOval(4, 8, 48, 48);
                g.fillOval(44, 8, 48, 48);
                g.fillPolygon(new int[] {7, 89, 48}, new int[] {42, 42, 92}, 3);
            }
            case CLOUD -> {
                g.fillOval(2, 40, 46, 46);
                g.fillOval(24, 14, 50, 54);
                g.fillOval(52, 38, 42, 48);
                g.fillRect(24, 60, 50, 26);
                g.setColor(accent);
                g.fillRect(14, 78, 68, 8);
            }
            case FOLDER -> {
                g.fillRoundRect(6, 12, 38, 22, 8, 8);
                g.fillRoundRect(6, 24, 84, 62, 10, 10);
                g.setColor(accent);
                g.fillRect(6, 38, 84, 9);
            }
            case GEAR -> {
                for (int tooth = 0; tooth < 8; tooth++) {
                    var turned = (Graphics2D) g.create();
                    turned.rotate(Math.PI / 4 * tooth, 48, 48);
                    turned.fillRect(38, 2, 20, 26);
                    turned.dispose();
                }
                g.fillOval(16, 16, 64, 64);
                g.setColor(accent);
                g.fillOval(34, 34, 28, 28);
            }
            case BOLT -> g.fillPolygon(new int[] {56, 16, 44, 34, 80, 52}, new int[] {2, 54, 54, 94, 38, 38}, 6);
            case CLOCK -> {
                g.fillOval(2, 2, 92, 92);
                g.setColor(accent);
                g.setStroke(new BasicStroke(10, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g.drawPolyline(new int[] {48, 48, 70}, new int[] {18, 48, 60}, 3);
            }
            case CAMERA -> {
                g.fillRoundRect(4, 24, 88, 58, 14, 14);
                g.fillRect(30, 12, 36, 16);
                g.setColor(accent);
                g.fillOval(30, 35, 36, 36);
            }
            case CHECKER -> {
                g.fillRect(4, 4, 44, 44);
                g.fillRect(48, 48, 44, 44);
                g.setColor(accent);
                g.fillRect(48, 4, 44, 44);
                g.fillRect(4, 48, 44, 44);
            }
            case PAWN -> {
                g.fillOval(30, 4, 36, 36);
                g.fillPolygon(new int[] {40, 56, 72, 24}, new int[] {34, 34, 80, 80}, 4);
                g.fillRect(14, 76, 68, 16);
            }
            case GRID -> { for (int cell = 0; cell < 9; cell++) g.fillRect(8 + 29 * (cell % 3), 8 + 29 * (cell / 3), 22, 22); }
            case SHIELD -> {
                g.fillPolygon(new int[] {48, 90, 90, 48, 6, 6}, new int[] {2, 16, 52, 94, 52, 16}, 6);
                g.setColor(accent);
                g.fillRect(42, 24, 12, 44);
                g.fillRect(26, 40, 44, 12);
            }
            case ARROW -> {
                g.fillRect(36, 4, 24, 46);
                g.fillPolygon(new int[] {8, 88, 48}, new int[] {46, 46, 92}, 3);
            }
            case MOUNTAIN -> {
                g.fillPolygon(new int[] {2, 34, 54, 66, 94}, new int[] {88, 30, 62, 44, 88}, 5);
                g.setColor(new Color(0xffeb3b));
                g.fillOval(62, 6, 24, 24);
            }
            case DICE -> {
                g.fillRoundRect(4, 4, 88, 88, 20, 20);
                g.setColor(accent);
                for (int[] pip : new int[][] {{26, 26}, {70, 26}, {48, 48}, {26, 70}, {70, 70}}) g.fillOval(pip[0] - 9, pip[1] - 9, 18, 18);
            }
            case LETTER -> {
                g.fillRect(8, 6, 80, 22);
                g.fillRect(36, 6, 24, 86);
            }
            case CODE -> {
                g.setStroke(new BasicStroke(13, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g.drawPolyline(new int[] {36, 10, 36}, new int[] {16, 48, 80}, 3);
                g.drawPolyline(new int[] {60, 86, 60}, new int[] {16, 48, 80}, 3);
            }
            case CHART -> {
                int[] heights = {40, 66, 52, 82};
                for (int bar = 0; bar < 4; bar++) g.fillRect(7 + 22 * bar, 92 - heights[bar], 16, heights[bar]);
            }
            case LOCK -> {
                g.fillRoundRect(12, 42, 72, 50, 12, 12);
                g.setStroke(new BasicStroke(13));
                g.drawArc(27, 8, 42, 66, 0, 180);
            }
            case GLOBE -> {
                // A round icon in three bands: its rim is not one colour, so the gate keeps the round outline.
                g.setClip(new Ellipse2D.Double(0, 0, 96, 96));
                g.fillRect(0, 0, 96, 96);
                g.setColor(accent);
                g.fillRect(0, 58, 96, 38);
                g.setColor(Color.WHITE);
                g.fillRect(0, 42, 96, 14);
                g.setClip(null);
            }
        }
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
