package dev.aresos.test;

import com.google.gson.JsonObject;
import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AppsScreen;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.AresOsMenuScreen;
import dev.aresos.client.HomeCreateScreen;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldSearchScreen;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.client.mixin.RecipeBookSearchAccess;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.AbstractButton;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.ChatScreen;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.AnvilScreen;
import net.minecraft.client.gui.screens.inventory.BookEditScreen;
import net.minecraft.client.gui.screens.inventory.BookSignScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.recipebook.RecipeBookComponent;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.inventory.AnvilMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.WritableBookContent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * Package 53d: the search over the world. Its pictures, the bar the owner chose (board #382) in four states (nothing
 * typed, several hits, no hit, a long list), and what it does: the best hit and its order, Enter, a click, Escape,
 * and {@code open_app} naming the world's screen.
 *
 * <p>Every opening is the helper's {@code shell_search} (Super), through the session's own wiring
 * ({@link ShellFocusClient#register}), and the moments it is ignored: chat open, the bar open already. The programs
 * are made up ("Test Web 1") and their icons are generated.
 */
public final class WorldSearchClientGameTest implements FabricClientGameTest {
    /** His apps in the fixture: two starters of the image and four programs he installed. */
    private static final int MINE = 6;
    private static final int TOOLS = 40;
    private static final List<String> WEB = List.of("test-web-1", "cobweb-test", "test-web-2", "webcam-test", "cobweb-viewer", "test-feeds");

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        Path sockets = null;
        FakeHelper helper = null;
        ShellClient shell = null;
        try {
            Path root = Path.of("world-search-fixtures").toAbsolutePath();
            deleteTree(root);
            Files.createDirectories(root.resolve("icons"));
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            var firstStart = AppsConfig.load(config, true).apps();
            // A Unix socket path is short, so the socket gets a folder of its own under the temp folder.
            sockets = Files.createTempDirectory("a53d");
            helper = new FakeHelper(sockets);
            helper.minor = 2;
            helper.pageSize = 40;
            helper.revision = "world-search";
            // An opened app answers at once, so no launch is still waiting for a window when the test ends.
            helper.launchState = "focused";
            var programs = programs(root.resolve("icons"));
            helper.entries = List.copyOf(programs);
            shell = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3), Duration.ofSeconds(1),
                    Duration.ofMillis(50), Duration.ofMillis(200), Duration.ofMillis(200)));
            var connection = shell;
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(firstStart);
                AppsTestAccess.aresos$startHelper(connection, true);
                // As in the session: shell_search opens the bar.
                ShellFocusClient.register(connection);
            });
            check(shell.awaitCatalogue(Duration.ofSeconds(5)).apps().size() == programs.size(), "The helper's list did not arrive");
            context.waitFor(client -> AresOs.apps().size() == programs.size());
            check(AresOs.apps().stream().filter(AppDefinition::mine).count() == MINE, "The fixture's My apps are "
                    + AresOs.apps().stream().filter(AppDefinition::mine).map(AppDefinition::id).toList());
            String lastPicture = FakeHelper.string(programs.getLast(), "id");
            context.waitFor(client -> AresOs.generatedIcons.contains(lastPicture) && client.gui.overlay() == null, 600);

            // Launches go to the fake helper on every system, never to a real program.
            var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(new LinuxAppLauncher(() -> connection)));
            // The laptop's screen with the game's own scale: 1920 x 1080 at scale 4 is this window at scale 2.
            context.getInput().resizeWindow(960, 540);
            try (var world = context.worldBuilder().adjustSettings(settings ->
                    settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL)).create()) {
                world.getConnection().waitForChunksRender();
                context.runOnClient(client -> client.player.connection.sendCommand("aresos desktop on"));
                // His apps have their short names once the world is a desktop: the rows show them in gold.
                context.waitFor(client -> AresOs.apps().stream().filter(AppDefinition::mine).noneMatch(app -> app.names().isEmpty())
                        && AresOsClient.acceptsAppCommands(client));
                // Noon, as in his flat home, where it always is: the brightest sky the bar has to be read over.
                world.getServer().runOnServer(server -> server.getCommands().performPrefixedCommand(
                        server.createCommandSourceStack().withSuppressedOutput(), "time set 6000"));
                context.runOnClient(client -> { client.gui.hud.getChat().clearMessages(true); client.gui.toastManager().clear(); });
                // The name of the item in his hand stands over the hotbar for two seconds after he gets it.
                context.waitTicks(80);

                pictures(context, helper);
                behaviour(context, helper);
                ignored(context, helper);
                // Review 1, round 1: last, so no earlier picture or check moves.
                bookDraft(context, helper);
                windowFocus(context, helper);
                // Review 2, round 2: last again.
                replacedScreens(context, helper);
                keptScreens(context, helper);
                newHomeDraft(context, helper);
                smallBar(context, helper);
                // Review 3, round 2b: last again.
                hiddenDrafts(context, helper);
            } finally {
                context.runOnClient(client -> {
                    AresOsClient.replaceLauncher(previousLauncher);
                    AresOsClient.FOCUS_RETURN.reset();
                    WorldSearchScreen.windowFocus = Minecraft::isWindowActive;
                });
            }
            AresOs.LOGGER.info("53d world search checks passed: shell_search opens the bar, in four states; nothing is "
                    + "listed until he types; his apps first, then a start of the name or of a word, then by name; Enter "
                    + "opens the framed best hit and a click any hit, both with open_app's screen \"world\", and the bar "
                    + "closes; a blank query and no hit leave Enter without effect; Escape returns to the world, from over "
                    + "the inventory too, which closes first; shell_search leaves chat and an open bar alone; the world "
                    + "keeps moving; it replaces the game menu, AresOS's menu and the empty Apps screen, and leaves a "
                    + "typed Apps search, an anvil with a name, an unlisted screen, the New home choice with its seed, and an "
                    + "inventory with a hidden recipe search, also behind an empty Apps screen");
        } catch (Exception error) {
            throw new RuntimeException(error);
        } finally {
            context.getInput().resizeWindow(854, 480);
            if (shell != null) shell.close();
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(previousShell);
                AppsTestAccess.aresos$setApps(previousApps);
                AresOs.generatedIcons = previousIcons;
            });
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try {
                if (helper != null) helper.close();
                if (sockets != null) deleteTree(sockets);
            } catch (IOException error) {
                AresOs.LOGGER.warn("Could not clear the fake helper's socket folder", error);
            }
        }
    }

    /** The bar in its four states, each checked for what it shows before its picture is taken. */
    private static void pictures(ClientGameTestContext context, FakeHelper helper) {
        String name = "53d-bar";

        search(context, helper, "");
        context.runOnClient(client -> {
            var bar = bar(client);
            check(bar.found().isEmpty() && bar.best() == null && bar.note() == null && bar.headings().isEmpty(),
                    "Nothing typed, and the bar lists " + bar.found());
            check(!client.isPaused(), "The search pauses the world");
        });
        screenshot(context, name + "-1-empty");
        escape(context);

        search(context, helper, "web");
        context.runOnClient(client -> {
            var bar = bar(client);
            check(bar.found().equals(WEB), "\"web\" finds " + bar.found());
            check("test-web-1".equals(bar.best()), "The best hit for \"web\" is " + bar.best());
            check(bar.headings().equals(List.of("My apps  2", "Other programs  4")), "The headings are " + bar.headings());
            for (String id : WEB) check(bar.middleOf(id) != null, id + " is not in view among several hits");
        });
        screenshot(context, name + "-2-several-hits");
        escape(context);

        search(context, helper, "zzz");
        context.runOnClient(client -> {
            var bar = bar(client);
            check(bar.found().isEmpty() && bar.best() == null, "\"zzz\" finds " + bar.found());
            check("No program matches \"zzz\".".equals(bar.note()), "No hit says: " + bar.note());
        });
        screenshot(context, name + "-3-no-hit");
        escape(context);

        search(context, helper, "test");
        context.runOnClient(client -> {
            var bar = bar(client);
            // Every "Test …" program and the two "… Test": his four first, by name.
            check(bar.found().size() == 4 + 1 + TOOLS + 2, "\"test\" finds " + bar.found().size() + " programs");
            check(bar.found().subList(0, 5).equals(List.of("cobweb-test", "test-mail", "test-notes", "test-web-1", "test-feeds")),
                    "\"test\" starts with " + bar.found().subList(0, 5));
            check(bar.middleOf("cobweb-test") != null && bar.middleOf("webcam-test") == null, "The long list is not cut to the bar's room");
        });
        screenshot(context, name + "-4-long-list");
        // The keys move through a long list; the best hit stays the one Enter opens.
        context.getInput().pressKey(InputConstants.KEY_PAGEDOWN);
        context.waitTick();
        context.runOnClient(client -> check(bar(client).scrolled() > 1 && "cobweb-test".equals(bar(client).best()),
                "A page on moved the long list by " + bar(client).scrolled()));
        // The framed best hit stays at the top, in view, while the lines under it scroll (review 1).
        context.runOnClient(client -> check(bar(client).middleOf("cobweb-test") != null && bar(client).middleOf("test-mail") == null,
                "After a page on, the best hit is " + (bar(client).middleOf("cobweb-test") == null ? "out of view" : "in view")
                        + " and the line after it " + (bar(client).middleOf("test-mail") == null ? "scrolled past" : "still in view")));
        context.getInput().pressKey(InputConstants.KEY_PAGEUP);
        context.waitTick();
        context.runOnClient(client -> check(bar(client).scrolled() == 0, "A page back did not come back to the best hit"));
        escape(context);
    }

    /** What Enter, a click and Escape do, and what the helper is asked. */
    private static void behaviour(ClientGameTestContext context, FakeHelper helper) throws InterruptedException {
        // Nothing typed, then nothing found: Enter does nothing and the bar stays.
        search(context, helper, "");
        context.getInput().pressKey(InputConstants.KEY_RETURN);
        context.waitTicks(3);
        context.runOnClient(client -> check(client.gui.screen() instanceof WorldSearchScreen, "Enter with nothing typed closed the bar"));
        context.getInput().typeChars("zzz");
        context.waitTicks(2);
        context.getInput().pressKey(InputConstants.KEY_RETURN);
        context.waitTicks(3);
        context.runOnClient(client -> check(client.gui.screen() instanceof WorldSearchScreen, "Enter with no hit closed the bar"));
        check(helper.received("open_app").isEmpty(), "Enter without a best hit asked the helper: " + helper.received("open_app"));
        escape(context);

        // Enter opens the framed best hit on the world's screen, and he is back in the world.
        search(context, helper, "web");
        context.getInput().pressKey(InputConstants.KEY_RETURN);
        context.waitFor(client -> client.gui.screen() == null);
        FakeHelper.await(() -> helper.received("open_app").size() == 1, "Enter's open_app");
        opened(helper.received("open_app").getLast(), "test-web-1", "world");
        context.runOnClient(client -> AresOsClient.FOCUS_RETURN.reset());

        // A click opens the program under it, his or not, the same way.
        search(context, helper, "web");
        double[] at = context.computeOnClient(client -> {
            int[] middle = bar(client).middleOf("webcam-test");
            double scale = (double) client.getWindow().getScreenWidth() / client.getWindow().getGuiScaledWidth();
            return new double[] {middle[0] * scale, middle[1] * scale};
        });
        context.getInput().setCursorPos(at[0], at[1]);
        context.waitTick();
        context.getInput().pressMouse(0);
        context.waitFor(client -> client.gui.screen() == null);
        FakeHelper.await(() -> helper.received("open_app").size() == 2, "the click's open_app");
        opened(helper.received("open_app").getLast(), "webcam-test", "world");
        context.runOnClient(client -> AresOsClient.FOCUS_RETURN.reset());

        // Only the search names a screen: the hotbar's and the Apps screen's way leaves the place to the helper.
        context.runOnClient(client -> AresOsClient.launch("terminal"));
        FakeHelper.await(() -> helper.received("open_app").size() == 3, "a plain launch's open_app");
        opened(helper.received("open_app").getLast(), "terminal", null);
        context.runOnClient(client -> AresOsClient.FOCUS_RETURN.reset());

        // Over the inventory: it closes the normal way, and Escape goes to the world, not back to the inventory.
        context.getInput().pressKey(options -> options.keyInventory);
        context.waitForScreen(InventoryScreen.class);
        search(context, helper, "web");
        escape(context);
        context.waitTicks(3);
        context.runOnClient(client -> check(client.gui.screen() == null && client.player.containerMenu == client.player.inventoryMenu,
                "Escape after a search over the inventory did not end in the world"));
    }

    /** Moments shell_search must not take: chat he types in, and the bar itself with what he typed. */
    private static void ignored(ClientGameTestContext context, FakeHelper helper) {
        context.getInput().pressKey(options -> options.keyChat);
        context.waitForScreen(ChatScreen.class);
        context.getInput().typeChars("hello");
        context.waitTicks(2);
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> check(client.gui.screen() instanceof ChatScreen, "shell_search took the chat away: " + client.gui.screen()));
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitFor(client -> client.gui.screen() == null);

        search(context, helper, "web");
        var open = context.computeOnClient(client -> client.gui.screen());
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> check(client.gui.screen() == open && bar(client).found().equals(WEB),
                "A second shell_search replaced the open bar or what he typed: " + client.gui.screen()));
        escape(context);
    }

    /**
     * Review 1, blocking 2: a book being signed. Its pages are written, Sign is clicked, a title typed, and Tab moves the
     * focus to "Sign and Close", off the title box. Super must leave the signing screen, its title and its pages alone:
     * entering it saved nothing, so replacing it would lose the draft.
     */
    private static void bookDraft(ClientGameTestContext context, FakeHelper helper) {
        // A book of his own on the client: it is never signed or saved here.
        var editor = context.computeOnClient(client -> {
            var book = new BookEditScreen(client.player, new ItemStack(Items.WRITABLE_BOOK), InteractionHand.MAIN_HAND,
                    WritableBookContent.EMPTY);
            client.gui.setScreen(book);
            return book;
        });
        context.waitForScreen(BookEditScreen.class);
        context.getInput().typeChars("Dear diary");
        context.waitTicks(2);
        click(context, Component.translatable("book.signButton").getString());
        context.waitForScreen(BookSignScreen.class);
        context.getInput().typeChars("Draft");
        context.waitTicks(2);
        // Tab, as often as it takes (the screen lists Cancel after the title box), to "Sign and Close".
        String finalize = Component.translatable("book.finalizeButton").getString();
        for (int press = 0; press < 4 && !context.computeOnClient(client -> focusedButton(client.gui.screen(), finalize)); press++) {
            context.getInput().pressKey(InputConstants.KEY_TAB);
            context.waitTicks(2);
        }
        var signing = context.computeOnClient(client -> {
            var screen = client.gui.screen();
            check(focusedButton(screen, finalize), "Tab did not move the focus to Sign and Close: " + screen.getFocused());
            check("Draft".equals(title(screen)), "The title box says " + title(screen));
            return screen;
        });
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> {
            check(client.gui.screen() == signing, "shell_search replaced the book being signed: " + client.gui.screen());
            check("Draft".equals(title(signing)), "The book's title is now " + title(signing));
        });
        // Cancel goes back to the same editor with its pages: the draft is all there.
        click(context, CommonComponents.GUI_CANCEL.getString());
        context.waitFor(client -> client.gui.screen() == editor);
        context.runOnClient(client -> client.gui.setScreen(null));
        context.waitFor(client -> client.gui.screen() == null);
    }

    /**
     * Review 1, blocking 1: the bar opens only while the game's window has the keyboard. A shell_search that comes
     * before the focus waits for it and opens once it is there; after half a second without it, nothing opens.
     */
    private static void windowFocus(ClientGameTestContext context, FakeHelper helper) {
        context.runOnClient(client -> check(client.isWindowActive(), "The test client's window does not have the keyboard,"
                + " so every opening above went past the focus rule"));
        context.runOnClient(client -> WorldSearchScreen.windowFocus = game -> false);
        superPressed(helper);
        context.waitFor(client -> WorldSearchScreen.waitingForFocus());
        context.waitTicks(3);
        context.runOnClient(client -> check(client.gui.screen() == null, "The bar opened without the window's focus"));
        context.runOnClient(client -> WorldSearchScreen.windowFocus = Minecraft::isWindowActive);
        context.waitForScreen(WorldSearchScreen.class);
        escape(context);

        context.runOnClient(client -> WorldSearchScreen.windowFocus = game -> false);
        superPressed(helper);
        context.waitFor(client -> WorldSearchScreen.waitingForFocus());
        context.waitFor(client -> !WorldSearchScreen.waitingForFocus());
        context.runOnClient(client -> WorldSearchScreen.windowFocus = Minecraft::isWindowActive);
        context.waitTicks(5);
        context.runOnClient(client -> check(client.gui.screen() == null,
                "The bar opened after the wait for the window's focus ran out: " + client.gui.screen()));
    }

    /** Review 2: the screens on Super's list, each replaced by the search (the world and the inventory are above). */
    private static void replacedScreens(ClientGameTestContext context, FakeHelper helper) {
        // The game's own menu: this test world is a desktop, not his home, where Esc opens AresOS's menu instead.
        context.runOnClient(client -> client.gui.setScreen(new PauseScreen(true)));
        context.waitForScreen(PauseScreen.class);
        search(context, helper, "");
        escape(context);

        context.runOnClient(client -> client.gui.setScreen(new AresOsMenuScreen()));
        context.waitForScreen(AresOsMenuScreen.class);
        search(context, helper, "");
        escape(context);

        // The Apps screen with nothing typed in its search box.
        context.runOnClient(client -> client.gui.setScreen(new AppsScreen(null)));
        context.waitForScreen(AppsScreen.class);
        context.waitTicks(2);
        search(context, helper, "");
        escape(context);
    }

    /** Review 2: whatever is not on the list stays, and a listed screen stays while a text box in it holds text. */
    private static void keptScreens(ClientGameTestContext context, FakeHelper helper) {
        // The Apps screen with a search typed.
        context.runOnClient(client -> client.gui.setScreen(new AppsScreen(null)));
        context.waitForScreen(AppsScreen.class);
        context.getInput().typeChars("web");
        context.waitTicks(2);
        kept(context, helper, "web", "the Apps screen with a search typed");

        // A container he types in: an anvil with a name in its box. Client-side only, its menu never reaches the server.
        context.runOnClient(client -> {
            var inventory = client.player.getInventory();
            client.gui.setScreen(new AnvilScreen(new AnvilMenu(0, inventory), inventory, Component.literal("Anvil")));
        });
        context.waitForScreen(AnvilScreen.class);
        context.runOnClient(client -> client.gui.screen().children().stream().filter(EditBox.class::isInstance)
                .map(EditBox.class::cast).findFirst().orElseThrow(() -> new AssertionError("The anvil has no name box")).setValue("Draft"));
        kept(context, helper, "Draft", "an anvil with a name typed");

        // A screen nobody listed, with no text box at all.
        context.runOnClient(client -> client.gui.setScreen(new Screen(Component.literal("Unlisted")) { }));
        context.waitTicks(2);
        kept(context, helper, null, "a screen that is not on the list");
    }

    /** Super with this screen open: it must still be the same screen, with the same text, ten ticks later. */
    private static void kept(ClientGameTestContext context, FakeHelper helper, String text, String what) {
        var open = context.computeOnClient(client -> client.gui.screen());
        check(open != null && !(open instanceof WorldSearchScreen), what + " is not open: " + open);
        check(java.util.Objects.equals(text, title(open)), what + " says " + title(open) + " before Super");
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> {
            check(client.gui.screen() == open, "shell_search replaced " + what + ": " + client.gui.screen());
            check(java.util.Objects.equals(text, title(open)), what + " now says " + title(open));
            check(!WorldSearchScreen.waitingForFocus(), "shell_search waits to replace " + what);
            client.gui.setScreen(null);
        });
        context.waitFor(client -> client.gui.screen() == null);
    }

    /**
     * Review 2, blocking 2: the New home choice. Nether is chosen, a seed of his own typed, and Tab moves the focus to
     * a button, off the seed box. Super must leave the choice, its seed and its settings alone.
     */
    private static void newHomeDraft(ClientGameTestContext context, FakeHelper helper) {
        var chooser = context.computeOnClient(client -> {
            var screen = new HomeCreateScreen(null, (game, choice, plan) -> { throw new AssertionError("Create was pressed"); });
            client.gui.setScreen(screen);
            return screen;
        });
        context.waitForScreen(HomeCreateScreen.class);
        click(context, "Home: Flat");
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(hasButton(chooser, "Home: Nether"), "The choice did not switch to the Nether home");
            // The seed box, as a click on it would: what he types next goes there.
            chooser.setFocused(chooser.children().stream().filter(EditBox.class::isInstance).findFirst()
                    .orElseThrow(() -> new AssertionError("The Nether home has no seed box")));
        });
        context.getInput().typeChars("123");
        context.waitTicks(2);
        for (int press = 0; press < 12 && !context.computeOnClient(client -> chooser.getFocused() instanceof AbstractButton); press++) {
            context.getInput().pressKey(InputConstants.KEY_TAB);
            context.waitTicks(2);
        }
        context.runOnClient(client -> {
            check(chooser.getFocused() instanceof AbstractButton, "Tab did not move the focus to a button: " + chooser.getFocused());
            check("49123".equals(title(chooser)), "The seed box says " + title(chooser));
            check(hasButton(chooser, "Placeholder hub: OFF"), "A seed of his own did not turn the placeholder off");
        });
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> {
            check(client.gui.screen() == chooser, "shell_search replaced the New home choice: " + client.gui.screen());
            check("49123".equals(title(chooser)), "The seed is now " + title(chooser));
            check(hasButton(chooser, "Home: Nether") && hasButton(chooser, "Placeholder hub: OFF"), "The home's settings changed");
            check(chooser.getFocused() instanceof AbstractButton, "The focus moved: " + chooser.getFocused());
            client.gui.setScreen(null);
        });
        context.waitFor(client -> client.gui.screen() == null);
    }

    /**
     * Review 2, finding 6: a bar with room for two lines pins nothing, so every hit can be scrolled to. The rule itself
     * is held by SearchLinesTest; this is the screen following it, in a window as low as the game still lays out.
     */
    private static void smallBar(ClientGameTestContext context, FakeHelper helper) {
        context.getInput().resizeWindow(480, 120);
        context.waitTicks(5);
        search(context, helper, "test");
        int slots = context.computeOnClient(client -> bar(client).slots());
        if (slots >= 4) {
            // Not a failure of the bar: the rule is held by SearchLinesTest, and the report says which of the two ran.
            AresOs.LOGGER.warn("53d: the test window could not be made low enough for a small bar ({} slots); the two-slot "
                    + "layout was checked by SearchLinesTest only", slots);
        } else {
            context.runOnClient(client -> {
                var bar = bar(client);
                check(bar.pinned() == 0, "A bar with " + bar.slots() + " slots pins " + bar.pinned() + " lines");
                check("cobweb-test".equals(bar.best()) && bar.middleOf("cobweb-test") != null, "The best hit is not shown first");
            });
            // A line on at a time, to the end: every hit comes into view, and the best hit scrolls away with the rest.
            var seen = new java.util.HashSet<String>();
            int last = -1;
            for (int step = 0; step < 100; step++) {
                seen.addAll(context.computeOnClient(client -> bar(client).found().stream()
                        .filter(id -> bar(client).middleOf(id) != null).toList()));
                int at = context.computeOnClient(client -> bar(client).scrolled());
                if (at == last) break;
                last = at;
                context.getInput().pressKey(InputConstants.KEY_DOWN);
                context.waitTick();
            }
            context.runOnClient(client -> {
                var bar = bar(client);
                check(seen.containsAll(bar.found()), "In a bar with " + bar.slots() + " slots only " + seen.size() + " of "
                        + bar.found().size() + " hits can be scrolled to");
                check(bar.middleOf("cobweb-test") == null && "cobweb-test".equals(bar.best()), "The small bar still pins the best hit");
            });
            AresOs.LOGGER.info("53d: a bar with {} slots pins nothing and scrolls to all {} hits", slots, seen.size());
        }
        escape(context);
        context.getInput().resizeWindow(960, 540);
        context.waitTicks(5);
    }

    /**
     * Review 3: text that is kept out of sight. A recipe-book search typed and the book hidden again stays in the
     * inventory screen, so Super must leave that inventory alone, and also the empty Apps screen opened from it.
     */
    private static void hiddenDrafts(ClientGameTestContext context, FakeHelper helper) {
        // First the other side: an empty Apps screen opened from an inventory with nothing typed is replaced, and the
        // inventory closes the normal way with it.
        context.getInput().pressKey(options -> options.keyInventory);
        context.waitForScreen(InventoryScreen.class);
        context.runOnClient(client -> client.gui.setScreen(new AppsScreen(client.gui.screen())));
        context.waitForScreen(AppsScreen.class);
        context.waitTicks(2);
        search(context, helper, "");
        escape(context);
        context.runOnClient(client -> check(client.player.containerMenu == client.player.inventoryMenu,
                "The inventory behind the Apps screen was not closed"));

        context.getInput().pressKey(options -> options.keyInventory);
        context.waitForScreen(InventoryScreen.class);
        var inventory = context.computeOnClient(client -> {
            var screen = client.gui.screen();
            var book = recipeBook(screen);
            if (!book.isVisible()) book.toggleVisibility();
            recipeQuery(book).setValue("stick");
            book.toggleVisibility();
            check(!book.isVisible(), "The recipe book did not hide");
            check("stick".equals(recipeQuery(book).getValue()), "The hidden recipe book forgot its search: " + recipeQuery(book).getValue());
            return screen;
        });
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> {
            check(client.gui.screen() == inventory, "shell_search replaced the inventory with a hidden recipe search: " + client.gui.screen());
            check("stick".equals(recipeQuery(recipeBook(inventory)).getValue()), "The recipe search is gone");
            check(!WorldSearchScreen.waitingForFocus(), "shell_search waits to replace that inventory");
            client.gui.setScreen(new AppsScreen(inventory));
        });
        context.waitForScreen(AppsScreen.class);
        context.waitTicks(2);
        var apps = context.computeOnClient(client -> client.gui.screen());
        check(title(apps) != null && title(apps).isEmpty(), "The Apps screen's search is not empty: " + title(apps));
        superPressed(helper);
        context.waitTicks(10);
        context.runOnClient(client -> {
            check(client.gui.screen() == apps, "shell_search replaced the Apps screen over an inventory with a hidden recipe search: "
                    + client.gui.screen());
            check("stick".equals(recipeQuery(recipeBook(inventory)).getValue()), "The recipe search behind the Apps screen is gone");
            client.player.closeContainer();
        });
        context.waitFor(client -> client.gui.screen() == null);
    }

    private static RecipeBookComponent<?> recipeBook(Screen screen) {
        return screen.children().stream().filter(child -> child instanceof RecipeBookComponent<?>)
                .map(child -> (RecipeBookComponent<?>) child).findFirst()
                .orElseThrow(() -> new AssertionError("No recipe book in " + screen));
    }

    private static EditBox recipeQuery(RecipeBookComponent<?> book) {
        EditBox box = ((RecipeBookSearchAccess) book).aresos$searchBox();
        if (box == null) throw new AssertionError("The recipe book has no search box yet");
        return box;
    }

    private static boolean hasButton(Screen screen, String label) {
        return screen.children().stream().anyMatch(child -> child instanceof AbstractButton button
                && button.getMessage().getString().equals(label));
    }

    /** Clicks the button that says {@code label} on the open screen, as he would with the pointer. */
    private static void click(ClientGameTestContext context, String label) {
        double[] at = context.computeOnClient(client -> {
            var button = client.gui.screen().children().stream()
                    .filter(child -> child instanceof AbstractWidget widget && widget.getMessage().getString().equals(label))
                    .map(AbstractWidget.class::cast).findFirst()
                    .orElseThrow(() -> new AssertionError("No \"" + label + "\" button on " + client.gui.screen()));
            double scale = (double) client.getWindow().getScreenWidth() / client.getWindow().getGuiScaledWidth();
            return new double[] {(button.getX() + button.getWidth() / 2.0) * scale, (button.getY() + button.getHeight() / 2.0) * scale};
        });
        context.getInput().setCursorPos(at[0], at[1]);
        context.waitTick();
        context.getInput().pressMouse(0);
        context.waitTick();
    }

    private static boolean focusedButton(Screen screen, String label) {
        return screen.getFocused() instanceof AbstractButton button && button.getMessage().getString().equals(label);
    }

    private static String title(Screen screen) {
        return screen.children().stream().filter(EditBox.class::isInstance).map(box -> ((EditBox) box).getValue())
                .findFirst().orElse(null);
    }

    private static void superPressed(FakeHelper helper) {
        try {
            helper.event("shell_search", Map.of());
        } catch (IOException error) {
            throw new AssertionError("The fake helper could not send shell_search", error);
        }
    }

    private static void opened(JsonObject request, String app, String screen) {
        check(app.equals(FakeHelper.string(request, "app_id")), "The helper was asked to open " + request);
        check(screen == null ? !request.has("screen") : screen.equals(FakeHelper.string(request, "screen")),
                "open_app names the wrong screen: " + request);
    }

    /** Super: the helper's shell_search opens the bar, and he types. The pointer waits in a corner, so no line is under it. */
    private static void search(ClientGameTestContext context, FakeHelper helper, String query) {
        superPressed(helper);
        context.waitForScreen(WorldSearchScreen.class);
        // Only now, with the pointer free: in the world a moved pointer would turn his head.
        context.getInput().setCursorPos(1, 1);
        context.waitTicks(2);
        if (!query.isEmpty()) context.getInput().typeChars(query);
        context.waitTicks(2);
    }

    private static void escape(ClientGameTestContext context) {
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitFor(client -> client.gui.screen() == null);
    }

    private static WorldSearchScreen bar(Minecraft client) {
        if (client.gui.screen() instanceof WorldSearchScreen bar) return bar;
        throw new AssertionError("The search is not open: " + client.gui.screen());
    }

    /**
     * Made-up programs: two starters of the image and four he installed are his; the rest came with the system.
     * "web" finds a start of a word and the inside of one among both; "test" finds 47.
     */
    private static List<JsonObject> programs(Path icons) throws IOException {
        var list = new ArrayList<JsonObject>();
        add(list, icons, "terminal", "Terminal", "image", "Command Line", List.of("shell"));
        add(list, icons, "notepad", "Notepad", "image", "Text Editor", List.of("text"));
        add(list, icons, "test-web-1", "Test Web 1", "user", "Web Browser", List.of("internet"));
        add(list, icons, "cobweb-test", "Cobweb Test", "user", "Puzzle Game", List.of());
        add(list, icons, "test-mail", "Test Mail", "user", "Mail Client", List.of("email"));
        add(list, icons, "test-notes", "Test Notes", "flatpak-user", "Handwritten Notes", List.of());
        add(list, icons, "test-web-2", "Test Web 2", "system", "Web Browser", List.of("internet"));
        add(list, icons, "webcam-test", "Webcam Test", "system", "Camera", List.of());
        add(list, icons, "cobweb-viewer", "Cobweb Viewer", "flatpak-system", "Picture Viewer", List.of());
        // Found by "web" only through what kind of program the system says it is.
        add(list, icons, "test-feeds", "Test Feeds", "system", "Web Feed Reader", List.of("news"));
        String[] kinds = {"Calculator", "File Manager", "Archiving Tool", "Disk Usage", "System Monitor"};
        for (int number = 1; number <= TOOLS; number++)
            add(list, icons, "test-tool-" + number, "Test Tool " + number, "system", kinds[number % kinds.length], List.of());
        return list;
    }

    private static void add(List<JsonObject> list, Path icons, String id, String name, String source, String kind,
                            List<String> keywords) throws IOException {
        list.add(MyAppsClientGameTest.program(icons, list.size(), id, name, source, kind, keywords, List.of("Utility"), true));
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.worldSearchReviewDir"))));
    }

    private static void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        try (var paths = Files.walk(root)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
