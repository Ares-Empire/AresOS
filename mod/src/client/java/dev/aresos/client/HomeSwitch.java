package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.world.HomeSwap;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.GenericMessageScreen;
import net.minecraft.client.gui.screens.LevelLoadingScreen;
import net.minecraft.client.gui.screens.ProgressScreen;
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
 * (moved back if it was moved) and a chat line says why; the staging folder of a failed attempt stays in the saves.
 *
 * <p>Each step that closes or opens a world is started from a task and its end is seen at a client tick, because the
 * game can finish those later than the call returns. While a switch runs, {@link #busy()} is true: the shell sends no
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
        FAILING, RESTORING, RECOVERING
    }

    private static volatile Phase phase = Phase.IDLE;
    private static int waited;
    private static HomePlan plan;
    private static Screen working;
    private static Path saves, staging, archived;
    private static String failure;
    /** What the failure's chat line says about the old home: null when it is back as AresHub, as it was. */
    private static String oldHome;
    private static long startedNanos;
    private static final long[] gapNanos = {-1};
    private static boolean failSecondRename;
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
        HomeSwitch.plan = plan;
        saves = client.getLevelSource().getBaseDir();
        staging = null;
        archived = null;
        failure = null;
        oldHome = null;
        gapNanos[0] = -1;
        // A game that switches homes is past its first start: a title screen now must never make a home of its own.
        FirstStart.decided();
        startedNanos = System.nanoTime();
        working = new HomeWorkingScreen(WORKING);
        AresOs.LOGGER.info("New home: making a {} home", plan.kind());
        enter(Phase.CLOSING_OLD);
        client.gui.setScreen(working);
        closeWorld(client);
    }

    private static void tick(Minecraft client) {
        Phase now = phase;
        if (now == Phase.IDLE || now == Phase.MAKING || now == Phase.SWAPPING || now == Phase.RESTORING) return;
        if (++waited > WAIT_LIMIT) {
            fail(client, "it took too long", null);
            return;
        }
        switch (now) {
            case CLOSING_OLD -> { if (closed(client)) next(client, Phase.MAKING, HomeSwitch::makeStaging); }
            case STAGING -> { if (inWorld(client, staging)) next(client, Phase.CLOSING_STAGING, HomeSwitch::closeStaging); }
            case CLOSING_STAGING -> { if (closed(client)) next(client, Phase.SWAPPING, HomeSwitch::swapAndOpen); }
            case OPENING -> { if (ready(client)) finish(client); }
            case FAILING -> { if (closed(client)) next(client, Phase.RESTORING, HomeSwitch::restoreAndOpen); }
            case RECOVERING -> { if (ready(client)) finish(client); }
            default -> { }
        }
    }

    /** The staging world: made with the plan's settings, the game's own create flow and the server's provisioning. */
    private static void makeStaging(Minecraft client) {
        try {
            Files.createDirectories(saves);
            staging = HomeSwap.freshStaging(saves, LocalDateTime.now());
            AresOs.LOGGER.info("New home: building it in {}", staging.getFileName());
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

    /** His player is in the staging world, so it is provisioned: it is saved and closed, never drawn. */
    private static void closeStaging(Minecraft client) {
        client.gui.setScreen(working);
        closeWorld(client);
    }

    private static void swapAndOpen(Minecraft client) {
        try {
            HomeSwap.checkComplete(staging);
            archived = HomeSwap.swap(saves, staging, LocalDateTime.now(), mover(), gapNanos);
        } catch (HomeSwap.UndoFailed error) {
            archived = error.archived;
            fail(client, "it could not be moved into place (" + reason(error) + ")", error);
            return;
        } catch (IOException error) {
            fail(client, "it could not be moved into place (" + reason(error) + ")", error);
            return;
        }
        AresOs.LOGGER.info("New home: in place as AresHub; the old one is {}; no AresHub on disk for {} µs",
                archived.getFileName(), gapNanos[0] / 1000);
        enter(Phase.OPENING);
        client.createWorldOpenFlows().openWorld(NetherHome.SAVE_FOLDER, () -> fail(client, "the new home did not open", null));
    }

    /**
     * After a failure: the new home, if it was moved into place, goes back to its staging name and the old home
     * becomes AresHub again; then AresHub opens. If the old home cannot be moved back, it opens under its dated name.
     */
    private static void restoreAndOpen(Minecraft client) {
        String open = NetherHome.SAVE_FOLDER;
        if (archived != null) {
            try {
                HomeSwap.restore(saves, archived, staging, mover());
                archived = null;
            } catch (IOException error) {
                AresOs.LOGGER.error("New home: the old home could not be moved back from {}", archived, error);
                if (!Files.exists(saves.resolve(NetherHome.SAVE_FOLDER), LinkOption.NOFOLLOW_LINKS)) {
                    open = archived.getFileName().toString();
                    oldHome = "Your home is open from the saves folder " + open
                            + ", and the AresOS session will not find it until it is named AresHub again.";
                }
            }
        }
        enter(Phase.RECOVERING);
        String name = open;
        client.createWorldOpenFlows().openWorld(name, () -> fail(client, "the old home did not open", null));
    }

    private static void finish(Minecraft client) {
        lastMillis = (System.nanoTime() - startedNanos) / 1_000_000;
        lastGapNanos = gapNanos[0];
        String why = failure;
        enter(Phase.IDLE);
        working = null;
        plan = null;
        if (why == null) {
            AresOs.LOGGER.info("New home: ready {} ms after he chose it", lastMillis);
        } else {
            AresOs.LOGGER.warn("New home: back in the old home {} ms after he chose the new one: {}", lastMillis, why);
            client.gui.hud.getChat().addClientSystemMessage(
                    Component.literal("Couldn't make the new home: " + why + ". "
                            + (oldHome == null ? "Your home is as it was." : oldHome)));
        }
    }

    /**
     * Any step that fails brings the old home back. A failure while the old home is coming back ends the switch: the
     * game's own screens then show what happened, and the title screen with its AresOS button is the last way home.
     */
    static void fail(Minecraft client, String reason, Throwable error) {
        Phase now = phase;
        if (now == Phase.IDLE) return;
        if (now == Phase.FAILING || now == Phase.RESTORING || now == Phase.RECOVERING) {
            AresOs.LOGGER.error("New home: the old home could not be opened again either: {}", reason, error);
            enter(Phase.IDLE);
            working = null;
            plan = null;
            return;
        }
        AresOs.LOGGER.error("New home: {}; opening the old home again", reason, error);
        failure = reason;
        enter(Phase.FAILING);
        client.schedule(() -> {
            if (phase != Phase.FAILING || closed(client)) return;
            client.gui.setScreen(working);
            closeWorld(client);
        });
    }

    /**
     * What {@code Gui.setScreen} gets while a switch runs ({@code GuiScreenMixin}). The title screen never shows: it
     * means the game gave up on a world, which is a failure. The game's message and progress screens become the
     * working screen, and so does the world itself until the last step; its loading screens stay (they finish the
     * load) and show the working line ({@code LevelLoadingCoverMixin}). Everything else is let through.
     */
    public static Screen screenComing(Minecraft client, Screen screen) {
        if (!busy() || screen == working) return screen;
        if (screen instanceof TitleScreen || (screen == null && client.level == null)) {
            fail(client, "the game went back to the title screen", null);
            return busy() ? working : screen;
        }
        if (screen instanceof DisconnectedScreen disconnected) {
            fail(client, "the world closed (" + disconnected.getNarrationMessage().getString() + ")", null);
            return busy() ? working : screen;
        }
        if (screen == null) return phase == Phase.OPENING || phase == Phase.RECOVERING ? null : working;
        if (screen instanceof GenericMessageScreen || screen instanceof ProgressScreen) return working;
        return screen;
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

    /** He is in a home again and its loading screen has gone. */
    private static boolean ready(Minecraft client) {
        var server = client.getSingleplayerServer();
        return client.player != null && client.level != null && server != null
                && !(client.gui.screen() instanceof LevelLoadingScreen) && client.gui.screen() != working
                && server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().getParent()
                    .equals(saves.toAbsolutePath().normalize());
    }

    private static HomeSwap.Mover mover() {
        if (!failSecondRename) return HomeSwap.FILES;
        return (from, to) -> {
            if (from.equals(staging)) throw new IOException("injected test failure");
            HomeSwap.FILES.move(from, to);
        };
    }

    private static String reason(Throwable error) {
        return error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
    }

    /** Client game tests: the second rename fails, so the old home has been moved and must come back. */
    public static void failSecondRenameForTests(boolean fail) { failSecondRename = fail; }

    /** Client game tests: how long the last switch took, from his choice to a home, and the gap without an AresHub. */
    public static long lastMillisForTests() { return lastMillis; }

    public static long lastGapNanosForTests() { return lastGapNanos; }
}
