package dev.aresos.test;

import net.minecraft.client.gui.screens.Screen;

import java.util.ArrayList;
import java.util.List;

/** Package 48: every screen {@code Gui.setScreen} actually sets while recording ({@code ScreenLogMixin}). Client thread. */
public final class ScreenLog {
    private static List<String> screens;

    private ScreenLog() { }

    public static void start() { screens = new ArrayList<>(); }

    /** What was set since {@link #start}, by class name ("null" for no screen); recording ends. */
    public static List<String> stop() {
        var recorded = screens == null ? List.<String>of() : List.copyOf(screens);
        screens = null;
        return recorded;
    }

    public static void set(Screen screen) {
        if (screens != null) screens.add(screen == null ? "null" : screen.getClass().getName());
    }
}
