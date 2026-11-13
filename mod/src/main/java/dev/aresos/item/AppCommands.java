package dev.aresos.item;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.builder.RequiredArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.world.DesktopWorld;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;

/** {@code /aresos app add|remove|list}: My apps by command. The host only, in an AresOS world. */
public final class AppCommands {
    private interface Change { String apply(ServerPlayer host, String id) throws IOException; }

    private AppCommands() { }

    public static LiteralArgumentBuilder<CommandSourceStack> app() {
        return Commands.literal("app")
                .then(Commands.literal("add").then(argument(false).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::add))))
                .then(Commands.literal("remove").then(argument(true).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::remove))))
                .then(Commands.literal("list").executes(c -> list(c.getSource())));
    }

    /** Completion over the right list: programs that are not his for add, his apps for remove. */
    private static RequiredArgumentBuilder<CommandSourceStack, String> argument(boolean mine) {
        return Commands.argument("app", word()).suggests((c, b) -> {
            String typed = b.getRemainingLowerCase();
            for (AppDefinition app : AresOs.apps()) if (app.mine() == mine && app.id().startsWith(typed)) b.suggest(app.id());
            return b.buildFuture();
        });
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
            // The apps file is written whole or not at all, so a failure leaves My apps as it was.
            source.sendFailure(Component.literal(error instanceof IOException ? error.getMessage()
                    : "Could not change My apps: " + error.getMessage()));
            return 0;
        }
    }

    private static int list(CommandSourceStack source) throws CommandSyntaxException {
        var player = host(source);
        if (player == null) return 0;
        var mine = AresOs.apps().stream().filter(AppDefinition::mine)
                .sorted(java.util.Comparator.comparing(app -> app.name().toLowerCase(java.util.Locale.ROOT))).toList();
        source.sendSuccess(() -> Component.literal("My apps: " + mine.size()), false);
        for (var app : mine) source.sendSuccess(() -> Component.literal(app.name() + " (" + app.id() + ")"
                + (app.pinned() ? ", in the hotbar" : "")), false);
        return mine.size();
    }
}
