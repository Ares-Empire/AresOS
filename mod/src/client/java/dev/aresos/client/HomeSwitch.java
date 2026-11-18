package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.hub.TownKeeper;
import dev.aresos.world.HomeSwap;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.GenericMessageScreen;
import net.minecraft.client.gui.screens.ProgressScreen;
import net.minecraft.client.gui.screens.RecoverWorldDataScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.time.LocalDateTime;

/**
 * Package 48, A.5: "New home…" in the AresOS menu, from one home to a new one without the title screen in between.
 *
 * <ol>
 *   <li>The open home is saved and closed ("Making your new home…" shows from here to the end).</li>
 *   <li>The new home is made under a staging name ({@code AresHub-new-<date>}) with the plan's manifest and settings;
 *       its server provisions it as it starts.</li>
 *   <li>Once his player is in it, it is saved and closed again, and its files are checked as the supervisor checks a
 *       home. Only then two renames: AresHub to {@code AresHub-<date>}, the staging folder to AresHub.</li>
 *   <li>AresHub opens; he arrives in Live mode as at every start.</li>
 * </ol>
 *
 * <p>So a game that dies anywhere in between leaves either the old AresHub as it was or, in the microseconds between
 * the two renames, no AresHub (the supervisor then says the hub is missing). Whatever fails, the old home opens again
 * (moved back if it was moved) and a chat line says why and where it is; a failed reopen keeps an actionable recovery
 * screen until Try again succeeds. The staging folder of a failed attempt stays in the saves.
 *
 * <p>The end of each close and open is seen at a client tick, because the game can finish those later than the call
 * returns. A world is opened from a task, as the game's buttons do, and closed from the client tick, as the game does
 * when a server says goodbye. Closing halts the integrated server, which runs a last task on the server thread and
 * waits for it; in the client game test framework's lock-step that only works from a test task (the framework defers
 * it to a safe point), so the tests take the closes over ({@link #closeFromTestTasksForTests}). Without that, a close
 * from a task or from the tick hung a full test run twice, the server waiting at the framework's barrier. While a switch runs, {@link #busy()} is true: the shell sends no
 * {@code world_ready} and no ready heartbeat ({@link ShellFocusClient#readyWorld}), and a title screen, a message or
 * progress screen the game sets is replaced by the working screen ({@link #screenComing}). Client thread only.
 */
public final class HomeSwitch {
    static final Component WORKING = Component.literal("Making your new home…");
    /** Two minutes of ticks: the longest a world may take to close, or to let him in, before the old home comes back. */
    private static final int WAIT_LIMIT = 20 * 120;

    private enum Phase {
        IDLE,
        /** The old home is closing; then MAKING (a task) makes the staging world and STAGING waits for his player. */
        CLOSING_OLD, MAKING, STAGING,
        /** The staging world is closing; then SWAPPING (a task) checks and renames, and OPENING waits for AresHub. */
        CLOSING_STAGING, SWAPPING, OPENING,
        /** Something failed: whatever is open closes, RESTORING (a task) puts the old home back, RECOVERING waits. */
        FAILING, RESTORING, RECOVERING, RETRY
    }

    private static volatile Phase phase = Phase.IDLE;
    private static int waited;
    /** FAILING has asked the open world to close (from the tick, once). */
    private static boolean closing;
    private static boolean closeFromTestTasks;
    private static Runnable pendingClose;
    private static HomePlan plan;
    private static Screen working;
    private static Path saves, staging, archived;
    /** The world he left, followed through every successful rename, including undo and restoration. */
    private static Path previousHome;
    private static String previousLevelName;
    private static boolean promoted;
    private static HomeRecoveryScreen recovery;
    private static String failure;
    private static long startedNanos;
    private static final long[] gapNanos = {-1};
    private static boolean failSecondRename;
    private static HomeSwap.Mover fileMover = HomeSwap.FILES;
    private static boolean failNewOpen, holdRecoveryOpen;
    private static long lastMillis = -1, lastGapNanos = -1;

    private HomeSwitch() { }

    public static void register() {
        ClientTickEvents.END_CLIENT_TICK.register(HomeSwitch::tick);
    }

    /**
     * A home switch is running: from his "Make the new home" until he is in a home again. Package 46's
     * {@code save_world} answers {@code no_world} meanwhile, and no world is reported ready.
     */
    public static boolean busy() { return phase != Phase.IDLE; }

    /** The line the switch shows from start to end, on its own screen and on the game's loading screens. */
    public static Component working() { return WORKING; }

