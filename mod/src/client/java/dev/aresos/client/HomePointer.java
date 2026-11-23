package dev.aresos.client;

import dev.aresos.AresOs;
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
        // Package 328c: with look = edge and the world in front, the free pointer's clicks go on to Minecraft.
        boolean worldActs = !HomeScreen.ignoresMouse(client);
        if (action != GLFW.GLFW_PRESS) return !worldActs;
        int slot = hoveredSlot(client);
        var shell = AresOs.shell();
        var click = PointerRules.click(true, button == GLFW.GLFW_MOUSE_BUTTON_LEFT,
                button == GLFW.GLFW_MOUSE_BUTTON_RIGHT, slot >= 0, shell != null && shell.canActivateApps(), worldActs);
        if (click == PointerRules.Click.VANILLA) return false;
        swallowedButtons |= bit;
        if (click == PointerRules.Click.OPEN_APP || click == PointerRules.Click.NEW_WINDOW) {
            // labwc activates the desktop on mouse-down. Its helper event can arrive on either side of this callback.
            appClick = foregroundFrames == 0;
            foregroundFrames = 0;
            long sequence = ++launchSequence;
            AresOsClient.launchFromPointer(client.player.getInventory().getItem(slot).get(AppItems.APP_ID),
                    click == PointerRules.Click.NEW_WINDOW, () -> {
                // The helper may coalesce the very brief desktop activation and leave the app focused throughout.
                // Once this app is focused, a later Alt+Tab to the world must not be mistaken for the old click.
                if (sequence == launchSequence) appClick = false;
            });
        } else {
            enterWorld(client, true);
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
            enterWorld(client, false);
        }
    }

    /** {@code pressed}: a press on the world; otherwise the helper's activation came without one. */
    private static void enterWorld(Minecraft client, boolean pressed) {
        foregroundFrames = 0;
        appClick = false;
        // A press reached the world (labwc focuses a window before it hands it the press), or the helper said so.
        WorldCapture.worldFocused(true);
        AppInput.reset();
        HomeScreen.appInFront(false);
        if (ClickToLook.on(client)) {
            // Package 328b: only a press starts look mode; an activation without one leaves the cursor free.
            if (pressed) ClickToLook.click(client);
        } else if (!EdgeLook.on(client) && client.gui.screen() == null && client.isWindowActive()) {
            // Package 328c: with look = edge the world never takes the mouse; the press only brought it to the front.
            client.mouseHandler.grabMouse();
        }
        AresOsClient.returnedFromApp();
    }

    static void reset() {
        foregroundFrames = 0;
        appClick = false;
        swallowedButtons = 0;
        launchSequence++;
    }
}
