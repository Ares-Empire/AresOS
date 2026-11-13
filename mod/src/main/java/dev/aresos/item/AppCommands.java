package dev.aresos.item;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.builder.RequiredArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import dev.aresos.world.DesktopWorld;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;
import static com.mojang.brigadier.arguments.StringArgumentType.greedyString;

/** {@code /aresos app add|remove|list}: My apps by command. The host only, in an AresOS world. */
public final class AppCommands {
    private interface Change { String apply(ServerPlayer host, String id) throws IOException; }

    private AppCommands() { }

    public static LiteralArgumentBuilder<CommandSourceStack> app() {
        return Commands.literal("app")
                .then(Commands.literal("add").then(argument(false).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::add))))
                .then(Commands.literal("remove").then(argument(true).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::remove))))
                .then(Commands.literal("list").executes(c -> list(c.getSource())))
                // Brigadier checks a requirement while parsing, against the source that typed the command, so
                // "execute as <host> run ..." from a command block or another operator cannot rename his apps.
                .then(Commands.literal("name").requires(AppCommands::allowed).then(argument(true).then(Commands.argument("name", greedyString())
                        .executes(c -> name(c.getSource(), getString(c, "app"), getString(c, "name"))))))
                .then(Commands.literal("unname").requires(AppCommands::allowed).then(Commands.argument("name", word()).suggests((c, b) -> {
                    if (allowed(c.getSource())) for (var app : AresOs.apps()) for (String name : app.names())
                        if (name.startsWith(b.getRemainingLowerCase())) b.suggest(name);
                    return b.buildFuture();
                }).executes(c -> unname(c.getSource(), getString(c, "name")))));
    }

    /** Completion over the right list: programs that are not his for add, his apps for remove. */
    private static RequiredArgumentBuilder<CommandSourceStack, String> argument(boolean mine) {
        return Commands.argument("app", word()).suggests((c, b) -> {
            if (!allowed(c.getSource())) return b.buildFuture();
            String typed = b.getRemainingLowerCase();
            for (AppDefinition app : AresOs.apps()) if (app.mine() == mine && app.id().startsWith(typed)) b.suggest(app.id());
            return b.buildFuture();
        });
    }

    public static boolean allowed(CommandSourceStack source) {
        var player = source.getPlayer();
        return player != null && DesktopWorld.isHost(source.getServer(), player) && DesktopWorld.isEnabled(source.getServer());
    }

    private static ServerPlayer host(CommandSourceStack source) throws CommandSyntaxException {
        var player = source.getPlayerOrException();
        if (!DesktopWorld.isHost(source.getServer(), player)) {
            source.sendFailure(Component.literal("Only the singleplayer host can change My apps"));
            return null;
        }
        if (!DesktopWorld.isEnabled(source.getServer())) {
            source.sendFailure(Component.literal("Not an AresOS world"));
            return null;
        }
        return player;
    }

    private static int change(CommandSourceStack source, String id, Change change) throws CommandSyntaxException {
        var player = host(source);
        if (player == null) return 0;
        try {
            String said = change.apply(player, id);
            source.sendSuccess(() -> Component.literal(said), false);
            return 1;
        } catch (IOException | RuntimeException error) {
            source.sendFailure(Component.literal(MyAppsGame.failure(error)));
            return 0;
        }
    }

    private static int name(CommandSourceStack source, String id, String name) throws CommandSyntaxException {
        if (host(source) == null) return 0;
        try {
            dev.aresos.names.SlashCommands.refresh(source.getServer());
            AresOs.name(id, name, dev.aresos.names.SlashCommands.reserved(source.getServer()));
            dev.aresos.names.SlashCommands.refresh(source.getServer());
            source.sendSuccess(() -> Component.literal("/" + name + " is now the main name of " + AresOs.app(id).name() + "."), false);
            return 1;
        } catch (IOException | RuntimeException error) { source.sendFailure(Component.literal(error.getMessage())); return 0; }
    }

    private static int unname(CommandSourceStack source, String name) throws CommandSyntaxException {
        if (host(source) == null) return 0;
        try {
            AresOs.unname(name);
            dev.aresos.names.SlashCommands.refresh(source.getServer());
            source.sendSuccess(() -> Component.literal("Removed /" + name + "."), false);
            return 1;
        } catch (IOException | RuntimeException error) { source.sendFailure(Component.literal(error.getMessage())); return 0; }
    }

    private static int list(CommandSourceStack source) throws CommandSyntaxException {
        var player = host(source);
        if (player == null) return 0;
        var mine = AresOs.apps().stream().filter(AppDefinition::mine).sorted(AppSearch.BY_NAME).toList();
        source.sendSuccess(() -> Component.literal("My apps: " + mine.size()), false);
        for (var app : mine) source.sendSuccess(() -> Component.literal(app.name() + " (" + app.id() + ")"
                + (app.pinned() ? ", in the hotbar" : "")), false);
        return mine.size();
    }
}
