package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.launch.LinuxAppLauncher;
import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.config.AppDefinition;
import dev.aresos.mode.LiveMode;
import dev.aresos.shell.FakeHelper;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.GameType;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Package 40: the world as the home screen, without a real session or helper. An app in front never opens the pause
 * menu while Esc still does, the game's own fullscreen is off in a session, and a launch that fails leaves a line in
 * the chat. The first check shows the game pausing without these rules, so the others prove something.
 *
 * <p>Step 2: a window that covers the world pauses it without a screen and slows its frame rate, while the helper keeps
 * hearing ready heartbeats (package 23's supervisor takes missing ones for a dead world). This part runs a real shell
 * client against a fake helper, wired up as in the session ({@link ShellFocusClient#register}). It is the last client
 * test, so the tick listener that registration leaves behind runs only against a closed client.
 */
public final class HomeScreenClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        boolean pauseSetting = context.computeOnClient(client -> client.options.pauseOnLostFocus);
        var previousLauncher = context.computeOnClient(client ->
                AresOsClient.replaceLauncher(new LinuxAppLauncher(() -> null)));
        try (var world = context.worldBuilder().create()) {
            world.getServer().runOnServer(server -> DesktopWorld.setEnabled(server, true));
            context.waitFor(AresOsClient::acceptsAppCommands);
            context.runOnClient(client -> {
                client.options.pauseOnLostFocus = true;
                AppsTestAccess.aresos$setApps(List.of(new AppDefinition("notepad", "Notepad", List.of(),
                        "minecraft:writable_book", false, "helper", null, null)));
                client.gui.setScreen(null);

                // Minecraft's own rule, with no session and no helper: half a second without focus pauses the game.
                HomeScreen.forTests(false, false);
                loseFocus(client);
                check(client.gui.screen() instanceof PauseScreen,
                        "Outside the home screen, losing the focus no longer opens the pause menu");
                regainFocus(client);
                client.gui.setScreen(null);

                // The home screen: an app in front pauses nothing and lets the mouse go.
                HomeScreen.forTests(true, true);
                client.mouseHandler.grabMouse();
                loseFocus(client);
                check(client.gui.screen() == null, "An app in front opened a screen over the home screen: "
                        + client.gui.screen());
                check(!client.mouseHandler.isMouseGrabbed(), "The mouse stayed captured while the focus was away");
                // Esc is Minecraft's own menu and stays.
                client.pauseGame(false);
                check(client.gui.screen() instanceof PauseScreen, "Esc no longer opens the game menu");
                client.gui.setScreen(null);
                regainFocus(client);

                // In a session the window is the desktop: F11 changes nothing.
                client.getWindow().toggleFullScreen();
                check(!client.getWindow().isFullscreen(), "F11 made the desktop window fullscreen");

                // A launch that cannot open says why in the chat, where the line stays.
                AresOsClient.launch("notepad");
            });
            context.waitFor(client -> chat(client).contains("Couldn't open Notepad: app helper unavailable"));
            liveMode(context, world);
            covered(context, world.getServer());
            AresOs.LOGGER.info("40 home screen checks passed: the pause menu opens on focus loss outside the home "
                    + "screen and not in it, the mouse is let go, Esc still opens the menu, F11 does nothing in a "
                    + "session, a failed launch leaves a chat line, Live mode shows only the hotbar, walks faster "
                    + "with the field of view kept, still flies after G and G and flies on a double space, a covered "
                    + "world pauses and draws slowly while "
                    + "ready heartbeats go on, and uncovering or losing the helper lets it run");
        } finally {
            context.runOnClient(client -> {
                HomeScreen.forTests(null, null);
                ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
                client.options.pauseOnLostFocus = pauseSetting;
                AppsTestAccess.aresos$setApps(previousApps);
                AresOsClient.replaceLauncher(previousLauncher);
                AresOsClient.FOCUS_RETURN.reset();
            });
        }
    }

    /**
     * Step 3, D: Live mode as his client sees it. The HUD shows only the hotbar, he walks at the desktop speed while
     * the field of view stays the game's, and after G to Build and G back his client still lets him fly: it gives
     * itself survival's abilities when it hears the game mode, so this fails if the server does not send Live's after
     * that. A double space then makes him fly, on the client and on the server.
     */
    private static void liveMode(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().setGameMode(GameType.SURVIVAL));
        context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL && !ModeSwitchClient.pending());
        context.waitFor(client -> client.player.getAbilities().mayfly);
        context.runOnClient(client -> {
            check(!client.gameMode.canHurtPlayer() && !client.gameMode.hasExperience(),
                    "Live mode's HUD still draws hearts, hunger or the experience bar");
            check(client.player.getAbilities().getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED
                    && Math.abs(client.player.getAttributeValue(Attributes.MOVEMENT_SPEED) - LiveMode.DESKTOP_WALKING_SPEED) < 1e-6,
                    "His client walks at " + client.player.getAttributeValue(Attributes.MOVEMENT_SPEED));
            float fov = client.player.getFieldOfViewModifier(true, 1.0f);
            check(Math.abs(fov - 1.0f) < 1e-4, "The desktop speed widened the field of view: " + fov);
        });
        screenshot(context, "40-live-shows-only-the-hotbar");

        for (GameType mode : new GameType[]{GameType.CREATIVE, GameType.SURVIVAL}) {
            context.getInput().pressKey(InputConstants.KEY_G);
            world.getConnection().waitForServerboundPackets();
            context.waitFor(client -> client.gameMode.getPlayerMode() == mode && !ModeSwitchClient.pending());
        }
        world.getConnection().waitForServerboundPackets();
        context.waitTicks(2);
        context.runOnClient(client -> check(client.player.getAbilities().mayfly && client.player.getAbilities().invulnerable
                && !client.player.getAbilities().instabuild, "After G and G his client's Live mode cannot fly"));

        context.getInput().pressKey(options -> options.keyJump);
        context.getInput().pressKey(options -> options.keyJump);
        context.waitFor(client -> client.player.getAbilities().flying, 40);
        world.getConnection().waitForServerboundPackets();
        check(world.getServer().computeOnServer(server -> world.getConnection().getServerPlayer().getAbilities().flying),
                "The server did not let Live mode fly");
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.getAbilities().flying = false;
            player.onUpdateAbilities();
        });
        context.waitFor(client -> !client.player.getAbilities().flying);
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.runOnClient(client -> {
            client.gui.hud.getChat().clearMessages(true);
            client.gui.hud.setOverlayMessage(Component.empty(), false);
            client.gui.toastManager().clear();
        });
        context.waitTicks(5);
        context.takeScreenshot(TestScreenshotOptions.of(name)
                .withDestinationDir(Path.of(System.getProperty("aresos.homeScreenReviewDir"))));
    }

    private static void covered(ClientGameTestContext context, TestServerContext server) {
        java.nio.file.Path folder;
        try {
            folder = Files.createTempDirectory("ac");  // a Unix socket path must stay short
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        try (var helper = new FakeHelper(folder); var shell = helper.client(FakeHelper.fast())) {
            shell.start();
            shell.awaitApps(Duration.ofSeconds(10));
            context.runOnClient(client -> ShellFocusClient.register(shell));
            String name = context.computeOnClient(ShellFocusClient::readyWorld);
            check(name != null, "The test world is not a ready desktop world");
            context.waitFor(client -> !helper.received("world_ready").isEmpty(), 1200);
            int normal = context.computeOnClient(client -> client.getFramerateLimitTracker().getFramerateLimit());
            serverPaused(context, server, false, "The world was paused before anything covered it");

            helper.event("shell_covered", Map.of("covered", true));
            context.waitFor(Minecraft::isPaused, 1200);
            check(context.computeOnClient(client -> client.gui.screen() == null), "Covering opened a screen");
            check(context.computeOnClient(client -> client.getFramerateLimitTracker().getFramerateLimit())
                    == Math.min(normal, HomeScreen.COVERED_FRAME_LIMIT), "A covered world kept its frame rate");
            int before = helper.received("heartbeat").size();
            context.waitFor(client -> helper.received("heartbeat").size() >= before + 5, 2400);
            serverPaused(context, server, true, "The integrated server ran on while covered");
            var beats = helper.received("heartbeat");
            for (var beat : beats.subList(before, beats.size())) {
                check(beat.get("ready").getAsBoolean() && name.equals(beat.getAsJsonObject("world").get("id").getAsString()),
                        "A heartbeat while covered was not a ready one for the world: " + beat);
            }
            check(helper.received("world_ready").size() == 1, "Covering sent world_ready again");

            helper.event("shell_covered", Map.of("covered", false));
            context.waitFor(client -> !client.isPaused(), 1200);
            check(context.computeOnClient(client -> client.getFramerateLimitTracker().getFramerateLimit()) == normal,
                    "The frame rate stayed low after the world was uncovered");
            serverPaused(context, server, false, "The server stayed paused after uncovering");

            // A helper that goes away must never leave the world paused.
            helper.event("shell_covered", Map.of("covered", true));
            context.waitFor(Minecraft::isPaused, 1200);
            helper.drop();
            context.waitFor(client -> !client.isPaused(), 1200);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            try { Files.deleteIfExists(folder); } catch (IOException ignored) { }
        }
    }

    /** The server takes the client's pause at its own next tick, so its state is polled between ticks. */
    private static void serverPaused(ClientGameTestContext context, TestServerContext server, boolean paused,
                                     String failure) {
        for (int tick = 0; tick < 200; tick++) {
            if (server.computeOnServer(MinecraftServer::isPaused) == paused) return;
            context.waitTick();
        }
        throw new AssertionError(failure);
    }

    private static void loseFocus(Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(false);
        ((MinecraftTestAccess) client).aresos$setLastActiveTime(0);
        ((MinecraftTestAccess) client).aresos$pauseIfInactive();
    }

    private static void regainFocus(Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
        ((MinecraftTestAccess) client).aresos$pauseIfInactive();
    }

    private static List<String> chat(Minecraft client) {
        return ((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().stream()
                .map(message -> message.content().getString()).toList();
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
