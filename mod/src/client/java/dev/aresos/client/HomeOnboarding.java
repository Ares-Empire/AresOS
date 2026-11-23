package dev.aresos.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.toasts.AdvancementToast;
import net.minecraft.client.gui.components.toasts.RecipeToast;
import net.minecraft.client.gui.components.toasts.Toast;
import net.minecraft.client.gui.components.toasts.TutorialToast;
import net.minecraft.client.tutorial.TutorialSteps;

public final class HomeOnboarding {
    private HomeOnboarding() { }

    static void tick(Minecraft client) {
        if (HomeScreen.home(client) && client.options.tutorialStep != TutorialSteps.NONE) {
            client.getTutorial().setStep(TutorialSteps.NONE);
        }
    }

    public static boolean hidesToast(boolean home, Class<? extends Toast> kind) {
        return home && (kind == TutorialToast.class || kind == RecipeToast.class || kind == AdvancementToast.class);
    }
}
