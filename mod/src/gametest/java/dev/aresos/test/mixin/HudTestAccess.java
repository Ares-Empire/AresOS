package dev.aresos.test.mixin;

import net.minecraft.client.gui.Hud;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import org.spongepowered.asm.mixin.gen.Invoker;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.GuiGraphicsExtractor;

@Mixin(Hud.class)
public interface HudTestAccess {
    @Accessor("overlayMessageString") Component aresos$overlayMessage();
    @Accessor("overlayMessageTime") int aresos$overlayTime();
    // Package 46: vanilla's "Saving world" corner text, as it fades in and out (0 to 1).
    @Accessor("autosaveIndicatorValue") float aresos$savingIndicator();
    @Accessor("lastAutosaveIndicatorValue") float aresos$lastSavingIndicator();
    @Accessor("autosaveIndicatorValue") void aresos$savingIndicator(float value);
    @Accessor("lastAutosaveIndicatorValue") void aresos$lastSavingIndicator(float value);
    @Invoker("extractSavingIndicator") void aresos$drawSavingIndicator(GuiGraphicsExtractor graphics, DeltaTracker delta);
}
