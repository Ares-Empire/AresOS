package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.client.mixin.RecipeBookSearchAccess;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import dev.aresos.item.AppItems;
import dev.aresos.names.NameRules;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.MultiLineEditBox;
import net.minecraft.client.gui.components.events.ContainerEventHandler;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.recipebook.RecipeBookComponent;
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
import java.util.function.Predicate;

/**
 * Package 53d: the search over the world, which Super opens (docs/design/LAPTOP-HOME.md section 6). A search box and
 * under it what the typing finds: My apps first, then the other programs, the best hit framed. Enter opens the framed
 * one, a click opens any of them, Escape goes back to the world. It is the quickest way to an app, so it shows nothing
 * until he types and it never pauses the world.
 *
 * <p>Which program is the best hit is {@link AppSearch#ranked}'s rule, not this screen's. The best hit stays at the
 * top of the list while the rest scrolls under it, so the program Enter opens is always in view, wherever the bar has
 * room for that ({@link SearchLines}). An app opened from here opens on the screen that shows the world
 * ({@link AresOsClient#launchOnWorldScreen}).
 *
 * <p>Its look is the bar the owner chose from three drawn for him (board #382, 2026-11-19): a search box in the upper
 * part of the sharp world, its hits on a dark plate under it.
 */
public final class WorldSearchScreen extends Screen {
    private static final Component HINT = Component.literal("Search programs…").withStyle(EditBox.SEARCH_HINT_STYLE);
    private static final String ENTER = "Enter";
    private static final Identifier SCROLLER = Identifier.withDefaultNamespace("widget/scroller");
    private static final Identifier SCROLLER_BACKGROUND = Identifier.withDefaultNamespace("widget/scroller_background");
    /** A line is a 16-pixel icon with two pixels around it, as in the Apps screen. */
    private static final int ROW = 20;
    private static final int BOX_HEIGHT = 20;
    private static final int SCROLLER_WIDTH = 6;
    // The Apps screen's own: a hovered row, and the rules beside a heading.
    private static final int HOVER = 0x30FFFFFF, RULE = 0x50FFFFFF;
    /** Behind the hits where the world stays sharp: dark enough to read white text over a noon sky. */
    private static final int PLATE = 0xC0000000;

    /** Where the box and the lines stand: the lines are as wide as the box, the first one's top at {@code top}. */
    private record Frame(int x, int boxY, int width, int top, int rows) { }

    private sealed interface Line permits Heading, Row, Note { }
    private record Heading(Component label) implements Line { }
    private record Row(AppDefinition app, ItemStack icon, boolean best) implements Line { }
    private record Note(Component text) implements Line { }

    /**
     * Whether the game's window has the keyboard. Public for the client test, which takes it away to check that the bar
     * waits for it; the game's own answer otherwise.
     */
    public static Predicate<Minecraft> windowFocus = Minecraft::isWindowActive;
    // Super's request that came before the window had the keyboard (client thread only).
    private static final SearchFocusWait WAITING = new SearchFocusWait();

    private EditBox search;
    private Frame frame;
    private List<Line> lines = List.of();
    // The program Enter opens: the first hit of a query that is not blank.
    private String best;
    // Which line stands in which slot: the first lines, up to the best hit, stay at the top where there is room.
    private SearchLines view = SearchLines.of(0, -1, 1);
    // How many of the lines after the pinned ones are scrolled past.
    private int scroll;
    // What the lines were last built from; see AppsScreen.
    private List<AppDefinition> shownApps;
    private Set<String> shownIcons;

    public WorldSearchScreen() { super(Component.literal("Search")); }

    /**
     * Opens the search over the world. An open container closes the normal way first, as when the Apps screen opens a
     * program from the inventory, so the server knows it is closed and a carried item goes back; so does the inventory
     * the Apps screen was opened from.
     *
     * <p>It does not decide whether now is a good moment: {@link #requested} does.
     */
    public static void open(Minecraft client) {
        var screen = client.gui.screen();
        boolean container = screen instanceof AbstractContainerScreen<?> || screen instanceof AppsScreen apps && apps.overContainer();
        if (container && client.player != null) client.player.closeContainer();
        client.gui.setScreen(new WorldSearchScreen());
    }

    /**
     * Super's {@code shell_search} (package 53d), on the client thread: opens the search unless this is the wrong
     * moment for it ({@link SearchMoment}), and says which moment it was. Without the window's focus it waits for it
     * ({@link SearchFocusWait}), then decides again.
     */
    public static SearchMoment requested(Minecraft client) {
        WAITING.cancel();
        var moment = moment(client);
        if (moment == SearchMoment.NO_FOCUS) WAITING.start();
        if (moment.opens()) open(client);
        return moment;
    }

