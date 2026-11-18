package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import dev.aresos.item.AppItems;
import dev.aresos.names.NameRules;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.input.CharacterEvent;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.util.CommonColors;
import net.minecraft.world.item.ItemStack;
import org.lwjgl.glfw.GLFW;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Package 53d: the search over the world, which Super opens (docs/design/LAPTOP-HOME.md section 6). A search box and
 * under it what the typing finds: My apps first, then the other programs, the best hit framed. Enter opens the framed
 * one, a click opens any of them, Escape goes back to the world. It is the quickest way to an app, so it shows nothing
 * until he types and it never pauses the world.
 *
 * <p>Which program is the best hit is {@link AppSearch#ranked}'s rule, not this screen's. An app opened from here
 * opens on the screen that shows the world ({@link AresOsClient#launchOnWorldScreen}).
 *
 * <p>How it looks is the owner's to choose from pictures ({@link Look}): one look is the default, the others are
 * reachable only from the client tests that take those pictures.
 */
public final class WorldSearchScreen extends Screen {
    /** The looks drawn for the owner (reviews/53d-world-search/PROGRESS.md says what each is and why). */
    public enum Look {
        /** A bar in the upper part of the sharp world, its hits on a dark plate under it. */
        BAR,
        /** The Apps screen's sibling: the game's blurred menu background, a title, the list in the game's dark band. */
        MENU,
        /** As wide as the hotbar and standing on it; the hits stack upward, the best one right above the typing. */
        HOTBAR
    }

    private static final Component HINT = Component.literal("Search programs…").withStyle(EditBox.SEARCH_HINT_STYLE);
    private static final Component MENU_HELP = Component.literal("Enter opens the framed program · Esc closes")
            .withStyle(ChatFormatting.GRAY);
    private static final String ENTER = "Enter";
    private static final Identifier LIST_BACKGROUND = Identifier.withDefaultNamespace("textures/gui/inworld_menu_list_background.png");
    private static final Identifier SCROLLER = Identifier.withDefaultNamespace("widget/scroller");
    private static final Identifier SCROLLER_BACKGROUND = Identifier.withDefaultNamespace("widget/scroller_background");
    /** A line is a 16-pixel icon with two pixels around it, as in the Apps screen. */
    private static final int ROW = 20;
    private static final int BOX_HEIGHT = 20;
    private static final int SCROLLER_WIDTH = 6;
    /** The hotbar's width and height in the game's HUD. */
    private static final int HOTBAR_WIDTH = 182, HOTBAR_HEIGHT = 22;
    /** The Apps screen's header: the title, the box and the gaps around them. */
    private static final int MENU_HEADER = 8 + 9 + 4 + BOX_HEIGHT + 6, MENU_FOOTER = 6 + 9 + 6;
    // The Apps screen's own: a hovered row, and the rules beside a heading.
    private static final int HOVER = 0x30FFFFFF, RULE = 0x50FFFFFF;
    /** Behind the hits where the world stays sharp: dark enough to read white text over a noon sky. */
    private static final int PLATE = 0xC0000000;

    private static Look look = Look.BAR;

    /** Where the box and the lines stand in the look. {@code edge}: the first line's top, or its bottom when upward. */
    private record Frame(int boxX, int boxY, int boxWidth, int listX, int listWidth, int edge, int rows, boolean upward) { }

    private sealed interface Line permits Heading, Row, Note { }
    private record Heading(Component label) implements Line { }
    /** {@code firstOther}: the first program that is not his, after at least one that is. */
    private record Row(AppDefinition app, ItemStack icon, boolean best, boolean firstOther) implements Line { }
    private record Note(Component text) implements Line { }

    private EditBox search;
    private Frame frame;
    private List<Line> lines = List.of();
    // The program Enter opens: the first hit of a query that is not blank.
    private String best;
    // How many lines are scrolled past, from the best hit on.
    private int scroll;
    // What the lines were last built from; see AppsScreen.
    private List<AppDefinition> shownApps;
    private Set<String> shownIcons;

    public WorldSearchScreen() { super(Component.literal("Search")); }

    /**
     * Opens the search over the world. An open container closes the normal way first, as when the Apps screen opens a
     * program from the inventory, so the server knows it is closed and a carried item goes back.
     *
     * <p>It does not decide whether now is a good moment: the caller does (step 2's {@code shell_search} handling).
     */
    public static void open(Minecraft client) {
        if (client.gui.screen() instanceof AbstractContainerScreen<?> && client.player != null) client.player.closeContainer();
        client.gui.setScreen(new WorldSearchScreen());
    }

    /** Client tests draw every look for the owner's pictures; null brings the default back. */
    public static void lookForTests(Look other) { look = other == null ? Look.BAR : other; }

    @Override protected void init() {
        // A resize builds the widgets again: what he typed and where he scrolled to stay.
        String typed = search == null ? "" : search.getValue();
        frame = frame();
        search = addRenderableWidget(new EditBox(font, frame.boxX, frame.boxY, frame.boxWidth, BOX_HEIGHT, Component.literal("Search programs")));
        search.setCanLoseFocus(false);
        search.setValue(typed);
        search.setResponder(text -> show(false));
        show(true);
    }

    private Frame frame() {
        return switch (look) {
            case BAR -> {
                int boxWidth = Math.min(260, width - 40), x = (width - boxWidth) / 2, y = Math.max(20, height / 5);
                int top = y + BOX_HEIGHT + 4;
                yield new Frame(x, y, boxWidth, x, boxWidth, top, Math.clamp((height - 24 - top) / ROW, 1, 9), false);
            }
            case MENU -> {
                int listWidth = Math.min(300, width - 40), top = MENU_HEADER + 4;
                yield new Frame((width - 200) / 2, 8 + 9 + 4, 200, (width - listWidth) / 2, listWidth, top,
                        Math.max(1, (height - MENU_FOOTER - 4 - top) / ROW), false);
            }
            case HOTBAR -> {
                int boxWidth = Math.min(HOTBAR_WIDTH, width - 40), x = (width - boxWidth) / 2;
                int y = height - HOTBAR_HEIGHT - 4 - BOX_HEIGHT, bottom = y - 4;
                yield new Frame(x, y, boxWidth, x, boxWidth, bottom, Math.clamp((bottom - 16) / ROW, 1, 8), true);
            }
        };
    }

    @Override protected void setInitialFocus() { setInitialFocus(search); }

    /** The world keeps moving behind it, as behind the Apps screen and the AresOS menu. */
    @Override public boolean isPauseScreen() { return false; }

    /** Escape goes back to the world, whatever was open before Super. */
    @Override public void onClose() { minecraft.gui.setScreen(null); }

    @Override public void tick() {
        if (!AresOsClient.acceptsAppCommands(minecraft)) { onClose(); return; }
        if (AresOs.apps() != shownApps || AresOs.generatedIcons != shownIcons) show(true);
    }

    /** Builds the lines again. {@code keepPlace}: the list changed under him; new typing starts at the best hit. */
    private void show(boolean keepPlace) {
        shownApps = AresOs.apps();
        shownIcons = AresOs.generatedIcons;
        String query = search.getValue();
        var built = new ArrayList<Line>();
        best = null;
        // Nothing until he types: the bar is over the world, and a list of every program would hide it.
        if (!query.isBlank()) {
            var found = AppSearch.ranked(shownApps, query);
            int mine = (int) found.stream().filter(AppDefinition::mine).count();
            if (found.isEmpty()) built.add(new Note(Component.literal("No program matches \"" + query.strip() + "\".")
                    .withStyle(ChatFormatting.GRAY)));
            else best = found.getFirst().id();
            for (int at = 0; at < found.size(); at++) {
                // The hotbar look has no room for headings: a rule sets his apps apart from the rest.
                if (look != Look.HOTBAR) {
                    if (at == 0 && mine > 0) built.add(heading("My apps", mine));
                    if (at == mine) built.add(heading("Other programs", found.size() - mine));
                }
                var app = found.get(at);
                built.add(new Row(app, AppItems.create(app), at == 0, at == mine && mine > 0));
            }
        }
        lines = built;
        scroll = keepPlace ? Math.clamp(scroll, 0, maxScroll()) : 0;
    }

    private static Heading heading(String name, int count) {
        return new Heading(Component.literal(name).append(Component.literal("  " + count).withStyle(ChatFormatting.GRAY)));
    }

    private int maxScroll() { return Math.max(0, lines.size() - frame.rows); }

    private int shownLines() { return Math.min(lines.size(), frame.rows); }

    /** The top of the shown line {@code place} (0 is the first one shown). */
    private int lineY(int place) {
        return frame.upward ? frame.edge - (place + 1) * ROW : frame.edge + place * ROW;
    }

    /** The width the lines have: the scroll bar takes its own strip when there is one. */
    private int lineWidth() { return frame.listWidth - (maxScroll() > 0 ? SCROLLER_WIDTH + 2 : 0); }

    private Line lineAt(double x, double y) {
        if (x < frame.listX || x >= frame.listX + lineWidth()) return null;
        for (int place = 0; place < shownLines(); place++) {
            int top = lineY(place);
            if (y >= top && y < top + ROW) return lines.get(scroll + place);
        }
        return null;
    }

    // Keys and the mouse.

    @Override public boolean charTyped(CharacterEvent event) {
        if (getFocused() != search) setFocused(search);
        return super.charTyped(event);
    }

    @Override public boolean keyPressed(KeyEvent event) {
        if (event.isConfirmation()) { enter(); return true; }
        int page = Math.max(1, frame.rows - 1);
        int step = event.isDown() ? 1 : event.isUp() ? -1 : event.key() == GLFW.GLFW_KEY_PAGE_DOWN ? page
                : event.key() == GLFW.GLFW_KEY_PAGE_UP ? -page : 0;
        // Where the hits stack upward, up is the way to the later ones.
        if (step != 0) { scrollBy(frame.upward ? -step : step); return true; }
        return super.keyPressed(event);
    }

    @Override public boolean mouseScrolled(double x, double y, double scrollX, double scrollY) {
        if (scrollY == 0 || maxScroll() == 0) return super.mouseScrolled(x, y, scrollX, scrollY);
        // Three lines for each notch of the wheel, as in the Apps screen.
        int step = scrollY < 0 ? 3 : -3;
        scrollBy(frame.upward ? -step : step);
        return true;
    }

    private void scrollBy(int step) { scroll = Math.clamp(scroll + step, 0, maxScroll()); }

    /** Enter opens the best hit. With nothing typed or nothing found there is none, and Enter does nothing. */
    private void enter() {
        if (best == null) return;
        AbstractWidget.playButtonClickSound(minecraft.getSoundManager());
        open(best);
    }

    @Override public boolean mouseClicked(MouseButtonEvent event, boolean doubleClick) {
        if (event.button() == 0 && lineAt(event.x(), event.y()) instanceof Row row) {
            AbstractWidget.playButtonClickSound(minecraft.getSoundManager());
            open(row.app.id());
            return true;
        }
        return super.mouseClicked(event, doubleClick);
    }

    /**
     * Opens a program as its hotbar item does, with the same lines when it cannot, on the screen that shows the world.
     * The bar closes first, so the app opens over the world and such a line shows in the chat there.
     */
    private void open(String id) {
        if (!AresOsClient.acceptsAppCommands(minecraft)) { onClose(); return; }
        // As it is now: the line may be a moment older than the list.
        if (AresOs.app(id) == null) return;
        minecraft.gui.setScreen(null);
        AresOsClient.launchOnWorldScreen(id);
    }

    // Drawing.

    @Override public void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        if (look == Look.MENU) { super.extractBackground(graphics, mouseX, mouseY, delta); return; }
        // The world stays sharp behind the bar: he is still in it. The subtitles are drawn as under any screen.
        minecraft.gui.hud.extractDeferredSubtitles();
    }

    @Override public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        int shown = shownLines(), listTop = frame.upward ? frame.edge - shown * ROW : frame.edge, listBottom = listTop + shown * ROW;
        switch (look) {
            case BAR -> {
                int bottom = shown == 0 ? frame.boxY + BOX_HEIGHT : listBottom;
                graphics.fill(frame.boxX - 5, frame.boxY - 5, frame.boxX + frame.boxWidth + 5, bottom + 5, PLATE);
                graphics.outline(frame.boxX - 5, frame.boxY - 5, frame.boxWidth + 10, bottom + 5 - (frame.boxY - 5), RULE);
            }
            case MENU -> {
                int bandBottom = height - MENU_FOOTER;
                Screen.extractMenuBackgroundTexture(graphics, LIST_BACKGROUND, 0, MENU_HEADER, 0, 0, width, bandBottom - MENU_HEADER);
                graphics.blit(RenderPipelines.GUI_TEXTURED, Screen.INWORLD_HEADER_SEPARATOR, 0, MENU_HEADER - 2, 0, 0, width, 2, 32, 2);
                graphics.blit(RenderPipelines.GUI_TEXTURED, Screen.INWORLD_FOOTER_SEPARATOR, 0, bandBottom, 0, 0, width, 2, 32, 2);
                graphics.centeredText(font, title, width / 2, 8, CommonColors.WHITE);
                graphics.centeredText(font, MENU_HELP, width / 2, bandBottom + 6, CommonColors.WHITE);
            }
            case HOTBAR -> {
                if (shown > 0) {
                    int left = frame.listX - 4, top = listTop - 4, plateWidth = frame.listWidth + 8;
                    graphics.fill(left, top, left + plateWidth, frame.boxY - 1, PLATE);
                    graphics.outline(left, top, plateWidth, frame.boxY - 1 - top, RULE);
                }
            }
        }
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        // The box hides its own hint while it has the keyboard, which here is always.
        if (search.getValue().isEmpty())
            graphics.text(font, HINT, search.getX() + 4, search.getY() + (search.getHeight() - 8) / 2, CommonColors.WHITE);
        int lineWidth = lineWidth();
        Line hovered = lineAt(mouseX, mouseY);
        for (int place = 0; place < shown; place++) {
            Line line = lines.get(scroll + place);
            int y = lineY(place);
            switch (line) {
                case Heading heading -> heading(graphics, heading, frame.listX, y, lineWidth);
                case Note note -> graphics.centeredText(font, note.text, frame.listX + lineWidth / 2, y + 6, CommonColors.WHITE);
                case Row row -> row(graphics, row, frame.listX, y, lineWidth, line == hovered);
            }
        }
        if (maxScroll() > 0) scroller(graphics, frame.listX + frame.listWidth - SCROLLER_WIDTH, listTop, listBottom - listTop);
    }

    /** The Apps screen's heading: the name, the count in gray, and a rule on both sides. */
    private void heading(GuiGraphicsExtractor graphics, Heading heading, int x, int y, int width) {
        int middle = x + width / 2, textY = y + ROW - 2 - font.lineHeight, gap = font.width(heading.label) / 2 + 8;
        graphics.centeredText(font, heading.label, middle, textY, CommonColors.WHITE);
        graphics.fill(x + 2, textY + 4, middle - gap, textY + 5, RULE);
        graphics.fill(middle + gap, textY + 4, x + width - 2, textY + 5, RULE);
    }

    /** One program as the Apps screen shows it: its icon, its name, his short command in gold, its kind in gray. */
    private void row(GuiGraphicsExtractor graphics, Row row, int x, int y, int width, boolean hovered) {
        var app = row.app;
        if (row.firstOther && look == Look.HOTBAR) {
            // Between the last of his apps and the first other program; upward, his apps are below this line.
            int ruleY = frame.upward ? y + ROW - 1 : y;
            graphics.fill(x + 2, ruleY, x + width - 2, ruleY + 1, RULE);
        }
        if (hovered || row.best) graphics.fill(x, y, x + width, y + ROW, HOVER);
        if (row.best) graphics.outline(x, y, width, ROW, CommonColors.WHITE);
        graphics.fakeItem(row.icon, x + 3, y + 2);
        int textX = x + 3 + 16 + 6, textY = y + 6, right = x + width - 5;
        if (row.best) {
            // The frame says which one, the word says which key.
            right -= font.width(ENTER);
            graphics.text(font, ENTER, right, textY, CommonColors.LIGHT_GRAY);
            right -= 8;
        }
        String main = app.mine() ? NameRules.mainName(app) : "";
        String command = main.isEmpty() ? "" : "/" + main;
        // The name comes first: a narrow bar drops the command before it cuts the name short.
        if (!command.isEmpty() && right - textX - font.width(app.name()) < font.width(command) + 8) command = "";
        int commandRoom = command.isEmpty() ? 0 : font.width(command) + 8;
        String name = clip(app.name(), right - textX - commandRoom);
        graphics.text(font, name, textX, textY, CommonColors.WHITE);
        int next = textX + font.width(name) + 8;
        if (!command.isEmpty()) {
            graphics.text(font, Component.literal(command).withStyle(ChatFormatting.GOLD), next, textY, CommonColors.WHITE);
            next += font.width(command) + 8;
        }
        String kind = app.system() == null ? null : app.system().genericName();
        // Only when there is room for a few words: half a word says nothing.
        if (kind != null && !kind.isBlank() && !kind.equalsIgnoreCase(app.name()) && right - next >= 48)
            graphics.text(font, clip(kind, right - next), next, textY, CommonColors.LIGHT_GRAY);
    }

    /** The game's own scroll bar, beside the lines. Upward, the best hit is at the bottom and so is the handle. */
    private void scroller(GuiGraphicsExtractor graphics, int x, int top, int span) {
        int handle = Math.max(8, span * frame.rows / lines.size());
        int travel = (span - handle) * scroll / maxScroll();
        graphics.blitSprite(RenderPipelines.GUI_TEXTURED, SCROLLER_BACKGROUND, x, top, SCROLLER_WIDTH, span);
        graphics.blitSprite(RenderPipelines.GUI_TEXTURED, SCROLLER, x, frame.upward ? top + span - handle - travel : top + travel,
                SCROLLER_WIDTH, handle);
    }

    private String clip(String text, int room) {
        if (font.width(text) <= room) return text;
        String ellipsis = CommonComponents.ELLIPSIS.getString();
        return font.plainSubstrByWidth(text, Math.max(0, room - font.width(ellipsis))) + ellipsis;
    }

    // What the client tests read and where they click.

    /** The look this screen is drawn in. */
    public static Look look() { return look; }

    /** The programs found, in the order of the lines, whether scrolled into view or not. */
    public List<String> found() {
        return lines.stream().filter(Row.class::isInstance).map(line -> ((Row) line).app.id()).toList();
    }

    /** The program Enter opens, or null. */
    public String best() { return best; }

    /** The line that says nothing was found, or null. */
    public String note() {
        return lines.stream().filter(Note.class::isInstance).map(line -> ((Note) line).text.getString()).findFirst().orElse(null);
    }

    /** The headings, as he reads them. */
    public List<String> headings() {
        return lines.stream().filter(Heading.class::isInstance).map(line -> ((Heading) line).label.getString()).toList();
    }

    /** How many lines are scrolled past. */
    public int scrolled() { return scroll; }

    /** The middle of a program's line in the screen's pixels, or null while it is not in view. */
    public int[] middleOf(String id) {
        for (int place = 0; place < shownLines(); place++)
            if (lines.get(scroll + place) instanceof Row row && row.app.id().equals(id))
                return new int[] {frame.listX + lineWidth() / 2, lineY(place) + ROW / 2};
        return null;
    }
}
