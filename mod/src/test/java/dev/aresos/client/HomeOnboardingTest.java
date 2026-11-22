package dev.aresos.client;

import net.minecraft.client.gui.components.toasts.AdvancementToast;
import net.minecraft.client.gui.components.toasts.FriendToast;
import net.minecraft.client.gui.components.toasts.RecipeToast;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.client.gui.components.toasts.Toast;
import net.minecraft.client.gui.components.toasts.TutorialToast;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HomeOnboardingTest {
    @Test void hidesOnlyVanillaOnboardingKindsInTheHome() {
        for (var kind : List.of(TutorialToast.class, RecipeToast.class, AdvancementToast.class)) {
            assertTrue(HomeOnboarding.hidesToast(true, kind), kind.getSimpleName());
            assertFalse(HomeOnboarding.hidesToast(false, kind), kind.getSimpleName());
        }
        for (var kind : List.of(SystemToast.class, FriendToast.class, ModToast.class)) {
            assertFalse(HomeOnboarding.hidesToast(true, kind), kind.getSimpleName());
            assertFalse(HomeOnboarding.hidesToast(false, kind), kind.getSimpleName());
        }
    }

    private interface ModToast extends Toast { }
}
