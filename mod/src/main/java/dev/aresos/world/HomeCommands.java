package dev.aresos.world;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;

import java.util.Locale;
import java.util.Set;

public final class HomeCommands {
    private static final String NO_HOME = "No readable AresOS home. Set a home in a marked desktop, or restore the complete AresHub backup.";

    private HomeCommands() { }

    /** {@code /home} (package 37): exactly what {@code /aresos home} does. */
    public static int home(CommandSourceStack source) throws CommandSyntaxException {
        return execute(source, "go");
    }

    /**
     * The H key (package 37): the same as {@code /aresos home}, from the keyboard. Only for the host of an AresOS
     * world (the client sends it only there); a refusal shows above the hotbar.
     */
    public static void key(ServerPlayer player) {
        var server = player.level().getServer();
        if (!DesktopWorld.isHost(server, player) || !DesktopWorld.isEnabled(server)) return;
        var data = NetherHome.get(server);
        String refusal = data == null ? NO_HOME : goHome(player, data);
        if (refusal != null) player.sendSystemMessage(Component.literal(refusal), true);
    }

    /** Moves him and nothing else: off any mount, standing still, not falling, not burning. */
    public static void teleport(ServerPlayer player, ServerLevel level, Vec3 position, float yaw, float pitch) {
        player.stopRiding();
        player.teleportTo(level, position.x, position.y, position.z, Set.of(), yaw, pitch, false);
        player.setDeltaMovement(Vec3.ZERO);
        player.fallDistance = 0;
        player.clearFire();
    }

    /** To the home spot, from any dimension, its respawn point kept with it. Null when he arrived; otherwise why not. */
    private static String goHome(ServerPlayer player, NetherHome data) {
        var home = data.home();
        var level = player.level().getServer().getLevel(home.dimension());
        if (level == null) return "Home dimension is unavailable; home was kept.";
        teleport(player, level, home.position(), home.yaw(), home.pitch());
        NetherHome.setRespawn(player, data);
        return null;
    }

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
            source.sendFailure(Component.literal(NO_HOME));
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
            String refusal = goHome(player, data);
            if (refusal != null) {
                source.sendFailure(Component.literal(refusal));
                return 0;
            }
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
