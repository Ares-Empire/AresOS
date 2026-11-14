package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppsConfig;
import dev.aresos.config.SystemInfo;
import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
import dev.aresos.hub.TownKeeper;
import dev.aresos.hub.TownMoves;
import dev.aresos.hub.Whereabouts;
import dev.aresos.names.ProgramCommands;
import dev.aresos.names.SlashCommands;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.GettingAround;
import dev.aresos.world.HomeCommands;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.Placing;
import dev.aresos.zone.ZoneData;
import dev.aresos.zone.ZoneLaunchPayload;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.common.ClientboundCustomPayloadPacket;
import net.minecraft.network.protocol.game.ClientboundSystemChatPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.util.Mth;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.Vec3;

import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import static dev.aresos.test.ModeInventoryFixtures.acknowledge;
import static dev.aresos.test.ModeInventoryFixtures.registerStateReceiver;

/**
 * Package 37, step 1: {@code /go}, {@code /home} and the H key's server half. Each test is alone in its batch: it
 * owns the server's hub record, the apps file and the host profile while it runs. Its town stands on new ground in
 * every run, far from every plot, and it holds the chunks it needs with a ticket of its own.
 */
public final class GettingAroundGameTests {
    private static final String TOWN = "aresos-test:go_town";
    private static final String NO_TOWN = "aresos-test:go_no_town";
    /**
     * How long a test may wait for its far-off chunks. The test server ticks without pause while tests wait (400,000
     * ticks passed in 8 seconds on the laptop while another build ran, too short to load a town on new ground), so this
     * is counted generously: it only says how long a test waits before it fails.
     */
    private static final int LOAD_TICKS = 4_000_000;

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }

    private static AppDefinition app(String id, String name, String shortName, boolean pinned, boolean mine, String place, String group) {
        return new AppDefinition(id, name, List.of(id), "minecraft:ender_pearl", pinned).withMine(mine)
                .withNames(shortName == null ? List.of() : List.of(shortName)).withSpot(place, group);
    }

    /** A drawn icon: a white ring on a dark plate. Nothing of a real app. */
    private static GatePicture picture() {
        var icon = new BufferedImage(96, 96, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 96; y++) for (int x = 0; x < 96; x++) {
            double r = Math.hypot(x - 47.5, y - 47.5);
            icon.setRGB(x, y, r > 18 && r < 32 ? 0xffffffff : 0xff2d2f8f);
        }
        return GatePicture.of(icon, HubLayout.SIZE);
    }

    private static Set<Long> chunks(BlockPos from, BlockPos to) {
        var chunks = new HashSet<Long>();
        for (int x = from.getX() >> 4; x <= to.getX() >> 4; x++)
            for (int z = from.getZ() >> 4; z <= to.getZ() >> 4; z++) chunks.add(ChunkPos.pack(x, z));
        return chunks;
    }

    private static void hold(ServerLevel level, Set<Long> chunks, boolean held) {
        for (long chunk : chunks) {
            if (held) level.getChunkSource().addTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
            else level.getChunkSource().removeTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
        }
    }

    private static boolean loaded(ServerLevel level, Set<Long> chunks) {
        return chunks.stream().allMatch(chunk -> level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) && level.areEntitiesLoaded(chunk));
    }

    private static BlockPos surface(ServerLevel level, BlockPos column) {
        var home = new BlockPos(column.getX(), level.getHeight(Heightmap.Types.WORLD_SURFACE, column.getX(), column.getZ()), column.getZ());
        check(level.getBlockState(home.below()).is(Blocks.GRASS_BLOCK) && level.getBlockState(home).isAir(), "Fixture: no grass surface at " + home);
        return home;
    }

    /** The host in Live mode with an embedded connection, his apps in a file of the test's own, AresOS on. */
    private static final class Host implements AutoCloseable {
        final MinecraftServer server;
        final ServerPlayer player;
        final EmbeddedChannel channel;
        final String config;
        final GameProfile profile;
        final boolean desktop;
        final HubData previous;
        final String prefix;

        Host(GameTestHelper helper, String prefix, List<AppDefinition> apps) throws Exception {
            server = helper.getLevel().getServer();
            this.prefix = prefix;
            config = System.getProperty("aresos.appsConfig");
            profile = server.getSingleplayerProfile();
            desktop = DesktopWorld.isEnabled(server);
            previous = HubData.get(server);
            Path file = Files.createTempDirectory(Path.of("."), "getting-around-").resolve("apps.json");
            AppsConfig.save(file, apps);
            System.setProperty("aresos.appsConfig", file.toString());
            AresOs.saveMine(Map.of());
            var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "GettingAroundTest"), false);
            server.setSingleplayerProfile(cookie.gameProfile());
            player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
            var connection = new Connection(PacketFlow.SERVERBOUND);
            channel = new EmbeddedChannel(connection);
            server.getPlayerList().placeNewPlayer(connection, player, cookie);
            registerStateReceiver(player);
            net.fabricmc.fabric.impl.networking.server.ServerNetworkingImpl.getAddon(player.connection).handle(
                    new net.fabricmc.fabric.impl.networking.RegistrationPayload(
                            net.fabricmc.fabric.impl.networking.RegistrationPayload.REGISTER, List.of(ZoneLaunchPayload.TYPE.id())));
            player.setGameMode(GameType.SURVIVAL);
            acknowledge(player);
            var dispatcher = server.getCommands().getDispatcher();
            ProgramCommands.register(dispatcher);
            GettingAround.register(dispatcher);
            // The game test server registers AresOS's commands only after a reload (as an integrated server); here they
            // are as the host's own world has them, whichever test ran first.
            dispatcher.register(net.minecraft.commands.Commands.literal("aresos").then(dev.aresos.item.AppCommands.app()));
            DesktopWorld.setEnabled(server, true);
            SlashCommands.refresh(server);
            ZoneData.get(server).remove(zone -> zone.app().startsWith(prefix));
        }

        int run(String command) throws Exception {
            return server.getCommands().getDispatcher().execute(command, player.createCommandSourceStack());
        }

        /** Runs a command and checks what it returned; the chat it said stays for {@link #lines}. */
        void ran(String command, int expected) throws Exception {
            int result = run(command);
            if (result != expected) throw new AssertionError("/" + command + " returned " + result + ", not " + expected + ": " + lines());
        }

        List<Object> sent() {
            channel.runPendingTasks();
            channel.flushOutbound();
            var all = new ArrayList<>();
            Object packet;
            while ((packet = channel.readOutbound()) != null) all.add(packet);
            return all;
        }

        /** The chat lines sent since the last look. */
        List<String> lines() {
            return sent().stream().filter(ClientboundSystemChatPacket.class::isInstance)
                    .map(packet -> ((ClientboundSystemChatPacket)packet).content().getString()).toList();
        }

        long launches(List<Object> packets) {
            return packets.stream().filter(packet -> packet instanceof ClientboundCustomPayloadPacket custom
                    && custom.payload() instanceof ZoneLaunchPayload).count();
        }

        void at(ServerLevel level, Vec3 position) {
            player.teleportTo(level, position.x, position.y, position.z, Set.of(), 0, 0, false);
            sent();
        }

        @Override public void close() throws Exception {
            ZoneData.get(server).remove(zone -> zone.app().startsWith(prefix));
            server.getPlayerList().remove(player);
            server.setSingleplayerProfile(profile);
            if (previous != null) HubData.store(server, previous);
            if (config == null) System.clearProperty("aresos.appsConfig"); else System.setProperty("aresos.appsConfig", config);
            AresOs.saveMine(Map.of());
            DesktopWorld.setEnabled(server, desktop);
            SlashCommands.refresh(server);
            channel.finishAndReleaseAll();
        }
    }

    private static void standsAt(ServerPlayer player, Vec3 expected, float yaw, float pitch, String what) {
        var at = player.position();
        check(at.distanceTo(expected) < 1e-6, what + ": he stands at " + at + ", not " + expected);
        check(Mth.wrapDegrees(player.getYRot()) == Mth.wrapDegrees(yaw) && player.getXRot() == pitch,
                what + ": he looks " + player.getYRot() + " / " + player.getXRot() + ", not " + yaw + " / " + pitch);
    }

    private static Map<BlockPos, BlockState> snapshot(ServerLevel level, BlockPos from, BlockPos to) {
        var states = new HashMap<BlockPos, BlockState>();
        for (var pos : BlockPos.betweenClosed(from, to)) states.put(pos.immutable(), level.getBlockState(pos));
        return states;
    }

    /**
     * {@code /go} in a town: a day-one app and one in a second row (position and facing as HUB.md 3.2's table), by a
     * short name, a prefix and the full name; arriving opens nothing, while walking into the doorway does; his build
     * at the exit point (he arrives nearer the door) and on the whole way in (he stays, nothing changes); a place not
     * loaded yet; a program that is not his; {@code /apps} with places.
     */
    @GameTest(environment = TOWN, maxTicks = LOAD_TICKS)
    public void goPutsHimInFrontOfHisAppsDoors(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(23000, 0, 0);
        var near = chunks(column.offset(-48, 0, -60), column.offset(48, 0, 30));
        hold(level, near, true);
        var state = new Object() { Host host; BlockPos home; Vec3 chrome; };
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    state.host = new Host(helper, "go-", List.of(
                            app("go-chrome", "Chrome", "chrome", true, true, "N0L0", "internet"),
                            app("go-discord", "Discord", "discord", false, true, "N0R0", "internet"),
                            app("go-lunar", "Lunar Client", "lunar", false, true, "E0L0", "games"),
                            app("go-notes", "Notes", "notes", false, true, "W1R1", "work_media"),
                            app("go-far", "Far", "far", false, true, "N40L0", "internet"),
                            app("go-new", "Newcomer", "newcomer", false, true, null, null),
                            app("go-stranger", "Stranger", "stranger", false, false, null, null)));
                    var host = state.host;
                    var server = host.server;
                    var home = surface(level, column);
                    state.home = home;
                    HubData.store(server, new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), FlatHub.build(level, home)));
                    var ring = picture();
                    for (var id : List.of("go-chrome", "go-discord", "go-lunar", "go-notes"))
                        Town.build(server, AresOs.app(id), Place.parse(AresOs.app(id).place()).orElseThrow(), ring);
                    host.at(level, Vec3.atBottomCenterOf(home));

                    // /apps says where each logo stands, or why it has none.
                    check(host.run("apps") == 6, "/apps did not list his six apps");
                    var lines = host.lines();
                    for (var expected : List.of("Chrome: /chrome. Internet, north, front row, left",
                            "Lunar Client: /lunar. Games, east, front row, left",
                            "Notes: /notes. Work & Media, west, row 2, right, 2nd from the road",
                            "Far: /far. Internet, north, row 41, left, built when you come near",
                            "Newcomer: /newcomer. System & Tools: no logo until the system has listed your programs"))
                        check(lines.contains(expected), "/apps lacks \"" + expected + "\": " + lines);

                    // A day-one app, by a prefix of its short name: the exit point of N0L0, looking north at the door.
                    host.ran("go chr", 1);
                    state.chrome = new Vec3(home.getX() - 9.0, home.getY(), home.getZ() - 13.5);
                    standsAt(host.player, state.chrome, 180, -10, "/go chr");
                    check(host.lines().isEmpty(), "/go to a standing logo said something");
                }))
                // Arriving is not walking in: some ticks later nothing was opened.
                .thenIdle(10)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    var host = state.host;
                    check(host.launches(host.sent()) == 0, "Arriving by /go opened the app");
                    standsAt(host.player, state.chrome, 180, -10, "After ten ticks at Chrome's door");
                    // The doorway itself still opens it: the test's eye for a launch is open.
                    var niche = new Vec3(state.home.getX() - 9.0, state.home.getY(), state.home.getZ() - 20.5);
                    host.player.teleportTo(level, niche.x, niche.y, niche.z, Set.of(), 180, 0, false);
                }))
                .thenIdle(5)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    var host = state.host;
                    check(host.launches(host.sent()) == 1, "Walking into Chrome's doorway did not open it");
                    var home = state.home;
                    host.at(level, Vec3.atBottomCenterOf(home));

                    // An app in the second row, by its full name: W1R1, looking west.
                    host.ran("go Notes", 1);
                    standsAt(host.player, new Vec3(home.getX() - 27.5, home.getY(), home.getZ() - 23.0), 90, -10, "/go Notes");
                    host.ran("go lunar client", 1);
                    standsAt(host.player, new Vec3(home.getX() + 14.5, home.getY(), home.getZ() - 9.0), -90, -10, "/go lunar client");

                    // His build at Discord's exit point: he arrives one block nearer the door. Nothing changes.
                    host.at(level, Vec3.atBottomCenterOf(home));
                    var stone = Blocks.STONE.defaultBlockState();
                    int exitZ = home.getZ() - 14;
                    for (int x = home.getX() + 9; x <= home.getX() + 10; x++) for (int y = 0; y < 2; y++)
                        level.setBlockAndUpdate(new BlockPos(x, home.getY() + y, exitZ), stone);
                    var before = snapshot(level, home.offset(-20, -1, -25), home.offset(20, 13, 0));
                    host.ran("go discord", 1);
                    standsAt(host.player, new Vec3(home.getX() + 10.0, home.getY(), home.getZ() - 14.5), 180, -10, "/go discord past his build");
                    check(snapshot(level, home.offset(-20, -1, -25), home.offset(20, 13, 0)).equals(before), "/go changed a block");

                    // His build on the whole way in, up to the layer in front of the logo: he stays, one line says why.
                    host.at(level, Vec3.atBottomCenterOf(home));
                    for (int z = home.getZ() - 19; z <= exitZ; z++) for (int x = home.getX() + 9; x <= home.getX() + 10; x++)
                        for (int y = 0; y < 2; y++) level.setBlockAndUpdate(new BlockPos(x, home.getY() + y, z), stone);
                    before = snapshot(level, home.offset(-20, -1, -25), home.offset(20, 13, 0));
                    check(host.run("go discord") == 0, "/go discord with the way in blocked moved him");
                    standsAt(host.player, Vec3.atBottomCenterOf(home), 0, 0, "/go discord blocked");
                    var said = host.lines();
                    check(said.equals(List.of("Something of yours stands in front of Discord's door (Internet, north, front row, right)"
                            + " with no free spot on the way in, so you stay where you are.")), "The blocked line: " + said);
                    check(snapshot(level, home.offset(-20, -1, -25), home.offset(20, 13, 0)).equals(before), "A refused /go changed a block");
                    for (int z = home.getZ() - 19; z <= exitZ; z++) for (int x = home.getX() + 9; x <= home.getX() + 10; x++)
                        for (int y = 0; y < 2; y++) level.setBlockAndUpdate(new BlockPos(x, home.getY() + y, z), Blocks.AIR.defaultBlockState());

                    // A program that is not his: one line with the command that adds it, and he stays.
                    check(host.run("go stranger") == 0, "/go to a program that is not his moved him");
                    said = host.lines();
                    check(said.equals(List.of("Stranger is not one of your apps. /aresos app add go-stranger adds it.")), "Not his: " + said);

                    // A place that is not loaded yet: its saved place, so he arrives where the town will build it.
                    var far = AresOs.app("go-far");
                    check(Whereabouts.of(host.server, far, true).kind() == Whereabouts.Kind.WAITS, "Fixture: the far place is loaded");
                    host.ran("go far", 1);
                    standsAt(host.player, new Vec3(home.getX() - 9.0, home.getY(), home.getZ() - 573.5), 180, -10, "/go far");
                    said = host.lines();
                    check(said.equals(List.of("Far's logo is built here once the system has listed your programs.")), "The far line: " + said);
                }))
                .thenExecute(() -> {
                    try (var host = state.host) {
                        for (var logo : HubData.get(host.server).logos()) if (logo.app().startsWith("go-")) Town.remove(host.server, logo.app());
                    } catch (Exception error) {
                        throw new AssertionError(error.getMessage(), error);
                    } finally {
                        hold(level, near, false);
                    }
                })
                .thenSucceed();
    }

    /**
     * Without a town: {@code /go} to the nearest zone he made by hand for the app, in his dimension, or one line;
     * {@code /home} and the H key from the Nether: on the home spot, facing north. A hub of other rules stands in
     * for a world without a town: the server's hub record cannot be taken away, and a town of other rules is no town
     * of these rules.
     */
    @GameTest(environment = NO_TOWN, maxTicks = LOAD_TICKS)
    public void goWithoutATownAndHomeFromTheNether(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(26000, 0, 0);
        var near = chunks(column.offset(-32, 0, -32), column.offset(32, 0, 32));
        hold(level, near, true);
        var state = new Object() { Host host; boolean failed; HomeRecord record; Vec3 inside, outside; };
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The chunks are not loaded yet"))
                .thenExecute(() -> {
                    NetherHome.Home before = null;
                    boolean recorded = false, hadRecord = false;
                    try (var host = new Host(helper, "go2-", List.of(
                            app("go2-zoned", "Zoned", "zoned", false, true, null, null),
                            app("go2-bare", "Bare", "bare", false, true, "N0L0", "internet"),
                            app("go2-other", "Other Program", "otherprogram", false, false, null, null)))) {
                        state.host = host;
                        var server = host.server;
                        var spot = surface(level, column);
                        HubData.store(server, new HubData("flat-0", HubLayout.numbers(), GlobalPos.of(level.dimension(), spot), new HubData.Fixed(List.of(), List.of())));
                        check(Whereabouts.of(server, AresOs.app("go2-bare"), true).kind() == Whereabouts.Kind.NO_TOWN, "A town of other rules is a town");
                        host.at(level, Vec3.atBottomCenterOf(spot));

                        // No zone of the app: one line, and he stays.
                        check(host.run("go bare") == 0, "/go bare moved him");
                        var said = host.lines();
                        check(said.equals(List.of("Bare has no logo here.")), "No logo: " + said);
                        standsAt(host.player, Vec3.atBottomCenterOf(spot), 0, 0, "/go bare");

                        // Two zones he made by hand: the nearer one's exit, as he made it.
                        var nearExit = new NetherHome.Home(level.dimension(), Vec3.atBottomCenterOf(spot.offset(0, 0, 6)), 180, 0);
                        var farExit = new NetherHome.Home(level.dimension(), Vec3.atBottomCenterOf(spot.offset(20, 0, 6)), 180, 0);
                        ZoneData.get(server).add(new AppZone("go2-near", "go2-zoned", level.dimension(), spot.offset(0, 0, 3), spot.offset(1, 2, 3), nearExit, List.of()));
                        ZoneData.get(server).add(new AppZone("go2-far", "go2-zoned", level.dimension(), spot.offset(20, 0, 3), spot.offset(21, 2, 3), farExit, List.of()));
                        host.ran("go zoned", 1);
                        standsAt(host.player, nearExit.position(), 180, 0, "/go zoned");

                        // Not his: the line that adds it.
                        check(host.run("go other") == 0, "/go other moved him");
                        said = host.lines();
                        check(said.equals(List.of("Other Program is not one of your apps. /aresos app add go2-other adds it.")), "Not his: " + said);

                        // /home from the Nether: the home spot, facing north, in the Overworld. Then the H key's half.
                        var previous = NetherHome.get(server);
                        before = previous != null && previous.hasExactHome() ? previous.home() : null;
                        hadRecord = previous != null;
                        var home = new NetherHome.Home(level.dimension(), Vec3.atBottomCenterOf(spot.offset(-6, 0, -6)), 180, -8);
                        recorded = true;
                        NetherHome.recordHome(server, home);
                        var nether = server.getLevel(Level.NETHER);
                        var away = new Vec3(column.getX() / 8 + 0.5, 100, column.getZ() / 8 + 0.5);
                        host.player.teleportTo(nether, away.x, away.y, away.z, Set.of(), 0, 0, false);
                        check(host.player.level().dimension() == Level.NETHER, "Fixture: he is not in the Nether");
                        host.ran("home", 1);
                        check(host.player.level().dimension() == level.dimension(), "/home left him in " + host.player.level().dimension());
                        standsAt(host.player, home.position(), 180, -8, "/home");
                        host.player.teleportTo(nether, away.x, away.y, away.z, Set.of(), 0, 0, false);
                        HomeCommands.key(host.player);
                        check(host.player.level().dimension() == level.dimension(), "The H key left him in " + host.player.level().dimension());
                        standsAt(host.player, home.position(), 180, -8, "The H key");
                    } catch (Exception | AssertionError error) {
                        state.failed = true;
                        throw error instanceof AssertionError assertion ? assertion : new AssertionError(error.getMessage(), error);
                    } finally {
                        var server = level.getServer();
                        try {
                            // The world's home record as it was: none, or the one it had (with its exact home or without).
                            if (recorded && hadRecord) NetherHome.get(server).setHome(before);
                            else if (recorded) forgetHome(server);
                        } finally {
                            if (state.failed) hold(level, near, false);
                        }
                    }
                })
                // Review fixes 1, point 1: a home inside a doorway (setting it checks safe ground only, as in Build mode).
                // /home and the H key arrive there and open nothing, ten ticks on; stepping out and in again opens it.
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    state.host = null;
                    state.host = new Host(helper, "go3-", List.of(app("go3-door", "Door", "door", false, true, null, null)));
                    var server = state.host.server;
                    var spot = surface(level, column);
                    var exit = new NetherHome.Home(level.dimension(), Vec3.atBottomCenterOf(spot.offset(0, 0, 6)), 180, 0);
                    ZoneData.get(server).add(new AppZone("go3-zone", "go3-door", level.dimension(), spot.offset(0, 0, 3), spot.offset(1, 2, 3), exit, List.of()));
                    state.inside = Vec3.atBottomCenterOf(spot.offset(0, 0, 3));
                    state.outside = Vec3.atBottomCenterOf(spot.offset(0, 0, 10));
                    check(dev.aresos.world.HomeSites.isSafe(level, state.inside), "Fixture: the doorway is no safe spot for a home");
                    state.record = HomeRecord.of(server);
                    NetherHome.recordHome(server, new NetherHome.Home(level.dimension(), state.inside, 180, 0));
                    state.host.at(level, state.outside);
                }, () -> state.record))
                .thenIdle(2)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    state.host.ran("home", 1);
                    standsAt(state.host.player, state.inside, 180, 0, "/home into the doorway");
                }, () -> state.record))
                .thenIdle(10)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    check(state.host.launches(state.host.sent()) == 0, "Arriving by /home opened the app");
                    state.host.at(level, state.outside);
                }, () -> state.record))
                .thenIdle(2)
                .thenExecute(() -> state.host.player.teleportTo(level, state.inside.x, state.inside.y, state.inside.z, Set.of(), 180, 0, false))
                .thenIdle(2)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    check(state.host.launches(state.host.sent()) == 1, "Walking out and into the doorway did not open it");
                    state.host.at(level, state.outside);
                }, () -> state.record))
                .thenIdle(2)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    HomeCommands.key(state.host.player);
                    standsAt(state.host.player, state.inside, 180, 0, "The H key into the doorway");
                }, () -> state.record))
                .thenIdle(10)
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    check(state.host.launches(state.host.sent()) == 0, "Arriving by the H key opened the app");
                    state.host.at(level, state.outside);
                }, () -> state.record))
                .thenIdle(2)
                .thenExecute(() -> state.host.player.teleportTo(level, state.inside.x, state.inside.y, state.inside.z, Set.of(), 180, 0, false))
                .thenIdle(2)
                .thenExecute(() -> {
                    try (var host = state.host) {
                        check(host.launches(host.sent()) == 1, "Walking out and into the doorway after H did not open it");
                    } catch (Exception error) {
                        throw new AssertionError(error.getMessage(), error);
                    } finally {
                        try {
                            state.record.restore(level.getServer());
                        } finally {
                            hold(level, near, false);
                        }
                    }
                })
                .thenSucceed();
    }

    /** The world's home record before a test made its own: none, or the one it had (with its exact home or without). */
    private record HomeRecord(boolean had, NetherHome.Home exact) {
        static HomeRecord of(MinecraftServer server) {
            var previous = NetherHome.get(server);
            return new HomeRecord(previous != null, previous != null && previous.hasExactHome() ? previous.home() : null);
        }

        void restore(MinecraftServer server) {
            if (had) NetherHome.get(server).setHome(exact);
            else forgetHome(server);
        }
    }


    // Package 37, step 2: swap and move. Each test is alone in its batch, like the ones above.
    private static final String SWAP = "aresos-test:go_swap";
    private static final String MOVE = "aresos-test:go_move";

    /** One of his apps as the system lists it: with a category, so its own group follows from it (none: System & Tools). */
    private static AppDefinition listed(String id, String name, String shortName, String category, String place, boolean mine) {
        return app(id, name, shortName, false, mine, place, null)
                .withSystem(new SystemInfo("user", null, category == null ? List.of() : List.of(category), null, null, id, id, false));
    }

    /** The game as swap and move see it, with the test's drawn picture; the apps file is the host's. */
    private static TownMoves.Game game(List<String> reads, Set<String> unread) {
        var ring = picture();
        return new TownMoves.Game(() -> new TownKeeper.Programs(AresOs.apps(), true),
                app -> unread.contains(app.id()) ? Optional.empty() : Optional.of(ring), app -> reads.add(app.id()), AresOs::saveSpots);
    }

    /** The same game with his apps changed as the system or My apps would have them, and more apps than the file holds. */
    private static TownMoves.Game game(TownMoves.Game game, java.util.function.UnaryOperator<AppDefinition> how, List<AppDefinition> more) {
        return new TownMoves.Game(() -> {
            var apps = new ArrayList<>(AresOs.apps().stream().map(how).toList());
            apps.addAll(more);
            return new TownKeeper.Programs(apps, true);
        }, game.pictures(), game.read(), game.spots());
    }

    /** A flat home of these rules on new ground, built by a first pass of the test's own keeper. */
    private static HubData town(ServerLevel level, BlockPos home, TownKeeper keeper, TownMoves.Game game, int logos) throws IOException {
        var hub = new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(level.dimension(), home), FlatHub.build(level, home));
        HubData.store(level.getServer(), hub);
        var first = keeper.keep(level.getServer(), game.programs().get(), game.pictures(), game.spots());
        check(first.lines().equals(List.of("The town is built: " + logos + " logos. /apps lists them.")), "The first build: " + first.lines());
        return hub;
    }

    /** His app's logo stands at this place, the apps file saves that place, and the hand-set group (null: none). */
    private static void stands(MinecraftServer server, String id, String place, String group) {
        var logo = HubData.get(server).logo(id).map(HubData.Logo::place).orElse("none");
        var app = AresOs.app(id);
        check(logo.equals(place) && place.equals(app.place()) && Objects.equals(group, app.group()),
                id + ": its logo at " + logo + ", saved at " + app.place() + " in the group " + app.group() + "; not " + place + ", " + group);
    }

    private static String text(ServerLevel level, UUID entity) {
        return ((dev.aresos.mixin.TextDisplayAccess) level.getEntity(entity)).aresos$text().getString();
    }

    /** What his app's logo shows on its sign and has for a doormat, as built now. */
    private static void looks(ServerLevel level, HubData hub, String id, String name, AppGroup group) {
        var logo = hub.logo(id).orElseThrow();
        check(text(level, logo.gate().sign().orElseThrow()).startsWith(name), id + "'s sign: " + text(level, logo.gate().sign().orElseThrow()));
        var plan = Town.plan(hub, AresOs.app(id), Place.parse(logo.place()).orElseThrow(), picture());
        for (var pos : plan.doormat())
            check(Placing.id(level.getBlockState(pos)).equals(group.concrete()), id + "'s doormat at " + pos + ": " + level.getBlockState(pos));
    }

    private static List<String> names(ServerLevel level, HubData hub) {
        return hub.fixed().names().stream().map(id -> text(level, id)).toList();
    }

    /** Whether a group's avenue is paved and recorded at this outward index, all five blocks. */
    private static boolean paved(ServerLevel level, HubData hub, AppGroup group, int outward) {
        for (int sideways = -2; sideways <= 2; sideways++) {
            var pos = group.block(hub.home().pos(), outward, sideways, -1);
            if (!Placing.id(level.getBlockState(pos)).equals(sideways == 0 ? group.concrete() : HubLayout.PAVING) || !hub.holds(level, pos)) return false;
        }
        return true;
    }

    /** Takes down the logos of the test's apps, then lets go of the host and the chunks. */
    private static void done(Host host, ServerLevel level, Set<Long> near) {
        try (host) {
            for (var logo : HubData.get(host.server).logos()) if (logo.app().startsWith(host.prefix)) Town.remove(host.server, logo.app());
        } catch (Exception error) {
            throw new AssertionError(error.getMessage(), error);
        } finally {
            hold(level, near, false);
        }
    }

    /**
     * {@code /aresos app swap}: inside one group; across two groups (doormats, signs, counts, the saved group, the group
     * {@code /apps} and the Apps screen show); a swap back, which leaves no hand-set group; a picture the town has not
     * read; his torch on one logo, which refuses the swap with file and world unchanged; an incomplete program list;
     * the command as he types it, and its completion.
     */
    @GameTest(environment = SWAP, maxTicks = LOAD_TICKS)
    public void swapExchangesTwoLogos(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos column = helper.absolutePos(BlockPos.ZERO).offset(29000, 0, 0);
        var near = chunks(column.offset(-48, 0, -48), column.offset(48, 0, 48));
        hold(level, near, true);
        var state = new Object() { Host host; };
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    state.host = new Host(helper, "sw-", List.of(
                            listed("sw-chrome", "Chrome", "chrome", "Network", "N0L0", true),
                            listed("sw-discord", "Discord", "discord", "Network", "N0R0", true),
                            listed("sw-lunar", "Lunar Client", "lunar", "Game", "E0L0", true),
                            listed("sw-steam", "Steam", "steam", "Game", "E0R0", true),
                            listed("sw-notes", "Notes", "notes", null, "S0L0", true)));
                    swapping(state.host, level, surface(level, column));
                }))
                .thenExecute(() -> done(state.host, level, near))
                .thenSucceed();
    }

    private static void swapping(Host host, ServerLevel level, BlockPos home) throws Exception {
        var server = host.server;
        var keeper = new TownKeeper();
        var reads = new ArrayList<String>();
        var unread = new HashSet<String>();
        var game = game(reads, unread);
        var hub = town(level, home, keeper, game, 5);
        check(AppGroup.of(AresOs.app("sw-chrome")) == AppGroup.INTERNET && AppGroup.of(AresOs.app("sw-lunar")) == AppGroup.GAMES
                && AppGroup.of(AresOs.app("sw-notes")) == AppGroup.SYSTEM_TOOLS, "Fixture: the apps' own groups");

        // Inside one group: the places change hands, the groups stay; the town adds no line of its own.
        var said = TownMoves.swap(server, keeper, game, "sw-chrome", "sw-discord");
        check(said.done() && said.line().equals("Chrome now stands at Internet, north, front row, right, and Discord at Internet, north, front row, left."),
                "Inside one group: " + said.line());
        check(said.pass().lines().isEmpty(), "The town's own lines after a swap: " + said.pass().lines());
        stands(server, "sw-chrome", "N0R0", null);
        stands(server, "sw-discord", "N0L0", null);
        looks(level, hub, "sw-chrome", "Chrome", AppGroup.INTERNET);
        looks(level, hub, "sw-discord", "Discord", AppGroup.INTERNET);

        // Across two groups: each takes the other's group by hand, with its doormat; the counts stay two and two.
        said = TownMoves.swap(server, keeper, game, "sw-chrome", "sw-lunar");
        check(said.done() && said.line().equals("Chrome now stands at Games, east, front row, left, and Lunar Client at Internet, north, front row, right."),
                "Across two groups: " + said.line());
        stands(server, "sw-chrome", "E0L0", "games");
        stands(server, "sw-lunar", "N0R0", "internet");
        looks(level, hub, "sw-chrome", "Chrome", AppGroup.GAMES);
        looks(level, hub, "sw-lunar", "Lunar Client", AppGroup.INTERNET);
        check(names(level, hub).subList(0, 3).equals(List.of("INTERNET · 2", "GAMES · 2", "SYSTEM & TOOLS · 1")), "The counts: " + names(level, hub));
        // The group /apps names (the place in words) and the one the Apps screen shows (the app's group).
        check(Whereabouts.of(server, AresOs.app("sw-chrome"), true).place().words().equals("Games, east, front row, left")
                && AppGroup.of(AresOs.app("sw-chrome")) == AppGroup.GAMES && AppGroup.of(AresOs.app("sw-lunar")) == AppGroup.INTERNET, "The groups shown");

        // A swap back: both in their own groups again, so no hand-set group is left.
        said = TownMoves.swap(server, keeper, game, "sw-lunar", "sw-chrome");
        check(said.done() && said.line().equals("Lunar Client now stands at Games, east, front row, left, and Chrome at Internet, north, front row, right."),
                "The swap back: " + said.line());
        stands(server, "sw-chrome", "N0R0", null);
        stands(server, "sw-lunar", "E0L0", null);
        looks(level, hub, "sw-chrome", "Chrome", AppGroup.INTERNET);
        looks(level, hub, "sw-lunar", "Lunar Client", AppGroup.GAMES);

        // A picture the town has not read: never read here; the town is asked to read it, and nothing changes.
        unread.add("sw-steam");
        said = TownMoves.swap(server, keeper, game, "sw-steam", "sw-notes");
        check(!said.done() && said.line().equals("Nothing was swapped: the town is still reading the picture of Steam. Try again in a moment.")
                && reads.equals(List.of("sw-steam")), "A picture not read: " + said.line() + ", " + reads);
        stands(server, "sw-steam", "E0R0", null);
        unread.clear();

        // His torch on Discord's doormat: Discord's logo cannot come down, so nothing changes, in the file or the world.
        var torch = Town.plan(hub, AresOs.app("sw-discord"), Place.parse("N0L0").orElseThrow(), picture()).doormat().getFirst().above();
        level.setBlockAndUpdate(torch, Blocks.TORCH.defaultBlockState());
        var before = snapshot(level, home.offset(-40, -1, -40), home.offset(40, 12, 40));
        var file = AresOs.apps();
        var logos = hub.logos();
        said = TownMoves.swap(server, keeper, game, "sw-discord", "sw-steam");
        check(!said.done() && said.line().startsWith("Nothing was swapped: Discord's logo at Internet, north, front row, left cannot come down. "
                + "Logo could disturb neighboring minecraft:torch at "), "His torch: " + said.line());
        check(snapshot(level, home.offset(-40, -1, -40), home.offset(40, 12, 40)).equals(before), "A refused swap changed a block");
        check(AresOs.apps().equals(file) && hub.logos().equals(logos), "A refused swap changed the apps file or the town's records");
        level.setBlockAndUpdate(torch, Blocks.AIR.defaultBlockState());

        // Before a complete program list it refuses before checking anything, as hub rebuild does.
        String waits = "The town waits for the system's list of programs. Nothing changed; try again in a moment.";
        var incomplete = new TownMoves.Game(() -> new TownKeeper.Programs(AresOs.apps(), false), game.pictures(), game.read(), game.spots());
        said = TownMoves.swap(server, keeper, incomplete, "sw-chrome", "sw-discord");
        check(!said.done() && said.line().equals(waits), "An incomplete list: " + said.line());

        // The command as he types it, and its completion. A name that finds none of his apps: /go's line.
        host.ran("aresos app swap chrome nothing", 0);
        var typed = host.lines();
        check(typed.equals(List.of("No program matches \"nothing\".")), "The typed swap with a name of nothing: " + typed);
        // Without a complete program list (no other test of this run gave one), the town's own line.
        if (!TownKeeper.complete()) {
            host.ran("aresos app swap chrome discord", 0);
            var lines = host.lines();
            check(lines.equals(List.of(waits)), "The typed swap: " + lines);
            host.ran("aresos app move lunar west", 0);
            lines = host.lines();
            check(lines.equals(List.of(waits)), "The typed move: " + lines);
        }
        var dispatcher = server.getCommands().getDispatcher();
        var source = host.player.createCommandSourceStack();
        var apps = dispatcher.getCompletionSuggestions(dispatcher.parse("aresos app swap chrome di", source)).join().getList().stream()
                .map(com.mojang.brigadier.suggestion.Suggestion::getText).toList();
        check(apps.equals(List.of("discord")), "Completing an app: " + apps);
        var ways = dispatcher.getCompletionSuggestions(dispatcher.parse("aresos app move lunar ", source)).join().getList().stream()
                .map(com.mojang.brigadier.suggestion.Suggestion::getText).sorted().toList();
        check(ways.equals(List.of("east", "north", "south", "west")), "Completing a direction: " + ways);
        stands(server, "sw-chrome", "N0R0", null);
        stands(server, "sw-discord", "N0L0", null);
    }

    /**
     * {@code /aresos app move}: to a free place (counts, sign, doormat, its old place free); to the group it stands
     * in (nothing changes); where the first place of the group is blocked by his build (the next place, the road grows);
     * back to its own group (no hand-set group, the road stays); a place that changes hands waits for the town's old
     * logo there (point 3: the move refuses, the town's pass keeps a newcomer waiting, then builds it); a place that is
     * not loaded (file and world unchanged).
     */
    @GameTest(environment = MOVE, maxTicks = LOAD_TICKS)
    public void moveSendsALogoToAnotherGroup(GameTestHelper helper) {
        var level = helper.getLevel();
        BlockPos start = helper.absolutePos(BlockPos.ZERO).offset(32000, 0, 0);
        // The home in the middle of a chunk, so that which chunks are loaded is known: two each way, held.
        BlockPos column = new BlockPos(((start.getX() >> 4) << 4) + 8, 0, ((start.getZ() >> 4) << 4) + 8);
        var near = chunks(column.offset(-40, 0, -40), column.offset(39, 0, 39));
        hold(level, near, true);
        var state = new Object() { Host host; };
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The town's chunks are not loaded yet"))
                .thenExecute(() -> guarded(() -> state.host, level, near, () -> {
                    state.host = new Host(helper, "mv-", List.of(
                            listed("mv-chrome", "Chrome", "chrome", "Network", "N0L0", true),
                            listed("mv-discord", "Discord", "discord", "Network", "N0R0", true),
                            listed("mv-lunar", "Lunar Client", "lunar", "Game", "E0L0", true),
                            listed("mv-steam", "Steam", "steam", "Game", "E0R0", true),
                            listed("mv-notes", "Notes", "notes", null, "S0L0", true),
                            listed("mv-new", "Newcomer", "newcomer", "Network", null, false)));
                    moving(state.host, level, surface(level, column));
                }))
                .thenExecute(() -> done(state.host, level, near))
                .thenSucceed();
    }

    private static void moving(Host host, ServerLevel level, BlockPos home) throws Exception {
        var server = host.server;
        var keeper = new TownKeeper();
        var game = game(new ArrayList<>(), Set.of());
        var hub = town(level, home, keeper, game, 5);

        // To a free place: Work & Media's first. Its old place is free; the counts follow.
        var said = TownMoves.move(server, keeper, game, "mv-steam", AppGroup.WORK_MEDIA);
        check(said.done() && said.line().equals("Steam now stands at Work & Media, west, front row, left."), "To a free place: " + said.line());
        check(said.pass().lines().isEmpty(), "The town's own lines after a move: " + said.pass().lines());
        stands(server, "mv-steam", "W0L0", "work_media");
        looks(level, hub, "mv-steam", "Steam", AppGroup.WORK_MEDIA);
        check(hub.logos().stream().noneMatch(logo -> logo.place().equals("E0R0")), "E0R0 still holds a logo");
        check(names(level, hub).equals(List.of("INTERNET · 2", "GAMES · 1", "SYSTEM & TOOLS · 1", "WORK & MEDIA · 1")), "The counts: " + names(level, hub));

        // To the group it stands in: nothing changes, and it says so.
        said = TownMoves.move(server, keeper, game, "mv-steam", AppGroup.WORK_MEDIA);
        check(!said.done() && said.line().equals("Steam already stands in Work & Media, west. Nothing was moved."), "To its group: " + said.line());

        // The group's first free place is blocked by his build: the next one, and the west road grows to its row.
        var his = Place.parse("W0R0").orElseThrow().origin(home);
        level.setBlockAndUpdate(his, Blocks.COBBLESTONE.defaultBlockState());
        said = TownMoves.move(server, keeper, game, "mv-lunar", AppGroup.WORK_MEDIA);
        check(said.done() && said.line().equals("Lunar Client now stands at Work & Media, west, row 2, left."), "Past his build: " + said.line());
        stands(server, "mv-lunar", "W1L0", "work_media");
        check(level.getBlockState(his).is(Blocks.COBBLESTONE), "His block was changed");
        for (int outward = 3; outward <= HubLayout.avenueEnd(1); outward++) check(paved(level, hub, AppGroup.WORK_MEDIA, outward), "West road at " + outward);

        // Back to its own group: no hand-set group; the road it paved stays.
        said = TownMoves.move(server, keeper, game, "mv-lunar", AppGroup.GAMES);
        check(said.done() && said.line().equals("Lunar Client now stands at Games, east, front row, left."), "Back to its group: " + said.line());
        stands(server, "mv-lunar", "E0L0", null);
        looks(level, hub, "mv-lunar", "Lunar Client", AppGroup.GAMES);
        for (int outward = 3; outward <= HubLayout.avenueEnd(1); outward++) check(paved(level, hub, AppGroup.WORK_MEDIA, outward), "West road unpaved at " + outward);
        level.setBlockAndUpdate(his, Blocks.AIR.defaultBlockState());

        // Point 3. Discord leaves My apps while his torch hangs on its logo: the logo stays, and its place waits for it.
        var torch = Town.plan(hub, AresOs.app("mv-discord"), Place.parse("N0R0").orElseThrow(), picture()).doormat().getFirst().above();
        level.setBlockAndUpdate(torch, Blocks.TORCH.defaultBlockState());
        var left = game(game, app -> app.id().equals("mv-discord") ? app.withMine(false) : app, List.of());
        var pass = keeper.keep(server, left.programs().get(), left.pictures(), left.spots());
        check(pass.lines().size() == 1 && pass.lines().getFirst().startsWith("The logo of Discord stays: ") && hub.logo("mv-discord").isPresent(),
                "Discord's logo with his torch: " + pass.lines());
        // A move there refuses (all or nothing) instead of going on to another place.
        said = TownMoves.move(server, keeper, left, "mv-steam", AppGroup.INTERNET);
        check(!said.done() && said.line().startsWith("Nothing was moved: Discord's logo at Internet, north, front row, right cannot come down. "),
                "A move to a place that waits: " + said.line());
        stands(server, "mv-steam", "W0L0", "work_media");
        // The town's pass gives that place to a newcomer of Internet, which waits there and is not sent on.
        java.util.function.UnaryOperator<AppDefinition> joining = app -> app.id().equals("mv-discord") ? app.withMine(false)
                : app.id().equals("mv-new") ? app.withMine(true) : app;
        var joined = game(game, joining, List.of());
        pass = keeper.keep(server, joined.programs().get(), joined.pictures(), joined.spots());
        check(pass.lines().isEmpty() && "N0R0".equals(AresOs.app("mv-new").place()) && hub.logo("mv-new").isEmpty(), "The newcomer waits: " + pass.lines()
                + ", saved at " + AresOs.app("mv-new").place());
        level.setBlockAndUpdate(torch, Blocks.AIR.defaultBlockState());
        pass = keeper.keep(server, joined.programs().get(), joined.pictures(), joined.spots());
        check(hub.logo("mv-discord").isEmpty(), "Discord's logo did not come down: " + pass.lines());
        stands(server, "mv-new", "N0R0", null);

        // A place that is not loaded: with System & Tools' first four rows taken, its first free place is in row 5,
        // beyond the loaded chunks. Nothing changes, in the file or the world.
        var crowd = new ArrayList<AppDefinition>();
        var taken = Place.inOrder(AppGroup.SYSTEM_TOOLS).skip(1).limit(19).toList();
        for (int i = 0; i < taken.size(); i++) crowd.add(listed("mv-p" + i, "Placeholder " + i, null, null, taken.get(i).name(), true));
        var crowded = game(game, joining, crowd);
        var before = snapshot(level, home.offset(-40, -1, -40), home.offset(39, 12, 39));
        var file = AresOs.apps();
        var logos = hub.logos();
        said = TownMoves.move(server, keeper, crowded, "mv-chrome", AppGroup.SYSTEM_TOOLS);
        check(!said.done() && said.line().equals("Nothing was moved: System & Tools, south, row 5, left is not loaded. Stand at home and try again."),
                "A place not loaded: " + said.line());
        check(snapshot(level, home.offset(-40, -1, -40), home.offset(39, 12, 39)).equals(before), "A refused move changed a block");
        check(AresOs.apps().equals(file) && hub.logos().equals(logos), "A refused move changed the apps file or the town's records");
        stands(server, "mv-chrome", "N0L0", null);
    }

    /**
     * Takes away the home record {@code NetherHome.recordHome} made in a test world that had none: from the server's
     * saved data and from the world's folder. Left there, every player who joins a later test (in this run or the next,
     * the test world is kept) is sent to this test's spot, and tests of void recovery and Build mode fail. The game has
     * no call that drops saved data, so the record is taken out of the storage's map of loaded data.
     */
    private static void forgetHome(MinecraftServer server) {
        var storage = server.getDataStorage();
        try {
            for (var field : storage.getClass().getDeclaredFields()) {
                if (!Map.class.isAssignableFrom(field.getType())) continue;
                field.setAccessible(true);
                ((Map<?, ?>)field.get(storage)).entrySet().removeIf(entry -> entry.getValue() instanceof Optional<?> data
                        ? data.filter(NetherHome.class::isInstance).isPresent() : entry.getValue() instanceof NetherHome);
            }
            Files.deleteIfExists(server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).resolve("data/aresos/nether_home.dat"));
        } catch (ReflectiveOperationException | IOException error) {
            throw new AssertionError("Could not take the test's home record away: " + error, error);
        }
        check(NetherHome.get(server) == null, "The test's home record is still there");
    }

    private interface Part { void run() throws Exception; }

    /** Runs a part of the town test; when it fails, puts the host, the hub record and the chunks back. */
    private static void guarded(java.util.function.Supplier<Host> hosting, ServerLevel level, Set<Long> near, Part part) {
        guarded(hosting, level, near, part, () -> null);
    }

    /** {@link #guarded}, also putting the world's home record back when the test made one ({@code home}: null when not). */
    private static void guarded(java.util.function.Supplier<Host> hosting, ServerLevel level, Set<Long> near, Part part,
                                java.util.function.Supplier<HomeRecord> home) {
        try {
            part.run();
        } catch (Throwable error) {
            var host = hosting.get();
            try {
                if (home.get() != null) {
                    try { home.get().restore(level.getServer()); } catch (Throwable ignored) { }
                }
                if (host != null) {
                    var hub = HubData.get(host.server);
                    if (hub != null) for (var logo : hub.logos()) if (logo.app().startsWith(host.prefix)) {
                        try { Town.remove(host.server, logo.app()); } catch (Exception ignored) { }
                    }
                    host.close();
                }
            } catch (Exception ignored) {
            } finally {
                hold(level, near, false);
            }
            throw error instanceof AssertionError assertion ? assertion : new AssertionError(error.getMessage(), error);
        }
    }
}
