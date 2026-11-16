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
import dev.aresos.test.mixin.MusicManagerTestAccess;
import dev.aresos.test.mixin.SoundEngineTestAccess;
import dev.aresos.test.mixin.SoundTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import com.mojang.blaze3d.platform.DisplayData;
import com.mojang.blaze3d.platform.Window;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.GameType;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Package 40: the world as the home screen, without a real session or helper. An app in front never opens the pause
 * menu while Esc still does, the game's own fullscreen is off in a session, and a launch that fails leaves a line in
 * the chat. The first check shows the game pausing without these rules, so the others prove something.
 *
 * <p>Step 2: a window that covers the world pauses it without a screen and slows its frame rate, while the helper keeps
 * hearing ready heartbeats (package 23's supervisor takes missing ones for a dead world). This part runs a real shell
 * client against a fake helper, wired up as in the session ({@link ShellFocusClient#register}). Only package 46's test,
 * which does the same, runs after it, so the tick listener that registration leaves behind runs only against a closed
 * client.
 *
 * <p>Review fixes 1: that part asks {@link HomeScreen#active} itself, with the game's helper connection set to the
 * test's (false before it connects, true connected in a session and a desktop world, false once the connection is
 * lost); a covered world is silent, music included, and its sounds go on where they were; the music starts no song
 * while covered; a small window in front changes no sound. A saved {@code fullscreen:true} opens no fullscreen window
 * in a session.
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
                savedFullscreen(client);

                // A launch that cannot open says why in the chat, where the line stays.
                AresOsClient.launch("notepad");
            });
            context.waitFor(client -> chat(client).contains("Couldn't open Notepad: app helper unavailable"));
            liveMode(context, world);
            covered(context, world.getServer());
            AresOs.LOGGER.info("40 home screen checks passed: the pause menu opens on focus loss outside the home "
                    + "screen and not in it, the mouse is let go, Esc still opens the menu, F11 does nothing in a "
                    + "session, a failed launch leaves a chat line, Live mode shows only the hotbar, walks faster "
                    + "with the field of view kept, still flies after G and G and flies on a double space, a saved "
                    + "fullscreen opens windowed in a session, the home screen is active only while the helper is "
                    + "connected, a covered world pauses, draws slowly and is silent (music too, no new song) while "
                    + "ready heartbeats go on, a small window in front changes no sound, and uncovering or losing the "
                    + "helper lets it run with its sounds where they were");
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
        // The abilities come at once, the movement attribute with the server's next entity update.
        for (int tick = 0; tick < 100 && !context.computeOnClient(HomeScreenClientGameTest::desktopSpeed); tick++)
            context.waitTick();
        String serverSide = world.getServer().computeOnServer(s -> {
            var player = world.getConnection().getServerPlayer();
            return player.getAbilities().getWalkingSpeed() + " / " + player.getAttributeBaseValue(Attributes.MOVEMENT_SPEED);
        });
        context.runOnClient(client -> {
            check(!client.gameMode.canHurtPlayer() && !client.gameMode.hasExperience(),
                    "Live mode's HUD still draws hearts, hunger or the experience bar");
            check(desktopSpeed(client), "His client walks at " + client.player.getAbilities().getWalkingSpeed() + " / "
                    + client.player.getAttributeValue(Attributes.MOVEMENT_SPEED) + " (walking speed / movement), the server "
                    + serverSide);
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

        // Two presses, each held over a tick, with the key up between them, within the game's 7 ticks.
        context.getInput().holdKeyFor(options -> options.keyJump, 2);
        context.waitTicks(2);
        context.getInput().holdKeyFor(options -> options.keyJump, 2);
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

    private static boolean desktopSpeed(Minecraft client) {
        return client.player.getAbilities().getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED
                && Math.abs(client.player.getAttributeValue(Attributes.MOVEMENT_SPEED) - LiveMode.DESKTOP_WALKING_SPEED) < 1e-6;
    }

    /**
     * Review fixes 1: the window a saved {@code fullscreen:true} opens. The window is made once, at the game's start,
     * so the redirect in its constructor ({@code WindowHomeScreenMixin}, merged into {@link Window}) is asked directly
     * what the constructor would get: windowed in a session, the saved fullscreen outside one.
     */
    private static void savedFullscreen(Minecraft client) {
        var saved = new DisplayData(854, 480, OptionalInt.empty(), OptionalInt.empty(), true);
        var redirect = Arrays.stream(Window.class.getDeclaredMethods())
                .filter(method -> method.getName().endsWith("aresos$startWindowed") && method.getParameterCount() == 1)
                .findFirst().orElseThrow(() -> new AssertionError("WindowHomeScreenMixin's redirect is not in Window"));
        redirect.setAccessible(true);
        try {
            check(!(boolean) redirect.invoke(client.getWindow(), saved),
                    "In a session a saved fullscreen:true would open the window fullscreen");
            HomeScreen.forTests(false, true);
            check((boolean) redirect.invoke(client.getWindow(), saved),
                    "Outside a session a saved fullscreen:true no longer opens the window fullscreen");
        } catch (ReflectiveOperationException error) {
            throw new AssertionError("Could not ask WindowHomeScreenMixin's redirect", error);
        } finally {
            HomeScreen.forTests(true, true);
        }
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
        var previousShell = AresOs.shell();
        var volumes = new EnumMap<SoundSource, Double>(SoundSource.class);
        SoundInstance music = SimpleSoundInstance.forMusic(SoundEvents.MUSIC_GAME.value());
        SoundInstance[] record = new SoundInstance[1];
        try (var helper = new FakeHelper(folder); var shell = helper.client(FakeHelper.fast())) {
            // Review fixes 1: from here on HomeScreen.active is not forced; it asks the game's helper connection,
            // which is this test's.
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(shell);
                HomeScreen.forTests(true, null);
                check(!HomeScreen.active(client), "The home screen was active before the helper connected");
            });
            shell.start();
            shell.awaitApps(Duration.ofSeconds(10));
            context.waitFor(HomeScreen::active, 200);
            context.runOnClient(client -> {
                HomeScreen.forTests(false, null);
                check(!HomeScreen.active(client), "A game the session did not start took the home screen's rules");
                HomeScreen.forTests(true, null);
            });
            context.runOnClient(client -> ShellFocusClient.register(shell));
            String name = context.computeOnClient(ShellFocusClient::readyWorld);
            check(name != null, "The test world is not a ready desktop world");
            context.waitFor(client -> !helper.received("world_ready").isEmpty(), 1200);
            int normal = context.computeOnClient(client -> client.getFramerateLimitTracker().getFramerateLimit());
            serverPaused(context, server, false, "The world was paused before anything covered it");

            // Sound: music, and a record as one of the world's own sounds, both at full volume.
            context.runOnClient(client -> {
                for (var source : List.of(SoundSource.MASTER, SoundSource.MUSIC, SoundSource.RECORDS)) {
                    volumes.put(source, client.options.getSoundSourceOptionInstance(source).get());
                    client.options.getSoundSourceOptionInstance(source).set(1.0);
                }
                record[0] = SimpleSoundInstance.forJukeboxSong(SoundEvents.MUSIC_DISC_CAT.value(), client.player.position());
                client.getSoundManager().play(music);
                client.getSoundManager().play(record[0]);
                // The game's own music between two songs, the next one five minutes away: its countdown runs.
                client.getMusicManager().stopPlaying();
                ((MusicManagerTestAccess) client.getMusicManager()).aresos$setNextSongDelay(6000);
            });
            waitForSounds(context, "playing", "Fixture: the music and the record did not start", music, record[0]);
            check(countsDown(context), "Fixture: the music's countdown to the next song does not run");
            // A small window in front changes no sound.
            helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
            context.waitTicks(10);
            waitForSounds(context, "playing", "A small window in front stopped a sound", music, record[0]);
            helper.event("shell_focus", Map.of("focus", "foreground", "reason", "desktop_activated"));
            context.waitTicks(2);

            helper.event("shell_covered", Map.of("covered", true));
            context.waitFor(Minecraft::isPaused, 1200);
            check(context.computeOnClient(client -> client.gui.screen() == null), "Covering opened a screen");
            waitForSounds(context, "paused", "A covered world was not silent (the music and the record pause)", music, record[0]);
            check(!countsDown(context), "The music counted down to its next song while covered");
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
            // The same two sounds go on (a new song would be another sound), and the countdown runs again.
            waitForSounds(context, "playing", "The music or the record did not go on after the cover", music, record[0]);
            check(countsDown(context), "The music's countdown stood still after the cover");

            // A helper that goes away must never leave the world paused.
            helper.event("shell_covered", Map.of("covered", true));
            context.waitFor(Minecraft::isPaused, 1200);
            helper.drop();
            context.waitFor(client -> !client.isPaused(), 1200);
            // Without a helper the home screen's rules end: the connection lost for good (no helper to reconnect to).
            helper.close();
            context.waitFor(client -> !HomeScreen.active(client), 200);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            context.runOnClient(client -> {
                client.getSoundManager().stop(music);
                if (record[0] != null) client.getSoundManager().stop(record[0]);
                volumes.forEach((source, volume) -> client.options.getSoundSourceOptionInstance(source).set(volume));
                AppsTestAccess.aresos$setShell(previousShell);
                HomeScreen.forTests(true, true);
            });
            try { Files.deleteIfExists(folder); } catch (IOException ignored) { }
        }
    }

    /**
     * Waits until each sound's channel is "playing" or "paused" (or "stopped"), as the sound thread reads it from
     * OpenAL. A paused channel goes on from where it was when it plays again.
     */
    private static void waitForSounds(ClientGameTestContext context, String state, String failure, SoundInstance... sounds) {
        List<String> last = List.of();
        for (int tick = 0; tick < 200; tick++) {
            var answers = new ConcurrentLinkedQueue<String>();
            int asked = context.computeOnClient(client -> {
                var channels = ((SoundEngineTestAccess) ((SoundTestAccess) client.getSoundManager()).aresos$soundEngine())
                        .aresos$channels();
                int count = 0;
                for (var sound : sounds) {
                    var channel = channels.get(sound);
                    if (channel == null) continue;
                    count++;
                    channel.execute(open -> answers.add(open.playing() ? "playing" : open.stopped() ? "stopped" : "paused"));
                }
                return count;
            });
            context.waitTicks(2);
            last = List.copyOf(answers);
            if (asked == sounds.length && last.size() == sounds.length && last.stream().allMatch(state::equals)) return;
        }
        throw new AssertionError(failure + " (last: " + last + ")");
    }

    /** Whether the game's music counts down to its next song over five ticks. */
    private static boolean countsDown(ClientGameTestContext context) {
        int before = context.computeOnClient(client -> ((MusicManagerTestAccess) client.getMusicManager()).aresos$nextSongDelay());
        context.waitTicks(5);
        return context.computeOnClient(client -> ((MusicManagerTestAccess) client.getMusicManager()).aresos$nextSongDelay()) < before;
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
