package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import dev.aresos.item.AppItems;
import dev.aresos.item.MyAppPayload;
import dev.aresos.item.TakeAppPayload;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.client.message.v1.ClientReceiveMessageEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.ObjectSelectionList;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.layouts.HeaderAndFooterLayout;
import net.minecraft.client.gui.layouts.LinearLayout;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.input.CharacterEvent;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.util.CommonColors;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import org.lwjgl.glfw.GLFW;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * E, then "Apps…" (docs/design/HUB.md 2.4): a search box, then one list that scrolls, "My apps" first and
 * "All programs" by name below it. A click on any program opens it, as its hotbar item would, and he is back in the
 * world (package 40, review fixes 1). Pressing on a program and moving before letting go is a drag: it picks up the
 * program's item to pin it, and a program that is not his becomes his first. A right-click on one of his takes it out
 * of My apps.
 */
public final class AppsScreen extends Screen {
    private static final Component HELP = Component.literal(
            "Click opens · drag to the hotbar to pin · right-click removes").withStyle(ChatFormatting.GRAY);
    private static final Component HINT = Component.literal("Search programs…").withStyle(EditBox.SEARCH_HINT_STYLE);
    private static final Identifier CHECK = Identifier.withDefaultNamespace("icon/checkmark");
    /** A row is a 16-pixel icon with the list's two pixels around it. */
    private static final int ROW = 20;
    private static final int ROW_WIDTH = 300;
    /** How long a line from the chat stays in the screen, in ticks. */
    private static final int NEWS_TICKS = 100;
    /** How far the pointer moves with the left button down, in the screen's pixels, before a press is a drag. */
    private static final double DRAG = 3;

    private final Screen parent;
    // The title and the search box above the list as on the game's world list, the hint and Done below it.
    private final HeaderAndFooterLayout layout = new HeaderAndFooterLayout(this, 8 + 9 + 4 + 20 + 6, 6 + 9 + 4 + 20 + 6);
    private EditBox search;
    private ProgramList list;
    private StringWidget status;
    // What the rows were last built from. Every add, remove and new program replaces the list object, and a
    // finished icon reload replaces the set, so comparing the two references is enough.
    private List<AppDefinition> shownApps;
    private Set<String> shownIcons;
    private Component news;
    private int ticks, newsAt;
    // The program whose row the left button went down on, and where; see mouseDragged and mouseReleased.
    private String pressed;
    private double pressedX, pressedY;

    public AppsScreen(Screen parent) { super(Component.literal("Apps")); this.parent = parent; }

    public static boolean active(Minecraft client) {
        return client.player != null && client.gameMode != null && client.gameMode.getPlayerMode() == GameType.SURVIVAL
                && client.getSingleplayerServer() != null && DesktopWorld.isEnabled(client.getSingleplayerServer());
    }

    public static void register() {
        ScreenEvents.AFTER_INIT.register((client, screen, width, height) -> {
            if (screen instanceof InventoryScreen && active(client)) {
                Screens.getWidgets(screen).add(Button.builder(Component.literal("Apps…"),
                        button -> client.gui.setScreen(new AppsScreen(screen))).bounds(width / 2 - 35, (height - 166) / 2 - 24, 70, 20).build());
            }
        });
        // The chat is behind this screen, so a line that arrives while it is open is shown in it as well.
        ClientReceiveMessageEvents.GAME.register((message, overlay) -> {
            if (!overlay && Minecraft.getInstance().gui.screen() instanceof AppsScreen screen) screen.said(message);
        });
    }

    @Override protected void init() {
        var header = layout.addToHeader(LinearLayout.vertical().spacing(4));
        header.defaultCellSetting().alignHorizontallyCenter();
        header.addChild(new StringWidget(title, font));
        search = header.addChild(new EditBox(font, 0, 0, 200, 20, Component.literal("Search programs")));
        search.setHint(HINT);
        search.setResponder(typed -> show(false));
        list = layout.addToContents(new ProgramList());
        layout.addToFooter(Button.builder(CommonComponents.GUI_DONE, button -> onClose()).width(200).build(),
                settings -> settings.alignVerticallyBottom().paddingBottom(6));
        layout.visitWidgets(this::addRenderableWidget);
        // Placed by hand above Done: in the footer's layout its changing width would nudge the button.
        status = addRenderableWidget(new StringWidget(HELP, font));
        repositionElements();
        show(false);
    }

