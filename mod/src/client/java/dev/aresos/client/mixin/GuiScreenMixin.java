package dev.aresos.client.mixin;

import dev.aresos.client.FirstStart;
import dev.aresos.client.HomeSwitch;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Package 48: every screen the game sets passes here first, so the home screen never shows the title screen where it
 * should not. A title screen comes as {@code new TitleScreen()} or as {@code setScreen(null)} with no world open
 * (which makes one), and both are caught: during a home switch ({@link HomeSwitch}) and at the first start
 * ({@link FirstStart}).
 */
@Mixin(Gui.class)
public abstract class GuiScreenMixin {
    @ModifyVariable(method = "setScreen", at = @At("HEAD"), argsOnly = true)
    private Screen aresos$homeScreens(Screen screen) {
        var client = Minecraft.getInstance();
        return FirstStart.screenComing(client, HomeSwitch.screenComing(client, screen));
    }
}
