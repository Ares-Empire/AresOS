package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.config.LookMode;
import dev.aresos.focus.ClickLook;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.util.Util;
import org.lwjgl.glfw.GLFW;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Package 328b, prototype A ("click to look"), with {@code look = click} in {@link LookMode#FILE}. In a session's
 * connected desktop world the cursor is free, a normal pointer that reaches the other output. A click on the world or
 * a movement key starts look mode: the world holds the mouse and steers the camera exactly as in classic, and clicks
 * act as in classic. It ends after {@link ClickLook#LOOK_RELEASE_MS} of stillness, on Esc (a screen opens) or when an
 * app takes the focus.
 *
 * <p>Every capture and release stays package 328a's: look mode starts with {@code MouseHandler.grabMouse}, so through
 * the safe fallback and {@link WorldCapture#grab}, and ends with {@code MouseHandler.releaseMouse}, so through
 * {@link WorldCapture#release}, which puts the pointer back where the click was. Every other grab (vanilla's when a
 * screen closes, the helper's and GLFW's focus regrabs) finds the pointer free ({@link HomeScreen#freePointer}) and is
 * refused at the head of {@code grabMouse}, as package 56 refuses grabs behind an app.
 */
public final class ClickToLook {
    // Client thread only.
    private static final ClickLook LOOK = new ClickLook();
    private static LookMode mode, modeForTests;
    private static boolean starting;

    private ClickToLook() { }

    /** The setting, read once from the config folder. */
    public static LookMode mode() {
        if (modeForTests != null) return modeForTests;
        if (mode == null) mode = load();
        return mode;
    }

    private static LookMode load() {
        Path file = FabricLoader.getInstance().getConfigDir().resolve(LookMode.FILE);
        try {
            var read = LookMode.read(file);
            if (read != LookMode.CLASSIC) AresOs.LOGGER.info("AresOS: look = {} ({})", read.value(), file);
            return read;
        } catch (IOException | IllegalArgumentException error) {
            AresOs.LOGGER.warn("AresOS: {}: {}; the world looks around as before (classic)", file, error.getMessage());
            return LookMode.CLASSIC;
        }
    }

    /** The click setting in a session's connected desktop world. */
    public static boolean on(Minecraft client) {
        return mode() == LookMode.CLICK && HomeScreen.active(client);
    }

    /** Not in look mode: the pointer is free over the world ({@link HomeScreen#freePointer} adds the other gates). */
    static boolean idle(Minecraft client) {
        return ClickLook.idle(mode() == LookMode.CLICK, starting, client.mouseHandler.isMouseGrabbed());
    }

    /** A press on the world that package 56 did not send to an app slot. The press itself does nothing else. */
    static void click(Minecraft client) {
        if (client.gui.screen() != null) return;
        if (client.isWindowActive()) start(client, false);
        else LOOK.clickWaits(Util.getMillis());
    }

    /** {@code KeyboardHandler.keyPress}, before Minecraft: a movement key may start look mode, and walks either way. */
    public static void key(Minecraft client, int action, KeyEvent event) {
        if (!ClickLook.keyStarts(on(client) && idle(client), HomeScreen.appInFront(),
                client.gui.screen() != null || client.gui.overlay() != null, action == GLFW.GLFW_PRESS,
                matches(client, event))) return;
        start(client, true);
    }

    private static void start(Minecraft client, boolean key) {
        LOOK.clickDone();
        starting = true;
        try {
            client.mouseHandler.grabMouse();
        } finally {
            starting = false;
        }
        if (client.mouseHandler.isMouseGrabbed()) LOOK.began();
        // After a key start the pointer reappears at the centre of the world's output, not where it happened to rest.
        if (key && client.mouseHandler.isMouseGrabbed()) WorldCapture.returnToCentre(client.getWindow());
    }

    /** Mouse motion, a button or the wheel reached Minecraft: in look mode the mouse is not still. */
    public static void input(Minecraft client) {
        if (on(client) && client.mouseHandler.isMouseGrabbed()) LOOK.moved(Util.getMillis());
    }

    /** Once a frame, from {@link HomeScreen#frame}. */
    static void frame(Minecraft client) {
        if (!on(client)) {
            LOOK.reset();
            return;
        }
        long now = Util.getMillis();
        var mouse = client.mouseHandler;
        LOOK.frame(mouse.isMouseGrabbed(), now);
        if (LOOK.looking()) {
            if (held(client)) LOOK.moved(now);
            // Stillness, or a capture look mode did not start (vanilla's at world join, before the helper connected).
            if (LOOK.due(now)) mouse.releaseMouse();
        } else if (LOOK.clickWaiting(now) && client.isWindowActive() && client.gui.screen() == null
                && !HomeScreen.appInFront()) {
            start(client, false);
        }
    }

    /** A movement key (walk, jump or fly up, sneak or fly down) or a mouse button is held. */
    private static boolean held(Minecraft client) {
        for (var key : movementKeys(client)) if (key.isDown()) return true;
        var mouse = client.mouseHandler;
        return mouse.isLeftPressed() || mouse.isRightPressed() || mouse.isMiddlePressed();
    }

    private static boolean matches(Minecraft client, KeyEvent event) {
        for (var key : movementKeys(client)) if (key.matches(event)) return true;
        return false;
    }

    private static KeyMapping[] movementKeys(Minecraft client) {
        var options = client.options;
        return new KeyMapping[] {options.keyUp, options.keyDown, options.keyLeft, options.keyRight, options.keyJump,
                options.keyShift};
    }

    /** Client game tests: the setting to use (null: the file's). Look mode starts over. */
    public static void forTests(LookMode look) {
        modeForTests = look;
        starting = false;
        LOOK.reset();
    }
}
