package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.*;
import dev.aresos.item.AppCommands;
import dev.aresos.item.MyAppsGame;
import dev.aresos.names.OwnedNodes;
import dev.aresos.names.ProgramCommands;
import dev.aresos.names.SlashCommands;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.ZoneLaunchPayload;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.commands.Commands;
import net.minecraft.commands.FunctionInstantiationException;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundCommandsPacket;
import net.minecraft.network.protocol.game.ClientboundSystemChatPacket;
import net.minecraft.network.protocol.common.ClientboundCustomPayloadPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.dedicated.DedicatedServerProperties;
import net.minecraft.server.permissions.LevelBasedPermissionSet;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.world.level.GameType;

import java.nio.file.*;
import java.util.*;
import static dev.aresos.test.ModeInventoryFixtures.*;

/** A separate batch: these synchronous tests temporarily own the shared catalogue and host profile. */
public final class SlashNamesGameTests {
    private static final String BATCH = "aresos-test:slash_names";
    /** Alone in its batch: it rebuilds the server's command tree and waits for ticks. */
    private static final String RELOAD = "aresos-test:slash_names_reload";
    /** Alone in its batch too: it breaks the apps file and waits for the retry. */
    private static final String RETRY = "aresos-test:slash_names_retry";
    private static AppDefinition app(String id, String name, boolean mine) {
        return new AppDefinition(id, name, List.of(id), "minecraft:book", false).withMine(mine);
    }

