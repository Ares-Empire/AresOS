package dev.aresos.test;

import com.google.gson.JsonObject;
import dev.aresos.AresOs;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldSaves;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.FakeSupervisor;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.AutosaveTestAccess;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.SectionPos;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.storage.RegionFile;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;
import net.minecraft.world.level.chunk.storage.SerializableChunkData;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Comparator;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Package 46: the supervisor asks, the mod saves. The real lifecycle client and the game's own saves
 * ({@link WorldSaves}) against a fake supervisor: a save while playing, with the Esc menu open and while a window covers
 * the world (package 40's {@code shell_covered}, through a fake helper as in {@link HomeScreenClientGameTest}). Each
 * time a block placed just before the request is missing from a copy of its region file before {@code world_saved}
 * and in it after, as a backup would copy it; the save opens no screen, pauses nothing and leaves nothing in the chat.
 * Then the refusals: no world, not a desktop world, a save still queued when the stop begins, and a request during
 * the stop.
 *
 * <p>Owner fix 1: the home screen shows no "Saving world" text. Outside it (the first save, before the test turns the
 * session flag on) the save raises the text as Minecraft does. From then on, in a game the session started and a
 * desktop world, every save raises it and no frame draws it: requested saves while playing, under the Esc menu and
 * while covered, the game's own autosave and {@code save-all}, and the saves when pausing and closing in between.
 */
public final class SaveNowClientGameTest implements FabricClientGameTest {
    private static final int Y = 150;
    private static final Set<String> SAVED = Set.of("op", "id", "ok", "ms", "world");
    private static final Set<String> REFUSED = Set.of("op", "id", "ok", "reason");

    @Override public void runTest(ClientGameTestContext context) {
        Path folder;
        try {
            folder = Files.createTempDirectory("a46");  // a Unix socket path must stay short
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        var previousShell = AresOs.shell();
        var duringStop = new AtomicReference<Object>();
        var arm = new AtomicReference<MinecraftServer>();
        try (var supervisor = new FakeSupervisor(folder.resolve("d.sock"));
             var lifecycle = supervisor.client(WorldSaves.INSTANCE)) {
            lifecycle.start();
            context.waitFor(client -> supervisor.received("lifecycle_hello").size() == 1, 200);
            ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
                if (arm.compareAndSet(server, null)) duringStop.set(askDuringStop(supervisor));
            });
            ServerLifecycleEvents.BEFORE_SAVE.register((server, flush, force) -> SavingText.began());
            SavingText.start();

            // The title screen: no world to save.
            refused(context, supervisor, 1, "no_world");

            int framesBeforeHome;
            try (var world = context.worldBuilder().create()) {
                var server = context.computeOnClient(Minecraft::getSingleplayerServer);
                // A world that is not a desktop world still answers.
                refused(context, supervisor, 2, "not_desktop_world");
                world.getServer().runOnServer(s -> {
                    var level = world.getConnection().getServerLevel();
                    for (int x = -2; x <= 8; x++) for (int z = -2; z <= 4; z++)
                        level.setBlockAndUpdate(new BlockPos(x, Y - 1, z), Blocks.STONE.defaultBlockState());
                    DesktopWorld.setEnabled(s, true);
                    world.getConnection().getServerPlayer().setGameMode(GameType.SURVIVAL);
                    var player = world.getConnection().getServerPlayer();
                    player.teleportTo(level, 0.5, Y, 0.5, Set.of(), 0, 0, false);
                    player.setDeltaMovement(Vec3.ZERO);
                });
                context.waitFor(client -> ShellFocusClient.readyWorld(client) != null, 400);
                String name = context.computeOnClient(ShellFocusClient::readyWorld);
                check(name.equals(DesktopWorld.saveName(server)), "world_ready and world_saved name the world differently");

                // Playing in a game the session did not start: saved, still playing, and the "Saving world" text shows
                // as in Minecraft.
                context.runOnClient(client -> HomeScreen.forTests(false, null));
                var playing = saveWithBlock(context, world, supervisor, folder, 3, new BlockPos(2, Y, 2), Blocks.GOLD_BLOCK, name, true);
                context.runOnClient(client -> check(!client.isPaused() && client.gui.screen() == null && client.level != null,
                        "The save paused the game or opened a screen"));
                serverPaused(context, world.getServer(), false, "The save paused the server");

                // The home screen from here on: a game the session started, in a desktop world, the helper not
                // connected (the cover below connects one). No frame may draw the text any more, for any save.
                context.runOnClient(client -> HomeScreen.forTests(true, null));
                framesBeforeHome = SavingText.frames();
                var home = saveWithBlock(context, world, supervisor, folder, 10, new BlockPos(6, Y, 2), Blocks.LAPIS_BLOCK, name, false);
                context.runOnClient(client -> check(!client.isPaused() && client.gui.screen() == null && client.level != null,
                        "The save paused the home screen or opened a screen"));

                // The Esc menu open: the server is paused, and still saves; the menu stays as it was.
                context.runOnClient(client -> client.pauseGame(false));
                context.waitFor(client -> client.gui.screen() instanceof PauseScreen && client.isPaused(), 200);
                serverPaused(context, world.getServer(), true, "Fixture: the Esc menu did not pause the server");
                var menu = context.computeOnClient(client -> client.gui.screen());
                var esc = saveWithBlock(context, world, supervisor, folder, 4, new BlockPos(3, Y, 2), Blocks.DIAMOND_BLOCK, name, false);
                context.runOnClient(client -> check(client.gui.screen() == menu && client.isPaused() && client.level != null,
                        "The save changed the Esc menu or left the world"));
                serverPaused(context, world.getServer(), true, "The save unpaused the server under the Esc menu");
                context.runOnClient(client -> client.gui.setScreen(null));
                context.waitFor(client -> !client.isPaused(), 200);

                // Covered: a maximized window over the world pauses it without a screen (package 40); it still saves.
                long covered = covered(context, world, supervisor, folder, name);

                // A save still queued when the server begins to stop is refused, never run afterwards, and later
                // requests are refused until the stop ends. The server thread waits for the test between ticks, so the
                // request stays queued until the test lets it tick.
                var pos = new BlockPos(5, Y, 2);
                place(world, pos, Blocks.IRON_BLOCK);
                supervisor.save(5, "shutdown");
                waitOff(() -> WorldSaves.INSTANCE.queued().contains(server), "the save to be queued");
                WorldSaves.INSTANCE.stopping(server);
                expect(supervisor, 5, "server_stopping");
                supervisor.save(6, "shutdown");
                expect(supervisor, 6, "server_stopping");
                WorldSaves.INSTANCE.started(server);
                context.waitTicks(10);
                check(WorldSaves.INSTANCE.queued().isEmpty(), "The refused save stayed queued");
                check(supervisor.answers(5).size() == 1, "The refused save was answered again: " + supervisor.answers(5));
                check(onDisk(folder, server, world, pos) != Blocks.IRON_BLOCK.defaultBlockState(),
                        "The refused save ran after all");
                saved(context, supervisor, 7, name, false);
                check(onDisk(folder, server, world, pos) == Blocks.IRON_BLOCK.defaultBlockState(), "The next save missed the block");

                // The game's own saves show no text in the home screen either.
                autosave(context, world.getServer());
                saveAll(context, world.getServer());

                // The real stop: a request while the world closes is refused (the test's listener asks on the server
                // thread, after the mod's own listener ran).
                arm.set(server);
                AresOs.LOGGER.info("46 save times in the test world: playing {} ms, home screen {} ms, Esc menu {} ms, "
                        + "covered {} ms", playing, home, esc, covered);
            }
            // Every save since the home screen began, the pauses' and the close's own included.
            int drawnAtHome = SavingText.frames() - framesBeforeHome;
            check(drawnAtHome == 0, "The home screen drew the Saving world text in " + drawnAtHome + " frames");
            check(duringStop.get() instanceof JsonObject, "No request was asked during the stop: " + duringStop.get());
            var during = (JsonObject) duringStop.get();
            check(REFUSED.equals(during.keySet()) && !during.get("ok").getAsBoolean()
                    && "server_stopping".equals(during.get("reason").getAsString()), "A request during the stop: " + during);
            // Closed: no world again.
            refused(context, supervisor, 9, "no_world");
            check(supervisor.received("lifecycle_hello").size() == 1, "The lifecycle channel reconnected during the test");
            AresOs.LOGGER.info("46 save-now checks passed: saves while playing, with the Esc menu open and covered put a "
                    + "block placed just before the request into the region file before world_saved, with world_ready's "
                    + "identity, no screen, no pause and no chat line; no_world on the title screen and after closing, "
                    + "not_desktop_world, server_stopping for a save queued when the stop began (which never ran) and "
                    + "for requests during the stop; the Saving world text showed outside the home screen and in it "
                    + "never, for requested saves while playing, under the Esc menu and covered, the autosave, save-all, "
                    + "and the pauses' and the close's saves");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            SavingText.stop();
            arm.set(null);
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(previousShell);
                HomeScreen.forTests(null, null);
            });
            deleteTree(folder);
        }
    }

    /**
     * Places the block while nothing saves (after the pause's own save, when paused), shows that the region file does
     * not have it yet, asks for a save and checks the answer, the file and the "Saving world" text ({@code shown}
     * outside the home screen, never drawn in it). Returns the save's ms.
     */
    private static long saveWithBlock(ClientGameTestContext context, TestSingleplayerContext world, FakeSupervisor supervisor,
                                      Path folder, int id, BlockPos pos, Block block, String name, boolean shown) {
        var server = context.computeOnClient(Minecraft::getSingleplayerServer);
        // Let a pause's own save (Minecraft saves when the game pauses) reach the file before the block goes in.
        context.waitTicks(10);
        place(world, pos, block);
        check(onDisk(folder, server, world, pos) != block.defaultBlockState(),
                "Fixture: the block was on disk before any save; the check could not tell");
        int chat = context.computeOnClient(client -> ((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().size());
        long ms = saved(context, supervisor, id, name, shown);
        check(onDisk(folder, server, world, pos) == block.defaultBlockState(),
                "After world_saved the region file does not hold the block placed before the request (" + block + ")");
        context.runOnClient(client -> check(((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().size() == chat,
                "The save left a line in the chat"));
        return ms;
    }

    private static long covered(ClientGameTestContext context, TestSingleplayerContext world, FakeSupervisor supervisor,
                                Path folder, String name) throws IOException {
        Path sockets = Files.createTempDirectory("a46h");
        var previousShell = AresOs.shell();
        try (var helper = new FakeHelper(sockets); var shell = helper.client(FakeHelper.fast())) {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(shell);
                HomeScreen.forTests(true, null);
            });
            shell.start();
            shell.awaitApps(Duration.ofSeconds(10));
            context.waitFor(HomeScreen::active, 200);
            context.runOnClient(client -> ShellFocusClient.register(shell));
            helper.event("shell_covered", Map.of("covered", true));
            context.waitFor(Minecraft::isPaused, 1200);
            check(context.computeOnClient(client -> client.gui.screen() == null), "Fixture: covering opened a screen");
            serverPaused(context, world.getServer(), true, "Fixture: covering did not pause the server");
            long ms = saveWithBlock(context, world, supervisor, folder, 8, new BlockPos(4, Y, 2), Blocks.EMERALD_BLOCK, name, false);
            context.runOnClient(client -> check(client.isPaused() && client.gui.screen() == null && client.level != null,
                    "The save uncovered the world, opened a screen or left the world"));
            serverPaused(context, world.getServer(), true, "The save unpaused the covered server");
            helper.event("shell_covered", Map.of("covered", false));
            context.waitFor(client -> !client.isPaused(), 1200);
            return ms;
        } finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(previousShell);
                HomeScreen.forTests(true, null);  // still the home screen, without the helper again
            });
            deleteTree(sockets);
        }
    }

    /**
     * Asks for a save and waits (ticking) for its answer: saved, with the world's identity. Then the "Saving world"
     * text: drawn if {@code shown}, else never. Returns the save's ms.
     */
    private static long saved(ClientGameTestContext context, FakeSupervisor supervisor, int id, String name, boolean shown) {
        var indicator = SavingIndicator.watch(context);
        try { supervisor.save(id, "backup"); }
        catch (IOException error) { throw new UncheckedIOException(error); }
        context.waitFor(client -> {
            indicator.sample(client);
            return !supervisor.answers(id).isEmpty();
        }, 1200);
        var answer = supervisor.answers(id).getFirst();
        check(SAVED.equals(answer.keySet()) && answer.get("ok").getAsBoolean(), "Not saved: " + answer);
        check(answer.get("id").getAsInt() == id && "world_saved".equals(answer.get("op").getAsString()), "Answer " + answer);
        var identity = answer.getAsJsonObject("world");
        check(identity.get("id").getAsString().equals(name) && identity.get("desktop").getAsBoolean()
                && identity.size() == 2, "Not world_ready's identity: " + identity);
        long ms = answer.get("ms").getAsLong();
        check(ms >= 0, "A negative save time: " + answer);
        indicator.settle(context, "save " + id + " (" + ms + " ms)", shown);
        return ms;
    }

    /** The game's own autosave, brought to the next server tick: no text in the home screen. */
    private static void autosave(ClientGameTestContext context, TestServerContext server) {
        var indicator = SavingIndicator.watch(context);
        server.runOnServer(s -> ((AutosaveTestAccess) s).aresos$setTicksUntilAutosave(1));
        // The autosave sets the next countdown, minutes long, when it runs.
        for (int tick = 0; server.computeOnServer(s -> ((AutosaveTestAccess) s).aresos$ticksUntilAutosave()) <= 1; tick++) {
            if (tick == 100) throw new AssertionError("Fixture: the autosave did not run");
            context.waitTick();
            context.runOnClient(indicator::sample);
        }
        indicator.settle(context, "the autosave", false);
    }

    /** {@code save-all flush}, as typed in the chat: no text in the home screen. */
    private static void saveAll(ClientGameTestContext context, TestServerContext server) {
        var indicator = SavingIndicator.watch(context);
        int began = SavingText.begun();
        server.runOnServer(s -> s.getCommands().performPrefixedCommand(s.createCommandSourceStack(), "save-all flush"));
        check(SavingText.begun() > began, "Fixture: save-all saved nothing");
        indicator.settle(context, "save-all", false);
    }

    /**
     * Vanilla's "Saving world" corner text for one save. A client tick that finds the server saving fades it in a fifth
     * of the way, and each tick after fades it out a fifth; a frame draws it while it is at least 1/255 opaque
     * ({@code Hud.extractSavingIndicator}). {@link SavingText} makes every save reach a client tick, so the text rises
     * for each save, as Minecraft would show it; then it either was drawn or not.
     */
    private static final class SavingIndicator {
        private final int framesBefore;
        private boolean rose;
        private float peak;

        private SavingIndicator(int framesBefore) {
            this.framesBefore = framesBefore;
        }

        /** Waits until no earlier save's text could be drawn, then starts watching. */
        static SavingIndicator watch(ClientGameTestContext context) {
            context.waitFor(client -> !visible(client), 200);
            return new SavingIndicator(SavingText.frames());
        }

        /** After each client tick: did the text fade in, and how far. */
        void sample(Minecraft client) {
            var hud = (HudTestAccess) client.gui.hud;
            float now = hud.aresos$savingIndicator();
            if (now > hud.aresos$lastSavingIndicator()) rose = true;
            if (rose) peak = Math.max(peak, now);
        }

        /** Ticks on until the text has risen and faded out again (3 s at most), then checks the frames that drew it. */
        void settle(ClientGameTestContext context, String what, boolean shown) {
            for (int tick = 0; ; tick++) {
                boolean done = context.computeOnClient(client -> {
                    sample(client);
                    return rose && !visible(client);
                });
                if (done) break;
                if (tick == 60) throw new AssertionError("Fixture: the Saving world text did not rise and fade for " + what
                        + " (rose: " + rose + ")");
                context.waitTick();
            }
            int frames = SavingText.frames() - framesBefore;
            AresOs.LOGGER.info("46 saving indicator for {}: rose to {}% opacity, drawn in {} frames", what,
                    Math.round(peak * 100), frames);
            if (shown) {
                boolean option = context.computeOnClient(client -> client.options.showAutosaveIndicator().get());
                check(frames > 0, "Outside the home screen " + what + " did not draw the Saving world text (the Autosave "
                        + "Indicator option is " + (option ? "on" : "off") + ")");
            } else {
                check(frames == 0, "The home screen drew the Saving world text for " + what + " in " + frames + " frames");
            }
        }

        /** Whether a frame could draw it now: it is drawn between its last two values. */
        private static boolean visible(Minecraft client) {
            var hud = (HudTestAccess) client.gui.hud;
            return Math.max(hud.aresos$savingIndicator(), hud.aresos$lastSavingIndicator()) * 255 >= 1;
        }
    }

    private static void refused(ClientGameTestContext context, FakeSupervisor supervisor, int id, String reason) {
        try { supervisor.save(id, "backup"); }
        catch (IOException error) { throw new UncheckedIOException(error); }
        context.waitFor(client -> !supervisor.answers(id).isEmpty(), 200);
        var answer = supervisor.answers(id).getFirst();
        check(REFUSED.equals(answer.keySet()) && !answer.get("ok").getAsBoolean()
                && reason.equals(answer.get("reason").getAsString()), "Expected " + reason + ": " + answer);
    }

    /** Waits for an answer that needs no tick (the server is not involved). */
    private static void expect(FakeSupervisor supervisor, int id, String reason) {
        JsonObject answer;
        try { answer = supervisor.answer(id, 10); }
        catch (InterruptedException error) { throw new AssertionError(error); }
        check(REFUSED.equals(answer.keySet()) && reason.equals(answer.get("reason").getAsString()),
                "Expected " + reason + ": " + answer);
    }

    /** On the server thread inside its stop: asks once and returns the answer, or what went wrong. */
    private static Object askDuringStop(FakeSupervisor supervisor) {
        try {
            supervisor.save(30, "shutdown");
            return supervisor.answer(30, 10);
        } catch (IOException | InterruptedException | AssertionError error) {
            return error.toString();
        }
    }

    private static void place(TestSingleplayerContext world, BlockPos pos, Block block) {
        world.getServer().runOnServer(server ->
                world.getConnection().getServerLevel().setBlockAndUpdate(pos, block.defaultBlockState()));
    }

    /**
     * The block at {@code pos} in a copy of its region file, as a backup would copy it: null when the chunk is not in
     * the file yet. A copy taken while the server writes may be torn; then it is read again.
     */
    private static BlockState onDisk(Path folder, MinecraftServer server, TestSingleplayerContext world, BlockPos pos) {
        ServerLevel level = world.getServer().computeOnServer(s -> world.getConnection().getServerLevel());
        var chunk = ChunkPos.containing(pos);
        Path file = DimensionType.getStorageFolder(level.dimension(), server.getWorldPath(LevelResource.ROOT))
                .resolve("region").resolve("r." + chunk.getRegionX() + "." + chunk.getRegionZ() + ".mca");
        RuntimeException last = null;
        for (int attempt = 0; attempt < 20; attempt++) {
            Path copies = null;
            try {
                if (!Files.exists(file)) return null;
                copies = Files.createTempDirectory(folder, "copy");
                Path copy = copies.resolve(file.getFileName());
                Files.copy(file, copy);
                try (var region = new RegionFile(new RegionStorageInfo("aresos-46", level.dimension(), "chunk"), copy, copies, false);
                     var in = region.getChunkDataInputStream(chunk)) {
                    if (in == null) return null;
                    var data = SerializableChunkData.parse(level, level.palettedContainerFactory(), NbtIo.read(in));
                    for (var section : data.sectionData())
                        if (section.y() == SectionPos.blockToSectionCoord(pos.getY()) && section.chunkSection() != null)
                            return section.chunkSection().getBlockState(pos.getX() & 15, pos.getY() & 15, pos.getZ() & 15);
                    return Blocks.AIR.defaultBlockState();
                }
            } catch (IOException | RuntimeException torn) {
                last = torn instanceof RuntimeException runtime ? runtime : new UncheckedIOException((IOException) torn);
                sleep(50);
            } finally {
                if (copies != null) deleteTree(copies);
            }
        }
        throw new AssertionError("Could not read the region file " + file, last);
    }

    /** Waits on the test thread without ticking (for what happens on the lifecycle client's own threads). */
    private static void waitOff(java.util.function.BooleanSupplier condition, String what) {
        long deadline = System.nanoTime() + 5_000_000_000L;
        while (!condition.getAsBoolean()) {
            if (System.nanoTime() > deadline) throw new AssertionError("Timed out waiting for " + what);
            sleep(5);
        }
    }

    private static void sleep(long millis) {
        try { Thread.sleep(millis); }
        catch (InterruptedException error) { throw new AssertionError(error); }
    }

    /** The server takes the client's pause at its own next tick, so its state is polled between ticks. */
    private static void serverPaused(ClientGameTestContext context, TestServerContext server, boolean paused, String failure) {
        for (int tick = 0; tick < 200; tick++) {
            if (server.computeOnServer(MinecraftServer::isPaused) == paused) return;
            context.waitTick();
        }
        throw new AssertionError(failure);
    }

    private static void deleteTree(Path root) {
        if (root == null || !Files.exists(root)) return;
        try (var files = Files.walk(root)) {
            for (var path : files.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        } catch (IOException ignored) {
            // A temporary folder; the next run makes a new one.
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
