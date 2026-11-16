package dev.aresos.test.mixin;

import net.minecraft.client.gui.Hud;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(Hud.class)
public interface HudTestAccess {
    @Accessor("overlayMessageString") Component aresos$overlayMessage();
    @Accessor("overlayMessageTime") int aresos$overlayTime();
    // Package 46: vanilla's "Saving world" corner text, as it fades in and out (0 to 1).
    @Accessor("autosaveIndicatorValue") float aresos$savingIndicator();
    @Accessor("lastAutosaveIndicatorValue") float aresos$lastSavingIndicator();
}
