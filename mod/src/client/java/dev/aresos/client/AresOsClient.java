package dev.aresos.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.launch.AppLauncher;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.client.launch.WindowsAppLauncher;
import dev.aresos.focus.FocusReturn;
import dev.aresos.mode.ToggleModePayload;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import org.lwjgl.glfw.GLFW;

import java.util.Locale;
import java.util.Objects;

public final class AresOsClient implements ClientModInitializer {
    public static final FocusReturn FOCUS_RETURN = new FocusReturn();
    private static AppLauncher launcher = System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("windows")
            ? new WindowsAppLauncher() : new LinuxAppLauncher();

    /** Allows client game tests to substitute a launcher without ever starting a real app. */
    public static AppLauncher replaceLauncher(AppLauncher replacement) {
        AppLauncher previous = launcher;
        launcher = Objects.requireNonNull(replacement);
        return previous;
    }

    @Override
    public void onInitializeClient() {
        HomeButton.register();
        AppsScreen.register();
        var category = KeyMapping.Category.register(AresOs.id("aresos"));
        var toggle = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.aresos.switch_mode",
                InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_G, category));
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            AppInput.endTick();
            while (toggle.consumeClick()) {
                if (client.player != null && client.gui.screen() == null
                        && ClientPlayNetworking.canSend(ToggleModePayload.TYPE)) {
                    ClientPlayNetworking.send(ToggleModePayload.INSTANCE);
                }
            }
        });
    }

    public static void launch(String id) {
        Minecraft client = Minecraft.getInstance();
        var app = AresOs.app(id);
        if (app == null) {
            message(client, "Unknown AresOS app");
            return;
        }
        long token = FOCUS_RETURN.arm(System.nanoTime());
        try {
            launcher.launch(app).whenComplete((ignored, error) -> {
                if (error != null) {
                    client.execute(() -> {
                        FOCUS_RETURN.cancel(token);
                        message(client, "Couldn't open " + app.name() + (launcher instanceof LinuxAppLauncher ? ": app helper unavailable" : ""));
                    });
                    AresOs.LOGGER.warn("Could not launch app {}", id, error);
                }
            });
        } catch (RuntimeException error) {
            FOCUS_RETURN.cancel(token);
            message(client, "Couldn't open " + app.name() + (launcher instanceof LinuxAppLauncher ? ": app helper unavailable" : ""));
            AresOs.LOGGER.warn("Could not launch app {}", id, error);
        }
    }

    private static void message(Minecraft client, String text) {
        if (client.player != null) client.gui.hud.setOverlayMessage(Component.literal(text), false);
    }
}
