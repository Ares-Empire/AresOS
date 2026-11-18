package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.ModeSwitchClient;
import dev.aresos.config.AppsConfig;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import dev.aresos.hub.Place;
import dev.aresos.item.AppInventory;
import dev.aresos.item.AppItems;
import dev.aresos.shell.FakeHelper;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.world.NetherHome;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.impl.client.gametest.context.TestSingleplayerContextImpl;
import net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;

public final class HomePublishClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        var oldApps = AresOs.apps();
        var oldIcons = AresOs.generatedIcons;
        var oldShell = AresOs.shell();
        String oldConfig = System.getProperty("aresos.appsConfig");
        Path home = context.computeOnClient(client -> client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER));
        Path root = Path.of("a53b");
        Path oldHome = root.resolve("previous-home");
        try {
            TownClientGameTest.deleteTree(root);
            Files.createDirectories(root);
            if (Files.exists(home)) Files.move(home, oldHome);
            try (var helper = new FakeHelper(root); var shell = helper.client(FakeHelper.fast())) {
                helper.minor = 2;
                helper.entries = List.of(FakeHelper.entry("notepad", "Notepad", null, "image"),
                        FakeHelper.entry("terminal", "Terminal", null, "image"),
                        FakeHelper.entry("browser", "Chrome", null, "image"),
                        FakeHelper.entry("etch", "Etch", null, "system"));
                Path config = root.resolve("apps.json");
                var apps = AppsConfig.load(config, true).apps();
                System.setProperty("aresos.appsConfig", config.toString());
                context.runOnClient(client -> {
                    AppsTestAccess.aresos$setApps(apps);
                    AppsTestAccess.aresos$startHelper(shell, true);
                });
                shell.awaitCatalogue(Duration.ofSeconds(5));
                context.waitFor(client -> shell.tracksHome(), 200);
                check(helper.received("publish_home").isEmpty(), "Hello without a host published a home");

                TownClientGameTest.openCreateScreen(context, home);
                context.clickScreenButton("aresos.home.create");
                context.waitFor(client -> client.player != null && client.gui.screen() == null, 2400);
                try (var world = new TestSingleplayerContextImpl(context, new TestWorldSaveImpl(context, home),
                        context.computeOnClient(Minecraft::getSingleplayerServer))) {
                    world.getConnection().waitForChunksRender();
                    TownClientGameTest.waitForServer(context, world,
                            server -> HubData.get(server) != null && HubData.get(server).logos().size() == 3,
                            "The home did not build its three logos", 600);
                    context.waitFor(client -> !helper.homes.isEmpty(), 600);
                    var first = helper.homes.getFirst();
                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer();
                        check(first.apps().keySet().equals(TownPicturesClientGameTest.places(server).keySet()),
                                "First publish differs from the town: " + first.apps().keySet());
                        for (var logo : HubData.get(server).logos())
                            check(logo.place().equals(FakeHelper.string(first.apps().get(logo.app()), "place")),
                                    "First publish placed " + logo.app() + " elsewhere");
                        checkSlots(first, AppInventory.hotbarSlots(player.getInventory()::getItem));
                    });

                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer();
                        for (int i = 9; i < 36; i++) {
                            var stack = player.getInventory().getItem(i);
                            if ("terminal".equals(stack.get(AppItems.APP_ID))) {
                                player.inventoryMenu.clicked(i, 5, ContainerInput.SWAP, player);
                                return;
                            }
                        }
                        throw new AssertionError("No unpinned Terminal in the Live inventory");
                    });
                    var pinned = after(context, helper, first);
                    checkSlots(pinned, Map.of("notepad", 0, "terminal", 5));

                    world.getServer().runOnServer(server -> {
                        var player = world.getConnection().getServerPlayer();
                        player.inventoryMenu.clicked(36, 5, ContainerInput.SWAP, player);
                    });
                    var swapped = after(context, helper, pinned);
                    var liveSlots = Map.of("notepad", 5, "terminal", 0);
                    checkSlots(swapped, liveSlots);

                    context.getInput().pressKey(InputConstants.KEY_G);
                    world.getConnection().waitForServerboundPackets();
                    context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE && !ModeSwitchClient.pending());
                    world.getConnection().waitForServerboundPackets();
                    world.getServer().runOnServer(server -> world.getConnection().getServerPlayer().getInventory()
                            .setItem(8, AppItems.create(AresOs.app("terminal"))));
                    command(context, "aresos app name notepad editnotes");
                    var renamed = after(context, helper, swapped);
                    check("editnotes".equals(FakeHelper.string(renamed.apps().get("notepad"), "short")),
                            "The short name change was not published");
                    checkSlots(renamed, liveSlots);

                    command(context, "aresos app move notepad west");
                    var moved = after(context, helper, renamed);
                    world.getServer().runOnServer(server -> {
                        var logo = HubData.get(server).logo("notepad").orElseThrow();
                        check(logo.place().startsWith("W") && logo.place().equals(FakeHelper.string(moved.apps().get("notepad"), "place")),
                                "Publish did not follow the world after /aresos app move");
                    });
                    checkSlots(moved, liveSlots);

                    command(context, "aresos app add etch");
                    var added = after(context, helper, moved);
                    check(added.apps().containsKey("etch"), "Publish missed a My apps addition");
                    command(context, "aresos app remove etch");
                    var removed = after(context, helper, added);
                    check(!removed.apps().containsKey("etch"), "Publish missed a My apps removal");

                    check(FakeHelper.string(removed.apps().get("notepad"), "cells").charAt(0) != '.', "Fixture has no upper-left cell");
                    world.getServer().runOnServer(server -> {
                        var hub = HubData.get(server);
                        var place = Place.parse(hub.logo("notepad").orElseThrow().place()).orElseThrow();
                        server.overworld().setBlockAndUpdate(place.origin(hub.home().pos()).above(HubLayout.SIZE - 1),
                                Blocks.AIR.defaultBlockState());
                    });
                    var edited = after(context, helper, removed);
                    check(FakeHelper.string(edited.apps().get("notepad"), "cells").charAt(0) == '.',
                            "Publish missed the front cell that left the town's record");
                    checkSlots(edited, liveSlots);
                    check(helper.invalidHome.isEmpty(), "The fake helper refused: " + helper.invalidHome);
                }
                AresOs.LOGGER.info("53b home publish checks passed: wait for host, standing places, pin, swap, saved Live slots, name, move, add, remove and front edit");
            }
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setShell(oldShell);
                AppsTestAccess.aresos$setApps(oldApps);
                AresOs.generatedIcons = oldIcons;
            });
            if (oldConfig == null) System.clearProperty("aresos.appsConfig");
            else System.setProperty("aresos.appsConfig", oldConfig);
            try {
                TownClientGameTest.deleteTree(home);
                if (Files.exists(oldHome)) Files.move(oldHome, home);
                TownClientGameTest.deleteTree(root);
            } catch (IOException error) { throw new UncheckedIOException(error); }
        }
    }

    private static void command(ClientGameTestContext context, String command) {
        context.runOnClient(client -> client.player.connection.sendCommand(command));
    }

    private static FakeHelper.PublishedHome after(ClientGameTestContext context, FakeHelper helper,
                                                   FakeHelper.PublishedHome previous) {
        context.waitFor(client -> !helper.homes.getLast().revision().equals(previous.revision()), 400);
        return helper.homes.getLast();
    }

    private static void checkSlots(FakeHelper.PublishedHome home, Map<String, Integer> expected) {
        var slots = new java.util.HashMap<String, Integer>();
        home.apps().forEach((id, row) -> {
            if (row.has("slot")) slots.put(id, row.get("slot").getAsInt());
        });
        check(slots.equals(expected), "Published slots " + slots + " differ from Live slots " + expected);
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
