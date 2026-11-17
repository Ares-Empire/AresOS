package dev.aresos.client;

import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.MultiLineTextWidget;
import net.minecraft.client.gui.layouts.FrameLayout;
import net.minecraft.client.gui.layouts.LinearLayout;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** A failed reopen stays actionable and keeps HomeSwitch's title-screen guard in force. */
public final class HomeRecoveryScreen extends Screen {
    private final Component detail;
    private final Runnable retry;

    HomeRecoveryScreen(String folder, String reason, Runnable retry) {
        super(Component.literal("Your home couldn't be opened"));
        detail = Component.literal("Your home is kept in " + folder + ". " + reason + ". Try opening it again.");
        this.retry = retry;
    }

    @Override protected void init() {
        var layout = LinearLayout.vertical().spacing(12);
        layout.defaultCellSetting().alignHorizontallyCenter();
        layout.addChild(new MultiLineTextWidget(title, font).setMaxWidth(width - 32).setCentered(true));
        layout.addChild(new MultiLineTextWidget(detail, font).setMaxWidth(Math.min(320, width - 32)).setCentered(true));
        layout.addChild(Button.builder(Component.literal("Try again"), button -> {
            button.active = false;
            retry.run();
        }).width(200).build());
        layout.arrangeElements();
        FrameLayout.centerInRectangle(layout, 0, 0, width, height);
        layout.visitWidgets(this::addRenderableWidget);
    }

    @Override public boolean shouldCloseOnEsc() { return false; }

    @Override public void onClose() { }
}
