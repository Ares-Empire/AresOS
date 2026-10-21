package dev.aresos.client;

import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.levelgen.WorldOptions;

public final class HomeCreateScreen extends Screen {
    private final Screen parent;
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
        int top = Math.max(12, height / 2 - 98);
        addRenderableWidget(new StringWidget(left, top, 280, 20, title, font));
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
        addRenderableWidget(Button.builder(Component.translatable("aresos.home.create"), button -> {
            button.active = false;
            long chosenSeed = WorldOptions.parseSeed(seedText).orElseGet(WorldOptions::randomSeed);
            HomeButton.create(minecraft, parent, chosenSeed, placeholder);
        }).bounds(left, top + 164, 136, 20).build());
        addRenderableWidget(Button.builder(Component.translatable("gui.cancel"), button -> onClose())
                .bounds(left + 144, top + 164, 136, 20).build());
        setInitialFocus(seed);
    }

    private Component toggleLabel() {
        return Component.literal("Placeholder hub: " + (placeholder ? "ON" : "OFF"));
    }

    @Override
    public void onClose() { minecraft.gui.setScreen(parent); }
}
