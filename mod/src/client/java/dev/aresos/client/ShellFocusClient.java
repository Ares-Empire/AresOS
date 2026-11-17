package dev.aresos.client;

import dev.aresos.shell.ShellClient;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.LevelLoadingScreen;
import net.minecraft.server.MinecraftServer;

/** AresOS (Linux) only: follows the app helper's focus changes and reports when the desktop world is usable. */
public final class ShellFocusClient {
    private static MinecraftServer namedServer;
    private static String worldName;

    private ShellFocusClient() { }

    /** Public for the client test, which connects a shell client of its own to a fake helper. */
    public static void register(ShellClient shell) {
        shell.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus focus) {
                var client = Minecraft.getInstance();
                client.execute(() -> apply(client, focus));
            }

            @Override public void covered(boolean covered) {
                Minecraft.getInstance().execute(() -> HomeScreen.covered(covered));
            }

            @Override public void launchFailed(String appId, String requestId, ShellClient.ShellException error) {
                Minecraft.getInstance().execute(() ->
                        AresOsClient.launchFailedLater(requestId, appId, ShellClient.describe(error)));
            }
        });
        ClientTickEvents.END_CLIENT_TICK.register(client -> shell.world(readyWorld(client)));
        ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> shell.world(null));
    }

    /** An app took the foreground, or the helper handed focus back to the hub. */
    public static void apply(Minecraft client, ShellClient.Focus focus) {
        // Keys held while focus moved (walking into a logo, the click that opened it) never see their release.
        KeyMapping.releaseAll();
        AppInput.reset();
        HomeScreen.appInFront(!focus.foreground());
        if (!focus.foreground()) {
            client.mouseHandler.releaseMouse();
            return;
        }
        if (client.gui.screen() == null && client.isWindowActive()) client.mouseHandler.grabMouse();
        AresOsClient.returnedFromApp();
    }

    /**
     * The marked desktop world's save folder once it is loaded and playable, otherwise null. Null during a home switch
     * (package 48) from start to end: the staging world is not his home, and the supervisor waits meanwhile.
     */
    public static String readyWorld(Minecraft client) {
        if (HomeSwitch.busy()) return null;
        var server = client.getSingleplayerServer();
        if (client.player == null || client.level == null || server == null || client.gui.overlay() != null
                || client.gui.screen() instanceof LevelLoadingScreen || !DesktopWorld.isEnabled(server)) return null;
        if (server != namedServer) {
            namedServer = server;
            worldName = DesktopWorld.saveName(server);
        }
        return worldName;
    }
}
