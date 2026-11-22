package dev.aresos.client;

import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.layouts.FrameLayout;
import net.minecraft.client.gui.layouts.LinearLayout;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.options.OptionsScreen;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.GameType;

/**
 * Package 48: the AresOS menu, which Esc opens in the home screen instead of the game's menu (brief 48, A). The home
 * screen is the desktop, not a game: there is nothing to save and quit, no LAN, no advancements. A column of the
 * game's own buttons, 200 wide as in the game menu, over the world with the game's in-world background, as the Apps
 * screen has it. It does not pause the world: like a desktop's start menu, the world keeps moving behind it.
 */
public final class AresOsMenuScreen extends Screen {
    static final Component BACK = Component.literal("Back to the world");
    static final Component APPS = Component.literal("Apps…");
    static final Component SETTINGS = Component.literal("Settings…");
    static final Component BUILD_OFF = Component.literal("Build mode: Off");
    static final Component BUILD_ON = Component.literal("Build mode: On");
    static final Component BUILD_HINT = Component.literal("In Build mode you can change the home's blocks. G switches it too.");
    static final Component NEW_HOME = Component.literal("Start a new home…");
    static final Component NEW_HOME_HINT = Component.literal("Builds a fresh home world and switches to it. Your current home is kept.");
    static final Component NEW_HOME_TITLE = Component.literal("Start a new home?");
    static final Component NEW_HOME_QUESTION = Component.literal("AresOS will build a fresh home and open it. "
            + "Your current home will stay in your saves.");
    static final Component MAKE_IT = Component.literal("Make the new home");
    private static final int BUTTON_WIDTH = 200;

    private LinearLayout layout;
    private Button apps;
    private Button buildMode;
    private StringWidget keyHint;

    public AresOsMenuScreen() { super(Component.literal("AresOS")); }

    /** Whether the game's menu gives way to this one here, using the saving indicator's home gate too. */
    public static boolean replacesGameMenu(Minecraft client) {
        return HomeScreen.home(client);
    }

    @Override protected void init() {
        layout = LinearLayout.vertical().spacing(4);
        layout.defaultCellSetting().alignHorizontallyCenter();
        layout.addChild(new StringWidget(title, font), settings -> settings.paddingBottom(8));
        layout.addChild(Button.builder(BACK, button -> onClose()).width(BUTTON_WIDTH).build());
        apps = layout.addChild(Button.builder(APPS, button -> minecraft.gui.setScreen(new AppsScreen(this)))
                .width(BUTTON_WIDTH).build());
        layout.addChild(Button.builder(SETTINGS, button -> minecraft.gui.setScreen(new OptionsScreen(this, minecraft.options, true)))
                .width(BUTTON_WIDTH).build());
        buildMode = layout.addChild(Button.builder(BUILD_OFF, button -> ModeSwitchClient.requestToggle())
                .tooltip(Tooltip.create(BUILD_HINT)).width(BUTTON_WIDTH).build());
        layout.addChild(Button.builder(NEW_HOME, button -> minecraft.gui.setScreen(
                new HomeCreateScreen(this, AresOsMenuScreen::confirmNewHome)))
                .tooltip(Tooltip.create(NEW_HOME_HINT)).width(BUTTON_WIDTH).build());
        keyHint = layout.addChild(new StringWidget(hint(minecraft), font), settings -> settings.paddingTop(8));
        keyHint.setMaxWidth(width - 16, StringWidget.TextOverflow.SCROLLING);
        layout.visitWidgets(this::addRenderableWidget);
        updateButtons();
        repositionElements();
    }

    @Override protected void repositionElements() {
        layout.arrangeElements();
        // Where the game menu stands: centred across, a quarter of the free height above it.
        FrameLayout.alignInRectangle(layout, 0, 0, width, height, 0.5f, 0.25f);
    }

    /**
     * Create on the home choice asks once (brief 48, A.5); yes switches homes, no goes back to the choice as it was.
     */
    static void confirmNewHome(Minecraft client, HomeCreateScreen choice, HomePlan plan) {
        client.gui.setScreen(new ConfirmScreen(yes -> {
            if (yes) HomeSwitch.start(client, plan);
            else {
                choice.confirmationCancelled();
                client.gui.setScreen(choice);
            }
        }, NEW_HOME_TITLE, NEW_HOME_QUESTION, MAKE_IT, CommonComponents.GUI_CANCEL));
    }

    /** The keys as he has them bound, in one gray line. */
    static Component hint(Minecraft client) {
        return Component.empty().append(modeKey()).append(" switches Live and Build · ")
                .append(client.options.keyInventory.getTranslatedKeyMessage()).append(" opens the inventory and Apps…")
                .withStyle(ChatFormatting.GRAY);
    }

    private static Component modeKey() {
        var mode = AresOsClient.modeKey();
        return mode == null ? Component.literal("G") : mode.getTranslatedKeyMessage();
    }

    /** Settings returns the same initialized menu. Refresh its bindings on every appearance. */
    @Override public void added() {
        super.added();
        if (keyHint != null) {
            keyHint.setMessage(hint(minecraft));
            repositionElements();
            updateButtons();
        }
    }

    /** The Apps screen is Live's: in Build mode it would close at once, so its button waits for Live. */
    private void updateButtons() {
        boolean live = AppsScreen.active(minecraft);
        apps.active = live;
        apps.setTooltip(live ? null : Tooltip.create(Component.literal("Apps open in Live mode. Use the Build mode button or press ")
                .append(modeKey()).append(" in the world.")));
        boolean building = minecraft.gameMode != null && minecraft.gameMode.getPlayerMode() == GameType.CREATIVE;
        buildMode.setMessage(building ? BUILD_ON : BUILD_OFF);
        buildMode.active = ModeSwitchClient.canRequestToggle(minecraft);
    }

    @Override public void tick() { updateButtons(); }

    /** The world keeps moving behind it, as behind the Apps screen. */
    @Override public boolean isPauseScreen() { return false; }
}