    private static final class Fixture implements AutoCloseable {
        final net.minecraft.server.MinecraftServer server;
        ServerPlayer player;
        EmbeddedChannel channel;
        final String config;
        final GameProfile profile;
        final boolean desktop;
        Fixture(GameTestHelper helper, AppDefinition... extra) throws Exception {
            server = helper.getLevel().getServer();
            config = System.getProperty("aresos.appsConfig"); profile = server.getSingleplayerProfile();
            desktop = DesktopWorld.isEnabled(server);
            Path file = Files.createTempDirectory(Path.of("."), "slash-names-").resolve("apps.json");
            var apps = new ArrayList<>(List.of(app("discord", "Discord", true), app("other", "Other", false), app("lunar", "Lunar Client", false),
                    app("helpapp", "Help", true).withNames(List.of("help")), app("timeapp", "Time", true).withNames(List.of("time")),
                    app("listapp", "List", true).withNames(List.of("list"))));
            apps.addAll(List.of(extra));
            AppsConfig.save(file, apps);
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
        /** Leaves and joins again as the same host; returns the commands the new login was sent. */
        Set<String> rejoin(GameTestHelper helper) {
            server.getPlayerList().remove(player);
            channel.finishAndReleaseAll();
            var cookie = CommonListenerCookie.createInitial(player.getGameProfile(), false);
            player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
            var connection = new Connection(PacketFlow.SERVERBOUND); channel = new EmbeddedChannel(connection);
            server.getPlayerList().placeNewPlayer(connection, player, cookie);
            return visibleNames();
        }
        /** Takes a command another "mod" put on the shared test tree off again, so later tests see the usual tree. */
        @SuppressWarnings("unchecked")
        void unregister(String name) {
            var access = (dev.aresos.mixin.CommandNodeAccess<Object>)(Object)server.getCommands().getDispatcher().getRoot();
            access.aresos$children().remove(name); access.aresos$literals().remove(name); access.aresos$arguments().remove(name);
        }
        /** -1 when the command does not even parse for this source. */
        int attempt(String command, net.minecraft.commands.CommandSourceStack source) throws Exception {
            try { return server.getCommands().getDispatcher().execute(command, source); }
            catch (com.mojang.brigadier.exceptions.CommandSyntaxException refused) { return -1; }
        }
        List<String> completions(String text) {
            var dispatcher = server.getCommands().getDispatcher();
            return dispatcher.getCompletionSuggestions(dispatcher.parse(text, player.createCommandSourceStack()))
                    .join().getList().stream().map(com.mojang.brigadier.suggestion.Suggestion::getText).toList();
        }
        /**
         * What reached the channel. From the second tick of a test on, the server holds packets back until its
         * end-of-tick flush, which an embedded channel never sees; flush it here.
         */
        Queue<Object> sent() {
            channel.runPendingTasks(); channel.flushOutbound();
            return channel.outboundMessages();
        }
        Set<String> visibleNames() {
            var packet = sent().stream().filter(ClientboundCommandsPacket.class::isInstance)
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
            return sent().stream().anyMatch(packet -> packet instanceof ClientboundSystemChatPacket chat
                    && chat.content().getString().contains(text));
        }
        long commandPackets() { return sent().stream().filter(ClientboundCommandsPacket.class::isInstance).count(); }
        /** The app IDs of every launch request sent so far, in order. */
        List<String> launches() {
            return sent().stream().filter(packet -> packet instanceof ClientboundCustomPayloadPacket p
                    && p.payload() instanceof ZoneLaunchPayload).map(packet -> ((ZoneLaunchPayload)((ClientboundCustomPayloadPacket)packet).payload()).app()).toList();
        }
        /** Every chat line with a click, oldest first. */
        List<net.minecraft.network.chat.Component> clickable() {
            return sent().stream().filter(ClientboundSystemChatPacket.class::isInstance)
                    .map(ClientboundSystemChatPacket.class::cast).map(ClientboundSystemChatPacket::content)
                    .filter(line -> line.getStyle().getClickEvent() instanceof net.minecraft.network.chat.ClickEvent.RunCommand).toList();
        }
        static String click(net.minecraft.network.chat.Component line) {
            return ((net.minecraft.network.chat.ClickEvent.RunCommand)line.getStyle().getClickEvent()).command();
        }
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

    /** Review 1, finding 1: a later command under an app's name takes the name whole, with its own permission. */
    @GameTest(environment = BATCH)
    public void aLaterCommandUnderAnAppNameWinsWhole(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            var root = dispatcher.getRoot();
            try {
                check(root.getChild("discord") != null && f.run("discord") == 1, "Fixture: /discord is not installed");
                // Another mod registers "discord" after us: anyone may run it, and it has a child.
                dispatcher.register(Commands.literal("discord").requires(source -> true).executes(c -> 42)
                        .then(Commands.literal("status").executes(c -> 43)));
                var foreign = root.getChild("discord");
                check(!OwnedNodes.ours(foreign), "The later command merged into ours");
                f.server.setSingleplayerProfile(new GameProfile(UUID.randomUUID(), "DifferentHost"));
                var guest = f.player.createCommandSourceStack();
                check(f.attempt("discord", guest) == 42 && f.attempt("discord status", guest) == 43, "The later command lost its own permission");
                f.server.setSingleplayerProfile(f.player.getGameProfile());
                SlashCommands.refresh(f.server);
                var names = AresOs.app("discord").names();
                check(!names.contains("discord") && names.contains("dc"), "Discord kept a name another command holds: " + names);
                check(f.run("discord") == 42, "The host does not reach the later command");
                check(f.run(names.getFirst()) == 1 && f.launches().getLast().equals("discord"), "Discord's next-best name does not open it: " + names);
                MyAppsGame.remove(f.player, "discord");
                check(root.getChild("discord") == foreign && f.attempt("discord status", guest) == 43,
                        "Removing the app took the later command or its child");
                check(names.stream().allMatch(name -> root.getChild(name) == null || root.getChild(name) == foreign), "Our names stayed after removal");
            } finally { f.unregister("discord"); }
        }
        helper.succeed();
    }

    /** Review 1, finding 1: the same for /open; and its rows still open the right apps. */
    @GameTest(environment = BATCH)
    public void aLaterOpenWinsWhole(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            var root = dispatcher.getRoot();
            var ours = root.getChild("open");
            check(ours != null && OwnedNodes.ours(ours), "Fixture: our /open is not installed");
            try {
                dispatcher.register(Commands.literal("open").requires(source -> true).executes(c -> 42)
                        .then(Commands.literal("door").executes(c -> 43)));
                var foreign = root.getChild("open");
                check(foreign != ours && !OwnedNodes.ours(foreign), "The later /open merged into ours");
                f.server.setSingleplayerProfile(new GameProfile(UUID.randomUUID(), "DifferentHost"));
                var guest = f.player.createCommandSourceStack();
                check(f.attempt("open", guest) == 42 && f.attempt("open door", guest) == 43, "The later /open lost its own permission");
                f.server.setSingleplayerProfile(f.player.getGameProfile());
                SlashCommands.refresh(f.server);
                ProgramCommands.register(dispatcher);
                check(root.getChild("open") == foreign && f.run("open door") == 43, "AresOS took /open back");
                int before = f.clickable().size(), launched = f.launches().size();
                check(f.run("apps") == 4, "/apps does not list My apps");
                for (var line : f.clickable().subList(before, f.clickable().size())) f.run(Fixture.click(line).substring(1));
                var expected = AresOs.apps().stream().filter(AppDefinition::mine).sorted(AppSearch.BY_NAME).map(AppDefinition::id).toList();
                check(f.launches().subList(launched, f.launches().size()).equals(expected), "Rows did not open My apps: " + f.launches());
            } finally {
                f.unregister("open");
                ProgramCommands.register(dispatcher);
            }
        }
        helper.succeed();
    }

