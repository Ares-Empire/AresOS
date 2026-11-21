package dev.aresos.client;

import dev.aresos.focus.PointerRules;
import dev.aresos.item.AppItems;
import dev.aresos.shell.ShellClient;
import net.minecraft.client.Minecraft;
import org.lwjgl.glfw.GLFW;

/** A click on the desktop first chooses an app or the world, before Minecraft can capture the pointer. */
public final class HomePointer {
    private static int swallowedButtons;
    private static int foregroundFrames;
    private static boolean appClick;
    private static long launchSequence;

    private HomePointer() { }

    public static int hoveredSlot(Minecraft client) {
        if (!HomeScreen.freePointer(client) || client.gui.screen() != null || client.gui.overlay() != null
                || client.gui.hud.isHidden()) return -1;
        var window = client.getWindow();
        int slot = PointerRules.slot(client.mouseHandler.getScaledXPos(window), client.mouseHandler.getScaledYPos(window),
                window.getGuiScaledWidth(), window.getGuiScaledHeight());
        return slot >= 0 && client.player.getInventory().getItem(slot).is(AppItems.APP) ? slot : -1;
    }

    /** True means neither this press nor its release belongs to Minecraft's item input. */
    public static boolean button(Minecraft client, int button, int action) {
        int bit = button >= 0 && button < 8 ? 1 << button : 0;
        // The previous release may have gone to the app that just took focus. It cannot belong to this new press.
        if (action == GLFW.GLFW_PRESS) swallowedButtons &= ~bit;
        if (action == GLFW.GLFW_RELEASE && (swallowedButtons & bit) != 0) {
            swallowedButtons &= ~bit;
            return true;
        }
        if (!HomeScreen.freePointer(client) || client.gui.screen() != null || client.gui.overlay() != null) return false;
        if (action != GLFW.GLFW_PRESS) return true;
        swallowedButtons |= bit;
        int slot = hoveredSlot(client);
        var click = PointerRules.click(true, button == GLFW.GLFW_MOUSE_BUTTON_LEFT, slot >= 0);
        if (click == PointerRules.Click.OPEN_APP) {
            // labwc activates the desktop on mouse-down. Its helper event can arrive on either side of this callback.
            appClick = foregroundFrames == 0;
            foregroundFrames = 0;
            long sequence = ++launchSequence;
            AresOsClient.launchFromPointer(client.player.getInventory().getItem(slot).get(AppItems.APP_ID), () -> {
                // The helper may coalesce the very brief desktop activation and leave the app focused throughout.
                // Once this app is focused, a later Alt+Tab to the world must not be mistaken for the old click.
                if (sequence == launchSequence) appClick = false;
            });
        } else {
            enterWorld(client);
        }
        return true;
    }

    /** Give the pending mouse-down a poll before handling an activation that could be a taskbar click. */
    static boolean focus(Minecraft client, ShellClient.Focus focus) {
        if (!HomeScreen.active(client)) return false;
        if (!focus.foreground()) {
            appClick = false;
            foregroundFrames = 0;
            return false;
        }
        if (HomeScreen.freePointer(client) && focus.reason().equals("desktop_activated")) {
            if (appClick) appClick = false;
            else foregroundFrames = 2;
            return true;
        }
        foregroundFrames = 0;
        appClick = false;
        return false;
    }

    static void frame(Minecraft client) {
        if (!HomeScreen.active(client)) {
            reset();
        } else if (foregroundFrames > 0 && --foregroundFrames == 0) {
            enterWorld(client);
        }
    }

    private static void enterWorld(Minecraft client) {
        foregroundFrames = 0;
        appClick = false;
        AppInput.reset();
        HomeScreen.appInFront(false);
        if (client.gui.screen() == null && client.isWindowActive()) client.mouseHandler.grabMouse();
        AresOsClient.returnedFromApp();
    }

    static void reset() {
        foregroundFrames = 0;
        appClick = false;
        swallowedButtons = 0;
        launchSequence++;
    }
}
