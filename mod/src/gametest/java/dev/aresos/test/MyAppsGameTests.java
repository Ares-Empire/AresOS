package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppInventory;
import dev.aresos.item.AppItems;
import dev.aresos.item.MyAppsGame;
import dev.aresos.mode.ModeInventories;
import dev.aresos.world.DesktopWorld;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundSetPlayerInventoryPacket;
import net.minecraft.network.protocol.game.ClientboundSystemChatPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static dev.aresos.test.ModeInventoryFixtures.*;

/**
 * My apps in the game (brief 34, B4): the inventory holds his apps and nothing else. Each test runs from start to
 * finish inside one tick and puts the app list back, and the tests have a batch of their own: they change the
 * app list of the whole game, which the other tests read.
 */
public final class MyAppsGameTests {
    private static final String BATCH = "aresos-test:my_apps";

    /** A player in Live in an AresOS world with three programs: "mine" and the pinned "pinned" are his, "other" is not. */
    private record Fixture(ServerPlayer player, EmbeddedChannel channel, Path config, String previousConfig) implements AutoCloseable {
        static Fixture open(GameTestHelper helper) {
            var server = helper.getLevel().getServer();
            String previous = System.getProperty("aresos.appsConfig");
            Path config;
            try {
                config = Files.createTempDirectory("aresos-my-apps").resolve("apps.json");
                AppsConfig.save(config, List.of(
                        new AppDefinition("mine", "Mine", List.of("never-run"), "minecraft:book", false).withMine(true),
                        new AppDefinition("pinned", "Pinned", List.of("never-run"), "minecraft:compass", true),
                        new AppDefinition("other", "Other", List.of("never-run"), "minecraft:paper", false)));
                System.setProperty("aresos.appsConfig", config.toString());
                // An edit that changes nothing: the game reads the file the property names now.
                AresOs.saveMine(Map.of());
            } catch (IOException error) { throw new UncheckedIOException(error); }
            DesktopWorld.setEnabled(server, true);
            var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "MyAppsTest"), false);
            var player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
            var connection = new Connection(PacketFlow.SERVERBOUND);
            var channel = new EmbeddedChannel(connection);
            server.getPlayerList().placeNewPlayer(connection, player, cookie);
            registerStateReceiver(player);
            player.setGameMode(GameType.SURVIVAL);
            acknowledge(player);
            player.getInventory().clearContent();
            player.getInventory().setSelectedSlot(0);
            AppInventory.populate(player);
            return new Fixture(player, channel, config, previous);
        }

        @Override public void close() {
            player.level().getServer().getPlayerList().remove(player);
            if (previousConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", previousConfig);
            try { AresOs.saveMine(Map.of()); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }

        long sent(int slot, String app) {
            return channel.outboundMessages().stream().filter(packet -> packet instanceof ClientboundSetPlayerInventoryPacket update
                    && update.slot() == slot && app.equals(id(update.contents()))).count();
        }

        long said(String text) {
            return channel.outboundMessages().stream().filter(packet -> packet instanceof ClientboundSystemChatPacket chat
                    && chat.content().getString().contains(text)).count();
        }

        boolean savedAsMine(String id) {
            try { return AppsConfig.load(config).apps().stream().filter(app -> app.id().equals(id)).findFirst().orElseThrow().mine(); }
            catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    private static String add(ServerPlayer player, String id) {
        try { return MyAppsGame.add(player, id); }
        catch (IOException error) { throw new UncheckedIOException(error); }
    }

    private static String remove(ServerPlayer player, String id) {
        try { return MyAppsGame.remove(player, id); }
        catch (IOException error) { throw new UncheckedIOException(error); }
    }

    private static ServerPlayer reconnect(ServerPlayer player) {
        var server = player.level().getServer();
        server.getPlayerList().remove(player);
        var cookie = CommonListenerCookie.createInitial(player.getGameProfile(), false);
        var returning = new ServerPlayer(server, player.level(), cookie.gameProfile(), cookie.clientInformation());
        var saved = server.getPlayerList().loadPlayerData(player.nameAndId()).orElseThrow();
        returning.load(net.minecraft.world.level.storage.TagValueInput.create(
                net.minecraft.util.ProblemReporter.DISCARDING, returning.registryAccess(), saved));
        check(items(returning, "mine") == 2, "Fixture: the saved inventories did not load before login");
        // This environment has no home. Run the same pre-login restore that NetherHome.arrive calls in a home world.
        check(ModeInventories.of(returning).enterLiveBeforeLogin(returning), "Pre-login Live restore failed");
        var connection = new Connection(PacketFlow.SERVERBOUND);
        new EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, returning, cookie);
        registerStateReceiver(returning);
        return returning;
    }

    @GameTest(environment = BATCH)
    public void everyLoginRemovesStaleAppsFromBothInventories(GameTestHelper helper) {
        // Both ordinary Live login and a login that restores Live from a saved Build session.
        for (boolean quitInBuild : List.of(false, true)) try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            check(switchAndAcknowledge(player, GameType.CREATIVE), "Switch to Build failed");
            player.getInventory().setItem(12, AppItems.create(AresOs.app("mine")));
            player.getInventory().setItem(13, new ItemStack(Items.DIAMOND, 7));
            if (!quitInBuild) check(switchAndAcknowledge(player, GameType.SURVIVAL), "Switch to Live failed");
            // Save the removal while unsafe, then leave before reconciliation can run.
            player.inventoryMenu.setCarried(new ItemStack(Items.STICK));
            remove(player, "mine");
            check(items(player, "mine") == 2, "Fixture: deferred removal ran before logout");
            player.inventoryMenu.setCarried(ItemStack.EMPTY);
            var returning = reconnect(player);
            try {
                check(ModeInventories.of(returning).restoredForLogin() == quitInBuild, "Wrong login path");
                MyAppsGame.tick(returning.level().getServer());
                check(items(returning, "mine") == 0, "Login left a removed app in one of the inventories");
                check(switchAndAcknowledge(returning, GameType.CREATIVE), "Return to Build failed");
                check(returning.getInventory().getItem(13).is(Items.DIAMOND)
                        && returning.getInventory().getItem(13).getCount() == 7, "Reconciliation touched an ordinary item");
            } finally { returning.level().getServer().getPlayerList().remove(returning); }
        }
        helper.succeed();
    }

    private static String id(ItemStack stack) { return stack.is(AppItems.APP) ? stack.get(AppItems.APP_ID) : null; }

    /** Everywhere an item can be: the inventory he holds, the saved one, and the ground. */
    private static int items(ServerPlayer player, String app) { return totalItems(player, AppItems.create(AresOs.app(app))); }

    private static long appsOnTheGround(ServerPlayer player) {
        long count = 0;
        for (var entity : player.level().getAllEntities())
            if (entity instanceof ItemEntity drop && !drop.isRemoved() && drop.getItem().is(AppItems.APP)) count++;
        return count;
    }

    private static void fillFreeSlots(ServerPlayer player) {
        var inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++)
            if (inventory.getItem(slot).isEmpty()) inventory.setItem(slot, new ItemStack(Items.PAPER, slot + 1));
    }

    private static Inventory without(Inventory inventory, int slot) {
        var items = new ArrayList<>(inventory.items());
        items.set(slot, ItemStack.EMPTY);
        return new Inventory(List.copyOf(items), inventory.selected());
    }

    @GameTest(environment = BATCH)
    public void addingPutsTheItemInTheFirstFreeSlotAndRemovingTakesItOutOfBothInventories(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var inventory = player.getInventory();
            var server = player.level().getServer();
            check("pinned".equals(id(inventory.getItem(0))) && "mine".equals(id(inventory.getItem(9))),
                    "His apps are not where a fresh inventory puts them");
            check(items(player, "other") == 0, "A program that is not his has an item");

            inventory.setItem(10, new ItemStack(Items.DIAMOND, 7));
            String said = add(player, "other");
            check(said.equals("Added Other to My apps."), "Add said: " + said);
            check("other".equals(id(inventory.getItem(11))) && items(player, "other") == 1,
                    "The new app's item is not in the first free slot beside the hotbar");
            check(inventory.getItem(10).is(Items.DIAMOND) && inventory.getItem(10).getCount() == 7 && inventory.getItem(1).isEmpty(),
                    "Adding an app moved another item or used the hotbar");
            check(AresOs.app("other").mine() && fixture.savedAsMine("other"), "The added app was not saved as his");
            check(add(player, "other").equals("Other is already one of your apps.") && items(player, "other") == 1,
                    "Adding twice made a second item");

            // The same app's item also lies in his Build inventory, beside something of his own.
            check(switchAndAcknowledge(player, GameType.CREATIVE), "Switch to Build failed");
            inventory.setItem(4, new ItemStack(Items.QUARTZ_BLOCK, 5));
            var buildWithoutApp = capturePersisted(player);
            inventory.setItem(3, AppItems.create(AresOs.app("other")));
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Switch to Live failed");
            check(items(player, "other") == 2, "Fixture: the app's item should be in both inventories");

            var live = capture(player);
            said = remove(player, "other");
            check(said.equals("Removed Other from My apps. It stays in All programs."), "Remove said: " + said);
            check(!AresOs.app("other").mine() && !fixture.savedAsMine("other"), "The removed app is still saved as his");
            assertExact(player, without(live, 11), "Removing an app from the Live inventory");
            assertInactive(player, buildWithoutApp, "Removing an app from the saved Build inventory");
            check(items(player, "other") == 0 && appsOnTheGround(player) == 0, "The removed app still has an item somewhere");
            check(remove(player, "other").equals("Other is not one of your apps."), "Removing twice");

            // Added while he builds: nothing goes into the Build inventory; the item is there when he is back.
            check(switchAndAcknowledge(player, GameType.CREATIVE), "Switch to Build failed");
            var build = capture(player);
            said = add(player, "other");
            check(said.equals("Added Other to My apps. Its item comes in Live mode."), "Add in Build said: " + said);
            MyAppsGame.tick(server);
            assertExact(player, build, "Adding an app in Build mode");
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Switch to Live failed");
            MyAppsGame.tick(server);
            assertExact(player, live, "The item of an app added in Build mode, back in Live");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void aRemovalThatCannotBeDoneNowIsDoneAtTheNextSafeMoment(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var inventory = player.getInventory();
            var server = player.level().getServer();
            inventory.setItem(20, new ItemStack(Items.DIAMOND, 7));
            var withApp = capture(player);

            // A container is open.
            player.openMenu(new SimpleMenuProvider((id, own, p) -> ChestMenu.threeRows(id, own, new SimpleContainer(27)),
                    Component.literal("My apps fixture")));
            check(player.containerMenu != player.inventoryMenu, "Fixture: the chest did not open");
            remove(player, "mine");
            MyAppsGame.tick(server);
            check(!AresOs.app("mine").mine(), "The removal was not saved");
            assertExact(player, withApp, "A removal while a container is open");
            player.closeContainer();
            MyAppsGame.tick(server);
            assertExact(player, without(withApp, 9), "The removal after the container closed");

            // An item on the cursor.
            add(player, "mine");
            assertExact(player, withApp, "Adding the app again");
            player.inventoryMenu.setCarried(new ItemStack(Items.STICK, 3));
            remove(player, "mine");
            MyAppsGame.tick(server);
            assertExact(player, withApp, "A removal with an item on the cursor");
            check(player.inventoryMenu.getCarried().is(Items.STICK) && player.inventoryMenu.getCarried().getCount() == 3,
                    "A removal touched the cursor");
            player.inventoryMenu.setCarried(ItemStack.EMPTY);
            MyAppsGame.tick(server);
            assertExact(player, without(withApp, 9), "The removal after the cursor was empty");

            // A mode switch the client has not confirmed yet: the Live inventory is the saved one now.
            add(player, "mine");
            var savedLive = capturePersisted(player);
            var modes = ModeInventories.of(player);
            check(modes.switchTo(player, GameType.CREATIVE, true) && modes.pending(), "Fixture: the switch is not pending");
            var build = capture(player);
            remove(player, "mine");
            MyAppsGame.tick(server);
            MyAppsGame.tick(server);
            check(modes.pending(), "Fixture: the switch ended by itself");
            assertExact(player, build, "A removal during a pending mode switch (the inventory he holds)");
            assertInactive(player, savedLive, "A removal during a pending mode switch (the saved Live inventory)");
            check(items(player, "mine") == 1, "The item was touched during a pending mode switch");
            acknowledge(player);
            MyAppsGame.tick(server);
            var expected = new ArrayList<>(savedLive.items());
            expected.set(9, savedLive.items().get(30));
            assertInactive(player, new PersistedInventory(List.copyOf(expected), savedLive.selected()),
                    "The removal after the mode switch finished");
            check(items(player, "mine") == 0, "The removed app still has an item");
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Switch to Live failed");
            assertExact(player, without(withApp, 9), "Back in Live after the removal");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void laterReconciliationNeverMovesAnExistingPin(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var inventory = player.getInventory();
            inventory.setItem(10, inventory.getItem(0));
            inventory.setItem(0, ItemStack.EMPTY);
            // A saved pin may have landed outside a previously full hotbar. A later free slot is not a pin action.
            inventory.getItem(10).set(net.minecraft.core.component.DataComponents.ITEM_MODEL,
                    net.minecraft.resources.Identifier.withDefaultNamespace("paper"));
            add(player, "other");
            check("pinned".equals(id(inventory.getItem(10))) && inventory.getItem(0).isEmpty(),
                    "An unrelated add moved a pinned item into the hotbar");
            check(net.minecraft.resources.Identifier.withDefaultNamespace("compass").equals(
                    inventory.getItem(10).get(net.minecraft.core.component.DataComponents.ITEM_MODEL)),
                    "Reconciliation did not refresh the existing item's look");
            remove(player, "other");
            MyAppsGame.changed();
            MyAppsGame.tick(player.level().getServer());
            check("pinned".equals(id(inventory.getItem(10))) && inventory.getItem(0).isEmpty(),
                    "A removal or icon refresh moved a pin");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void aFullInventoryLeavesTheAppWithoutAnItemAndSaysSoOnce(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var server = player.level().getServer();
            fillFreeSlots(player);
            var full = capture(player);
            check(add(player, "other").equals("Added Other to My apps."), "Add with a full inventory");
            assertExact(player, full, "Adding an app to a full inventory");
            check(AresOs.app("other").mine() && fixture.savedAsMine("other") && items(player, "other") == 0
                    && appsOnTheGround(player) == 0, "A full inventory: the app must be his and have no item");
            check(fixture.said("No free inventory slot: Other has no item for now.") == 1, "Nobody said the app has no item");
            // Another change later does not say it again.
            MyAppsGame.changed();
            MyAppsGame.tick(server);
            check(fixture.said("No free inventory slot") == 1, "The missing item was announced twice");
            assertExact(player, full, "A later tidy-up of a full inventory");
            // A slot becomes free: no catalogue change, just the next safe tick.
            player.getInventory().setItem(20, ItemStack.EMPTY);
            MyAppsGame.tick(server);
            check("other".equals(id(player.getInventory().getItem(20))) && items(player, "other") == 1,
                    "The item did not arrive once a slot was free");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void aReturnedCursorItemWaitsForRoomAndForAPendingSwitch(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var server = player.level().getServer();
            var inventory = player.getInventory();
            var cursor = inventory.removeItemNoUpdate(9);
            fillFreeSlots(player);
            var full = capture(player);
            AppInventory.giveBack(player, cursor);
            MyAppsGame.tick(server);
            assertExact(player, full, "Returning a cursor item over a full inventory");
            inventory.setItem(20, ItemStack.EMPTY);
            MyAppsGame.tick(server);
            check("mine".equals(id(inventory.getItem(20))) && items(player, "mine") == 1,
                    "The returned cursor item did not arrive after a slot was freed");

            cursor = inventory.removeItemNoUpdate(20);
            var modes = ModeInventories.of(player);
            check(modes.switchTo(player, GameType.CREATIVE, true) && modes.pending(), "Fixture: switch is not pending");
            var build = capture(player);
            AppInventory.giveBack(player, cursor);
            MyAppsGame.tick(server);
            assertExact(player, build, "giveBack during a pending switch");
            check(items(player, "mine") == 0, "giveBack edited an inventory during a pending switch");
            acknowledge(player);
            MyAppsGame.tick(server);
            assertExact(player, build, "giveBack after acknowledgement in Build");
            check(switchAndAcknowledge(player, GameType.SURVIVAL), "Return to Live failed");
            MyAppsGame.tick(server);
            check("mine".equals(id(inventory.getItem(20))) && items(player, "mine") == 1,
                    "The item returned during a switch was not supplied back in Live");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void droppingAnAppsItemNeverRemovesTheAppOrPutsItOnTheGround(GameTestHelper helper) {
        try (var fixture = Fixture.open(helper)) {
            var player = fixture.player();
            var inventory = player.getInventory();
            var before = capture(player);
            check(inventory.getSelectedSlot() == 0 && "pinned".equals(id(inventory.getSelectedItem())), "Fixture: the pinned app is not in the hand");

            // Q and Ctrl+Q in the world.
            long sent = fixture.sent(0, "pinned");
            player.drop(false);
            player.drop(true);
            assertExact(player, before, "Q on an app's item");
            check(fixture.sent(0, "pinned") == sent + 2, "The client was not sent the item it had already let go");

            // Q over a slot of the open inventory (menu slot 9 is inventory slot 9, menu slot 36 is the first hotbar slot).
            player.inventoryMenu.clicked(9, 0, ContainerInput.THROW, player);
            player.inventoryMenu.clicked(36, 1, ContainerInput.THROW, player);
            assertExact(player, before, "Q over an app's item in the inventory");

            // Picked up and clicked outside the window: it stays on the cursor and can be put back.
            player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
            check("mine".equals(id(player.inventoryMenu.getCarried())) && inventory.getItem(9).isEmpty(), "Fixture: the item was not picked up");
            player.inventoryMenu.clicked(AbstractContainerMenu.SLOT_CLICKED_OUTSIDE, 0, ContainerInput.PICKUP, player);
            player.inventoryMenu.clicked(AbstractContainerMenu.SLOT_CLICKED_OUTSIDE, 1, ContainerInput.PICKUP, player);
            check("mine".equals(id(player.inventoryMenu.getCarried())), "A click outside the window dropped an app's item");
            player.inventoryMenu.clicked(9, 0, ContainerInput.PICKUP, player);
            assertExact(player, before, "Putting the item back after a click outside the window");

            // Whatever else tries to put it on the ground: a free slot takes it, beside the hotbar first.
            check(player.drop(AppItems.create(AresOs.app("mine")), false) == null && "mine".equals(id(inventory.getItem(10))),
                    "An app's item that was to be dropped did not go into the first free slot beside the hotbar");
            inventory.setItem(10, ItemStack.EMPTY);
            // And with no room at all it is let go; nothing else moves and nothing lies on the ground.
            fillFreeSlots(player);
            var full = capture(player);
            check(player.drop(AppItems.create(AresOs.app("mine")), true) == null, "An app's item became an entity");
            assertExact(player, full, "Dropping an app's item over a full inventory");
            check(appsOnTheGround(player) == 0, "An app's item lies on the ground");
            check(items(player, "mine") == 1 && items(player, "pinned") == 1, "Dropping made or lost an app's item");
            check(AresOs.app("mine").mine() && AresOs.app("pinned").mine() && AresOs.app("pinned").pinned()
                    && fixture.savedAsMine("mine") && fixture.savedAsMine("pinned"), "Dropping an app's item changed My apps");

            // Anything that is not an app still drops as always.
            var diamond = player.drop(new ItemStack(Items.DIAMOND), false);
            check(diamond != null && diamond.getItem().is(Items.DIAMOND), "A normal item no longer drops");
            diamond.discard();
        }
        helper.succeed();
    }
}