    /** Review 2, point 2: a registration under another parent that holds our node too leaves our /open where it is. */
    @GameTest(environment = BATCH)
    public void aRegistrationElsewhereLeavesOpenAlone(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            var root = dispatcher.getRoot();
            var ours = root.getChild("open");
            check(ours != null && OwnedNodes.ours(ours), "Fixture: our /open is not installed");
            try {
                // Another mod hangs our /open under its own namespace too, then registers its own "open" there.
                var namespace = Commands.literal("othermod").build();
                namespace.addChild(ours);
                root.addChild(namespace);
                namespace.addChild(Commands.literal("open").executes(c -> 42).build());
                check(root.getChild("open") == ours, "A registration under another parent took /open off the root");
                check(f.run("othermod open") == 42, "Fixture: the other mod's registration did not land");
                int launched = f.launches().size();
                check(f.run("open discord") == 1 && f.launches().size() == launched + 1 && f.launches().getLast().equals("discord"),
                        "/open no longer opens his apps");
                // Control: the same registration at the root, where we installed /open, still takes the name whole.
                dispatcher.register(Commands.literal("apps").executes(c -> 43));
                check(f.run("apps") == 43, "A later /apps at the root did not win");
            } finally {
                f.unregister("othermod"); f.unregister("open"); f.unregister("apps");
                ProgramCommands.register(dispatcher);
            }
        }
        helper.succeed();
    }

    /** Review 1, finding 1: a rebuilt tree (/reload) and a rejoin. Vanilla's commands are vanilla's; the names come back. */
    @GameTest(environment = RELOAD, maxTicks = 600)
    public void reloadAndRejoinBringTheNamesBack(GameTestHelper helper) throws Exception {
        var f = new Fixture(helper);
        var old = f.server.getCommands().getDispatcher();
        // Review 2, point 5: every node of the old tree, to show afterwards that none of them is still recorded.
        var oldTree = Collections.newSetFromMap(new IdentityHashMap<com.mojang.brigadier.tree.CommandNode<?>, Boolean>());
        var pending = new ArrayDeque<com.mojang.brigadier.tree.CommandNode<?>>(List.of(old.getRoot()));
        while (!pending.isEmpty()) {
            var node = pending.pop();
            if (oldTree.add(node)) pending.addAll(node.getChildren());
        }
        try {
            check(old.getRoot().getChild("dc") != null, "Fixture: no /dc before the reload");
            check(List.of("dc", "discord", "open", "apps").stream().allMatch(name -> OwnedNodes.recorded(old.getRoot().getChild(name))),
                    "Fixture: the old tree's nodes are not recorded");
            f.server.reloadResources(f.server.getPackRepository().getSelectedIds());
        } catch (Exception | Error error) { f.close(); throw error; }
        boolean[] done = {false};
        helper.onEachTick(() -> {
            if (done[0]) return;
            try {
                var dispatcher = f.server.getCommands().getDispatcher();
                var root = dispatcher.getRoot();
                if (dispatcher == old || root.getChild("dc") == null) {
                    if (helper.getTick() > 400) throw new AssertionError("No rebuilt tree with the app names after "
                            + helper.getTick() + " ticks; tree rebuilt: " + (dispatcher != old));
                    return;
                }
                done[0] = true;
                var names = AresOs.app("discord").names();
                for (String name : names) check(OwnedNodes.ours(root.getChild(name)), "Not back after /reload: /" + name);
                var kept = oldTree.stream().filter(OwnedNodes::recorded).map(com.mojang.brigadier.tree.CommandNode::getName).toList();
                check(kept.isEmpty(), "Still recorded from the old tree after /reload: " + kept);
                check(f.visibleNames().containsAll(names), "The rebuilt list was not sent without a rejoin");
                var all = f.player.createCommandSourceStack().withPermission(PermissionSet.ALL_PERMISSIONS);
                for (String vanilla : List.of("help", "list", "time"))
                    check(root.getChild(vanilla) != null && !OwnedNodes.ours(root.getChild(vanilla)), "Not vanilla's after /reload: /" + vanilla);
                check(dispatcher.execute("help", all) > 0 && dispatcher.execute("list", all) > 0, "Vanilla commands do not run after /reload");
                check(f.run("dc") == 1 && f.launches().getLast().equals("discord"), "/dc does not open Discord after /reload");
                var seen = f.rejoin(helper);
                check(seen.containsAll(names) && seen.containsAll(List.of("help", "list", "time")), "The rejoin's command list: " + seen);
                f.close();
                helper.succeed();
            } catch (AssertionError error) {
                done[0] = true; closeQuietly(f);
                helper.fail(error.getMessage());
            } catch (Exception error) {
                done[0] = true; closeQuietly(f);
                throw new RuntimeException(error);
            }
        });
    }

    /** Review 1, finding 6: a failed save still removes what must go, and tries again by itself after a growing pause. */
    @GameTest(environment = RETRY, maxTicks = 300)
    public void aFailedSaveRemovesAndRetriesByItself(GameTestHelper helper) throws Exception {
        check(SlashCommands.retryDelay(1) == 20 && SlashCommands.retryDelay(2) == 40 && SlashCommands.retryDelay(3) == 80
                && SlashCommands.retryDelay(30) == 1200, "The pause does not grow from a second to a minute");
        var f = new Fixture(helper);
        var root = f.server.getCommands().getDispatcher().getRoot();
        try {
            check(root.getChild("dc") != null && root.getChild("other") == null, "Fixture: unexpected commands");
            Path file = Path.of(System.getProperty("aresos.appsConfig"));
            // Discord leaves and Other joins at once; then the apps file cannot be read, so Other's names cannot be saved.
            AresOs.saveMine(Map.of("discord", false, "other", true));
            String saved = Files.readString(file);
            Files.writeString(file, "{ not json");
            SlashCommands.refresh(f.server);
            check(root.getChild("dc") == null && root.getChild("discord") == null, "A failed save kept the commands of a removed app");
            check(root.getChild("other") == null, "Other has a command without saved names");
            check(f.said("Could not save app names"), "The host was not told");
            // The file is fine again. Nothing else changes from here on.
            Files.writeString(file, saved);
            SlashCommands.refresh(f.server);
            check(root.getChild("other") == null, "Retried at once, without a pause");
        } catch (Exception | Error error) { f.close(); throw error; }
        long start = helper.getTick();
        boolean[] done = {false};
        helper.onEachTick(() -> {
            if (done[0]) return;
            try {
                if (root.getChild("other") == null) {
                    if (helper.getTick() - start > 100) throw new AssertionError("No retry within 100 ticks");
                    return;
                }
                done[0] = true;
                check(helper.getTick() - start >= 15, "Retried before its pause: after " + (helper.getTick() - start) + " ticks");
                check(AresOs.app("other").names().equals(List.of("other")), "Other's names: " + AresOs.app("other").names());
                check(f.run("other") == 1 && f.launches().getLast().equals("other"), "/other does not open Other");
                f.close();
                helper.succeed();
            } catch (AssertionError error) {
                done[0] = true; closeQuietly(f);
                helper.fail(error.getMessage());
            } catch (Exception error) {
                done[0] = true; closeQuietly(f);
                throw new RuntimeException(error);
            }
        });
    }

    private static void closeQuietly(Fixture f) {
        try { f.close(); } catch (Exception error) { AresOs.LOGGER.error("Could not restore the slash-names fixture", error); }
    }

    /**
     * Client test, first run: a clicked /apps row opened Minecraft's "elevated permissions" question instead of the
     * app. Minecraft marks a node restricted when its requirement fails for a probe without server and permissions.
     */
    @GameTest(environment = BATCH)
    public void hostCommandsAreNotRestrictedForClicks(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var root = f.server.getCommands().getDispatcher().getRoot();
            var probe = Commands.createCompilationContext(PermissionSet.NO_PERMISSIONS);
            var app = root.getChild("aresos").getChild("app");
            var click = app.getChild("open");
            for (var node : List.of(app, click, root.getChild("dc"), root.getChild("open"), root.getChild("apps")))
                check(node.canUse(probe), "The client would ask before running /" + node.getName());
            check(!click.canUse(f.server.createCommandSourceStack()), "The console may use the click command");
        }
        helper.succeed();
    }

    private static final net.minecraft.resources.Identifier FUNCTION = net.minecraft.resources.Identifier.fromNamespaceAndPath("aresos-test", "host_commands");

    /** Whether a function file holding this one line loads: ServerFunctionLibrary's own call, with its source. */
    private static boolean compiles(com.mojang.brigadier.CommandDispatcher<net.minecraft.commands.CommandSourceStack> dispatcher,
                                    net.minecraft.commands.CommandSourceStack loader, String line) {
        try { CommandFunction.fromLines(FUNCTION, dispatcher, loader, List.of(line)); return true; }
        catch (IllegalArgumentException refused) { return false; }
    }

    /** Whether a macro function "$$(line)" runs this line when called: macro lines are parsed then, with the loader's source. */
    private static boolean instantiates(com.mojang.brigadier.CommandDispatcher<net.minecraft.commands.CommandSourceStack> dispatcher,
                                        net.minecraft.commands.CommandSourceStack loader, String line) {
        var arguments = new CompoundTag();
        arguments.putString("line", line);
        try { CommandFunction.fromLines(FUNCTION, dispatcher, loader, List.of("$$(line)")).instantiate(arguments, dispatcher); return true; }
        catch (FunctionInstantiationException refused) { return false; }
    }

    /**
     * Review 2, point 4. ServerFunctionLibrary compiles every function with
     * Commands.createCompilationContext(server.getFunctionCompilationPermissions()); that permission set is the game
     * test server's OWNER here, the integrated server's GAMEMASTER, a dedicated server's function-permission-level.
     * None of them lets a function hold one of the host's commands, as a plain line or through a macro.
     */
    @GameTest(environment = BATCH)
    public void functionsCannotHoldHostCommands(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var dispatcher = f.server.getCommands().getDispatcher();
            var root = dispatcher.getRoot();
            var before = AresOs.apps();
            var names = AresOs.app("discord").names();
            var nodes = names.stream().map(root::getChild).toList();
            var permissions = new LinkedHashMap<String, PermissionSet>();
            permissions.put("this game test server", f.server.getFunctionCompilationPermissions());
            permissions.put("integrated server", LevelBasedPermissionSet.GAMEMASTER);
            for (String level : List.of("0", "1", "2", "3", "4"))
                permissions.put("dedicated server at function-permission-level " + level, DedicatedServerProperties.deserializePermission(level));
            String host = f.player.getStringUUID();
            var lines = List.of("aresos app remove discord", "aresos app add other", "aresos app list", "aresos app open discord",
                    "aresos app name discord changed", "aresos app unname dc", "dc", "discord", "open discord", "apps",
                    "execute as " + host + " run aresos app remove discord", "execute as " + host + " run dc");
            for (var entry : permissions.entrySet()) {
                var loader = Commands.createCompilationContext(entry.getValue());
                check(loader.getServer() == null && loader.permissions() != PermissionSet.NO_PERMISSIONS, "Not a loader's source: " + entry.getKey());
                // Control: the same source compiles an ordinary command, plain and through a macro.
                check(compiles(dispatcher, loader, "help") && instantiates(dispatcher, loader, "help"), "The loader compiles nothing: " + entry.getKey());
                for (String line : lines) {
                    check(!compiles(dispatcher, loader, line), "A function holds \"" + line + "\" (" + entry.getKey() + ")");
                    check(!instantiates(dispatcher, loader, line), "A macro function runs \"" + line + "\" (" + entry.getKey() + ")");
                }
            }
            // Control: these commands are on this tree; the click probe's source, which never runs anything, parses them.
            var probe = Commands.createCompilationContext(PermissionSet.NO_PERMISSIONS);
            check(compiles(dispatcher, probe, "aresos app remove discord") && compiles(dispatcher, probe, "dc"), "Fixture: the commands are missing");
            SlashCommands.refresh(f.server);
            check(AresOs.apps().equals(before), "His apps changed: " + AresOs.apps());
            for (int i = 0; i < names.size(); i++)
                check(root.getChild(names.get(i)) == nodes.get(i) && OwnedNodes.ours(nodes.get(i)), "His command changed: /" + names.get(i));
        }
        helper.succeed();
    }

    /** Review 1, finding 2: the requirement is checked against who typed it, not whom "execute as" picks. */
    @GameTest(environment = BATCH)
    public void onlyTheHostWhoTypesItCanNameApps(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            var before = AresOs.app("discord").names();
            var console = f.server.createCommandSourceStack();
            String as = "execute as " + f.player.getStringUUID() + " run aresos app ";
            check(f.attempt(as + "name discord changed", console) <= 0, "execute as the host renamed an app");
            check(f.attempt(as + "unname dc", console) <= 0, "execute as the host removed a name");
            f.server.setSingleplayerProfile(new GameProfile(UUID.randomUUID(), "DifferentHost"));
            check(f.attempt("aresos app name discord changed", f.player.createCommandSourceStack()) == -1, "A guest may type name");
            check(f.attempt("aresos app unname dc", f.player.createCommandSourceStack()) == -1, "A guest may type unname");
            f.server.setSingleplayerProfile(f.player.getGameProfile());
            check(AresOs.app("discord").names().equals(before), "Names changed: " + AresOs.app("discord").names());
            check(f.run("aresos app name discord changed") == 1, "The host could not name his app");
        }
        helper.succeed();
    }

    /** Review 2, point 1: no branch of /aresos app parses for "execute as <host>" or a guest, so My apps stays his. */
    @GameTest(environment = BATCH)
    public void onlyTheHostWhoTypesItCanChangeMyApps(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper, app("notes", "Notes", true).withPinned(true))) {
            var root = f.server.getCommands().getDispatcher().getRoot();
            var before = AresOs.apps();
            var names = new ArrayList<>(AresOs.app("discord").names());
            names.addAll(AresOs.app("notes").names());
            var commands = names.stream().map(root::getChild).toList();
            check(commands.stream().allMatch(OwnedNodes::ours) && root.getChild("other") == null, "Fixture: unexpected commands " + names);
            var console = f.server.createCommandSourceStack();
            String as = "execute as " + f.player.getStringUUID() + " run aresos app ";
            for (String branch : List.of("remove discord", "remove notes", "add other", "list"))
                check(f.attempt(as + branch, console) == -1, "execute as the host parses: " + branch);
            f.server.setSingleplayerProfile(new GameProfile(UUID.randomUUID(), "DifferentHost"));
            for (String branch : List.of("remove discord", "add other", "list"))
                check(f.attempt("aresos app " + branch, f.player.createCommandSourceStack()) == -1, "A guest may type " + branch);
            f.server.setSingleplayerProfile(f.player.getGameProfile());
            SlashCommands.refresh(f.server);
            check(AresOs.apps().equals(before), "My apps or pins changed: " + AresOs.apps());
            for (int i = 0; i < names.size(); i++)
                check(root.getChild(names.get(i)) == commands.get(i) && OwnedNodes.ours(commands.get(i)), "His command changed: /" + names.get(i));
            check(root.getChild("other") == null, "Other got a command");
            // Control: the host's own typing still reaches every branch.
            check(f.run("aresos app list") == 5 && f.run("aresos app add other") == 1 && f.run("aresos app remove other") == 1,
                    "The host could not use /aresos app");
        }
        helper.succeed();
    }

    /** Review 1, finding 3: rows open by ID through /aresos app open; typed /open follows HUB.md 4.4 only. */
    @GameTest(environment = BATCH)
    public void clicksOpenByIdAndTypedOpenIgnoresIds(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper, app("editor", "Editor", false), app("texteditor", "Editor", false), app("chat", "Talk", false))) {
            check(f.run("open editor") == 2 && f.said("Several programs match"), "An ID took precedence over a shared name");
            check(f.launches().isEmpty(), "Typed /open launched by ID");
            var rows = f.clickable().stream().map(Fixture::click).toList();
            check(rows.equals(List.of(ProgramCommands.CLICK + "editor", ProgramCommands.CLICK + "texteditor")), "Rows: " + rows);
            check(f.run("aresos app name discord chat") == 1, "Fixture: could not name Discord chat");
            check(f.run("open chat") == 1 && f.launches().equals(List.of("discord")), "An ID beat another app's saved name: " + f.launches());

            // A foreign /open that was there before AresOS: ours is never installed, the rows still open the right apps.
            var dispatcher = new com.mojang.brigadier.CommandDispatcher<net.minecraft.commands.CommandSourceStack>();
            var foreign = new java.util.concurrent.atomic.AtomicInteger();
            dispatcher.register(Commands.literal("open").then(Commands.argument("what", com.mojang.brigadier.arguments.StringArgumentType.greedyString())
                    .executes(c -> foreign.incrementAndGet())));
            ProgramCommands.register(dispatcher);
            dispatcher.register(Commands.literal("aresos").then(AppCommands.app()));
            int before = f.clickable().size();
            int mine = dispatcher.execute("apps", f.player.createCommandSourceStack());
            var appRows = f.clickable().subList(before, f.clickable().size());
            check(mine == 4 && appRows.size() == mine, "/apps rows: " + appRows.size() + " of " + mine);
            int launched = f.launches().size();
            for (var line : appRows) dispatcher.execute(Fixture.click(line).substring(1), f.player.createCommandSourceStack());
            check(foreign.get() == 0, "A row ran the foreign /open");
            var opened = f.launches().subList(launched, f.launches().size());
            var expected = AresOs.apps().stream().filter(AppDefinition::mine).sorted(AppSearch.BY_NAME).map(AppDefinition::id).toList();
            check(opened.equals(expected), "Rows opened " + opened + " instead of " + expected);
        }
        helper.succeed();
    }

    /** Review 1, finding 4: a program the latest complete list no longer names has no command until it returns. */
    @GameTest(environment = BATCH)
    public void programsTheSystemNoLongerListsHaveNoCommands(GameTestHelper helper) throws Exception {
        try (var f = new Fixture(helper)) {
            Path file = Path.of(System.getProperty("aresos.appsConfig"));
            var root = f.server.getCommands().getDispatcher().getRoot();
            var everything = AresOs.apps();
            var names = AresOs.app("discord").names();
            check(names.equals(List.of("discord", "dc")) && root.getChild("dc") != null, "Fixture: Discord has no commands");
            AppsConfig.merge(file, everything.stream().filter(app -> !app.id().equals("discord")).toList(), false, null, true);
            AresOs.saveMine(Map.of()); SlashCommands.refresh(f.server);
            var gone = AresOs.app("discord");
            check(gone.absent() && gone.mine() && gone.names().equals(names), "Discord lost its place or names: " + gone);
            check(names.stream().allMatch(name -> root.getChild(name) == null), "An absent program kept a command");
            check(names.stream().noneMatch(f.visibleNames()::contains), "The command list still offers an absent program");
            check(f.run("open discord") == 0 && f.said("No program matches"), "/open found an absent program");
            check(!f.completions("open dis").contains("discord"), "/open completes an absent program");
            int launches = f.launches().size();
            check(f.run("aresos app open discord") == 0 && f.said("not installed"), "An absent program opened by ID");
            check(f.launches().size() == launches, "An absent program sent a launch");
            int clickable = f.clickable().size();
            check(f.run("apps") == 4 && f.said("Discord  not installed"), "/apps does not say Discord is not installed");
            check(f.clickable().size() == clickable + 3, "/apps offers a click for an absent program");
            // The next complete list names it again: the same names, the same place, its commands back.
            AppsConfig.merge(file, everything, false, null, true);
            AresOs.saveMine(Map.of()); SlashCommands.refresh(f.server);
            check(!AresOs.app("discord").absent() && AresOs.app("discord").names().equals(names), "Discord did not return as it was");
            check(f.run("dc") == 1 && f.launches().getLast().equals("discord"), "The returned program has no command");
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
