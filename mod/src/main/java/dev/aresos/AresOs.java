package dev.aresos;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ToggleModePayload;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.NetherHome;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.commands.Commands;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;

public final class AresOs implements ModInitializer {
    public static final Logger LOGGER = LoggerFactory.getLogger("aresos");
    private static List<AppDefinition> apps = AppsConfig.defaults();

    public static Identifier id(String path) {
        return Identifier.fromNamespaceAndPath("aresos", path);
    }

    public static List<AppDefinition> apps() {
        return apps;
    }

    public static AppDefinition app(String id) {
        return apps.stream().filter(app -> app.id().equals(id)).findFirst().orElse(null);
    }

    @Override
    public void onInitialize() {
        try {
            var loaded = AppsConfig.load(FabricLoader.getInstance().getConfigDir().resolve("aresos/apps.json"));
            apps = loaded.apps();
            if (loaded.brokenBackup() != null) {
                LOGGER.warn("Invalid apps.json; using defaults. Original saved at {}", loaded.brokenBackup());
            }
        } catch (IOException error) {
            LOGGER.error("Cannot read/write apps.json; using defaults in memory and leaving the file intact", error);
        }
        AppItems.register();
        LiveMode.register();
        NetherHome.register();
        PayloadTypeRegistry.serverboundPlay().register(ToggleModePayload.TYPE, ToggleModePayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(ToggleModePayload.TYPE,
                (payload, context) -> LiveMode.toggleForHost(context.server(), context.player()));
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
                AppItems.placePinned(handler.player, apps));
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) -> {
            if (!environment.includeIntegrated) return;
            dispatcher.register(Commands.literal("aresos")
                        .then(dev.aresos.world.HomeCommands.command())
                        .then(Commands.literal("desktop")
                                .then(Commands.literal("on").executes(context -> desktop(context.getSource(), true)))
                                .then(Commands.literal("off").executes(context -> desktop(context.getSource(), false))))
                        .then(Commands.literal("give").then(Commands.argument("app", word())
                                .suggests((context, builder) -> {
                                    apps.forEach(app -> builder.suggest(app.id()));
                                    return builder.buildFuture();
                                }).executes(context -> {
                                    var source = context.getSource();
                                    var player = source.getPlayerOrException();
                                    if (!DesktopWorld.isHost(source.getServer(), player)) {
                                        source.sendFailure(Component.literal("Only the singleplayer host can give apps"));
                                        return 0;
                                    }
                                    if (!DesktopWorld.isEnabled(source.getServer())) {
                                        source.sendFailure(Component.literal("Not an AresOS world"));
                                        return 0;
                                    }
                                    AppDefinition app = app(getString(context, "app"));
                                    if (app == null) {
                                        context.getSource().sendFailure(Component.literal("Unknown AresOS app"));
                                        return 0;
                                    }
                                    if (!player.getInventory().add(AppItems.create(app))) {
                                        context.getSource().sendFailure(Component.literal("Inventory is full"));
                                        return 0;
                                    }
                                    return 1;
                                }))));
        });
    }

    private static int desktop(CommandSourceStack source, boolean enabled) throws CommandSyntaxException {
        var player = source.getPlayerOrException();
        if (!DesktopWorld.isHost(source.getServer(), player)) {
            source.sendFailure(Component.literal("Only the singleplayer host can change the desktop marker"));
            return 0;
        }
        DesktopWorld.setEnabled(source.getServer(), enabled);
        source.sendSuccess(() -> Component.literal("AresOS desktop " + (enabled ? "on" : "off")), false);
        return 1;
    }
}