    /** Starts the switch from the open home to a new one made from {@code plan}. */
    static void start(Minecraft client, HomePlan plan) {
        if (busy()) return;
        var server = client.getSingleplayerServer();
        Path base = client.getLevelSource().getBaseDir().toAbsolutePath().normalize();
        Path source = server == null ? null : server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
        // Never close a world unless its actual save can be used to bring him back.
        if (source == null || !base.equals(source.getParent()) || Files.isSymbolicLink(source)
                || !Files.isDirectory(source, LinkOption.NOFOLLOW_LINKS)) {
            AresOs.LOGGER.error("New home: the current save folder could not be found; leaving the world open");
            client.gui.hud.getChat().addClientSystemMessage(Component.literal(
                    "Couldn't make the new home: the current save folder could not be found. Your home is still open."));
            client.gui.setScreen(new AresOsMenuScreen());
            return;
        }
        HomeSwitch.plan = plan;
        saves = base;
        previousHome = source;
        previousLevelName = server.getWorldData().getLevelName();
        promoted = false;
        recovery = null;
        staging = null;
        archived = null;
        failure = null;
        gapNanos[0] = -1;
        // A game that switches homes is past its first start: a title screen now must never make a home of its own.
        FirstStart.decided();
        startedNanos = System.nanoTime();
        working = new HomeWorkingScreen(WORKING);
        AresOs.LOGGER.info("New home: making a {} home from {} ({})", plan.kind(), previousHome.getFileName(), previousLevelName);
        enter(Phase.CLOSING_OLD);
        WorldSaves.INSTANCE.homeSwitchStarted();
        client.gui.setScreen(working);
        closeWorld(client);
    }

    private static void tick(Minecraft client) {
        Phase now = phase;
        if (now == Phase.RETRY) {
            if (client.gui.screen() != recovery) client.gui.setScreen(recovery);
            return;
        }
        if (now == Phase.IDLE || now == Phase.MAKING || now == Phase.SWAPPING || now == Phase.RESTORING) return;
        if (++waited > WAIT_LIMIT) {
            fail(client, "it took too long", null);
            return;
        }
        switch (now) {
            case CLOSING_OLD -> { if (closed(client)) next(client, Phase.MAKING, HomeSwitch::makeStaging); }
            case STAGING -> {
                // His player is in the staging world, so it is provisioned: it is saved and closed, never drawn.
                if (inWorld(client, staging)) {
                    enter(Phase.CLOSING_STAGING);
                    closeFromTick(client);
                }
            }
            case CLOSING_STAGING -> { if (closed(client)) next(client, Phase.SWAPPING, HomeSwitch::swapAndOpen); }
            case OPENING -> { if (ready(client, saves.resolve(NetherHome.SAVE_FOLDER))) finish(client); }
            case FAILING -> {
                if (closed(client)) next(client, Phase.RESTORING, HomeSwitch::restoreAndOpen);
                else if (!closing) {
                    closing = true;
                    closeFromTick(client);
                }
            }
            case RECOVERING -> {
                if (ready(client, previousHome)
                        && client.getSingleplayerServer().getWorldData().getLevelName().equals(previousLevelName)) finish(client);
            }
            default -> { }
        }
    }

    /** The staging world: made with the plan's settings, the game's own create flow and the server's provisioning. */
    private static void makeStaging(Minecraft client) {
        try {
            Files.createDirectories(saves);
            staging = HomeSwap.freshStaging(saves, LocalDateTime.now());
            AresOs.LOGGER.info("New home: building it in {}", staging.getFileName());
            TownKeeper.preparingHome(staging, true);
            plan.create(client, staging, working);
        } catch (IOException | RuntimeException error) {
            fail(client, "it could not be started (" + reason(error) + ")", error);
            return;
        }
        // The game gave up on it and said so by going to the title screen, which is already a failure.
        if (phase != Phase.MAKING) return;
        if (client.getSingleplayerServer() == null) {
            fail(client, "the new world did not start", null);
            return;
        }
        enter(Phase.STAGING);
    }

    private static void swapAndOpen(Minecraft client) {
        TownKeeper.preparingHome(staging, false);
        try {
            HomeSwap.checkComplete(staging);
            archived = HomeSwap.swap(saves, staging, LocalDateTime.now(), mover(), gapNanos);
        } catch (HomeSwap.UndoFailed error) {
            archived = error.archived;
            fail(client, "it could not be moved into place (" + reason(error) + ")", error);
            return;
        } catch (IOException | RuntimeException error) {
            fail(client, "it could not be moved into place (" + reason(error) + ")", error);
            return;
        }
        AresOs.LOGGER.info("New home: in place as AresHub; previous AresHub: {}; renames took {} µs",
                archived == null ? "none" : archived.getFileName(), gapNanos[0] / 1000);
        enter(Phase.OPENING);
        open(client, saves.resolve(NetherHome.SAVE_FOLDER), false);
    }

