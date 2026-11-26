package dev.aresos.client.mixin;

import dev.aresos.client.HomePointer;
import dev.aresos.client.HotbarAppMarks;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.resources.Identifier;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Hud.class)
public abstract class HotbarPointerMixin {
    @Shadow private ItemStack lastToolHighlight;
    @Shadow private int toolHighlightTimer;

    @Inject(method = "extractItemHotbar", at = @At("TAIL"))
    private void aresos$hover(GuiGraphicsExtractor graphics, DeltaTracker delta, CallbackInfo ci) {
        int slot = HomePointer.hoveredSlot(Minecraft.getInstance());
        if (slot >= 0) graphics.blitSprite(RenderPipelines.GUI_TEXTURED,
                Identifier.withDefaultNamespace("hud/hotbar_selection"),
                graphics.guiWidth() / 2 - 92 + slot * 20, graphics.guiHeight() - 23, 24, 23);
        HotbarAppMarks.draw(Minecraft.getInstance(), graphics);
    }

    // Reuse the game's name line, including its font, rarity, backdrop and position. Hover never changes the held slot.
    @Redirect(method = "extractSelectedItemName", at = @At(value = "FIELD",
            target = "Lnet/minecraft/client/gui/Hud;lastToolHighlight:Lnet/minecraft/world/item/ItemStack;"))
    private ItemStack aresos$hoverName(Hud hud) {
        var client = Minecraft.getInstance();
        int slot = HomePointer.hoveredSlot(client);
        return slot < 0 ? lastToolHighlight : client.player.getInventory().getItem(slot);
    }

    @Redirect(method = "extractSelectedItemName", at = @At(value = "FIELD",
            target = "Lnet/minecraft/client/gui/Hud;toolHighlightTimer:I"))
    private int aresos$hoverNameTime(Hud hud) {
        return HomePointer.hoveredSlot(Minecraft.getInstance()) < 0 ? toolHighlightTimer : 10;
    }
}
