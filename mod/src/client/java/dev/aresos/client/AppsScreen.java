package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.item.*;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.screen.v1.*;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.GameType;

public final class AppsScreen extends Screen {
    private static final int PAGE_SIZE = 27;
    private final Screen parent;
    private int page;
    public AppsScreen(Screen parent) { super(Component.literal("Apps")); this.parent = parent; }
    public static boolean active(Minecraft client) {
        return client.player != null && client.gameMode != null && client.gameMode.getPlayerMode() == GameType.SURVIVAL
                && client.getSingleplayerServer() != null && DesktopWorld.isEnabled(client.getSingleplayerServer());
    }
    public static void register() {
        ScreenEvents.AFTER_INIT.register((client, screen, width, height) -> {
            if (screen instanceof InventoryScreen && active(client)) {
                Screens.getWidgets(screen).add(Button.builder(Component.literal("Apps…"),
                        button -> client.gui.setScreen(new AppsScreen(screen))).bounds(width / 2 - 35, height / 2 + 90, 70, 20).build());
            }
        });
    }
    @Override protected void init() {
        int pages = Math.max(1, (AresOs.apps().size() + PAGE_SIZE - 1) / PAGE_SIZE);
        page = Math.min(page, pages - 1);
        int left = width/2 - 162, top = height/2 - 86;
        for (int index = page*PAGE_SIZE; index < Math.min((page+1)*PAGE_SIZE, AresOs.apps().size()); index++) {
            var app = AresOs.apps().get(index);
            int cell = index % PAGE_SIZE;
            var button = Button.builder(Component.literal("    " + app.name()), clicked -> {
                if (!active(minecraft)) { onClose(); return; }
                ClientPlayNetworking.send(new TakeAppPayload(app.id()));
                minecraft.gui.setScreen(parent);
            }).bounds(left + (cell%3)*108, top + (cell/3)*18, 106, 18).build();
            button.setTooltip(net.minecraft.client.gui.components.Tooltip.create(Component.literal(app.name() + " — pick up, then drag into the hotbar to pin")));
            addRenderableWidget(button);
        }
        addRenderableWidget(Button.builder(Component.literal("‹"), button -> { page--; rebuildWidgets(); }).bounds(left, top+168, 30,20).build()).active = page > 0;
        addRenderableWidget(Button.builder(Component.literal("Back"), button -> onClose()).bounds(width/2-40,top+168,80,20).build());
        addRenderableWidget(Button.builder(Component.literal("›"), button -> { page++; rebuildWidgets(); }).bounds(left+294,top+168,30,20).build()).active = page+1 < pages;
    }
    @Override public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        int left=width/2-162, top=height/2-86;
        graphics.centeredText(font, "Apps · " + (page+1) + "/" + Math.max(1,(AresOs.apps().size()+PAGE_SIZE-1)/PAGE_SIZE), width/2,top-18,0xffffffff);
        for(int index=page*PAGE_SIZE;index<Math.min((page+1)*PAGE_SIZE,AresOs.apps().size());index++) {
            int cell=index%PAGE_SIZE;
            graphics.item(AppItems.create(AresOs.apps().get(index)),left+(cell%3)*108+2,top+(cell/3)*18+1);
        }
    }
    @Override public void tick() { if (!active(minecraft)) onClose(); }
    @Override public void onClose() { minecraft.gui.setScreen(parent); }
}
