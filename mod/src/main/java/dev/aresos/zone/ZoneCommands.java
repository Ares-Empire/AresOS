package dev.aresos.zone;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.AresOs;
import dev.aresos.hub.HubData;
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
        return Commands.literal("logo")
                .then(Commands.literal("remove").then(Commands.argument("target", word()).suggests((c, b) -> {
                    b.suggest("here"); AresOs.apps().forEach(app -> b.suggest(app.id())); return b.buildFuture();
                }).executes(c -> removeLogo(c.getSource(), getString(c, "target")))))
                .then(appArgument()
                .executes(c -> gate(c.getSource(), getString(c, "app")))
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
                java.util.function.Predicate<AppZone> named = z -> target.equals("here") ? z.dimension().equals(player.level().dimension()) && z.box().intersects(player.getBoundingBox()) : z.app().equals(target);
                // A gate's zone goes with its blocks and its sign, never alone; the town's go with their logos.
                var town = data.zones().stream().filter(named).filter(z -> HubData.town(source.getServer(), z)).toList();
                long gates = data.zones().stream().filter(named).filter(AppZone::isGate).count();
                int removed = data.remove(z -> named.test(z) && !z.isGate() && !town.contains(z));
                message = "Removed " + removed + " zone(s). Logo blocks remain; removed zones no longer protect them."
                        + (gates > 0 ? " " + gates + " gate(s) stay: /aresos logo remove takes a gate down." : "")
                        + town.stream().map(z -> " " + townLogo(z.app())).collect(java.util.stream.Collectors.joining());
            } else {
                source.sendSuccess(() -> Component.literal("AresOS zones: " + data.zones().size()), false);
                for (var zone : data.zones()) source.sendSuccess(() -> Component.literal(zone.app() + " | " + zone.dimension().identifier()
                        + " | " + zone.min().toShortString() + " to " + zone.max().toShortString()
                        + " | exit " + zone.exit().position() + (zone.isGate() ? " | gate" : HubData.town(source.getServer(), zone) ? " | town" : "")), false);
                return 1;
            }
            source.sendSuccess(() -> Component.literal(message), false); return 1;
        } catch (IOException | IllegalArgumentException error) { source.sendFailure(Component.literal(error.getMessage())); return 0; }
    }

    private static int gate(CommandSourceStack source, String id) throws CommandSyntaxException {
        var player = host(source); if (player == null) return 0;
        var app = AresOs.app(id);
        if (app == null) { source.sendFailure(Component.literal("Unknown AresOS app")); return 0; }
        try {
            var built = GateBuilder.build(player.level(), id, GateBuilder.planInFrontOf(player, app));
            boolean doormat = built.gate().map(gate -> !gate.ground().isEmpty()).orElse(false);
            source.sendSuccess(() -> Component.literal("Built the gate of " + app.name() + ". Step into its doorway to open it; closing it puts you back here."
                    + (doormat ? "" : " No doormat: the floor at the door isn't untouched ground.")
                    + " /aresos logo remove " + id + " takes it down."), false);
            return 1;
        } catch (IOException | RuntimeException error) { source.sendFailure(Component.literal("Logo refused: " + error.getMessage())); return 0; }
    }

    /** Takes down the gates of an app, or the one he stands at. An older wall or floor only loses its zone, as with `zone remove`. */
    private static int removeLogo(CommandSourceStack source, String target) throws CommandSyntaxException {
        var player = host(source); if (player == null) return 0;
        var data = ZoneData.get(source.getServer());
        boolean here = target.equals("here");
        var town = data.zones().stream().filter(zone -> HubData.town(source.getServer(), zone))
                .filter(zone -> !here ? zone.app().equals(target) : zone.dimension().equals(player.level().dimension())
                        && zone.area().intersects(player.getBoundingBox())).toList();
        // The town's logos are the town's: this command leaves them standing and says what takes one down.
        for (var zone : town) source.sendFailure(Component.literal(townLogo(zone.app())));
        var logos = data.zones().stream().filter(zone -> zone.isGate() || !zone.blocks().isEmpty())
                .filter(zone -> !here ? zone.app().equals(target) : zone.dimension().equals(player.level().dimension())
                        && (zone.isGate() ? zone.area() : zone.box()).intersects(player.getBoundingBox())).toList();
        if (logos.isEmpty() && !town.isEmpty()) return 0;
        if (logos.isEmpty()) {
            source.sendFailure(Component.literal(here ? "No logo here. Stand at its door, or name the app." : "No logo of " + target + " stands in this world."));
            return 0;
        }
        int done = 0;
        for (var zone : logos) {
            if (!zone.isGate()) {
                data.remove(saved -> saved.id().equals(zone.id()));
                source.sendSuccess(() -> Component.literal("Removed the zone of " + zone.app() + "'s older wall or floor logo. Its blocks stay and are no longer protected."), false);
                done++;
                continue;
            }
            try {
                var removal = GateBuilder.remove(source.getServer(), zone);
                source.sendSuccess(() -> Component.literal("Took down the gate of " + zone.app() + ": " + removal.removed() + " blocks removed"
                        + (removal.kept() > 0 ? ", " + removal.kept() + " that you changed stay." : ".")), false);
                done++;
            } catch (IOException | RuntimeException error) { source.sendFailure(Component.literal(error.getMessage())); }
        }
        return done;
    }

    /** What he is told when a zone command meets a logo of the town. */
    static String townLogo(String app) {
        var definition = AresOs.app(app);
        return "The logo of " + (definition == null ? app : definition.name()) + " belongs to the town and stays: /aresos app remove "
                + app + " takes it down.";
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
