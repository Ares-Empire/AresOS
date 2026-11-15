package dev.aresos.names;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.tree.CommandNode;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.item.AppCommands;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.ZoneLaunchPayload;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.util.*;

/** The host's saved names on the real command tree; reconciled on the server thread. */
public final class SlashCommands {
    /** One app name on the tree, and the app it opens. Ours only while {@link OwnedNodes#ours} says so. */
    private record Owned(CommandNode<CommandSourceStack> node, String app) { }
    private static final class State {
        CommandDispatcher<CommandSourceStack> dispatcher;
        final Map<String, Owned> owned = new HashMap<>();
        List<AppDefinition> apps;
        Set<String> reserved = Set.of();
        boolean enabled;
        // Failed saves in a row, and the server tick of the next try.
        int failures;
        long retryAt;
    }
    /** After a failed save: a second, then twice as long each time, at most a minute. */
    static final int FIRST_RETRY_TICKS = 20, LONGEST_RETRY_TICKS = 1200;
    private static final Map<MinecraftServer, State> STATES = new WeakHashMap<>();
    private SlashCommands() { }

    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(SlashCommands::refresh);
        ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
            var state = STATES.remove(server);
            if (state != null && state.dispatcher != null) OwnedNodes.forget(state.dispatcher);
            OwnedNodes.forget(server.getCommands().getDispatcher());
        });
    }

    /** Every command on the tree except our app names as we installed them, and AresOS's own. */
    public static Set<String> reserved(MinecraftServer server) {
        var state = STATES.get(server);
        var root = server.getCommands().getDispatcher().getRoot();
        var names = new HashSet<>(NameRules.OWN);
        for (var node : root.getChildren()) {
            var owned = state == null ? null : state.owned.get(node.getName());
            // A node of ours that another registration changed is somebody else's command now.
            if (owned == null || owned.node() != node || !OwnedNodes.ours(node)) names.add(node.getName());
        }
        return Set.copyOf(names);
    }

    public static void refresh(MinecraftServer server) {
        var state = STATES.computeIfAbsent(server, ignored -> new State());
        var dispatcher = server.getCommands().getDispatcher();
        if (state.dispatcher != dispatcher) {
            // A rebuilt tree (/reload) has none of our names; the old nodes go with the old tree, and so do their records.
            if (state.dispatcher != null) OwnedNodes.forget(state.dispatcher);
            state.owned.clear(); state.apps = null; state.dispatcher = dispatcher;
        }
        boolean enabled = server.isSingleplayer() && DesktopWorld.isEnabled(server);
        var reserved = reserved(server);
        long now = server.getTickCount();
        boolean changed = state.apps != AresOs.apps() || state.enabled != enabled || !state.reserved.equals(reserved);
        if (!changed && !(state.failures > 0 && now >= state.retryAt)) return;
        if (enabled) save(server, state, reserved, now); else state.failures = 0;
        // Whether or not that save worked: removals, and names already saved, never depend on it.
        follow(dispatcher, state, enabled);
        state.apps = AresOs.apps(); state.enabled = enabled; state.reserved = reserved(server);
        for (var player : server.getPlayerList().getPlayers()) server.getCommands().sendCommands(player);
    }

    /** Missing names and displaced ones are saved first; a failure stays due and is tried again by itself. */
    private static void save(MinecraftServer server, State state, Set<String> reserved, long now) {
        try {
            AresOs.assignNames(reserved);
            if (state.failures > 0) AresOs.LOGGER.info("App names saved after {} failed attempts", state.failures);
            state.failures = 0;
        } catch (IOException | RuntimeException error) {
            state.failures++;
            state.retryAt = now + retryDelay(state.failures);
            if (state.failures > 1) { AresOs.LOGGER.warn("Could not save app names (attempt {}): {}", state.failures, error.getMessage()); return; }
            AresOs.LOGGER.error("Could not save app names; trying again by itself", error);
            for (var player : server.getPlayerList().getPlayers()) if (DesktopWorld.isHost(server, player))
                player.sendSystemMessage(Component.literal("Could not save app names: " + error.getMessage()
                        + ". New names wait; AresOS tries again by itself."));
        }
    }

    /** Ticks to wait after this many failed saves in a row. */
    public static long retryDelay(int failures) {
        return Math.min((long)FIRST_RETRY_TICKS << Math.min(Math.max(failures - 1, 0), 16), LONGEST_RETRY_TICKS);
    }

    /** Brings the tree in line with the saved names: names that lost their app go, free saved names come. */
    private static void follow(CommandDispatcher<CommandSourceStack> dispatcher, State state, boolean enabled) {
        var wanted = new HashMap<String, String>();
        if (enabled) for (var app : AresOs.apps()) if (app.mine() && !app.absent())
            for (String name : app.names()) wanted.putIfAbsent(name, app.id());
        for (var iterator = state.owned.entrySet().iterator(); iterator.hasNext(); ) {
            var entry = iterator.next();
            var owned = entry.getValue();
            // Changed by another registration: not ours any more, so it is left exactly as it is.
            if (!OwnedNodes.ours(owned.node())) iterator.remove();
            else if (!owned.app().equals(wanted.get(entry.getKey()))) { OwnedNodes.remove(owned.node()); iterator.remove(); }
        }
        for (var entry : wanted.entrySet()) {
            String name = entry.getKey(), id = entry.getValue();
            if (state.owned.containsKey(name) || NameRules.OWN.contains(name)) continue;
            // Only where the tree has nothing of that name: Minecraft's and other mods' commands always win.
            var node = OwnedNodes.install(dispatcher, Commands.literal(name).requires(AppCommands::allowed)
                    .executes(c -> run(c.getSource(), id, name)));
            if (node != null) state.owned.put(name, new Owned(node, id));
        }
    }

    private static int run(CommandSourceStack source, String id, String name) {
        var current = AresOs.app(id);
        return current != null && current.mine() && !current.absent() && current.names().contains(name) ? launch(source, id) : 0;
    }

    /** Visit zero is the ordinary hotbar launch: no zone visit and no return teleport. */
    public static int launch(CommandSourceStack source, String id) {
        if (!AppCommands.allowed(source)) return 0;
        var app = AresOs.app(id);
        if (app == null) { source.sendFailure(Component.literal("Unknown AresOS app")); return 0; }
        if (app.absent()) { source.sendFailure(Component.literal(app.name() + " is not installed: the system no longer lists it.")); return 0; }
        var player = source.getPlayer();
        if (!ServerPlayNetworking.canSend(player, ZoneLaunchPayload.TYPE)) {
            source.sendFailure(Component.literal("This client cannot receive AresOS app requests.")); return 0;
        }
        ServerPlayNetworking.send(player, new ZoneLaunchPayload(id, 0));
        return 1;
    }
}
