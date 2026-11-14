package dev.aresos.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.launch.AppLauncher;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.client.launch.WindowsAppLauncher;
import dev.aresos.focus.FocusReturn;
import dev.aresos.mode.ToggleModePayload;
import dev.aresos.zone.ZoneLaunchPayload;
import dev.aresos.zone.ZoneReturnPayload;
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
    private static long zoneFocusToken;
    private static long zoneVisit;
    // Focus tokens of launches that may still fail later, by request ID; bounded, client thread only.
    private static final java.util.Map<String, Long> LATE_TOKENS = new java.util.LinkedHashMap<>() {
        @Override protected boolean removeEldestEntry(java.util.Map.Entry<String, Long> eldest) { return size() > 32; }
    };
    private static KeyMapping modeToggle;
    private static AppLauncher launcher = System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("windows")
            ? new WindowsAppLauncher() : new LinuxAppLauncher(AresOs::shell);

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
        IconReload.register(dev.aresos.item.MyAppsGame.icons());
        if (AresOs.shell() != null) ShellFocusClient.register(AresOs.shell());
        ClientPlayNetworking.registerGlobalReceiver(dev.aresos.mode.ModeSwitchStatePayload.TYPE,
                (payload, context) -> ModeSwitchClient.receive(payload));
        ClientPlayNetworking.registerGlobalReceiver(ZoneLaunchPayload.TYPE, (payload, context) -> {
            // A remote Minecraft server must never be able to auto-launch local programs.
            if (acceptsAppCommands(Minecraft.getInstance())
                    && (payload.visit() == 0 || AppsScreen.active(Minecraft.getInstance()))) launch(payload.app(), payload.visit());
            else if (ClientPlayNetworking.canSend(ZoneReturnPayload.TYPE))
                ClientPlayNetworking.send(new ZoneReturnPayload(payload.visit(), false));
        });
        net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> {
            FOCUS_RETURN.reset(); zoneFocusToken = 0; zoneVisit = 0;
            ModeSwitchClient.reset();
        });
        var category = KeyMapping.Category.register(AresOs.id("aresos"));
        var toggle = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.aresos.switch_mode",
                InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_G, category));
        modeToggle = toggle;
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            AppInput.endTick();
            while (toggle.consumeClick()) {
                if (client.player != null && client.gui.screen() == null
                        && ClientPlayNetworking.canSend(ToggleModePayload.TYPE)) {
                    ModeSwitchClient.requestToggle();
                }
            }
        });
    }

    public static void modeKeyInMenu(Minecraft client, int action, net.minecraft.client.input.KeyEvent event) {
        if (action == GLFW.GLFW_PRESS && modeToggle != null && modeToggle.matches(event) && client.player != null
                && client.getSingleplayerServer() != null && dev.aresos.world.DesktopWorld.isEnabled(client.getSingleplayerServer())
                && (client.gui.screen() instanceof net.minecraft.client.gui.screens.inventory.AbstractContainerScreen<?>
                    || client.gui.screen() instanceof AppsScreen
                    || client.gui.screen() instanceof net.minecraft.client.gui.screens.PauseScreen)) {
            client.gui.hud.setOverlayMessage(Component.literal("Close the menu before switching AresOS mode"), false);
        }
    }

    public static void discardModeToggle() {
        if (modeToggle != null) while (modeToggle.consumeClick()) { }
    }

    public static boolean acceptsAppCommands(Minecraft client) {
        return client.player != null && client.getSingleplayerServer() != null
                && dev.aresos.world.DesktopWorld.isEnabled(client.getSingleplayerServer());
    }

    public static void launch(String id) {
        launch(id, 0);
    }

    public static boolean regainedFocus(Object screen) {
        boolean close = FOCUS_RETURN.regainedFocus(screen);
        long returned = FOCUS_RETURN.takeReturnedToken();
        if (returned != 0 && returned == zoneFocusToken) finishZone(true);
        return close;
    }

    /** The app helper gave the hub its focus back (AresOS); the GLFW focus path may already have done this. */
    static void returnedFromApp() {
        if (zoneVisit != 0) finishZone(true);
    }

    private static void finishZone(boolean returned) {
        if (zoneVisit != 0 && ClientPlayNetworking.canSend(ZoneReturnPayload.TYPE))
            ClientPlayNetworking.send(new ZoneReturnPayload(zoneVisit, returned));
        zoneVisit = 0; zoneFocusToken = 0;
    }

    private static void launch(String id, long visit) {
        Minecraft client = Minecraft.getInstance();
        finishZone(false);
        var app = AresOs.app(id);
        if (app == null) {
            if (visit != 0 && ClientPlayNetworking.canSend(ZoneReturnPayload.TYPE))
                ClientPlayNetworking.send(new ZoneReturnPayload(visit, false));
            message(client, "Unknown AresOS app");
            return;
        }
        long token = FOCUS_RETURN.arm(System.nanoTime());
        zoneFocusToken = visit == 0 ? 0 : token;
        zoneVisit = visit;
        try {
            launcher.launchTracked(app).whenComplete((requestId, error) -> {
                if (error == null && requestId != null) client.execute(() -> LATE_TOKENS.put(requestId, token));
                if (error != null) {
                    client.execute(() -> {
                        FOCUS_RETURN.cancel(token);
                        if (zoneFocusToken == token) finishZone(false);
                        message(client, "Couldn't open " + app.name() + failureDetail(error));
                    });
                    AresOs.LOGGER.warn("Could not launch app {}", id, error);
                }
            });
        } catch (RuntimeException error) {
            FOCUS_RETURN.cancel(token);
            if (zoneFocusToken == token) finishZone(false);
            message(client, "Couldn't open " + app.name() + failureDetail(error));
            AresOs.LOGGER.warn("Could not launch app {}", id, error);
        }
    }

    /**
     * AresOS without window tracking: a launch that already counted as opened failed after all. Only that launch's
     * focus return and logo visit end; another launch of the same app is left alone.
     */
    public static void launchFailedLater(String requestId, String id, String reason) {
        var client = Minecraft.getInstance();
        Long token = requestId == null ? null : LATE_TOKENS.remove(requestId);
        if (token != null) {
            FOCUS_RETURN.cancel(token);
            if (zoneFocusToken == token) finishZone(false);
        }
        var app = AresOs.app(id);
        message(client, "Couldn't open " + (app == null ? id : app.name()) + ": " + reason);
    }

    /** Windows keeps its plain message; on AresOS the helper's reason says what to fix. */
    private static String failureDetail(Throwable error) {
        return launcher instanceof LinuxAppLauncher ? ": " + LinuxAppLauncher.reason(error) : "";
    }

    private static void message(Minecraft client, String text) {
        if (client.player != null) client.gui.hud.setOverlayMessage(Component.literal(text), false);
    }
}
