package dev.aresos;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ToggleModePayload;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.NetherHome;
import net.fabricmc.api.EnvType;
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
import java.time.Duration;
import java.util.List;
import java.nio.file.Path;
import java.util.Locale;
import java.util.Set;
import dev.aresos.catalogue.WindowsAppCatalogue;
import dev.aresos.catalogue.LinuxAppCatalogue;
import dev.aresos.icon.IconPack;
import dev.aresos.icon.PixelIconConverter;
import dev.aresos.item.AppInventory;
import dev.aresos.shell.ShellClient;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.word;

public final class AresOs implements ModInitializer {
    public static final Logger LOGGER = LoggerFactory.getLogger("aresos");
    private static volatile List<AppDefinition> apps = List.of();
    private static String configError;
    private static String discoveryError;
    // The apps that have a pixel icon the game can draw; swapped whole (item/MyAppsGame, icon/IconRefresh).
    public static volatile Set<String> generatedIcons = Set.of();
    private static final Duration HELPER_WAIT = Duration.ofSeconds(5);
    private static ShellClient shell;

    public static Path configPath() {
        return Path.of(System.getProperty("aresos.appsConfig", FabricLoader.getInstance().getConfigDir().resolve("aresos/apps.json").toString()));
    }

    public static Path iconPackPath() {
        return FabricLoader.getInstance().getGameDir().resolve("aresos-runtime/app-icons");
    }

    public static synchronized void savePins(java.util.Map<String, Boolean> changes) throws IOException {
        apps = AppsConfig.pins(configPath(), changes);
    }

    /** The AresOS app helper connection; null on Windows and on dedicated servers. */
    public static ShellClient shell() {
        return shell;
    }

    public static synchronized void saveMine(java.util.Map<String, Boolean> changes) throws IOException {
        apps = AppsConfig.mine(configPath(), changes);
    }

    /** One complete program list from the helper goes into the apps file; My apps follows (item/MyAppsGame). */
    private static synchronized void takeIn(List<AppDefinition> listed) throws IOException {
        var merged = AppsConfig.merge(configPath(), listed, shell.detailed(), java.time.LocalDate.now());
        apps = merged.apps();
        dev.aresos.item.MyAppsGame.listed(merged);
    }

    private static synchronized void mergeHelperApps(List<ShellClient.App> listed) {
        try {
            takeIn(LinuxAppCatalogue.definitions(listed));
            dev.aresos.item.MyAppsGame.pictures(apps);
        } catch (IOException | RuntimeException error) {
            LOGGER.error("Could not merge apps from the AresOS app helper; existing catalogue kept", error);
        }
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
                LOGGER.info("Moved apps.json to schema {}; original saved at {}", AppsConfig.SCHEMA, loaded.migrationBackup());
            }
            boolean discovery = !Boolean.getBoolean("aresos.disableDiscovery");
            if (!windows && FabricLoader.getInstance().getEnvironmentType() == EnvType.CLIENT) {
                // On AresOS only the OS app helper opens apps; the session supervisor provides its socket and nonce.
                shell = ShellClient.fromEnvironment(System.getenv(), ShellClient.Settings.DEFAULT);
                shell.start();
            }
            if (discovery && (windows || shell != null)) {
                try {
                    if (windows) apps = AppsConfig.merge(configPath(), new WindowsAppCatalogue(
                            FabricLoader.getInstance().getGameDir().resolve("aresos-runtime/discovery"), apps).listApps());
                    else takeIn(new LinuxAppCatalogue(shell, HELPER_WAIT).listApps());
                } catch (ShellClient.ShellException helper) {
                    // Reported in game from the connection status; apps stay as configured until the helper answers.
                    LOGGER.warn("AresOS app helper not available at startup: {}", helper.getMessage());
                } catch (IOException | RuntimeException error) {
                    discoveryError = error.getMessage();
                    LOGGER.error("App discovery failed; existing catalogue kept intact", error);
                }
                if (shell != null) shell.addListener(new ShellClient.Listener() {
                    @Override public void apps(List<ShellClient.App> listed) { mergeHelperApps(listed); }
                });
            }
            try { generatedIcons = IconPack.generate(iconPackPath(), apps, new PixelIconConverter()).generated(); }
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
            var helper = shell == null ? null : shell.status();
            if (helper != null && helper.state() != ShellClient.State.CONNECTED && DesktopWorld.isEnabled(server))
                handler.player.sendSystemMessage(Component.literal(helper.state() == ShellClient.State.INCOMPATIBLE
                        ? "AresOS apps can't open: the app helper is incompatible (" + helper.detail() + ")"
                        : "AresOS apps can't open right now: the app helper is unavailable (" + helper.detail() + ")"));
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) -> {
            if (!environment.includeIntegrated) return;
            dispatcher.register(Commands.literal("aresos")
                        .then(dev.aresos.world.HomeCommands.command())
                        .then(dev.aresos.zone.ZoneCommands.zone())
                        .then(dev.aresos.zone.ZoneCommands.logo())
                        .then(dev.aresos.item.AppCommands.app())
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
                                    return AppInventory.give(source, app);
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
