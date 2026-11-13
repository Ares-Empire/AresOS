package dev.aresos.names;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.tree.CommandNode;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.item.AppCommands;
import dev.aresos.mixin.CommandNodeAccess;
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
    private static final class State {
        CommandDispatcher<CommandSourceStack> dispatcher;
        final Map<String, CommandNode<CommandSourceStack>> owned = new HashMap<>();
        List<AppDefinition> apps;
        Set<String> reserved = Set.of();
        boolean enabled;
    }
    private static final Map<MinecraftServer, State> STATES = new WeakHashMap<>();
    private SlashCommands() { }

    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(SlashCommands::refresh);
        ServerLifecycleEvents.SERVER_STOPPED.register(STATES::remove);
    }

    /** Excludes only the exact nodes we registered, so replacement commands from other mods always win. */
    public static Set<String> reserved(MinecraftServer server) {
        var state = STATES.get(server);
        var root = server.getCommands().getDispatcher().getRoot();
        var names = new HashSet<>(NameRules.OWN);
        for (var node : root.getChildren())
            if (state == null || state.owned.get(node.getName()) != node) names.add(node.getName());
        return Set.copyOf(names);
    }

    public static void refresh(MinecraftServer server) {
        var state = STATES.computeIfAbsent(server, ignored -> new State());
        var dispatcher = server.getCommands().getDispatcher();
        if (state.dispatcher != dispatcher) {
            state.owned.clear(); state.apps = null; state.dispatcher = dispatcher;
        }
        boolean enabled = server.isSingleplayer() && DesktopWorld.isEnabled(server);
        var reserved = reserved(server);
        if (state.apps == AresOs.apps() && state.enabled == enabled && state.reserved.equals(reserved)) return;
        var root = dispatcher.getRoot();
        // Failed persistence keeps the previous working commands, which still check current membership.
        if (enabled) try { AresOs.assignNames(reserved); }
        catch (IOException | RuntimeException error) {
            AresOs.LOGGER.error("Could not save app names; commands will retry after the next app change", error);
            state.apps = AresOs.apps(); state.enabled = enabled; state.reserved = reserved;
            for (var player : server.getPlayerList().getPlayers()) if (DesktopWorld.isHost(server, player))
                player.sendSystemMessage(Component.literal("Could not save app names: " + error.getMessage()));
            return;
        }
        for (var entry : state.owned.entrySet()) if (root.getChild(entry.getKey()) == entry.getValue()) remove(root, entry.getKey());
        state.owned.clear();
        if (enabled) for (var app : AresOs.apps()) if (app.mine()) for (String name : app.names()) {
            // Check again at the actual registration, without merging into somebody else's literal.
            if (root.getChild(name) != null || NameRules.OWN.contains(name)) continue;
            var node = dispatcher.register(Commands.literal(name).requires(AppCommands::allowed)
                    .executes(c -> {
                        var current = AresOs.app(app.id());
                        return current != null && current.mine() && current.names().contains(name) ? launch(c.getSource(), app.id()) : 0;
                    }));
            state.owned.put(name, node);
        }
        state.apps = AresOs.apps(); state.enabled = enabled; state.reserved = reserved(server);
        for (var player : server.getPlayerList().getPlayers()) server.getCommands().sendCommands(player);
    }

    @SuppressWarnings("unchecked")
    private static void remove(CommandNode<CommandSourceStack> root, String name) {
        var access = (CommandNodeAccess<CommandSourceStack>)(Object)root;
        access.aresos$children().remove(name);
        access.aresos$literals().remove(name);
        access.aresos$arguments().remove(name);
    }

    /** Visit zero is the ordinary hotbar launch: no zone visit and no return teleport. */
    public static int launch(CommandSourceStack source, String id) {
        if (!AppCommands.allowed(source)) return 0;
        var app = AresOs.app(id);
        if (app == null) { source.sendFailure(Component.literal("Unknown AresOS app")); return 0; }
        var player = source.getPlayer();
        if (!ServerPlayNetworking.canSend(player, ZoneLaunchPayload.TYPE)) {
            source.sendFailure(Component.literal("This client cannot receive AresOS app requests.")); return 0;
        }
        ServerPlayNetworking.send(player, new ZoneLaunchPayload(id, 0));
        return 1;
    }
}
