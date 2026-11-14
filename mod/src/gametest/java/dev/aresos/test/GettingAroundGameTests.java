package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.hub.Town;
import dev.aresos.hub.Whereabouts;
import dev.aresos.names.ProgramCommands;
import dev.aresos.names.SlashCommands;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.GettingAround;
import dev.aresos.world.HomeCommands;
import dev.aresos.world.NetherHome;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GatePicture;
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
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
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
    private static final int LOAD_TICKS = 400_000;

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
        var state = new Object() { Host host; };
        helper.startSequence()
                .thenWaitUntil(() -> helper.assertTrue(loaded(level, near), "The chunks are not loaded yet"))
                .thenExecute(() -> {
                    NetherHome.Home before = null;
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
                        var home = new NetherHome.Home(level.dimension(), Vec3.atBottomCenterOf(spot.offset(-6, 0, -6)), 180, -8);
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
                    } catch (Exception error) {
                        throw new AssertionError(error.getMessage(), error);
                    } finally {
                        var server = level.getServer();
                        if (before != null) NetherHome.get(server).setHome(before);
                        hold(level, near, false);
                    }
                })
                .thenSucceed();
    }

    private interface Part { void run() throws Exception; }

    /** Runs a part of the town test; when it fails, puts the host, the hub record and the chunks back. */
    private static void guarded(java.util.function.Supplier<Host> hosting, ServerLevel level, Set<Long> near, Part part) {
        try {
            part.run();
        } catch (Throwable error) {
            var host = hosting.get();
            try {
                if (host != null) {
                    var hub = HubData.get(host.server);
                    if (hub != null) for (var logo : hub.logos()) if (logo.app().startsWith("go-")) {
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
