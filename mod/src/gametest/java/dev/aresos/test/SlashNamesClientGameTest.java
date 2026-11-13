package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AppsScreen;
import dev.aresos.client.AresOsClient;
import dev.aresos.config.*;
import dev.aresos.names.NameRules;
import dev.aresos.test.mixin.*;
import dev.aresos.zone.ZoneData;
import dev.aresos.zone.ZoneLaunchPayload;
import net.fabricmc.fabric.api.client.gametest.v1.*;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.client.gui.screens.ChatScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.world.entity.Display;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.nio.file.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import static dev.aresos.test.ModeInventoryFixtures.check;
import static dev.aresos.test.WalkInLogosClientGameTest.*;

/** Last in the client list: screenshots keep the running numbers of every earlier package. */
public final class SlashNamesClientGameTest implements FabricClientGameTest {
    private static AppDefinition app(String id, String name, String exec, boolean mine, String... categories) {
        return new AppDefinition(id, name, List.of("fake-" + id), "minecraft:book", false).withMine(mine)
                .withSystem(new SystemInfo("user", null, List.of(categories), null, null, id, exec, false));
    }

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var previousIcons = AresOs.generatedIcons;
        String previousConfig = System.getProperty("aresos.appsConfig");
        var calls = new CopyOnWriteArrayList<List<String>>();
        var previousLauncher = AresOsClient.replaceLauncher(command -> { calls.add(command); return CompletableFuture.completedFuture(null); });
        try {
            Path root = Path.of("build/review/35-slash-names").toAbsolutePath();
            Files.createDirectories(root);
            Path config = root.resolve("apps.json");
            AppsConfig.save(config, List.of(app("browser", "Chrome", "google-chrome", true, "Network"),
                    app("terminal", "Terminal", "foot", true), app("notepad", "Notepad", "kwrite", true),
                    app("discord", "Discord", "flatpak", true, "Network"),
                    app("lunar", "Lunar Client", "LunarClient.AppImage", true, "Game"),
                    app("disks", "Disks", "gnome-disks", false), app("helpapp", "Help", "yelp", false)));
            System.setProperty("aresos.appsConfig", config.toString());
            context.runOnClient(client -> { AppsTestAccess.aresos$setApps(read(config)); AresOs.generatedIcons = Set.of(); });
            context.getInput().resizeWindow(960, 540);
            try (var world = context.worldBuilder().adjustSettings(settings -> {
                settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL);
                settings.setAllowCommands(false);
            }).create()) {
                world.getConnection().waitForChunksRender();
                context.runOnClient(client -> check(client.player.connection.getCommands().getRoot().getChild("discord") == null,
                        "Normal world has an app command"));
                world.getServer().runOnServer(server -> {
                    var level = world.getConnection().getServerLevel();
                    // Original plain test field: no downloaded app art or owner world in the screenshots.
                    for (int x = -22; x <= 22; x++) for (int z = -30; z <= 24; z++) {
                        level.setBlock(new BlockPos(x, 99, z), Blocks.GRASS_BLOCK.defaultBlockState(), 2);
                        for (int y = 100; y <= 127; y++) level.setBlock(new BlockPos(x, y, z), Blocks.AIR.defaultBlockState(), 2);
                    }
                });
                move(context, world, new Vec3(0, 100, 8.5));
                command(context, world, "aresos desktop on");
                context.waitFor(client -> client.player.connection.getCommands().getRoot().getChild("dc") != null);
                check(AresOs.app("discord").names().equals(List.of("discord", "dc")), "Discord names not saved");
                check(read(config).stream().filter(app -> app.id().equals("discord")).findFirst().orElseThrow().names()
                        .equals(List.of("discord", "dc")), "Names exist only in memory");

                context.runOnClient(client -> { client.gui.hud.getChat().clearMessages(true); client.gui.toastManager().clear(); });
                context.getInput().pressKey(options -> options.keyChat);
                context.waitForScreen(ChatScreen.class);
                context.getInput().typeChars("/d");
                context.waitFor(client -> ((SlashChatTestAccess)client.gui.screen()).aresos$suggestions().isVisible());
                context.runOnClient(client -> {
                    var dispatcher = client.player.connection.getCommands();
                    var suggestions = dispatcher.getCompletionSuggestions(dispatcher.parse("d", client.player.connection.getSuggestionsProvider()))
                            .join().getList().stream().map(com.mojang.brigadier.suggestion.Suggestion::getText).toList();
                    check(suggestions.containsAll(List.of("dc", "discord")), "Completion is missing dc or discord: " + suggestions);
                });
                shot(context, "35-chat-d-completion");
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                Vec3 standing = world.getServer().computeOnServer(server -> world.getConnection().getServerPlayer().position());
                // Type the command through the real chat, with cheats disabled.
                context.getInput().pressKey(options -> options.keyChat);
                context.waitForScreen(ChatScreen.class);
                context.getInput().typeChars("/dc");
                context.getInput().pressKey(InputConstants.KEY_RETURN);
                context.waitFor(client -> calls.size() == 1);
                check(calls.getFirst().equals(List.of("fake-discord")), "/dc opened the wrong app");
                focusRoundTrip(context, true);
                world.getConnection().waitForServerboundPackets(); context.waitTicks(8);
                check(calls.size() == 1, "/dc launched more than once");
                world.getServer().runOnServer(server -> check(world.getConnection().getServerPlayer().position().distanceToSqr(standing) < 0.0001,
                        "Closing Discord teleported the player"));
                context.runOnClient(client -> check(client.player.position().distanceToSqr(standing) < 0.0001, "Client position moved on close"));

                command(context, world, "apps");
                context.waitFor(client -> messages(client).stream().anyMatch(line -> line.content().getString().contains("/discord, /dc")));
                context.getInput().pressKey(options -> options.keyChat);
                context.waitForScreen(ChatScreen.class);
                shot(context, "35-apps-chat");
                // Exercise the real chat's click handler with the row received from the server.
                context.runOnClient(client -> {
                    var row = messages(client).stream().map(net.minecraft.client.multiplayer.chat.GuiMessage::content)
                            .filter(line -> line.getString().startsWith("Discord ") && line.getStyle().getClickEvent() instanceof ClickEvent.RunCommand)
                            .findFirst().orElseThrow();
                    check(((SlashChatTestAccess)client.gui.screen()).aresos$click(row.getStyle(), false), "Chat row did not handle its click");
                });
                context.waitFor(client -> calls.size() == 2);
                context.runOnClient(client -> client.gui.setScreen(null));
                focusRoundTrip(context, false);

                command(context, world, "open disks");
                context.waitFor(client -> calls.size() == 3);
                check(!AresOs.app("disks").mine() && calls.getLast().equals(List.of("fake-disks")), "/open made the program his");
                focusRoundTrip(context, false);
                command(context, world, "open d");
                context.waitFor(client -> messages(client).stream().anyMatch(line -> line.content().getString().contains("Several programs match")));
                check(calls.size() == 3, "Ambiguous /open launched a program");
                command(context, world, "open nothingmatches");
                context.waitFor(client -> messages(client).stream().anyMatch(line -> line.content().getString().contains("No program matches")));

                context.getInput().pressKey(options -> options.keyInventory);
                context.waitForScreen(InventoryScreen.class); context.clickScreenButton("Apps…");
                context.waitForScreen(AppsScreen.class); context.waitTicks(4);
                shot(context, "35-apps-short-names");
                context.getInput().typeChars("dc"); context.waitTicks(3);
                context.runOnClient(client -> {
                    var rows = client.gui.screen().children().stream().filter(AppsScreen.ProgramList.class::isInstance)
                            .map(AppsScreen.ProgramList.class::cast).findFirst().orElseThrow().children().stream()
                            .filter(AppsScreen.Row.class::isInstance).map(AppsScreen.Row.class::cast).toList();
                    check(rows.size() == 2 && rows.stream().allMatch(row -> row.app().id().equals("discord")), "Alias search did not find Discord alone");
                });
                shot(context, "35-apps-search-dc");
                context.runOnClient(client -> client.gui.setScreen(null));

                // Build mode commands still open an app; new names arrive without a reconnect.
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
                command(context, world, "aresos app name discord chat");
                context.waitFor(client -> client.player.connection.getCommands().getRoot().getChild("chat") != null);
                command(context, world, "chat"); context.waitFor(client -> calls.size() == 4);
                focusRoundTrip(context, false);
                command(context, world, "aresos app unname chat");
                context.waitFor(client -> client.player.connection.getCommands().getRoot().getChild("chat") == null);
                check(NameRules.mainName(AresOs.app("discord")).equals("discord"), "Main name did not return");
                // A newly built gate has the second line; renaming leaves that standing sign unchanged.
                command(context, world, "aresos logo discord");
                String signText = world.getServer().computeOnServer(server -> {
                    var gate = ZoneData.get(server).zones().getLast().gate().orElseThrow();
                    var sign = (Display.TextDisplay)world.getConnection().getServerLevel().getEntity(gate.sign().orElseThrow());
                    return sign.getText().getString();
                });
                check(signText.equals("Discord\n/discord"), "New sign lacks slash name: " + signText);
                command(context, world, "aresos app name discord chat");
                world.getServer().runOnServer(server -> {
                    var gate = ZoneData.get(server).zones().getLast().gate().orElseThrow();
                    var sign = (Display.TextDisplay)world.getConnection().getServerLevel().getEntity(gate.sign().orElseThrow());
                    check(sign.getText().getString().equals(signText), "Renaming rewrote a standing sign");
                });
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    player.teleportTo(player.level(), 0, 100, 26, Set.of(), 180, -17, false);
                });
                context.waitFor(client -> client.player.getZ() > 25); context.waitTicks(8);
                context.runOnClient(client -> { client.gui.hud.getChat().clearMessages(true); client.gui.toastManager().clear(); });
                shot(context, "35-gate-sign");

                command(context, world, "aresos desktop off");
                context.waitFor(client -> client.player.connection.getCommands().getRoot().getChild("dc") == null);
                // A payload cannot open anything after the marker is off, including in Build mode.
                world.getServer().runOnServer(server -> ServerPlayNetworking.send(world.getConnection().getServerPlayer(), new ZoneLaunchPayload("discord", 0)));
                context.waitTicks(6); check(calls.size() == 4, "Normal-world payload launched an app");
            }
            AresOs.LOGGER.info("35 client checks passed: real completion, dc once without teleport, clickable apps, open one/many/none, "
                    + "alias search, Build launch, live command refresh, new and unchanged standing signs, normal-world receiver gating; five screenshots");
        } catch (Exception error) { throw new RuntimeException(error); }
        finally {
            context.getInput().resizeWindow(854, 480);
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps); AresOs.generatedIcons = previousIcons;
                AresOsClient.replaceLauncher(previousLauncher); AresOsClient.FOCUS_RETURN.reset();
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
            if (previousConfig == null) System.clearProperty("aresos.appsConfig"); else System.setProperty("aresos.appsConfig", previousConfig);
        }
    }

    private static List<AppDefinition> read(Path config) {
        try { return AppsConfig.load(config).apps(); } catch (Exception error) { throw new RuntimeException(error); }
    }
    private static List<net.minecraft.client.multiplayer.chat.GuiMessage> messages(net.minecraft.client.Minecraft client) {
        return ((ChatMessagesTestAccess)client.gui.hud.getChat()).aresos$messages();
    }
    private static void shot(ClientGameTestContext context, String name) {
        context.waitTicks(4);
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.slashNamesReviewDir"))));
    }
}
