package dev.aresos.client;

import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.util.CommonColors;

/**
 * Package 48: one line while a home is being made ("Making your home…", "Making your new home…"), over the game's
 * own menu background, as its "Saving world" has it. Esc does nothing: the work goes on whatever he presses. While
 * the AresOS menu switches homes the game's loading screens show this same line ({@link HomeSwitch}), so the whole
 * switch reads as one wait.
 */
public final class HomeWorkingScreen extends Screen {
    public HomeWorkingScreen(Component text) { super(text); }

    @Override public boolean shouldCloseOnEsc() { return false; }

    /** Never the world behind it, even while a world is loaded: the same background as the game's message screens. */
    @Override public void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        extractPanorama(graphics, delta);
        extractBlurredBackground(graphics);
        extractMenuBackground(graphics);
    }

    @Override public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        draw(graphics, font, title, width, height);
    }

    /** The line, centred; also drawn in place of a loading screen's own text during a home switch. */
    public static void draw(GuiGraphicsExtractor graphics, Font font, Component text, int width, int height) {
        graphics.centeredText(font, text, width / 2, (height - font.lineHeight) / 2, CommonColors.WHITE);
    }
}