    @Override protected void repositionElements() {
        layout.arrangeElements();
        list.updateSize(width, layout);
        placeStatus();
    }

    private void placeStatus() {
        status.setMaxWidth(width - 16, StringWidget.TextOverflow.SCROLLING);
        status.setPosition((width - status.getWidth()) / 2, height - layout.getFooterHeight() + 6);
    }

    @Override public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        // The box hides its own hint while it has the keyboard, which here is nearly always.
        if (search.isFocused() && search.getValue().isEmpty())
            graphics.text(font, HINT, search.getX() + 4, search.getY() + (search.getHeight() - 8) / 2, CommonColors.WHITE);
    }

    @Override protected void setInitialFocus() { setInitialFocus(search); }

    /** The integrated server must keep running: an add or a remove is answered while the screen is open. */
    @Override public boolean isPauseScreen() { return false; }

    @Override public void tick() {
        if (!active(minecraft)) { onClose(); return; }
        ticks++;
        if (AresOs.apps() != shownApps || AresOs.generatedIcons != shownIcons) show(true);
        if (news != null && ticks - newsAt > NEWS_TICKS) say(null);
    }

    @Override public void onClose() { minecraft.gui.setScreen(parent); }

    /** Builds the rows again. {@code keepPlace}: the list changed under him; a new search starts at the top. */
    private void show(boolean keepPlace) {
        shownApps = AresOs.apps();
        shownIcons = AresOs.generatedIcons;
        list.show(AppSearch.find(shownApps, search.getValue()), search.getValue().strip(), keepPlace);
    }

    private void said(Component message) {
        // Two lines of one tick belong together ("No free inventory slot: …" and "Added …").
        say(news != null && newsAt == ticks ? news.copy().append(" ").append(message) : message);
    }

    private void say(Component message) {
        news = message;
        newsAt = ticks;
        status.setMessage(message == null ? HELP : message);
        placeStatus();
    }

    @Override public boolean charTyped(CharacterEvent event) {
        // Typing goes to the search box, wherever the last click left the focus.
        if (getFocused() != search) setFocused(search);
        return super.charTyped(event);
    }

    @Override public boolean keyPressed(KeyEvent event) {
        // Tab can put the focus on the list; any other key still belongs to the search.
        if (getFocused() == list && !event.isCycleFocus()) setFocused(search);
        if (getFocused() == search) {
            if (event.isConfirmation()) { enter(); return true; }
            int rows = event.isDown() ? 1 : event.isUp() ? -1 : event.key() == GLFW.GLFW_KEY_PAGE_DOWN ? list.page()
                    : event.key() == GLFW.GLFW_KEY_PAGE_UP ? -list.page() : 0;
            if (rows != 0) { list.setScrollAmount(list.scrollAmount() + rows * ROW); return true; }
        }
        return super.keyPressed(event);
    }

    /** Enter is a click on the only program the search found: it opens. */
    private void enter() {
        String only = list.only();
        if (only == null || AresOs.app(only) == null) return;
        AbstractWidget.playButtonClickSound(minecraft.getSoundManager());
        open(only);
    }

    /**
     * A button goes down on a program: the left one starts a click or a drag (told apart when it moves or is let go),
     * the right one takes one of his out of My apps.
     */
    private boolean press(String id, boolean right, double x, double y) {
        pressed = null;
        if (!active(minecraft)) { onClose(); return true; }
        // As it is now: the row may be a moment older than the list.
        var app = AresOs.app(id);
        if (app == null || (right && !app.mine())) return false;
        AbstractWidget.playButtonClickSound(minecraft.getSoundManager());
        if (right) ClientPlayNetworking.send(new MyAppPayload(id, false));
        else {
            pressed = id;
            pressedX = x;
            pressedY = y;
        }
        return true;
    }

    /** The pointer moved away from where the left button went down on a program: a drag, which picks up its item. */
    @Override public boolean mouseDragged(MouseButtonEvent event, double dx, double dy) {
        if (event.button() == 0 && pressed != null
                && Math.max(Math.abs(event.x() - pressedX), Math.abs(event.y() - pressedY)) > DRAG) {
            String id = pressed;
            pressed = null;
            pickUp(id);
            return true;
        }
        return super.mouseDragged(event, dx, dy);
    }

    /** The left button let go where it went down on a program: a click, which opens it. */
    @Override public boolean mouseReleased(MouseButtonEvent event) {
        boolean handled = super.mouseReleased(event);
        // A click on a row or a pull at the scroll bar took the focus to the list; the search box gets it back.
        if (getFocused() == list) setFocused(search);
        if (event.button() != 0 || pressed == null) return handled;
        String id = pressed;
        pressed = null;
        open(id);
        return true;
    }

    /**
     * Opens a program the way its hotbar item does (AresOsClient.launch), with the same lines when it cannot. He is
     * back in the world first, so the app opens over the world and such a line shows in the chat there.
     */
    private void open(String id) {
        if (!active(minecraft)) { onClose(); return; }
        if (AresOs.app(id) == null) return;
        if (parent instanceof AbstractContainerScreen<?> && minecraft.player != null) minecraft.player.closeContainer();
        else minecraft.gui.setScreen(null);
        AresOsClient.launch(id);
    }

    /**
     * A drag picks up the program's item to pin it. A program that is not his becomes his first: what is in his
     * inventory is his ("Pinning a program makes it one of his", HUB.md 2.4); the server takes the two requests in
     * order. The inventory comes back while the button is still down, so the drag goes on there: letting go over a
     * slot puts the item in it, as a drag in the inventory does, and letting go before the item arrived leaves it on
     * the cursor for the next click.
     */
    private void pickUp(String id) {
        if (!active(minecraft)) { onClose(); return; }
        var app = AresOs.app(id);
        if (app == null) return;
        if (!app.mine()) ClientPlayNetworking.send(new MyAppPayload(id, true));
        ClientPlayNetworking.send(new TakeAppPayload(id));
        // The inventory would skip this release as the one of the click that opened it; here it ends the drag.
        if (parent instanceof AbstractContainerScreen<?> inventory)
            ((dev.aresos.client.mixin.ContainerScreenAccess) inventory).aresos$setSkipNextRelease(false);
        minecraft.gui.setScreen(parent);
    }

    private String clip(String text, int room) {
        if (font.width(text) <= room) return text;
        String ellipsis = CommonComponents.ELLIPSIS.getString();
        return font.plainSubstrByWidth(text, Math.max(0, room - font.width(ellipsis))) + ellipsis;
    }

    /** The one list of the screen: a heading and the rows of My apps, then a heading and the rows of every program. */
    public final class ProgramList extends ObjectSelectionList<Line> {
        ProgramList() {
            super(AppsScreen.this.minecraft, AppsScreen.this.width, layout.getContentHeight(), layout.getHeaderHeight(), ROW);
        }

        @Override public int getRowWidth() { return Math.min(ROW_WIDTH, AppsScreen.this.width - 40); }
        /** A click acts at once, so no row stays marked as chosen. */
        @Override protected boolean entriesCanBeSelected() { return false; }
        /** Three rows for each notch of the wheel: 200 programs are a long way at the game's half a row. */
        @Override protected double scrollRate() { return ROW * 3; }

        int page() { return Math.max(1, getHeight() / ROW - 1); }

        void show(List<AppDefinition> found, String query, boolean keepPlace) {
            // The row under the pointer stays under it when a row appears or goes above it, so the next click
            // lands on the program he is looking at.
            Row held = keepPlace && getHovered() instanceof Row row ? row : null;
            int heldY = held == null ? 0 : held.getY();
            var mine = found.stream().filter(AppDefinition::mine).toList();
            var lines = new ArrayList<Line>();
            if (!mine.isEmpty()) {
                lines.add(new Heading("My apps", mine.size()));
                for (var app : mine) lines.add(new Row(app, true));
            }
            if (found.isEmpty()) lines.add(new Note(query.isEmpty() ? "No programs yet." : "No program matches \"" + query + "\"."));
            else {
                lines.add(new Heading("All programs", found.size()));
                for (var app : found) lines.add(new Row(app, false));
            }
            replaceEntries(lines);
            double scroll = keepPlace ? scrollAmount() : 0;
            if (held != null) for (var line : children())
                if (line instanceof Row row && row.inMyApps == held.inMyApps && row.app.id().equals(held.app.id())) {
                    scroll += row.getY() - heldY;
                    break;
                }
            setScrollAmount(scroll);
        }

        /** The program the list shows, if it shows exactly one. */
        String only() {
            String only = null;
            for (var line : children()) if (line instanceof Row row) {
                if (only != null && !only.equals(row.app.id())) return null;
                only = row.app.id();
            }
            return only;
        }
    }

    public abstract class Line extends ObjectSelectionList.Entry<Line> {
        @Override public boolean mouseClicked(MouseButtonEvent event, boolean doubleClick) { return false; }
    }

    private final class Heading extends Line {
        private final Component label;

        Heading(String name, int count) {
            label = Component.literal(name).append(Component.literal("  " + count).withStyle(ChatFormatting.GRAY));
        }

        @Override public void extractContent(GuiGraphicsExtractor graphics, int mouseX, int mouseY, boolean hovered, float delta) {
            int middle = getContentXMiddle(), y = getContentBottom() - font.lineHeight, gap = font.width(label) / 2 + 8;
            graphics.centeredText(font, label, middle, y, CommonColors.WHITE);
            // A rule on both sides sets the heading apart from the names above and below it.
            graphics.fill(getContentX(), y + 4, middle - gap, y + 5, 0x50FFFFFF);
            graphics.fill(middle + gap, y + 4, getContentRight(), y + 5, 0x50FFFFFF);
        }

        @Override public Component getNarration() { return label; }
    }

    private final class Note extends Line {
        private final Component text;

        Note(String text) { this.text = Component.literal(text).withStyle(ChatFormatting.GRAY); }

        @Override public void extractContent(GuiGraphicsExtractor graphics, int mouseX, int mouseY, boolean hovered, float delta) {
            graphics.centeredText(font, text, getContentXMiddle(), getContentBottom() - font.lineHeight - 2, CommonColors.WHITE);
        }

        @Override public Component getNarration() { return text; }
    }

    /** One program: its icon, its name, and in gray what kind of program the system says it is. */
    public final class Row extends Line {
        private final AppDefinition app;
        private final boolean inMyApps;
        private final ItemStack icon;

        Row(AppDefinition app, boolean inMyApps) {
            this.app = app;
            this.inMyApps = inMyApps;
            this.icon = AppItems.create(app);
        }

        public AppDefinition app() { return app; }
        /** True for a row under "My apps", false for one under "All programs". */
        public boolean inMyApps() { return inMyApps; }

        @Override public void extractContent(GuiGraphicsExtractor graphics, int mouseX, int mouseY, boolean hovered, float delta) {
            if (hovered) graphics.fill(getX(), getY(), getX() + getWidth(), getY() + getHeight(), 0x30FFFFFF);
            int x = getContentX(), y = getContentY(), right = getContentRight() - 2;
            graphics.fakeItem(icon, x, y);
            // Under "All programs" a check mark says which ones are his already; under "My apps" all of them are.
            if (app.mine() && !inMyApps) {
                right -= 9;
                graphics.blitSprite(RenderPipelines.GUI_TEXTURED, CHECK, right, y + 4, 9, 8);
                right -= 6;
            }
            int textX = x + 16 + 6, textY = y + 4;
            String main = app.mine() ? dev.aresos.names.NameRules.mainName(app) : "";
            String command = main.isEmpty() ? "" : "/" + main;
            int commandRoom = command.isEmpty() ? 0 : font.width(command) + 8;
            String name = clip(app.name(), right - textX - commandRoom);
            graphics.text(font, name, textX, textY, CommonColors.WHITE);
            String kind = app.system() == null ? null : app.system().genericName();
            int kindX = textX + font.width(name) + 8;
            if (!command.isEmpty()) {
                graphics.text(font, Component.literal(command).withStyle(ChatFormatting.GOLD), kindX, textY, CommonColors.WHITE);
                kindX += font.width(command) + 8;
            }
            // Only when there is room for a few words: half a word says nothing.
            if (kind != null && !kind.isBlank() && !kind.equalsIgnoreCase(app.name()) && right - kindX >= 48)
                graphics.text(font, clip(kind, right - kindX), kindX, textY, CommonColors.LIGHT_GRAY);
        }

        @Override public boolean mouseClicked(MouseButtonEvent event, boolean doubleClick) {
            // Reflow can put a different row under this same pointer, especially when the list cannot scroll.
            if (doubleClick) { pressed = null; return true; }
            return (event.button() == 0 || event.button() == 1) && press(app.id(), event.button() == 1, event.x(), event.y());
        }

        @Override public Component getNarration() {
            return Component.literal(app.name() + (app.mine() ? ", one of your apps, /" + dev.aresos.names.NameRules.mainName(app) : ""));
        }
    }
}
