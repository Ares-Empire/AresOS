package dev.aresos.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.platform.InputConstants;
import com.mojang.brigadier.suggestion.Suggestion;
import dev.aresos.AresOs;
import dev.aresos.client.AppsScreen;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.shell.FakeHelper;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.ChatMessagesTestAccess;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.lwjgl.glfw.GLFW;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Package 34, My apps, in the real client with a helper that lists 150 programs: day one, the Apps screen (search,
 * add, remove, pick up), the three commands, a program that joins later, and the helper's pictures as pixel icons.
 * The helper is the unit tests' fake one on a real socket; every picture is drawn here.
 */
public final class MyAppsClientGameTest implements FabricClientGameTest {
    private static final Set<String> DAY_ONE = Set.of("browser", "terminal", "notepad", "lunar-client", "discord");
    private static final int LEFT = 0, RIGHT = 1;

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        var previousShell = AresOs.shell();
        String previousConfig = System.getProperty("aresos.appsConfig");
        Path sockets = null;
        FakeHelper helper = null;
        ShellClient shell = null;
        try {
            Path root = Path.of("my-apps-fixtures").toAbsolutePath();
            deleteTree(root);
            Files.createDirectories(root.resolve("icons"));
            Path config = root.resolve("apps.json");
            System.setProperty("aresos.appsConfig", config.toString());
            // No apps file yet: the first start on AresOS writes its one default, the pinned Notepad.
            var firstStart = AppsConfig.load(config, true).apps();
            // A Unix socket path is short, so the socket gets a folder of its own under the temp folder.
            sockets = Files.createTempDirectory("a34");
            helper = new FakeHelper(sockets);
            helper.minor = 1;
            helper.pageSize = 40;
            helper.revision = "day-one";
            var programs = programs(root.resolve("icons"));
            check(programs.size() == 150, "The fixture lists " + programs.size() + " programs, not 150");
            helper.entries = List.copyOf(programs.subList(0, 149));
            shell = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3), Duration.ofSeconds(1),
                    Duration.ofMillis(50), Duration.ofMillis(200), Duration.ofMillis(200)));
            var connection = shell;
            // The game's own helper connection comes from the session's environment, which a test run does not
            // have. This one gets the wiring AresOs gives its own: every complete list goes to mergeHelperApps.
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(firstStart);
                AppsTestAccess.aresos$startHelper(connection, true);
            });
            var initial = shell.awaitCatalogue(Duration.ofSeconds(5));
            check(initial.detailed() && initial.apps().size() == 149, "Startup lost the initial listing's details");
            helper.entries = List.copyOf(programs);
            helper.revision = "startup-refresh";
            helper.event("apps_changed", Map.of("revision", "startup-refresh"));

            // Day one, before any world: the first complete list, in four pages, sets the baseline and My apps.
            context.waitFor(client -> AresOs.apps().size() == 150);
            check(mine().equals(DAY_ONE), "Day one made these his: " + mine());
            var saved = AppsConfig.load(config);
            check(saved.baseline() != null, "Day one wrote no baseline");
            check(saved.apps().stream().filter(AppDefinition::mine).map(AppDefinition::id).collect(Collectors.toSet()).equals(DAY_ONE),
                    "The apps file does not hold day one's My apps");
            // A caller returning late from the startup wait gets the old list, but production never reapplies it.
            check(shell.awaitCatalogue(Duration.ofSeconds(1)) == initial && AresOs.apps().size() == 150,
                    "An older startup snapshot replaced a later callback");
            check(saved.apps().size() == 150, "The startup refresh did not reach the apps file");
            check(helper.received("list_apps").size() == 8, "The startup lists did not each come in four pages: "
                    + helper.received("list_apps").size());
            // The helper's pictures become the icon pack, and the game loads it without being asked.
            context.waitFor(client -> AresOs.generatedIcons.contains("discord") && client.gui.overlay() == null, 600);
            check(!AresOs.generatedIcons.contains("kcalc"), "A program without a picture got a pixel icon");

            // The laptop's screen with the game's own scale: 1920 x 1080 at scale 4 is this window at scale 2.
            context.getInput().resizeWindow(960, 540);
            try (var world = context.worldBuilder().adjustSettings(settings ->
                    settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL)).create()) {
                world.getConnection().waitForChunksRender();
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    for (String command : List.of("aresos app add ", "aresos app remove ", "aresos give "))
                        check(completions(player, command).isEmpty(), "Normal-world completion exposed My apps");
                });
                context.runOnClient(client -> client.player.connection.sendCommand("aresos desktop on"));
                context.waitFor(client -> items(client).size() == 5);
                context.runOnClient(client -> {
                    check(items(client).keySet().equals(DAY_ONE), "Day one's inventory holds " + items(client).keySet());
                    check(items(client).get("notepad") == 0, "The pinned Notepad is not in the first hotbar slot");
                    check(items(client).entrySet().stream().allMatch(item -> item.getKey().equals("notepad") || item.getValue() >= 9),
                            "Day one put an app he did not pin in the hotbar: " + items(client));
                    check(AresOs.id("apps/discord").equals(stack(client, "discord").get(DataComponents.ITEM_MODEL)),
                            "Discord's item does not show the helper's picture");
                    check(chat(client).stream().noneMatch(line -> line.contains("joined My apps")),
                            "Day one announced programs: " + chat(client));
                });
                context.getInput().pressKey(options -> options.keyInventory);
                context.waitForScreen(InventoryScreen.class);
                context.waitTicks(5);
                context.runOnClient(client -> {
                    var screen = client.gui.screen();
                    var button = net.fabricmc.fabric.api.client.screen.v1.Screens.getButtons(screen).stream()
                            .filter(widget -> widget.getMessage().getString().equals("Apps…")).findFirst().orElseThrow();
                    check(button.getWidth() == 70 && button.getHeight() == 20 && button.getX() == screen.width / 2 - 35
                            && button.getY() + button.getHeight() == (screen.height - 166) / 2 - 4,
                            "The Apps button is not centred four pixels above the inventory panel");
                });
                screenshot(context, "34-day-one-inventory");

                appsScreen(context, world);
                commands(context, world, config);
                laterProgram(context, world, helper, programs, root.resolve("icons"));

                // Q on an app's item: nothing leaves the hotbar and nothing lies on the ground.
                context.getInput().pressKey(InputConstants.KEY_1);
                context.waitTick();
                context.getInput().pressKey(options -> options.keyDrop);
                world.getConnection().waitForServerboundPackets();
                context.waitTicks(3);
                context.runOnClient(client -> check(Integer.valueOf(0).equals(items(client).get("notepad")),
                        "Q took Notepad out of the hotbar"));
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check("notepad".equals(player.getInventory().getItem(0).get(AppItems.APP_ID)), "Q took Notepad from the server's hotbar");
                    check(player.level().getEntitiesOfClass(ItemEntity.class, player.getBoundingBox().inflate(16)).isEmpty(),
                            "Q put an app's item on the ground");
                });
                // A full inventory unlocked a recipe on the way; its toast is not part of this picture.
                context.runOnClient(client -> client.gui.toastManager().clear());
                context.waitTicks(5);
                screenshot(context, "34-hotbar-pixel-icons");
            }
            AresOs.LOGGER.info("34 client checks passed: day one with 150 programs in four pages and five items; Apps screen "
                    + "search, click and Enter add, right-click remove, pick up and pin; app add, remove, list and their "
                    + "completion; a full inventory; a later program's chat line and pixel icon; Q keeps the item");
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

    /** E, "Apps…": the list, the search, an add by click and by Enter, a remove, and picking up an item to pin it. */
    private static void appsScreen(ClientGameTestContext context, TestSingleplayerContext world) {
        context.clickScreenButton("Apps…");
        context.waitForScreen(AppsScreen.class);
        context.waitTicks(3);
        context.runOnClient(client -> {
            var mine = rows(client).stream().filter(AppsScreen.Row::inMyApps).map(row -> row.app().name()).toList();
            var all = rows(client).stream().filter(row -> !row.inMyApps()).map(row -> row.app().name()).toList();
            check(mine.equals(List.of("Chrome", "Discord", "Lunar Client", "Notepad", "Terminal")), "My apps shows " + mine);
            check(all.size() == 150, "All programs shows " + all.size() + " rows");
            check(all.equals(all.stream().sorted(Comparator.comparing(name -> name.toLowerCase(Locale.ROOT))).toList()),
                    "All programs is not in order of name");
            check(list(client).children().indexOf(rows(client).getFirst()) == 1, "My apps does not start under its heading");
            check(client.gui.screen().getFocused() == search(client), "The search box does not have the keyboard");
        });
        screenshot(context, "34-apps-150-programs");

        // The keyboard scrolls too: Down and Up by a row, Page Down and Page Up by a screenful.
        context.getInput().pressKey(GLFW.GLFW_KEY_DOWN);
        context.runOnClient(client -> check(list(client).scrollAmount() == 20, "Down scrolled to " + list(client).scrollAmount()));
        context.getInput().pressKey(GLFW.GLFW_KEY_PAGE_DOWN);
        context.runOnClient(client -> check(list(client).scrollAmount() > 60 && list(client).scrollAmount() < list(client).getHeight(),
                "Page Down scrolled to " + list(client).scrollAmount() + " in a list " + list(client).getHeight() + " high"));
        context.getInput().pressKey(GLFW.GLFW_KEY_PAGE_UP);
        context.getInput().pressKey(GLFW.GLFW_KEY_UP);
        context.runOnClient(client -> check(list(client).scrollAmount() == 0, "Page Up and Up scrolled to " + list(client).scrollAmount()));

        // The wheel reaches the last of the 150 programs.
        double[] middle = context.computeOnClient(client -> window(client, list(client).getX() + list(client).getWidth() / 2.0,
                list(client).getY() + list(client).getHeight() / 2.0));
        context.getInput().setCursorPos(middle[0], middle[1]);
        context.getInput().scroll(-100);
        context.waitTicks(2);
        context.runOnClient(client -> {
            var last = rows(client).getLast();
            check(last.app().name().equals("Xournal++"), "The last program is " + last.app().name());
            check(last.getY() >= list(client).getY() && last.getY() + last.getHeight() <= list(client).getBottom(),
                    "Scrolling did not bring the last program into view");
        });
        screenshot(context, "34-apps-scrolled-to-the-end");

        // The search looks in names and keywords, and starts the list at its top again.
        context.getInput().typeChars("pdf");
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(shown(client).equals(List.of("Okular", "PDF Arranger", "Xournal++")), "\"pdf\" finds " + shown(client));
            check(list(client).scrollAmount() == 0, "A new search did not go back to the top");
        });
        screenshot(context, "34-apps-search-pdf");
        // Enter is for the only match; with three it does nothing.
        context.getInput().pressKey(InputConstants.KEY_RETURN);
        world.getConnection().waitForServerboundPackets();
        context.waitTicks(2);
        check(mine().equals(DAY_ONE), "Enter with three matches changed My apps: " + mine());

        // In a short list, adding its last result inserts My apps above it and puts Okular under the old pointer.
        var doubleAt = context.computeOnClient(client -> {
            check(list(client).children().size() * 20 <= list(client).getHeight(), "Fixture: the search list can scroll");
            var row = rows(client).stream().filter(r -> r.app().id().equals("xournal")).findFirst().orElseThrow();
            return new double[] {row.getX() + row.getWidth() / 2.0, row.getY() + row.getHeight() / 2.0};
        });
        context.runOnClient(client -> {
            var event = new MouseButtonEvent(doubleAt[0], doubleAt[1], new MouseButtonInfo(LEFT, 0));
            client.gui.screen().mouseClicked(event, false);
            client.gui.screen().mouseReleased(event);
        });
        context.waitFor(client -> AresOs.app("xournal").mine() && rows(client).stream().anyMatch(r -> r.inMyApps() && r.app().id().equals("xournal")));
        context.runOnClient(client -> {
            check(list(client).scrollAmount() == 0 && list(client).children().size() * 20 <= list(client).getHeight(),
                    "Fixture: the changed list should still be too short to scroll");
            check(rows(client).stream().anyMatch(r -> r.app().id().equals("okular") && r.isMouseOver(doubleAt[0], doubleAt[1])),
                    "Fixture: reflow did not put the neighbour under the pointer");
            var event = new MouseButtonEvent(doubleAt[0], doubleAt[1], new MouseButtonInfo(LEFT, 0));
            client.gui.screen().mouseClicked(event, true);
            client.gui.screen().mouseReleased(event);
        });
        world.getConnection().waitForServerboundPackets();
        context.waitTicks(2);
        check(!AresOs.app("okular").mine() && !AresOs.app("pdf-arranger").mine(), "A double-click added the neighbour");
        clickRow(context, "xournal", true, RIGHT);
        context.waitFor(client -> !AresOs.app("xournal").mine() && !items(client).containsKey("xournal"));
        context.waitTicks(2);

        // A left click on a program that is not his adds it; the screen stays open and shows it.
        clickRow(context, "okular", false, LEFT);
        context.waitFor(client -> AresOs.app("okular").mine() && items(client).containsKey("okular"));
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(client.gui.screen() instanceof AppsScreen, "Adding a program closed the Apps screen");
            check(items(client).get("okular") >= 9, "The added program's item went to the hotbar");
            check(rows(client).stream().filter(AppsScreen.Row::inMyApps).map(row -> row.app().id()).toList().equals(List.of("okular")),
                    "The added program is not shown under My apps");
            check(status(client).contains("Added Okular to My apps."), "The screen does not say what happened: " + status(client));
            check(client.gui.screen().getFocused() == search(client), "The click took the keyboard away from the search box");
        });
        screenshot(context, "34-apps-after-add");

        // Typing still goes to the search box; Enter adds the only match, found by its kind ("Archiving Tool").
        for (int i = 0; i < 3; i++) context.getInput().pressKey(GLFW.GLFW_KEY_BACKSPACE);
        context.getInput().typeChars("archiv");
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(search(client).getValue().equals("archiv"), "Typing after a click reached \"" + search(client).getValue() + "\"");
            check(shown(client).equals(List.of("Ark")), "\"archiv\" finds " + shown(client));
        });
        context.getInput().pressKey(InputConstants.KEY_RETURN);
        context.waitFor(client -> AresOs.app("ark").mine() && items(client).containsKey("ark"));
        context.runOnClient(client -> {
            check(client.gui.screen() instanceof AppsScreen, "Enter on a program that was not his closed the Apps screen");
            check(search(client).getHighlighted().equals("archiv"), "The finished search is not selected for the next one");
        });

        // The whole list again; a right click on one of his takes it out of My apps and its item out of the inventory.
        context.getInput().pressKey(GLFW.GLFW_KEY_BACKSPACE);
        context.waitTicks(2);
        context.runOnClient(client -> check(search(client).getValue().isEmpty() && rows(client).size() == 7 + 150,
                "Clearing the search shows " + rows(client).size() + " rows"));
        clickRow(context, "okular", true, RIGHT);
        context.waitFor(client -> !AresOs.app("okular").mine() && !items(client).containsKey("okular"));
        context.waitTicks(2);
        context.runOnClient(client -> {
            check(client.gui.screen() instanceof AppsScreen, "Removing an app closed the Apps screen");
            check(rows(client).stream().filter(AppsScreen.Row::inMyApps).noneMatch(row -> row.app().id().equals("okular")),
                    "The removed app is still shown under My apps");
            check(rows(client).stream().anyMatch(row -> !row.inMyApps() && row.app().id().equals("okular")),
                    "The removed app left All programs");
            check(status(client).contains("Removed Okular from My apps."), "The screen does not say what happened: " + status(client));
        });
        world.getServer().runOnServer(server -> {
            var inventory = world.getConnection().getServerPlayer().getInventory();
            for (int slot = 0; slot < inventory.getContainerSize(); slot++)
                check(!"okular".equals(inventory.getItem(slot).get(AppItems.APP_ID)), "The removed app's item is still in slot " + slot);
        });
        screenshot(context, "34-apps-after-remove");

        // A right click on a program that is not his does nothing.
        context.getInput().typeChars("pdf");
        context.waitTicks(2);
        clickRow(context, "pdf-arranger", false, RIGHT);
        world.getConnection().waitForServerboundPackets();
        context.waitTicks(3);
        check(!AresOs.app("pdf-arranger").mine(), "A right click added a program");

        // A left click on one of his picks up its item, as before; dropped in the hotbar it is pinned.
        for (int i = 0; i < 3; i++) context.getInput().pressKey(GLFW.GLFW_KEY_BACKSPACE);
        context.waitTicks(2);
        clickRow(context, "ark", true, LEFT);
        context.waitForScreen(InventoryScreen.class);
        context.waitFor(client -> "ark".equals(client.player.inventoryMenu.getCarried().get(AppItems.APP_ID)));
        clickSlot(context, 38);
        world.getConnection().waitForServerboundPackets();
        context.waitFor(client -> AresOs.app("ark").pinned());
        context.runOnClient(client -> check(items(client).get("ark") == 2, "Ark was not put in the third hotbar slot"));
        // Escape closes: first the Apps screen back to the inventory, then the inventory.
        context.clickScreenButton("Apps…");
        context.waitForScreen(AppsScreen.class);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(InventoryScreen.class);
        context.getInput().pressKey(InputConstants.KEY_ESCAPE);
        context.waitForScreen(null);
    }

    /** /aresos app add, remove and list as the host, their completion, and an add with no free slot. */
    private static void commands(ClientGameTestContext context, TestSingleplayerContext world, Path config) throws IOException {
        var his = Set.of("browser", "terminal", "notepad", "lunar-client", "discord", "ark");
        check(mine().equals(his), "Before the commands My apps is " + mine());
        // Picking through Apps must not manufacture a second item while the first is in the 2x2 grid.
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var inventory = player.getInventory();
            player.inventoryMenu.getCraftSlots().setItem(0, inventory.getItem(0));
            inventory.setItem(0, ItemStack.EMPTY);
        });
        context.runOnClient(client -> net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking.send(
                new dev.aresos.item.TakeAppPayload("notepad")));
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(player.inventoryMenu.getCarried().isEmpty(), "Apps picked up a copy while crafting was occupied");
            check("notepad".equals(player.inventoryMenu.getCraftSlots().getItem(0).get(AppItems.APP_ID)), "Apps touched crafting");
            player.getInventory().setItem(0, player.inventoryMenu.getCraftSlots().removeItemNoUpdate(0));
        });
        command(context, "aresos give notepad");
        command(context, "aresos give notepad");
        world.getConnection().waitForServerboundPackets();
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            check(ModeInventoryFixtures.totalItems(player, AppItems.create(AresOs.app("notepad"))) == 1,
                    "Repeated /aresos give copied the existing item");
        });
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            var cookie = net.minecraft.server.network.CommonListenerCookie.createInitial(
                    new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "Guest"), false);
            var guest = new net.minecraft.server.level.ServerPlayer(server, player.level(), cookie.gameProfile(), cookie.clientInformation());
            for (String command : List.of("aresos app add ", "aresos app remove ", "aresos give ")) {
                check(completions(guest, command).isEmpty(), "Guest completion exposed My apps");
                var dispatcher = server.getCommands().getDispatcher();
                check(dispatcher.getCompletionSuggestions(dispatcher.parse(command, server.createCommandSourceStack())).join()
                        .getList().isEmpty(), "Console completion exposed My apps");
            }
            var add = completions(player, "aresos app add ");
            var remove = completions(player, "aresos app remove ");
            check(remove.equals(his), "\"app remove\" offers " + remove);
            check(add.size() == 150 - his.size() && add.contains("okular") && add.stream().noneMatch(his::contains),
                    "\"app add\" offers " + add.size() + " programs, some of them his: " + add.stream().filter(his::contains).toList());
            check(completions(player, "aresos app add ok").equals(Set.of("okular")), "\"app add ok\" offers "
                    + completions(player, "aresos app add ok"));
        });

        command(context, "aresos app list");
        waitForChat(context, "My apps: 6");
        context.runOnClient(client -> {
            for (String line : List.of("Ark (ark), in the hotbar", "Chrome (browser)", "Discord (discord)",
                    "Lunar Client (lunar-client)", "Notepad (notepad), in the hotbar", "Terminal (terminal)"))
                check(chat(client).contains(line), "\"app list\" did not say: " + line);
        });

        command(context, "aresos app add okular");
        waitForChat(context, "Added Okular to My apps.");
        context.waitFor(client -> items(client).containsKey("okular"));
        check(AppsConfig.load(config).apps().stream().anyMatch(app -> app.id().equals("okular") && app.mine()),
                "\"app add\" did not reach the apps file");
        command(context, "aresos app add okular");
        waitForChat(context, "Okular is already one of your apps.");
        command(context, "aresos app remove okular");
        waitForChat(context, "Removed Okular from My apps. It stays in All programs.");
        context.waitFor(client -> !items(client).containsKey("okular"));
        check(AppsConfig.load(config).apps().stream().anyMatch(app -> app.id().equals("okular") && !app.mine()),
                "\"app remove\" did not reach the apps file");
        command(context, "aresos app add no-such-program");
        waitForChat(context, "Unknown AresOS app");

        // No free slot: the program is his all the same, has no item, and the chat says so.
        var filled = new ArrayList<Integer>();
        world.getServer().runOnServer(server -> {
            var inventory = world.getConnection().getServerPlayer().getInventory();
            for (int slot = 9; slot < 36; slot++) if (inventory.getItem(slot).isEmpty()) {
                inventory.setItem(slot, new ItemStack(Items.BEDROCK, 3));
                filled.add(slot);
            }
        });
        command(context, "aresos app add okular");
        waitForChat(context, "No free inventory slot: Okular has no item for now.");
        check(AresOs.app("okular").mine(), "A full inventory kept the program out of My apps");
        context.runOnClient(client -> check(!items(client).containsKey("okular"), "A full inventory still got the item"));
        world.getServer().runOnServer(server -> {
            var inventory = world.getConnection().getServerPlayer().getInventory();
            for (int slot : filled) {
                check(inventory.getItem(slot).is(Items.BEDROCK) && inventory.getItem(slot).getCount() == 3,
                        "Adding with a full inventory changed slot " + slot);
                inventory.setItem(slot, ItemStack.EMPTY);
            }
        });
        command(context, "aresos app remove okular");
        waitForChat(context, "Removed Okular from My apps. It stays in All programs.");
        context.runOnClient(client -> client.gui.hud.getChat().clearMessages(true));
    }

    /**
     * After the baseline the system lists two more programs: the one he installed joins My apps with one chat line,
     * its item arrives, and when its picture has been made and loaded the item shows it. The one that came with the
     * system is only listed.
     */
    private static void laterProgram(ClientGameTestContext context, TestSingleplayerContext world, FakeHelper helper,
                                     List<JsonObject> programs, Path icons) throws IOException {
        var later = new ArrayList<>(programs);
        later.add(program(icons, 150, "spotify", "Spotify", "flatpak-user", "Music Streaming", List.of("music"), List.of("AudioVideo"), true));
        later.add(program(icons, 151, "print-queue", "Print Queue", "system", null, List.of(), List.of("System"), true));
        for (int i = 1; i <= 6; i++) later.add(program(icons, 151 + i, "new-tool-" + i, "New Tool " + i,
                "user", null, List.of(), List.of("Utility"), false));
        helper.entries = List.copyOf(later);
        helper.revision = "later";
        helper.event("apps_changed", Map.of("revision", "later"));
        waitForChat(context, "Spotify is new and joined My apps.");
        for (int i = 1; i <= 6; i++) waitForChat(context, "New Tool " + i + " is new and joined My apps.");
        context.waitFor(client -> items(client).containsKey("spotify"));
        check(AresOs.apps().size() == 158 && !AresOs.app("print-queue").mine(), "The program that came with the system joined My apps");
        context.runOnClient(client -> {
            check(chat(client).stream().filter(line -> line.contains("joined My apps")).count() == 7,
                    "Every new app must be named once: " + chat(client));
            check(chat(client).stream().noneMatch(line -> line.contains("more new programs")), "New app names were truncated");
        });
        // The picture's way from the helper's path to the hotbar ends here: the pack is made again, the game
        // loads it, and the item that was already in the inventory gets the new look.
        context.waitFor(client -> AresOs.id("apps/spotify").equals(stack(client, "spotify").get(DataComponents.ITEM_MODEL))
                && client.gui.overlay() == null, 600);
        context.runOnClient(client -> {
            check(client.getResourceManager().getResource(AresOs.id("textures/item/apps/spotify.png")).isPresent(),
                    "The game did not load the later program's picture");
            check(AresOs.id("apps/ark").equals(stack(client, "ark").get(DataComponents.ITEM_MODEL)), "Ark lost its picture");
        });
        world.getConnection().waitForServerboundPackets();
    }

    // The fixture: the three starters, two programs he installed, and 145 that came with the system.

    private static List<JsonObject> programs(Path icons) throws IOException {
        var list = new ArrayList<JsonObject>();
        add(list, icons, "terminal", "Terminal", "image", "Command Line", List.of("shell", "prompt"), List.of("System"), true);
        add(list, icons, "notepad", "Notepad", "image", "Text Editor", List.of("text"), List.of("Utility"), true);
        add(list, icons, "browser", "Chrome", "image", "Web Browser", List.of("web", "internet"), List.of("Network"), true);
        add(list, icons, "lunar-client", "Lunar Client", "user", "Game Launcher", List.of(), List.of("Game"), true);
        add(list, icons, "discord", "Discord", "flatpak-user", "Internet Messenger", List.of("chat", "voice"), List.of("Network"), true);
        String[][] named = {
                {"ark", "Ark", "Archiving Tool", "zip tar", "Utility"},
                {"dolphin", "Dolphin", "File Manager", "files folders", "System"},
                {"kate", "Kate", "Advanced Text Editor", "text code", "Development"},
                {"okular", "Okular", "Document Viewer", "pdf epub", "Office"},
                {"gwenview", "Gwenview", "Image Viewer", "photo picture", "Graphics"},
                {"spectacle", "Spectacle", "Screenshot Capture Utility", "screenshot", "Utility"},
                {"kcalc", "KCalc", "Scientific Calculator", "calculator", "Utility"},
                {"elisa", "Elisa", "Music Player", "music", "AudioVideo"},
                {"haruna", "Haruna", "Media Player", "video movie", "AudioVideo"},
                {"discover", "Discover", "Software Center", "install update", "System"},
                {"system-settings", "System Settings", null, "preferences", "Settings"},
                {"info-center", "Info Center", null, "hardware", "System"},
                {"kwrite", "KWrite", "Text Editor", "text", "Utility"},
                {"filelight", "Filelight", "Disk Usage Statistics", "space", "System"},
                {"partition-manager", "KDE Partition Manager", "Partition Editor", "drive", "System"},
                {"system-monitor", "System Monitor", null, "process cpu memory", "System"},
                {"kfind", "KFind", "Find Files/Folders", "search", "Utility"},
                {"kcharselect", "KCharSelect", "Character Selector", "symbols", "Utility"},
                {"kcolorchooser", "KColorChooser", "Color Chooser", "palette", "Graphics"},
                {"kleopatra", "Kleopatra", "Certificate Manager and Unified Crypto GUI", "encryption keys", "Utility"},
                {"kwalletmanager", "KWalletManager", "Wallet Management Tool", "passwords", "System"},
                {"krdc", "KRDC", "Remote Desktop Client", "vnc rdp", "Network"},
                {"krfb", "Krfb", "Desktop Sharing", "vnc", "Network"},
                {"kde-connect", "KDE Connect", "Device Synchronization", "phone", "Network"},
                {"emoji-selector", "Emoji Selector", null, "smiley", "Utility"},
                {"welcome-center", "Welcome Center", null, "tour", "System"},
                {"help-center", "Help Center", null, "manual", "System"},
                {"steam", "Steam", "Game Store and Launcher", "games", "Game"},
                {"lutris", "Lutris", "Game Launcher", "games wine", "Game"},
                {"bazzite-portal", "Bazzite Portal", null, "setup", "System"},
                {"waydroid", "Waydroid", "Android Container", "android", "System"},
                {"input-remapper", "Input Remapper", null, "keyboard mouse", "Settings"},
                {"mission-center", "Mission Center", "Resource Monitor", "cpu gpu", "System"},
                {"flatseal", "Flatseal", "Flatpak Permissions", "sandbox", "System"},
                {"warehouse", "Warehouse", "Flatpak Manager", "flatpak", "System"},
                {"firefox", "Firefox", "Web Browser", "web internet", "Network"},
                {"thunderbird", "Thunderbird", "Mail Client", "email", "Network"},
                {"pdf-arranger", "PDF Arranger", "Document Page Sorter", "merge split", "Office"},
                {"xournal", "Xournal++", "Handwritten Notes", "pdf annotate", "Office"},
                {"proton-tool", "Proton Experimental Compatibility Tool Settings", null, "wine", "Game"},
        };
        for (String[] row : named)
            add(list, icons, row[0], row[1], list.size() % 4 == 0 ? "flatpak-system" : "system", row[2],
                    List.of(row[3].split(" ")), List.of(row[4]), !row[0].equals("kcalc") && list.size() % 5 != 2);
        String[] things = {"Photo", "Audio", "Video", "Disk", "Font", "Color", "Clock", "Map", "Note", "Task", "Code",
                "Data", "Print", "Scan", "Backup"};
        String[] kinds = {"Viewer", "Editor", "Manager", "Monitor", "Studio", "Tools", "Settings"};
        String[] categories = {"Graphics", "Utility", "System", "Network", "Development", "Game", "Settings"};
        for (String thing : things) for (int kind = 0; kind < kinds.length; kind++) {
            String name = thing + " " + kinds[kind];
            add(list, icons, name.toLowerCase(Locale.ROOT).replace(' ', '-'), name, "system", null, List.of(),
                    List.of(categories[kind]), list.size() % 3 != 0);
        }
        return list;
    }

    private static void add(List<JsonObject> list, Path icons, String id, String name, String source, String kind,
                            List<String> keywords, List<String> categories, boolean picture) throws IOException {
        list.add(program(icons, list.size(), id, name, source, kind, keywords, categories, picture));
    }

    private static JsonObject program(Path icons, int number, String id, String name, String source, String kind,
                                      List<String> keywords, List<String> categories, boolean picture) throws IOException {
        var entry = FakeHelper.entry(id, name, null, source);
        if (kind != null) entry.addProperty("generic_name", kind);
        entry.add("keywords", strings(keywords));
        entry.add("categories", strings(categories));
        if (picture) {
            Path file = icons.resolve(id + ".png");
            ImageIO.write(picture(number), "png", file.toFile());
            entry.addProperty("icon", file.toString());
        }
        return entry;
    }

    private static JsonArray strings(List<String> values) {
        var array = new JsonArray();
        values.forEach(array::add);
        return array;
    }

    /** A made-up icon: a rounded tile in the program's own colour with one of five plain shapes on it. */
    private static BufferedImage picture(int number) {
        var image = new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB);
        var graphics = image.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        float hue = (number * 0.381966f) % 1f;
        graphics.setColor(Color.getHSBColor(hue, 0.75f, 0.55f));
        graphics.fillRoundRect(2, 2, 60, 60, 18, 18);
        graphics.setColor(Color.getHSBColor(hue, 0.65f, 0.85f));
        graphics.fillRoundRect(6, 6, 52, 52, 14, 14);
        graphics.setColor(number % 2 == 0 ? Color.WHITE : new Color(0x202030));
        switch (number % 5) {
            case 0 -> graphics.fillOval(18, 18, 28, 28);
            case 1 -> graphics.fillRect(18, 18, 28, 28);
            case 2 -> graphics.fillPolygon(new int[] {32, 48, 32, 16}, new int[] {14, 32, 50, 32}, 4);
            case 3 -> graphics.fillPolygon(new int[] {32, 50, 14}, new int[] {16, 46, 46}, 3);
            default -> { graphics.fillRect(16, 20, 32, 8); graphics.fillRect(16, 36, 32, 8); }
        }
        graphics.dispose();
        return image;
    }

    // What the client shows.

    private static Set<String> mine() {
        return AresOs.apps().stream().filter(AppDefinition::mine).map(AppDefinition::id).collect(Collectors.toSet());
    }

    /** The app items in the client's inventory: app ID to slot. */
    private static Map<String, Integer> items(Minecraft client) {
        var items = new java.util.TreeMap<String, Integer>();
        var inventory = client.player.getInventory();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            var stack = inventory.getItem(slot);
            if (stack.is(AppItems.APP)) check(items.put(stack.get(AppItems.APP_ID), slot) == null,
                    "Two items of " + stack.get(AppItems.APP_ID));
        }
        return items;
    }

    private static ItemStack stack(Minecraft client, String id) {
        Integer slot = items(client).get(id);
        return slot == null ? ItemStack.EMPTY : client.player.getInventory().getItem(slot);
    }

    private static List<String> chat(Minecraft client) {
        return ((ChatMessagesTestAccess) client.gui.hud.getChat()).aresos$messages().stream()
                .map(message -> message.content().getString()).toList();
    }

    private static void waitForChat(ClientGameTestContext context, String line) {
        context.waitFor(client -> chat(client).contains(line));
    }

    /** Sends a command from an empty chat, so the lines waited for afterwards are this command's. */
    private static void command(ClientGameTestContext context, String command) {
        context.runOnClient(client -> {
            check(chat(client).stream().noneMatch(line -> line.contains("joined My apps")), "A program was announced: " + chat(client));
            client.gui.hud.getChat().clearMessages(true);
            client.player.connection.sendCommand(command);
        });
    }

    private static Set<String> completions(net.minecraft.server.level.ServerPlayer player, String typed) {
        var dispatcher = player.level().getServer().getCommands().getDispatcher();
        return dispatcher.getCompletionSuggestions(dispatcher.parse(typed, player.createCommandSourceStack())).join()
                .getList().stream().map(Suggestion::getText).collect(Collectors.toSet());
    }

    private static AppsScreen.ProgramList list(Minecraft client) {
        return client.gui.screen().children().stream().filter(AppsScreen.ProgramList.class::isInstance)
                .map(AppsScreen.ProgramList.class::cast).findFirst().orElseThrow(() -> new AssertionError("No program list on screen"));
    }

    private static List<AppsScreen.Row> rows(Minecraft client) {
        return list(client).children().stream().filter(AppsScreen.Row.class::isInstance).map(AppsScreen.Row.class::cast).toList();
    }

    /** The names under "All programs", in the order shown. */
    private static List<String> shown(Minecraft client) {
        return rows(client).stream().filter(row -> !row.inMyApps()).map(row -> row.app().name()).toList();
    }

    private static EditBox search(Minecraft client) {
        return client.gui.screen().children().stream().filter(EditBox.class::isInstance).map(EditBox.class::cast)
                .findFirst().orElseThrow(() -> new AssertionError("No search box on screen"));
    }

    /** Every line of text the screen shows outside its list: the title and the line above Done. */
    private static String status(Minecraft client) {
        return client.gui.screen().children().stream().filter(StringWidget.class::isInstance)
                .map(widget -> ((StringWidget) widget).getMessage().getString()).collect(Collectors.joining("\n"));
    }

    /** A real click: the pointer moves onto the row, one frame passes so the list knows the row under it, then the button. */
    private static void clickRow(ClientGameTestContext context, String id, boolean inMyApps, int button) {
        double[] at = context.computeOnClient(client -> {
            var row = rows(client).stream().filter(candidate -> candidate.inMyApps() == inMyApps && candidate.app().id().equals(id))
                    .findFirst().orElseThrow(() -> new AssertionError("No row of " + id + " under " + (inMyApps ? "My apps" : "All programs")));
            check(row.getY() >= list(client).getY() && row.getY() + row.getHeight() <= list(client).getBottom(),
                    "The row of " + id + " is not in view");
            return window(client, row.getX() + row.getWidth() / 2.0, row.getY() + row.getHeight() / 2.0);
        });
        context.getInput().setCursorPos(at[0], at[1]);
        context.waitTick();
        context.getInput().pressMouse(button);
    }

    /** A point of the screen, as the pointer's position in the window. */
    private static double[] window(Minecraft client, double x, double y) {
        double scale = (double) client.getWindow().getScreenWidth() / client.getWindow().getGuiScaledWidth();
        return new double[] {x * scale, y * scale};
    }

    private static void clickSlot(ClientGameTestContext context, int slotId) {
        context.runOnClient(client -> {
            var screen = (InventoryScreen) client.gui.screen();
            var slot = client.player.inventoryMenu.getSlot(slotId);
            var event = new MouseButtonEvent((screen.width - 176) / 2.0 + slot.x + 8, (screen.height - 166) / 2.0 + slot.y + 8,
                    new MouseButtonInfo(0, 0));
            screen.mouseClicked(event, false);
            screen.mouseDragged(event, 0, 0);
            screen.mouseReleased(event);
        });
        context.waitTick();
    }

    private static void screenshot(ClientGameTestContext context, String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.myAppsReviewDir"))));
    }

    private static void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        try (var paths = Files.walk(root)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }

    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
