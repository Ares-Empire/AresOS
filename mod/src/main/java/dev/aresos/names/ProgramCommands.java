package dev.aresos.names;

import com.mojang.brigadier.CommandDispatcher;
import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppSearch;
import dev.aresos.item.AppCommands;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import static com.mojang.brigadier.arguments.StringArgumentType.*;

/** /open for every listed program, /apps for My apps. Clicks use a stable ID, never a shell command. */
public final class ProgramCommands {
    /** What a clicked row runs (item/AppCommands): AresOS's own command, whoever owns /open. */
    public static final String CLICK = "/aresos app open ";
    private ProgramCommands() { }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        // Installed only where nothing has the name; a later registration of either takes the name whole (OwnedNodes).
        OwnedNodes.install(dispatcher, Commands.literal("open").requires(AppCommands::allowed)
                .then(Commands.argument("name", greedyString()).suggests((c, b) -> {
                    if (!AppCommands.allowed(c.getSource())) return b.buildFuture();
                    var apps = listed();
                    var reserved = SlashCommands.reserved(c.getSource().getServer());
                    var keys = new java.util.TreeSet<String>();
                    for (var app : apps) keys.addAll(OpenPrograms.keys(app, apps, reserved));
                    for (String key : keys) if (key.startsWith(NameRules.squeeze(b.getRemaining()))) b.suggest(key);
                    return b.buildFuture();
                }).executes(c -> open(c.getSource(), getString(c, "name")))));
        OwnedNodes.install(dispatcher, Commands.literal("apps").requires(AppCommands::allowed)
                .executes(c -> apps(c.getSource())));
    }

    private static int open(CommandSourceStack source, String query) {
        if (!AppCommands.allowed(source)) return 0;
        var found = OpenPrograms.find(listed(), query, SlashCommands.reserved(source.getServer()));
        if (found.isEmpty()) { source.sendFailure(Component.literal("No program matches \"" + query + "\".")); return 0; }
        if (found.size() == 1) return SlashCommands.launch(source, found.getFirst().id());
        source.sendSuccess(() -> Component.literal("Several programs match. Click one to open it:"), false);
        for (var app : found) source.sendSuccess(() -> line(app), false);
        return found.size();
    }

    private static int apps(CommandSourceStack source) {
        if (!AppCommands.allowed(source)) return 0;
        var mine = AresOs.apps().stream().filter(AppDefinition::mine).sorted(AppSearch.BY_NAME).toList();
        source.sendSuccess(() -> Component.literal("My apps: " + mine.size() + ". Click one to open it."), false);
        // Absent programs are listed too, as not installed: he sees why their commands are gone. The others say where
        // their logo stands, or why it does not (package 37).
        boolean complete = dev.aresos.hub.TownKeeper.complete();
        for (var app : mine) {
            String where = app.absent() ? null : dev.aresos.hub.Whereabouts.of(source.getServer(), app, complete).said(AppGroup.of(app));
            source.sendSuccess(() -> line(app, where), false);
        }
        return mine.size();
    }

    /** The programs the latest complete list from the system names; only these can be opened. */
    private static java.util.List<AppDefinition> listed() {
        return AresOs.apps().stream().filter(app -> !app.absent()).toList();
    }

    private static MutableComponent line(AppDefinition app) { return line(app, null); }

    /**
     * One clickable row. {@code where}: for {@code /apps}, where the app's logo stands in words ("Lunar Client:
     * /lunar. Games, east, front row, left") or why it has none; null for {@code /open}'s choices, which name the group.
     */
    private static MutableComponent line(AppDefinition app, String where) {
        // Still one of his apps, kept for its return, but nothing to open and no command while it is gone.
        if (app.absent()) return Component.literal(app.name()).withStyle(ChatFormatting.DARK_GRAY)
                .append(Component.literal("  not installed  · " + AppGroup.of(app).title()).withStyle(ChatFormatting.DARK_GRAY));
        String commands = app.mine() ? app.names().stream().map(name -> "/" + name).collect(java.util.stream.Collectors.joining(", ")) : "";
        String rest = where == null ? "  " + commands + "  · " + AppGroup.of(app).title()
                : ": " + (commands.isEmpty() ? "" : commands + ". ") + where;
        return Component.literal(app.name()).withStyle(ChatFormatting.AQUA)
                .append(Component.literal(rest).withStyle(ChatFormatting.GRAY))
                .withStyle(style -> style.withClickEvent(new ClickEvent.RunCommand(CLICK + app.id()))
                        .withHoverEvent(new HoverEvent.ShowText(Component.literal("Open " + app.name() + " (" + app.id() + ")"))));
    }
}
