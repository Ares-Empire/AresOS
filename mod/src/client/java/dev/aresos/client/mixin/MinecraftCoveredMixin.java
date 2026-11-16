package dev.aresos.client.mixin;

import dev.aresos.client.HomeScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Gui;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Package 40: while a window hides the home screen's world, the world pauses as under a pause screen, but without one.
 * {@code runTick} decides the pause from the open screen; the integrated server and the client level follow it.
 */
@Mixin(Minecraft.class)
public abstract class MinecraftCoveredMixin {
    @Redirect(method = "runTick", at = @At(value = "INVOKE", target = "Lnet/minecraft/client/gui/Gui;isPausing()Z"))
    private boolean aresos$pauseWhileCovered(Gui gui) {
        return HomeScreen.pausing((Minecraft) (Object) this, gui.isPausing());
    }
}
