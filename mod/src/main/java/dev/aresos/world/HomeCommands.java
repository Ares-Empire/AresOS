package dev.aresos.world;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;

import java.util.Locale;
import java.util.Set;

public final class HomeCommands {
    private HomeCommands() { }

    public static LiteralArgumentBuilder<CommandSourceStack> command() {
        return Commands.literal("home").executes(context -> execute(context.getSource(), "go"))
                .then(Commands.literal("set").executes(context -> execute(context.getSource(), "set")))
                .then(Commands.literal("info").executes(context -> execute(context.getSource(), "info")));
    }

    private static int execute(CommandSourceStack source, String action) throws CommandSyntaxException {
        var player = source.getPlayerOrException();
        var server = source.getServer();
        if (!DesktopWorld.isHost(server, player)) {
            source.sendFailure(Component.literal("Only the singleplayer host can use AresOS home commands"));
            return 0;
        }
        if (!DesktopWorld.isEnabled(server)) {
            source.sendFailure(Component.literal("Not an AresOS world"));
            return 0;
        }
        var data = NetherHome.get(server);
        // A marked ordinary desktop may opt into a home, but unreadable provisioned saves stay untouched.
        if (data == null && (!action.equals("set") || java.nio.file.Files.exists(
                server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).resolve(NetherHome.MANIFEST)))) {
            source.sendFailure(Component.literal("No readable AresOS home. Set a home in a marked desktop, or restore the complete AresHub backup."));
            return 0;
        }
        if (action.equals("set")) {
            if (!HomeSites.isSafe(player.level(), player.position())) {
                source.sendFailure(Component.literal("Home not set: stand on solid ground with clear feet and head, away from lava and fire."));
                return 0;
            }
            data = NetherHome.recordHome(server, new NetherHome.Home(player.level().dimension(), player.position(),
                    Mth.wrapDegrees(player.getYRot()), Mth.clamp(player.getXRot(), -90, 90)));
            NetherHome.setRespawn(player, data);
            server.saveEverything(false, true, true);
            String message = "AresOS home set. " + describe(data);
            source.sendSuccess(() -> Component.literal(message), false);
        } else if (action.equals("info")) {
            String message = describe(data);
            source.sendSuccess(() -> Component.literal(message), false);
        } else {
            var home = data.home();
            var level = server.getLevel(home.dimension());
            if (level == null) {
                source.sendFailure(Component.literal("Home dimension is unavailable; home was kept."));
                return 0;
            }
            player.stopRiding();
            player.teleportTo(level, home.position().x, home.position().y, home.position().z, Set.of(), home.yaw(), home.pitch(), false);
            player.setDeltaMovement(Vec3.ZERO);
            player.fallDistance = 0;
            player.clearFire();
            NetherHome.setRespawn(player, data);
        }
        return 1;
    }

    private static String describe(NetherHome data) {
        var home = data.home();
        return String.format(Locale.ROOT, "Seed: %d | Home: %.3f, %.3f, %.3f | %s | Facing: %.1f, %.1f",
                data.site().seed(), home.position().x, home.position().y, home.position().z,
                home.dimension().identifier(), home.yaw(), home.pitch());
    }
}
