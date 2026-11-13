package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.*;
import dev.aresos.item.AppCommands;
import dev.aresos.item.MyAppsGame;
import dev.aresos.names.SlashCommands;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.ZoneLaunchPayload;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.commands.Commands;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundCommandsPacket;
import net.minecraft.network.protocol.game.ClientboundSystemChatPacket;
import net.minecraft.network.protocol.common.ClientboundCustomPayloadPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.world.level.GameType;

import java.nio.file.*;
import java.util.*;
import static dev.aresos.test.ModeInventoryFixtures.*;

/** A separate batch: these synchronous tests temporarily own the shared catalogue and host profile. */
public final class SlashNamesGameTests {
    private static final String BATCH = "aresos-test:slash_names";
    private static AppDefinition app(String id, String name, boolean mine) {
        return new AppDefinition(id, name, List.of(id), "minecraft:book", false).withMine(mine);
    }

    private static final class Fixture implements AutoCloseable {
        final net.minecraft.server.MinecraftServer server;
        final ServerPlayer player;
        final EmbeddedChannel channel;
        final String config;
        final GameProfile profile;
        final boolean desktop;
        Fixture(GameTestHelper helper) throws Exception {
            server = helper.getLevel().getServer();
            config = System.getProperty("aresos.appsConfig"); profile = server.getSingleplayerProfile();
            desktop = DesktopWorld.isEnabled(server);
            Path file = Files.createTempDirectory(Path.of("."), "slash-names-").resolve("apps.json");
            AppsConfig.save(file, List.of(app("discord", "Discord", true), app("other", "Other", false), app("lunar", "Lunar Client", false),
                    app("helpapp", "Help", true).withNames(List.of("help")), app("timeapp", "Time", true).withNames(List.of("time")),
                    app("listapp", "List", true).withNames(List.of("list"))));
            System.setProperty("aresos.appsConfig", file.toString()); AresOs.saveMine(Map.of());
            var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "SlashNamesTest"), false);
            server.setSingleplayerProfile(cookie.gameProfile());
            player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
            var connection = new Connection(PacketFlow.SERVERBOUND); channel = new EmbeddedChannel(connection);
            server.getPlayerList().placeNewPlayer(connection, player, cookie);
            registerStateReceiver(player);
            net.fabricmc.fabric.impl.networking.server.ServerNetworkingImpl.getAddon(player.connection).handle(
                    new net.fabricmc.fabric.impl.networking.RegistrationPayload(
                            net.fabricmc.fabric.impl.networking.RegistrationPayload.REGISTER, List.of(ZoneLaunchPayload.TYPE.id())));
            player.setGameMode(GameType.SURVIVAL); acknowledge(player);
            server.getCommands().getDispatcher().register(Commands.literal("aresos").then(AppCommands.app()));
            dev.aresos.names.ProgramCommands.register(server.getCommands().getDispatcher());
            DesktopWorld.setEnabled(server, true); SlashCommands.refresh(server);
        }
        int run(String command) throws Exception {
            return server.getCommands().getDispatcher().execute(command, player.createCommandSourceStack());
        }
        List<String> completions(String text) {
            var dispatcher = server.getCommands().getDispatcher();
            return dispatcher.getCompletionSuggestions(dispatcher.parse(text, player.createCommandSourceStack()))
                    .join().getList().stream().map(com.mojang.brigadier.suggestion.Suggestion::getText).toList();
        }
        Set<String> visibleNames() {
            var packet = channel.outboundMessages().stream().filter(ClientboundCommandsPacket.class::isInstance)
                    .map(ClientboundCommandsPacket.class::cast).reduce((first, last) -> last).orElseThrow();
            var root = packet.getRoot(Commands.createValidationContext(server.registryAccess()),
                    new ClientboundCommandsPacket.NodeBuilder<net.minecraft.commands.CommandSourceStack>() {
                        @Override public com.mojang.brigadier.builder.ArgumentBuilder<net.minecraft.commands.CommandSourceStack, ?> createLiteral(String name) {
                            return Commands.literal(name);
                        }
                        @Override public com.mojang.brigadier.builder.ArgumentBuilder<net.minecraft.commands.CommandSourceStack, ?> createArgument(
                                String name, com.mojang.brigadier.arguments.ArgumentType<?> type, net.minecraft.resources.Identifier suggestions) {
                            return Commands.argument(name, type);
                        }
                        @Override public com.mojang.brigadier.builder.ArgumentBuilder<net.minecraft.commands.CommandSourceStack, ?> configure(
                                com.mojang.brigadier.builder.ArgumentBuilder<net.minecraft.commands.CommandSourceStack, ?> builder, boolean executable, boolean restricted) {
                            return executable ? builder.executes(c -> 1) : builder;
                        }
                    });
            return root.getChildren().stream().map(com.mojang.brigadier.tree.CommandNode::getName).collect(java.util.stream.Collectors.toSet());
        }
        boolean said(String text) {
            return channel.outboundMessages().stream().anyMatch(packet -> packet instanceof ClientboundSystemChatPacket chat
                    && chat.content().getString().contains(text));
        }
        long commandPackets() { return channel.outboundMessages().stream().filter(ClientboundCommandsPacket.class::isInstance).count(); }
        @Override public void close() throws Exception {
            server.getPlayerList().remove(player);
            server.setSingleplayerProfile(profile);
            if (config == null) System.clearProperty("aresos.appsConfig"); else System.setProperty("aresos.appsConfig", config);
            AresOs.saveMine(Map.of()); DesktopWorld.setEnabled(server, desktop); SlashCommands.refresh(server);
            channel.finishAndReleaseAll();
        }
    }

    @GameTest(environment = BATCH)
    public void namesAreHostOnlyAndFollowMembershipWithoutRejoin(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            check(f.visibleNames().containsAll(List.of("dc", "discord")), "Host command packet lacks both names");
            check(f.run("dc") == 1, "Alias did not launch");
            check(f.channel.outboundMessages().stream().anyMatch(packet -> packet instanceof ClientboundCustomPayloadPacket custom
                    && custom.payload() instanceof ZoneLaunchPayload launch && launch.app().equals("discord") && launch.visit() == 0),
                    "Alias did not send a visit-free launch");
            check(switchAndAcknowledge(f.player, GameType.CREATIVE), "Build refused");
            check(f.run("discord") == 1, "Build command did not launch");
            long before = f.commandPackets();
            MyAppsGame.add(f.player, "other");
            check(f.completions("oth").contains("other") && f.commandPackets() > before, "Add did not resend new commands");
            MyAppsGame.remove(f.player, "other");
            check(dispatcher.getRoot().getChild("other") == null, "Removed app still has a command node");
            check(AresOs.app("other").names().equals(List.of("other")), "Removal forgot names");
            MyAppsGame.add(f.player, "other");
            check(dispatcher.getRoot().getChild("other") != null, "Return did not restore command");
            f.server.setSingleplayerProfile(new GameProfile(UUID.randomUUID(), "DifferentHost"));
            f.server.getCommands().sendCommands(f.player);
            check(f.visibleNames().stream().noneMatch(name -> name.equals("dc") || name.equals("discord")), "Guest sees app commands");
            f.server.setSingleplayerProfile(f.player.getGameProfile());
            DesktopWorld.setEnabled(f.server, false); SlashCommands.refresh(f.server);
            check(dispatcher.getRoot().getChild("discord") == null && dispatcher.getRoot().getChild("dc") == null,
                    "Normal world retains app commands");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void vanillaAndLaterModCommandsAlwaysWin(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            for (String command : List.of("help", "time", "list")) {
                check(AresOs.apps().stream().noneMatch(app -> app.names().contains(command)), "Saved vanilla name survived: " + command);
                check(dispatcher.getRoot().getChild(command) != null, "Vanilla command disappeared: " + command);
            }
            check(dispatcher.execute("help", f.player.createCommandSourceStack().withPermission(PermissionSet.ALL_PERMISSIONS)) > 0,
                    "Vanilla help no longer runs");
            check(dispatcher.execute("list", f.player.createCommandSourceStack().withPermission(PermissionSet.ALL_PERMISSIONS)) > 0,
                    "Vanilla list no longer runs");
            check(dispatcher.execute("time query gametime", f.player.createCommandSourceStack().withPermission(PermissionSet.ALL_PERMISSIONS)) >= 0,
                    "Vanilla time no longer runs");
            // Another mod installs a new command after our first registration.
            dispatcher.register(Commands.literal("future").executes(c -> 42));
            check(f.run("aresos app name discord future") == 0 && f.said("Reserved"), "Later command was not reserved");
            check(dispatcher.execute("future", f.player.createCommandSourceStack()) == 42, "Later mod command changed");
        }
        helper.succeed();
    }

    @GameTest(environment = BATCH)
    public void ownerNamesAndEveryRefusal(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            MyAppsGame.add(f.player, "other");
            check(f.run("aresos app name discord chat") == 1, "Could not add own name");
            check(AresOs.app("discord").names().equals(List.of("chat", "discord", "dc")), "New name is not main");
            check(f.completions("ch").contains("chat"), "New name did not reach commands");
            for (String bad : List.of("a", "Upper", "1bad", "bad-name", "abcdefghijklmnopq", "two words", "bad$", "éé"))
                check(f.run("aresos app name discord " + bad) == 0 && f.said("Invalid name"), "Invalid accepted: " + bad);
            for (String bad : List.of("help", "list", "time", "aresos", "home", "go", "open", "apps"))
                check(f.run("aresos app name discord " + bad) == 0 && f.said("Reserved command"), "Reserved accepted: " + bad);
            check(f.run("aresos app name other chat") == 0 && f.said("belongs to Discord"), "Clash lacks owner");
            check(f.run("aresos app name absent valid") == 0 && f.said("Unknown AresOS app"), "Unknown app accepted");
            check(f.run("aresos app unname missing") == 0 && f.said("No app holds"), "Unknown alias accepted");
            check(f.run("aresos app unname other") == 0 && f.said("last name"), "Last name removed");
            check(f.run("aresos app unname chat") == 1 && !f.completions("ch").contains("chat"), "Unname did not remove command");
            check(AresOs.app("discord").names().getFirst().equals("discord"), "Unname did not expose next name");
            MyAppsGame.remove(f.player, "other");
            check(f.run("aresos app name other valid") == 0 && f.said("not in My apps"), "Named an inactive app");
        }
        helper.succeed();
    }
    @GameTest(environment = BATCH)
    public void openOneManyNoneCompletionAndClickableApps(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            check(f.run("open oth") == 1, "Unique /open prefix failed for a program outside My apps");
            check(f.run("open missing") == 0 && f.said("No program matches"), "Missing /open lacks explanation");
            check(f.run("open l") >= 2 && f.said("Several programs match"), "Ambiguous /open did not list choices");
            check(f.completions("open dis").contains("discord"), "/open does not complete programs");
            long before = f.channel.outboundMessages().stream().filter(packet -> packet instanceof ClientboundCustomPayloadPacket p
                    && p.payload() instanceof ZoneLaunchPayload).count();
            int size = f.run("apps");
            check(size == 4, "/apps includes a program outside My apps");
            check(f.said("/discord, /dc") && f.said("System & Tools"), "/apps lacks aliases or group");
            var lines = f.channel.outboundMessages().stream().filter(ClientboundSystemChatPacket.class::isInstance)
                    .map(ClientboundSystemChatPacket.class::cast).map(ClientboundSystemChatPacket::content)
                    .filter(line -> line.getStyle().getClickEvent() instanceof net.minecraft.network.chat.ClickEvent.RunCommand).toList();
            check(lines.size() >= 6, "Ambiguity or app rows are not clickable");
            for (var line : lines) {
                var click = (net.minecraft.network.chat.ClickEvent.RunCommand)line.getStyle().getClickEvent();
                check(f.run(click.command().substring(1)) == 1, "Click did not resolve exactly one app: " + click.command());
            }
            check(f.channel.outboundMessages().stream().filter(packet -> packet instanceof ClientboundCustomPayloadPacket p
                    && p.payload() instanceof ZoneLaunchPayload).count() == before + lines.size(), "Clicks did not send one launch each");
            DesktopWorld.setEnabled(f.server, false); SlashCommands.refresh(f.server);
            check(!f.visibleNames().contains("open") && !f.visibleNames().contains("apps"), "Normal-world packet exposes commands");
        }
        helper.succeed();
    }

}
