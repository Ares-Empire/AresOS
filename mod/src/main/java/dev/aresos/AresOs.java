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
import java.nio.file.Path;
import java.util.Locale;
import java.util.Set;
import dev.aresos.catalogue.WindowsAppCatalogue;
import dev.aresos.catalogue.LinuxAppCatalogue;
import dev.aresos.icon.IconPack;
import dev.aresos.icon.PixelIconConverter;
import dev.aresos.item.AppInventory;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;

public final class AresOs implements ModInitializer {
    public static final Logger LOGGER = LoggerFactory.getLogger("aresos");
    private static volatile List<AppDefinition> apps = List.of();
    private static String configError;
    private static String discoveryError;
    public static Set<String> generatedIcons = Set.of();

    public static Path configPath() {
        return Path.of(System.getProperty("aresos.appsConfig", FabricLoader.getInstance().getConfigDir().resolve("aresos/apps.json").toString()));
    }

    public static Path iconPackPath() {
        return FabricLoader.getInstance().getGameDir().resolve("aresos-runtime/app-icons");
    }

    public static void savePins(java.util.Map<String, Boolean> changes) throws IOException {
        apps = AppsConfig.pins(configPath(), changes);
    }

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
            boolean windows = System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("windows");
            var loaded = AppsConfig.load(configPath(), !windows);
            apps = loaded.apps();
            if (loaded.migrationBackup() != null) {
                LOGGER.info("Migrated apps.json to schema 2; original saved at {}", loaded.migrationBackup());
            }
            if (!Boolean.getBoolean("aresos.disableDiscovery")) {
                try {
                    var catalogue = windows ? new WindowsAppCatalogue(FabricLoader.getInstance().getGameDir().resolve("aresos-runtime/discovery"), apps)
                            : new LinuxAppCatalogue();
                    apps = AppsConfig.merge(configPath(), catalogue.listApps());
                } catch (IOException | RuntimeException error) {
                    discoveryError = error.getMessage();
                    LOGGER.error("App discovery failed; existing catalogue kept intact", error);
                }
            }
            try { generatedIcons = IconPack.generate(iconPackPath(), apps, new PixelIconConverter()); }
            catch (IOException error) { LOGGER.error("Cannot write icon cache; using configured vanilla looks", error); }
        } catch (IOException error) {
            configError = error.getMessage();
            LOGGER.error("Cannot load app catalogue; apps disabled and original file left intact", error);
        }
        AppItems.register();
        LiveMode.register();
        NetherHome.register();
        dev.aresos.zone.WalkInZones.register();
        PayloadTypeRegistry.serverboundPlay().register(ToggleModePayload.TYPE, ToggleModePayload.CODEC);
        PayloadTypeRegistry.clientboundPlay().register(dev.aresos.mode.ModeSwitchStatePayload.TYPE, dev.aresos.mode.ModeSwitchStatePayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(dev.aresos.mode.ModeSwitchAckPayload.TYPE, dev.aresos.mode.ModeSwitchAckPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(dev.aresos.mode.ModeSwitchAckPayload.TYPE,
                (payload, context) -> dev.aresos.mode.ModeInventories.of(context.player()).acknowledge(payload.transaction()));
        ServerPlayNetworking.registerGlobalReceiver(ToggleModePayload.TYPE,
                (payload, context) -> {
                    if (!LiveMode.toggleForHost(context.server(), context.player()))
                        dev.aresos.mode.ModeInventories.of(context.player()).rejectToggle(context.player());
                });
        AppInventory.register();
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            dev.aresos.mode.ModeInventories.of(handler.player).reportLoginError(handler.player);
            if (!dev.aresos.mode.ModeInventories.of(handler.player).restoredForLogin()) AppInventory.populate(handler.player);
            if (configError != null) handler.player.sendSystemMessage(Component.literal("AresOS apps disabled: " + configError));
            if (discoveryError != null) handler.player.sendSystemMessage(Component.literal("App discovery failed; existing apps kept. " + discoveryError));
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) -> {
            if (!environment.includeIntegrated) return;
            dispatcher.register(Commands.literal("aresos")
                        .then(dev.aresos.world.HomeCommands.command())
                        .then(dev.aresos.zone.ZoneCommands.zone())
                        .then(dev.aresos.zone.ZoneCommands.logo())
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