    /** Restore the canonical save if possible; always open the world he left, at its tracked location. */
    private static void restoreAndOpen(Minecraft client) {
        TownKeeper.preparingHome(staging, false);
        if (archived != null || promoted) {
            try {
                HomeSwap.restore(saves, archived, staging, mover());
                archived = null;
            } catch (IOException | RuntimeException error) {
                AresOs.LOGGER.error("New home: restoration failed; previous home is {}, canonical folder is {} (replacement: {})",
                        previousHome.getFileName(), NetherHome.SAVE_FOLDER, promoted, error);
            }
        }
        enter(Phase.RECOVERING);
        open(client, previousHome, true);
    }

    private static void open(Minecraft client, Path folder, boolean recovering) {
        String problem = recovering ? "the old home did not open" : "the new home did not open";
        try {
            if (recovering && holdRecoveryOpen) return;
            if (!recovering && failNewOpen) {
                fail(client, problem, new IOException("injected open failure"));
                return;
            }
            client.createWorldOpenFlows().openWorld(folder.getFileName().toString(), () -> fail(client, problem, null));
            // This failure screen owns the storage lock. Cancel through its callback before offering our retry;
            // replacing it on timeout alone would leak the lock and make every subsequent open fail too.
            if (client.gui.screen() instanceof RecoverWorldDataScreen damaged) damaged.onClose();
        } catch (RuntimeException error) {
            fail(client, problem + " (" + reason(error) + ")", error);
        }
    }

    /** Retries restoration and opening, after closing anything a failed or timed-out open left behind. */
    private static void retry(Minecraft client) {
        if (phase != Phase.RETRY) return;
        closing = false;
        enter(Phase.FAILING);
        client.gui.setScreen(working);
    }

    private static String recoveryMessage() {
        if (previousHome.equals(saves.resolve(NetherHome.SAVE_FOLDER))) return "Your home is as it was.";
        String location = "Your previous home is open from the saves folder " + previousHome.getFileName() + ". ";
        if (promoted) return location + "The new home remains in AresHub.";
        if (Files.exists(saves.resolve(NetherHome.SAVE_FOLDER), LinkOption.NOFOLLOW_LINKS))
            return location + "AresHub is a separate home.";
        return location + "AresHub is missing; the AresOS session will not find this home until it is named AresHub again.";
    }

    private static void finish(Minecraft client) {
        lastMillis = (System.nanoTime() - startedNanos) / 1_000_000;
        lastGapNanos = gapNanos[0];
        String why = failure;
        enter(Phase.IDLE);
        working = null;
        plan = null;
        recovery = null;
        if (why == null) {
            AresOs.LOGGER.info("New home: ready {} ms after he chose it", lastMillis);
        } else {
            AresOs.LOGGER.warn("New home: back in {} ({}) after {} ms: {}; canonical folder {} holds replacement: {}",
                    previousHome.getFileName(), previousLevelName, lastMillis, why, NetherHome.SAVE_FOLDER, promoted);
            client.gui.hud.getChat().addClientSystemMessage(
                    Component.literal("Couldn't make the new home: " + why + ". "
                            + recoveryMessage()));
        }
    }

    /** A failed recovery keeps its target and the title-screen guard until a retry opens the old home. */
    static void fail(Minecraft client, String reason, Throwable error) {
        Phase now = phase;
        if (now == Phase.IDLE || now == Phase.RETRY) return;
        if (now == Phase.FAILING || now == Phase.RESTORING || now == Phase.RECOVERING) {
            AresOs.LOGGER.error("New home: could not reopen {} ({}); canonical folder is {}: {}",
                    previousHome.getFileName(), previousLevelName, NetherHome.SAVE_FOLDER, reason, error);
            recovery = new HomeRecoveryScreen(previousHome.getFileName().toString(), reason, () -> retry(client));
            enter(Phase.RETRY);
            return;
        }
        AresOs.LOGGER.error("New home: {}; opening {} again", reason, previousHome.getFileName(), error);
        failure = reason;
        closing = false;
        enter(Phase.FAILING);
    }

