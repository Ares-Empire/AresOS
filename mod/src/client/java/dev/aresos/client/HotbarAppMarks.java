package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.resources.Identifier;

/** Running app indicators on the world's own hotbar. */
public final class HotbarAppMarks {
    private static final Identifier BAR = Identifier.withDefaultNamespace("boss_bar/white_progress");

    private HotbarAppMarks() { }

    public static void draw(Minecraft client, GuiGraphicsExtractor graphics) {
        if (!HomeScreen.active(client)) return;
        var shell = AresOs.shell();
        if (shell == null) return;
        var snapshot = shell.appWindows();
        if (snapshot.isEmpty()) return;
        var inventory = client.player.getInventory();
        for (int slot = 0; slot < 9; slot++) {
            var item = inventory.getItem(slot);
            if (!item.is(AppItems.APP)) continue;
            var id = item.get(AppItems.APP_ID);
            var state = id == null ? null : snapshot.get(id);
            if (state == null) continue;
            int width = state.active() ? 14 : 8;
            int tint = state.active() ? 0xffffffff : state.hidden() ? 0xff747474 : 0xffc4c4c4;
            int center = graphics.guiWidth() / 2 - 80 + slot * 20;
            graphics.blitSprite(RenderPipelines.GUI_TEXTURED, BAR, center - width / 2, graphics.guiHeight() - 2,
                    width, 2, tint);
        }
    }
}
