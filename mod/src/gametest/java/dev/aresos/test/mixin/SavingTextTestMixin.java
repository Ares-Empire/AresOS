package dev.aresos.test.mixin;

import dev.aresos.test.SavingText;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Package 46, owner fix 1: the "Saving world" text as {@link SavingText} describes. */
@Mixin(Hud.class)
public abstract class SavingTextTestMixin {
    @Redirect(method = "tickAutosaveIndicator", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/server/MinecraftServer;isCurrentlySaving()Z"))
    private boolean aresos$everySaveReachesATick(MinecraftServer server) {
        return SavingText.saving(server.isCurrentlySaving());
    }

    @Inject(method = "extractSavingIndicator", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/client/gui/GuiGraphicsExtractor;textWithBackdrop(Lnet/minecraft/client/gui/Font;Lnet/minecraft/network/chat/Component;IIII)V"))
    private void aresos$countDrawn(GuiGraphicsExtractor graphics, DeltaTracker delta, CallbackInfo ci) {
        SavingText.drawn();
    }
}
