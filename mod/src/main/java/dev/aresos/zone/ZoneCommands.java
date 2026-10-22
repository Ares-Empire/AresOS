package dev.aresos.zone;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.HomeSites;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;

public final class ZoneCommands {
    private record Selection(ResourceKey<Level> dimension, BlockPos first, BlockPos second) { }
    private static final Map<ServerPlayer, Selection> SELECTIONS = new WeakHashMap<>();
    private ZoneCommands() { }

    public static LiteralArgumentBuilder<CommandSourceStack> zone() {
        return Commands.literal("zone")
                .then(Commands.literal("pos1").executes(c -> execute(c.getSource(), "pos1", "")))
                .then(Commands.literal("pos2").executes(c -> execute(c.getSource(), "pos2", "")))
                .then(Commands.literal("set").then(appArgument().executes(c -> execute(c.getSource(), "set", getString(c, "app")))))
                .then(Commands.literal("list").executes(c -> execute(c.getSource(), "list", "")))
                .then(Commands.literal("remove").then(Commands.argument("target", word()).suggests((c, b) -> {
                    b.suggest("here"); AresOs.apps().forEach(app -> b.suggest(app.id())); return b.buildFuture();
                }).executes(c -> execute(c.getSource(), "remove", getString(c, "target")))));
    }

    public static LiteralArgumentBuilder<CommandSourceStack> logo() {
        return Commands.literal("logo").then(appArgument()
                .executes(c -> build(c.getSource(), getString(c, "app"), false))
                .then(Commands.literal("wall").executes(c -> build(c.getSource(), getString(c, "app"), false)))
                .then(Commands.literal("floor").executes(c -> build(c.getSource(), getString(c, "app"), true))));
    }

    private static com.mojang.brigadier.builder.RequiredArgumentBuilder<CommandSourceStack, String> appArgument() {
        return Commands.argument("app", word()).suggests((c, b) -> { AresOs.apps().forEach(app -> b.suggest(app.id())); return b.buildFuture(); });
    }

    private static ServerPlayer host(CommandSourceStack source) throws CommandSyntaxException {
        var player = source.getPlayerOrException();
        if (!DesktopWorld.isHost(source.getServer(), player)) {
            source.sendFailure(Component.literal("Only the singleplayer host can edit AresOS zones")); return null;
        }
        if (!DesktopWorld.isEnabled(source.getServer())) { source.sendFailure(Component.literal("Not an AresOS world")); return null; }
        return player;
    }

    private static int execute(CommandSourceStack source, String action, String target) throws CommandSyntaxException {
        var player = host(source); if (player == null) return 0;
        var data = ZoneData.get(source.getServer());
        try {
            String message;
            if (action.startsWith("pos")) {
                var old = SELECTIONS.get(player);
                if (old == null || !old.dimension.equals(player.level().dimension())) old = new Selection(player.level().dimension(), null, null);
                SELECTIONS.put(player, new Selection(old.dimension, action.equals("pos1") ? player.blockPosition() : old.first,
                        action.equals("pos2") ? player.blockPosition() : old.second));
                message = action + " = " + player.blockPosition().toShortString() + ". Corners are inclusive feet blocks. Stand outside on safe ground before zone set (this saves the exit).";
            } else if (action.equals("set")) {
                if (AresOs.app(target) == null) throw new IOException("Unknown AresOS app");
                var selection = SELECTIONS.get(player);
                if (selection == null || selection.first == null || selection.second == null || !selection.dimension.equals(player.level().dimension()))
                    throw new IOException("Set pos1 and pos2 in this dimension first.");
                var a = selection.first; var b = selection.second;
                var min = new BlockPos(Math.min(a.getX(), b.getX()), Math.min(a.getY(), b.getY()), Math.min(a.getZ(), b.getZ()));
                var max = new BlockPos(Math.max(a.getX(), b.getX()), Math.max(a.getY(), b.getY()), Math.max(a.getZ(), b.getZ()));
                if (max.getX() - (long)min.getX() >= 64 || max.getY() - (long)min.getY() >= 64 || max.getZ() - (long)min.getZ() >= 64)
                    throw new IOException("Zone must be at most 64 blocks on each axis.");
                if (!HomeSites.isSafe(player.level(), player.position())) throw new IOException("Stand outside on safe solid ground to save the exit point.");
                var box = new AABB(min.getX(), min.getY(), min.getZ(), max.getX() + 1, max.getY() + 1, max.getZ() + 1);
                data.add(new AppZone(UUID.randomUUID().toString(), target, selection.dimension, min, max,
                        AppZone.exit(selection.dimension, player.position(), box), List.of()));
                message = "Zone saved for " + target + ". Your current position is its exit, facing the zone.";
            } else if (action.equals("remove")) {
                int removed = data.remove(z -> target.equals("here") ? z.dimension().equals(player.level().dimension()) && z.box().intersects(player.getBoundingBox()) : z.app().equals(target));
                message = "Removed " + removed + " zone(s). Logo blocks remain; removed zones no longer protect them.";
            } else {
                source.sendSuccess(() -> Component.literal("AresOS zones: " + data.zones().size()), false);
                for (var zone : data.zones()) source.sendSuccess(() -> Component.literal(zone.app() + " | " + zone.dimension().identifier()
                        + " | " + zone.min().toShortString() + " to " + zone.max().toShortString()
                        + " | exit " + zone.exit().position()), false);
                return 1;
            }
            source.sendSuccess(() -> Component.literal(message), false); return 1;
        } catch (IOException | IllegalArgumentException error) { source.sendFailure(Component.literal(error.getMessage())); return 0; }
    }

    private static int build(CommandSourceStack source, String id, boolean floor) throws CommandSyntaxException {
        var player = host(source); if (player == null) return 0;
        var app = AresOs.app(id);
        if (app == null) { source.sendFailure(Component.literal("Unknown AresOS app")); return 0; }
        try {
            var image = LogoBuilder.readIcon(app);
            LogoBuilder.build(player, LogoBuilder.plan(player, id, image, floor));
            source.sendSuccess(() -> Component.literal("Built " + image.width() + "x" + image.height() + " " + (floor ? "floor" : "wall")
                    + " logo for " + id + ". Zone saved; return exit is where you stood."), false);
            return 1;
        } catch (IOException | RuntimeException error) { source.sendFailure(Component.literal("Logo refused: " + error.getMessage())); return 0; }
    }
}