    private static SearchMoment moment(Minecraft client) {
        return SearchMoment.of(ShellFocusClient.readyWorld(client) != null, opened(client.gui.screen()), windowFocus.test(client));
    }

    /** Whether Super's request waits for the window's focus now. For the client test. */
    public static boolean waitingForFocus() { return WAITING.waiting(); }

    /** The wait for the window's focus runs on the client's ticks. Once, from the mod's client start. */
    public static void register() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (!WAITING.waiting()) return;
            switch (WAITING.tick(windowFocus.test(client))) {
                case OPEN -> {
                    var moment = moment(client);
                    if (moment.opens()) open(client);
                    else AresOs.LOGGER.info("Super: the game has the keyboard now, but the search does not open ({})", moment);
                }
                case DROP -> AresOs.LOGGER.info("Super: the game's window did not get the keyboard within 500 ms; no search");
                case NOTHING -> { }
            }
        });
    }

    /**
     * What is open, for Super's rule. Review 2: an allowlist, after two rounds of listing the screens to keep each
     * missed one (a book being signed, then the New home choice with its seed). The search replaces only screens known
     * to hold nothing typed: the inventory and other containers, the game menu (the game's own class exactly, or
     * AresOS's) and the Apps screen, and each of them only while no text box in it holds text: an anvil's name, the
     * creative inventory's search, the recipe book's, the Apps screen's own. Every other screen is
     * {@link SearchMoment.Open#OTHER} and stays, the game's, another mod's and AresOS's own: nobody has said what would
     * be lost with it.
     */
    static SearchMoment.Open opened(Screen screen) {
        if (screen == null) return SearchMoment.Open.NOTHING;
        if (screen instanceof WorldSearchScreen) return SearchMoment.Open.SEARCH;
        SearchMoment.Open kind = screen instanceof AbstractContainerScreen<?> ? SearchMoment.Open.CONTAINER
                : screen.getClass() == PauseScreen.class || screen instanceof AresOsMenuScreen ? SearchMoment.Open.MENU
                : screen instanceof AppsScreen ? SearchMoment.Open.APPS : SearchMoment.Open.OTHER;
        return kind != SearchMoment.Open.OTHER && holdsText(screen, 0) ? SearchMoment.Open.OTHER : kind;
    }

    /** Whether a text box in there holds text, typed or put there (an anvil shows the item's name): either way it stays. */
    private static boolean holdsText(ContainerEventHandler parent, int depth) {
        for (GuiEventListener child : parent.children()) {
            if (child instanceof EditBox box && !box.getValue().isEmpty()) return true;
            if (child instanceof MultiLineEditBox box && !box.getValue().isEmpty()) return true;
            if (child instanceof RecipeBookComponent<?> book) {
                // What he typed there shows only while the book is open.
                EditBox search = ((RecipeBookSearchAccess) book).aresos$searchBox();
                if (book.isVisible() && search != null && !search.getValue().isEmpty()) return true;
            }
            // A text box can sit in a list or a tab inside the screen: a few levels at most.
            if (child instanceof ContainerEventHandler inner && depth < 8 && holdsText(inner, depth + 1)) return true;
        }
        return false;
    }

    @Override protected void init() {
        // A resize builds the widgets again: what he typed and where he scrolled to stay.
        String typed = search == null ? "" : search.getValue();
        frame = frame();
        search = addRenderableWidget(new EditBox(font, frame.x, frame.boxY, frame.width, BOX_HEIGHT, Component.literal("Search programs")));
        search.setCanLoseFocus(false);
        search.setValue(typed);
        search.setResponder(text -> show(false));
        show(true);
    }

    /** 260 wide, a fifth of the way down, so the hotbar and the ground stay in view; up to nine lines under it. */
    private Frame frame() {
        int boxWidth = Math.min(260, width - 40), x = (width - boxWidth) / 2, y = Math.max(20, height / 5);
        int top = y + BOX_HEIGHT + 4;
        return new Frame(x, y, boxWidth, top, Math.clamp((height - 24 - top) / ROW, 1, 9));
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
                if (at == 0 && mine > 0) built.add(heading("My apps", mine));
                if (at == mine) built.add(heading("Other programs", found.size() - mine));
                var app = found.get(at);
                built.add(new Row(app, AppItems.create(app), at == 0));
            }
        }
        lines = built;
        // The best hit and its heading stand at the top whatever is scrolled (review 1: Enter's program stays in view),
        // where the bar has the room (SearchLines).
        int bestLine = -1;
        for (int at = 0; best != null && bestLine < 0 && at < built.size(); at++)
            if (built.get(at) instanceof Row) bestLine = at;
        view = SearchLines.of(built.size(), bestLine, frame.rows);
        scroll = keepPlace ? Math.clamp(scroll, 0, maxScroll()) : 0;
    }

    private static Heading heading(String name, int count) {
        return new Heading(Component.literal(name).append(Component.literal("  " + count).withStyle(ChatFormatting.GRAY)));
    }

    private int maxScroll() { return view.maxScroll(); }

    private int shownLines() { return view.shown(); }

    /** The line at shown place {@code place}: the pinned ones first, then the rest from where it is scrolled to. */
    private Line shown(int place) { return lines.get(view.line(place, scroll)); }

    /** The top of the shown line {@code place} (0 is the first one shown). */
    private int lineY(int place) { return frame.top + place * ROW; }

    /** The width the lines have: the scroll bar takes its own strip when there is one. */
    private int lineWidth() { return frame.width - (maxScroll() > 0 ? SCROLLER_WIDTH + 2 : 0); }

    private Line lineAt(double x, double y) {
        if (x < frame.x || x >= frame.x + lineWidth()) return null;
        for (int place = 0; place < shownLines(); place++) {
            int top = lineY(place);
            if (y >= top && y < top + ROW) return shown(place);
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
        if (step != 0) { scrollBy(step); return true; }
        return super.keyPressed(event);
    }

    @Override public boolean mouseScrolled(double x, double y, double scrollX, double scrollY) {
        if (scrollY == 0 || maxScroll() == 0) return super.mouseScrolled(x, y, scrollX, scrollY);
        // Three lines for each notch of the wheel, as in the Apps screen.
        scrollBy(scrollY < 0 ? 3 : -3);
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
        // The world stays sharp behind the bar: he is still in it. The subtitles are drawn as under any screen.
        minecraft.gui.hud.extractDeferredSubtitles();
    }

    @Override public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        int shown = shownLines(), listBottom = frame.top + shown * ROW;
        // A dark plate with a thin light rule: just the box with nothing typed, growing downward with the hits.
        int bottom = shown == 0 ? frame.boxY + BOX_HEIGHT : listBottom;
        graphics.fill(frame.x - 5, frame.boxY - 5, frame.x + frame.width + 5, bottom + 5, PLATE);
        graphics.outline(frame.x - 5, frame.boxY - 5, frame.width + 10, bottom + 5 - (frame.boxY - 5), RULE);
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        // The box hides its own hint while it has the keyboard, which here is always.
        if (search.getValue().isEmpty())
            graphics.text(font, HINT, search.getX() + 4, search.getY() + (search.getHeight() - 8) / 2, CommonColors.WHITE);
        int lineWidth = lineWidth();
        Line hovered = lineAt(mouseX, mouseY);
        for (int place = 0; place < shown; place++) {
            Line line = shown(place);
            int y = lineY(place);
            switch (line) {
                case Heading heading -> heading(graphics, heading, frame.x, y, lineWidth);
                case Note note -> graphics.centeredText(font, note.text, frame.x + lineWidth / 2, y + 6, CommonColors.WHITE);
                case Row row -> row(graphics, row, frame.x, y, lineWidth, line == hovered);
            }
        }
        // Beside the lines that scroll, not beside the pinned best hit.
        int scrolling = lineY(view.pinned());
        if (maxScroll() > 0 && listBottom > scrolling)
            scroller(graphics, frame.x + frame.width - SCROLLER_WIDTH, scrolling, listBottom - scrolling);
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

    /** The game's own scroll bar, beside the lines. */
    private void scroller(GuiGraphicsExtractor graphics, int x, int top, int span) {
        int handle = Math.max(8, span * (frame.rows - view.pinned()) / (lines.size() - view.pinned()));
        int travel = (span - handle) * scroll / maxScroll();
        graphics.blitSprite(RenderPipelines.GUI_TEXTURED, SCROLLER_BACKGROUND, x, top, SCROLLER_WIDTH, span);
        graphics.blitSprite(RenderPipelines.GUI_TEXTURED, SCROLLER, x, top + travel, SCROLLER_WIDTH, handle);
    }

    private String clip(String text, int room) {
        if (font.width(text) <= room) return text;
        String ellipsis = CommonComponents.ELLIPSIS.getString();
        return font.plainSubstrByWidth(text, Math.max(0, room - font.width(ellipsis))) + ellipsis;
    }

    // What the client tests read and where they click.

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

    /** How many lines under the pinned best hit are scrolled past. */
    public int scrolled() { return scroll; }

    /** How many lines the bar has room for, and how many of the first ones stay at the top. */
    public int slots() { return frame.rows; }

    public int pinned() { return view.pinned(); }

    /** The middle of a program's line in the screen's pixels, or null while it is not in view. */
    public int[] middleOf(String id) {
        for (int place = 0; place < shownLines(); place++)
            if (shown(place) instanceof Row row && row.app.id().equals(id))
                return new int[] {frame.x + lineWidth() / 2, lineY(place) + ROW / 2};
        return null;
    }
}
