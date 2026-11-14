package dev.aresos.item;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.builder.RequiredArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
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
        // Brigadier checks a requirement while parsing, against the source that typed the command, so
        // "execute as <host> run ..." from a command block, a function or another operator reaches no branch of
        // /aresos app. Every branch checks the host again when it runs.
        return Commands.literal("app").requires(AppCommands::allowed)
                .then(Commands.literal("add").then(argument(false).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::add))))
                .then(Commands.literal("remove").then(argument(true).executes(c -> change(c.getSource(), getString(c, "app"), MyAppsGame::remove))))
                .then(Commands.literal("list").executes(c -> list(c.getSource())))
                // The click target of /apps and /open rows: the stable ID, through AresOS's own command, so a
                // foreign /open can never receive it and two programs with one name stay apart.
                .then(Commands.literal("open").requires(AppCommands::allowed).then(Commands.argument("app", word())
                        .executes(c -> dev.aresos.names.SlashCommands.launch(c.getSource(), getString(c, "app")))))
                .then(Commands.literal("name").requires(AppCommands::allowed).then(argument(true).then(Commands.argument("name", greedyString())
                        .executes(c -> name(c.getSource(), getString(c, "app"), getString(c, "name"))))))
                // Package 37: he arranges the town. Names as /go takes them, among his apps.
                .then(Commands.literal("swap").requires(AppCommands::allowed).then(his("a").then(his("b")
                        .executes(c -> arrange(c.getSource(), () -> {
                            var a = dev.aresos.world.GettingAround.his(c.getSource(), getString(c, "a"));
                            var b = a.isEmpty() ? a : dev.aresos.world.GettingAround.his(c.getSource(), getString(c, "b"));
                            return b.isEmpty() ? null : dev.aresos.hub.TownMoves.swap(c.getSource().getServer(), a.get().id(), b.get().id());
                        })))))
                .then(move())
                .then(Commands.literal("unname").requires(AppCommands::allowed).then(Commands.argument("name", word()).suggests((c, b) -> {
                    if (allowed(c.getSource())) for (var app : AresOs.apps()) for (String name : app.names())
                        if (name.startsWith(b.getRemainingLowerCase())) b.suggest(name);
                    return b.buildFuture();
                }).executes(c -> unname(c.getSource(), getString(c, "name")))));
    }

    /** {@code /aresos app move <app> <north|east|south|west>}: the four directions are the four groups' avenues. */
    private static LiteralArgumentBuilder<CommandSourceStack> move() {
        var app = his("app");
        for (var group : AppGroup.clockwise())
            app.then(Commands.literal(dev.aresos.hub.TownMoves.direction(group)).executes(c -> arrange(c.getSource(), () -> {
                var found = dev.aresos.world.GettingAround.his(c.getSource(), getString(c, "app"));
                return found.isEmpty() ? null : dev.aresos.hub.TownMoves.move(c.getSource().getServer(), found.get().id(), group);
            })));
        return Commands.literal("move").requires(AppCommands::allowed).then(app);
    }

    /** An app of his, completed with any name {@code /go} takes. */
    private static RequiredArgumentBuilder<CommandSourceStack, String> his(String name) {
        return Commands.argument(name, word()).suggests(dev.aresos.world.GettingAround::suggestHis);
    }

    /** Swap or move for the host: its one line, after the line of a name that found none of his apps (then null). */
    private static int arrange(CommandSourceStack source, java.util.function.Supplier<dev.aresos.hub.TownMoves.Said> arranging) throws CommandSyntaxException {
        if (host(source) == null) return 0;
        var said = arranging.get();
        if (said == null) return 0;
        if (said.done()) source.sendSuccess(() -> Component.literal(said.line()), false);
        else source.sendFailure(Component.literal(said.line()));
        dev.aresos.hub.TownMoves.told(source.getServer(), said);
        return said.done() ? 1 : 0;
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
        // Minecraft marks a node "restricted" for the client when its requirement fails for a probe without a server
        // and with the PermissionSet.NO_PERMISSIONS singleton (Commands.createCompilationContext); the client then
        // asks before running a clicked /apps row. The probe never runs anything.
        // The game's only other source without a server is the function loader's (ServerFunctionLibrary, for plain
        // lines at load and macro lines when instantiated): the same factory with the server's function permissions,
        // which is always one of the five LevelBasedPermissionSet constants and never that singleton (integrated
        // server GAMEMASTER, game test server OWNER, dedicated server its function-permission-level 0 to 4, clamped).
        // So no function can hold these commands. Every source that runs a command has a server: checked in full below.
        if (source.getServer() == null) return source.permissions() == net.minecraft.server.permissions.PermissionSet.NO_PERMISSIONS;
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
