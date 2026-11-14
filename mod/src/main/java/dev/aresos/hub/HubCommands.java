package dev.aresos.hub;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.item.AppCommands;
import dev.aresos.world.DesktopWorld;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

/** {@code /aresos hub rebuild}: the town built again from the rules (HUB.md 2.5). */
public final class HubCommands {
    private HubCommands() { }

    public static LiteralArgumentBuilder<CommandSourceStack> hub() {
        // Host-only where it is parsed, like /aresos app since package 35: no command block, function or other
        // player reaches it. The host is checked again when it runs.
        return Commands.literal("hub").requires(AppCommands::allowed)
                .then(Commands.literal("rebuild").executes(context -> rebuild(context.getSource())));
    }

    private static int rebuild(CommandSourceStack source) throws CommandSyntaxException {
        var player = source.getPlayerOrException();
        var server = source.getServer();
        if (!DesktopWorld.isHost(server, player)) return refuse(source, "Only the singleplayer host can rebuild the town.");
        var hub = HubData.get(server);
        if (hub == null) return refuse(source, "This world is not a flat home: it has no town to rebuild.");
        if (!HubLayout.LOOK.equals(hub.look()))
            return refuse(source, "This town was built by other rules (" + hub.look() + "). This AresOS cannot rebuild it.");
        // Taking logos down needs the list that says which apps are installed, as every pass of the town does.
        if (!TownKeeper.complete())
            return refuse(source, "The town waits for the system's list of programs. Nothing was rebuilt; try again in a moment.");
        // Its line goes to his chat with the town's other lines.
        TownKeeper.rebuild(server);
        return 1;
    }

    private static int refuse(CommandSourceStack source, String why) {
        source.sendFailure(Component.literal(why));
        return 0;
    }
}