    /**
     * What {@code Gui.setScreen} gets while a switch runs ({@code GuiScreenMixin}). The title screen never shows: it
     * means the game gave up on a world, which is a failure. The game's message and progress screens become the
     * working screen, and so does the world itself until the last step; its loading screens stay (they finish the
     * load) and show the working line ({@code LevelLoadingCoverMixin}). Everything else is let through.
     */
    public static Screen screenComing(Minecraft client, Screen screen) {
        if (!busy()) return screen;
        if (phase == Phase.RETRY) return recovery;
        if (screen == working) return screen;
        if (screen instanceof TitleScreen || (screen == null && client.level == null)) {
            fail(client, "the game went back to the title screen", null);
            return phase == Phase.RETRY ? recovery : working;
        }
        if (screen instanceof DisconnectedScreen disconnected) {
            fail(client, "the world closed (" + disconnected.getNarrationMessage().getString() + ")", null);
            return phase == Phase.RETRY ? recovery : working;
        }
        if (screen == null) return phase == Phase.OPENING || phase == Phase.RECOVERING ? null : working;
        if (screen instanceof GenericMessageScreen || screen instanceof ProgressScreen) return working;
        return screen;
    }

    /** Saves and closes the open world now, or, in the client game tests, from the test's next task. */
    private static void closeFromTick(Minecraft client) {
        Phase asked = phase;
        Runnable close = () -> {
            if (phase != asked) return;
            client.gui.setScreen(working);
            closeWorld(client);
        };
        if (closeFromTestTasks) pendingClose = close;
        else close.run();
    }

    private static void closeWorld(Minecraft client) {
        if (client.level != null) client.level.disconnect(ClientLevel.DEFAULT_QUIT_MESSAGE);
        client.disconnect(working, false);
    }

    private static void enter(Phase next) {
        phase = next;
        waited = 0;
    }

    /** Runs {@code step} from the next task, unless something failed meanwhile. */
    private static void next(Minecraft client, Phase step, java.util.function.Consumer<Minecraft> action) {
        enter(step);
        client.schedule(() -> {
            if (phase == step) action.accept(client);
        });
    }

    private static boolean closed(Minecraft client) {
        return client.level == null && client.getSingleplayerServer() == null;
    }

    /** His player is in the world saved in {@code folder}. */
    private static boolean inWorld(Minecraft client, Path folder) {
        var server = client.getSingleplayerServer();
        return folder != null && client.player != null && client.level != null && server != null
                && server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().equals(folder.toAbsolutePath().normalize());
    }

    /** Only the requested world, with its loading screen gone, can finish a switch. */
    private static boolean ready(Minecraft client, Path folder) {
        return inWorld(client, folder) && client.gui.screen() == null;
    }

    private static HomeSwap.Mover mover() {
        return (from, to) -> {
            if (failSecondRename && from.equals(staging)) throw new IOException("injected test failure");
            fileMover.move(from, to);
            // Update only after a rename succeeds: a failed restore must never redirect recovery to the replacement.
            if (from.equals(previousHome)) previousHome = to;
            Path canonical = saves.resolve(NetherHome.SAVE_FOLDER);
            if (from.equals(staging) && to.equals(canonical)) promoted = true;
            if (from.equals(canonical) && to.equals(staging)) promoted = false;
        };
    }

    private static String reason(Throwable error) {
        return error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
    }

    /**
     * Client game tests: the switch leaves each close it would make at a tick for {@link #runPendingCloseForTests},
     * which the test calls from its own task on the client (see the class comment). Everything else runs as in the game.
     */
    public static void closeFromTestTasksForTests(boolean on) {
        closeFromTestTasks = on;
        pendingClose = null;
    }

    public static void runPendingCloseForTests() {
        Runnable close = pendingClose;
        pendingClose = null;
        if (close != null) close.run();
    }

    /** Client game tests: the second rename fails, so the old home has been moved and must come back. */
    public static void failSecondRenameForTests(boolean fail) { failSecondRename = fail; }

    /** Client game tests: fail a rename, or the replacement world's opening. */
    public static void failuresForTests(HomeSwap.Mover mover, boolean newOpen) {
        fileMover = mover;
        failNewOpen = newOpen;
    }

    /** Client game tests: drive the recovery timeout without waiting two minutes. */
    public static void timeoutForTests() { waited = WAIT_LIMIT; }

    public static void holdRecoveryOpenForTests(boolean hold) { holdRecoveryOpen = hold; }

    /** Client game tests: how long the last switch took, from his choice to a home, and the gap without an AresHub. */
    public static long lastMillisForTests() { return lastMillis; }

    public static long lastGapNanosForTests() { return lastGapNanos; }
}
