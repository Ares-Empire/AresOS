package dev.aresos.client;

import dev.aresos.shell.ShellClient;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.LevelLoadingScreen;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;

/** AresOS (Linux) only: follows the app helper's focus changes and reports when the desktop world is usable. */
public final class ShellFocusClient {
    private static MinecraftServer namedServer;
    private static String worldName;

    private ShellFocusClient() { }

    static void register(ShellClient shell) {
        shell.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus focus) {
                var client = Minecraft.getInstance();
                client.execute(() -> apply(client, focus));
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
        if (!focus.foreground()) {
            client.mouseHandler.releaseMouse();
            return;
        }
        if (client.gui.screen() == null && client.isWindowActive()) client.mouseHandler.grabMouse();
        AresOsClient.returnedFromApp();
    }

    /** The marked desktop world's save folder once it is loaded and playable, otherwise null. */
    public static String readyWorld(Minecraft client) {
        var server = client.getSingleplayerServer();
        if (client.player == null || client.level == null || server == null || client.gui.overlay() != null
                || client.gui.screen() instanceof LevelLoadingScreen || !DesktopWorld.isEnabled(server)) return null;
        if (server != namedServer) {
            namedServer = server;
            var folder = server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().getFileName();
            worldName = folder == null ? "world" : folder.toString();
        }
        return worldName;
    }
}
