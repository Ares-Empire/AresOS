package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;

import java.util.List;

/**
 * Package 40: the world as the home screen, without a real session or helper. An app in front never opens the pause
 * menu while Esc still does, the game's own fullscreen is off in a session, and a launch that fails leaves a line in
 * the chat. The first check shows the game pausing without these rules, so the others prove something.
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
            AresOs.LOGGER.info("40 home screen checks passed: the pause menu opens on focus loss outside the home "
                    + "screen and not in it, the mouse is let go, Esc still opens the menu, F11 does nothing in a "
                    + "session, a failed launch leaves a chat line");
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
