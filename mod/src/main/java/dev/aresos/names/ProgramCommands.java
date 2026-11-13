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
    private ProgramCommands() { }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        if (dispatcher.getRoot().getChild("open") == null) dispatcher.register(Commands.literal("open").requires(AppCommands::allowed)
                .then(Commands.argument("name", greedyString()).suggests((c, b) -> {
                    if (!AppCommands.allowed(c.getSource())) return b.buildFuture();
                    var apps = AresOs.apps();
                    var reserved = SlashCommands.reserved(c.getSource().getServer());
                    var keys = new java.util.TreeSet<String>();
                    for (var app : apps) keys.addAll(OpenPrograms.keys(app, apps, reserved));
                    for (String key : keys) if (key.startsWith(NameRules.squeeze(b.getRemaining()))) b.suggest(key);
                    return b.buildFuture();
                }).executes(c -> open(c.getSource(), getString(c, "name")))));
        if (dispatcher.getRoot().getChild("apps") == null) dispatcher.register(Commands.literal("apps").requires(AppCommands::allowed)
                .executes(c -> apps(c.getSource())));
    }

    private static int open(CommandSourceStack source, String query) {
        if (!AppCommands.allowed(source)) return 0;
        var found = OpenPrograms.find(AresOs.apps(), query, SlashCommands.reserved(source.getServer()));
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
        for (var app : mine) source.sendSuccess(() -> line(app), false);
        return mine.size();
    }

    private static MutableComponent line(AppDefinition app) {
        String commands = app.mine() ? app.names().stream().map(name -> "/" + name).collect(java.util.stream.Collectors.joining(", ")) : "";
        return Component.literal(app.name()).withStyle(ChatFormatting.AQUA)
                .append(Component.literal("  " + commands + "  · " + AppGroup.of(app).title()).withStyle(ChatFormatting.GRAY))
                .withStyle(style -> style.withClickEvent(new ClickEvent.RunCommand("/open " + app.id()))
                        .withHoverEvent(new HoverEvent.ShowText(Component.literal("Open " + app.name() + " (" + app.id() + ")"))));
    }
}
