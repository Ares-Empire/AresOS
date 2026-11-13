package dev.aresos.client;

import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.levelgen.WorldOptions;

public final class HomeCreateScreen extends Screen {
    private final Screen parent;
    // The flat home is the first choice; the Nether home and its seed settings stay one click away.
    private boolean flat = true;
    private String seedText = "49";
    private boolean placeholder = true;
    private Button toggle;

    public HomeCreateScreen(Screen parent) {
        super(Component.translatable("aresos.home.create"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int left = width / 2 - 140;
        // 212 high with the Nether settings; the smallest GUI the game allows is 240 high.
        int top = Math.max(12, height / 2 - 106);
        addRenderableWidget(new StringWidget(left, top, 280, 20, title, font));
        var choice = addRenderableWidget(Button.builder(Component.literal("Home: " + (flat ? "Flat" : "Nether")), button -> {
            flat = !flat;
            rebuildWidgets();
        }).bounds(left, top + 24, 280, 20).build());
        if (flat) {
            addRenderableWidget(new StringWidget(left, top + 56, 280, 16,
                    Component.literal("Flat grass at noon, a home pad and four roads"), font));
            setInitialFocus(choice);
        } else nether(left, top + 28);
        addRenderableWidget(Button.builder(Component.translatable("aresos.home.create"), button -> {
            button.active = false;
            if (flat) HomeButton.createFlat(minecraft, parent);
            else HomeButton.create(minecraft, parent, WorldOptions.parseSeed(seedText).orElseGet(WorldOptions::randomSeed), placeholder);
        }).bounds(left, top + 192, 136, 20).build());
        addRenderableWidget(Button.builder(Component.translatable("gui.cancel"), button -> onClose())
                .bounds(left + 144, top + 192, 136, 20).build());
    }

    /** The seed, the quick picks and the placeholder toggle: only a Nether home has them. */
    private void nether(int left, int top) {
        addRenderableWidget(new StringWidget(left, top + 28, 280, 16, Component.literal("Seed"), font));
        var seed = addRenderableWidget(new EditBox(font, left, top + 46, 280, 20, Component.literal("Seed")));
        seed.setMaxLength(128);
        seed.setValue(seedText);
        toggle = addRenderableWidget(Button.builder(toggleLabel(), button -> {
            placeholder = !placeholder;
            toggle.setMessage(toggleLabel());
        }).bounds(left, top + 102, 280, 20).build());
        seed.setResponder(value -> {
            seedText = value;
            placeholder = WorldOptions.parseSeed(value).orElse(0) == 49;
            toggle.setMessage(toggleLabel());
        });
        long[] picks = {49, 50, 26};
        for (int i = 0; i < picks.length; i++) {
            String value = Long.toString(picks[i]);
            addRenderableWidget(Button.builder(Component.literal(value), button -> seed.setValue(value))
                    .bounds(left + i * 96, top + 74, 88, 20).build());
        }
        addRenderableWidget(new StringWidget(left, top + 130, 280, 16,
                Component.literal("Explore in Build mode (G), then /aresos home set"), font));
        setInitialFocus(seed);
    }

    private Component toggleLabel() {
        return Component.literal("Placeholder hub: " + (placeholder ? "ON" : "OFF"));
    }

    @Override
    public void onClose() { minecraft.gui.setScreen(parent); }
}
