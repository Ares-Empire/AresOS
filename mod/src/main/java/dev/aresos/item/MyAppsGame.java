package dev.aresos.item;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.AppsConfig;
import dev.aresos.icon.IconRefresh;
import dev.aresos.icon.PixelIconConverter;
import dev.aresos.mode.LiveMode;
import dev.aresos.mode.ModeInventories;
import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;

import java.io.IOException;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * My apps in the running game (docs/design/HUB.md 2.4): adding and removing an app, a program that joins by
 * itself, and the moment the inventories follow.
 *
 * Nothing here edits an inventory on the spot. A change only raises a counter; each tick every player whose
 * inventories are behind is brought in step if that is safe right now ({@link #tidy}), and otherwise on a later
 * tick. What is his is saved in the apps file before the counter moves, so work that was still due when the game
 * closed is done after the next login.
 */
public final class MyAppsGame {
    /** How far one player's inventories are: the counter value his removals and his items were last done for. */
    private static final class Seen {
        long removed, added, attempted;
        Set<String> without = Set.of();
    }

    private static final int NEWS_AT_ONCE = 5;
    private static final AtomicLong CHANGES = new AtomicLong(1);
    // Server thread only.
    private static final Map<UUID, Seen> SEEN = new HashMap<>();
    // Written by the helper's thread, read by the server's.
    private static final Queue<String> NEWS = new ConcurrentLinkedQueue<>();
    private static final IconRefresh ICONS = new IconRefresh(AresOs::iconPackPath, new PixelIconConverter(),
            Duration.ofSeconds(5), () -> AresOs.generatedIcons, pictures -> {
                AresOs.generatedIcons = pictures;
                // The items in the inventory still name their old look.
                changed();
            });

    private MyAppsGame() { }

    static void register() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            // The counter is only in memory. A previous session may have saved either inventory before a
            // deferred removal ran, or the apps file may have moved here from another machine.
            SEEN.put(handler.player.getUUID(), new Seen());
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> SEEN.remove(handler.player.getUUID()));
        ServerTickEvents.END_SERVER_TICK.register(MyAppsGame::tick);
    }

    /** The icon pack of the running game; the client hangs its resource reload on it. */
    public static IconRefresh icons() { return ICONS; }

    /** Any thread: what is his, or what an item looks like, changed. The inventories follow on a tick. */
    public static void changed() { CHANGES.incrementAndGet(); }

    /** Any thread: a complete program list went into the apps file. */
    public static void listed(AppsConfig.Merged merged) {
        if (merged.joined().isEmpty()) return;
        // Day one fills My apps quietly; a program that turns up later is announced by name.
        if (!merged.dayOne()) for (String id : merged.joined())
            merged.apps().stream().filter(app -> app.id().equals(id)).findFirst()
                    .ifPresent(app -> NEWS.add(app.name() + " is new and joined My apps."));
        changed();
    }

    /** Any thread: the list or a picture may have changed while the game runs; the pixel icons follow. */
    public static void pictures(List<AppDefinition> apps) { ICONS.request(apps); }

    /** Makes a program one of his. Returns the line for the chat; throws with the reason when it cannot be done. */
    public static String add(ServerPlayer host, String id) throws IOException {
        var app = AresOs.app(id);
        if (app == null) throw new IOException("Unknown AresOS app");
        if (app.mine()) return app.name() + " is already one of your apps.";
        AresOs.saveMine(Map.of(id, true));
        changed();
        tick(host.level().getServer());
        if (AppInventory.has(host, id)) return "Added " + app.name() + " to My apps.";
        if (!LiveMode.isLive(host)) return "Added " + app.name() + " to My apps. Its item comes in Live mode.";
        // No free slot (said by the tidy-up itself), or his inventory is busy and the item comes in a moment.
        return "Added " + app.name() + " to My apps.";
    }

    /** Takes an app out of My apps; it stays in All programs with everything saved about it. */
    public static String remove(ServerPlayer host, String id) throws IOException {
        var app = AresOs.app(id);
        if (app == null) throw new IOException("Unknown AresOS app");
        if (!app.mine()) return app.name() + " is not one of your apps.";
        AresOs.saveMine(Map.of(id, false));
        changed();
        tick(host.level().getServer());
        return "Removed " + app.name() + " from My apps. It stays in All programs.";
    }

    /**
     * The Apps screen's click: the same change as the command, for the host in an AresOS world. The line goes to
     * the chat; the screen shows it too while it covers the chat.
     */
    static void asked(ServerPlayer player, String id, boolean mine) {
        var server = player.level().getServer();
        if (!DesktopWorld.isHost(server, player) || !DesktopWorld.isEnabled(server)) return;
        String said;
        try { said = mine ? add(player, id) : remove(player, id); }
        catch (IOException | RuntimeException error) { said = failure(error); }
        player.sendSystemMessage(Component.literal(said));
    }

    /** Why My apps could not be changed. The apps file is written whole or not at all, so nothing changed. */
    static String failure(Exception error) {
        return error instanceof IOException ? error.getMessage() : "Could not change My apps: " + error.getMessage();
    }

    /** {@code /aresos give}: what is in his inventory is his, so giving a program that is not his makes it his. */
    public static boolean own(net.minecraft.commands.CommandSourceStack source, AppDefinition app) {
        if (app.mine()) return true;
        try {
            AresOs.saveMine(Map.of(app.id(), true));
            changed();
            return true;
        } catch (IOException | RuntimeException error) {
            source.sendFailure(Component.literal("Could not change My apps: " + error.getMessage()));
            return false;
        }
    }

    /** Once per server tick; also called right after a change, so the usual case shows at once. */
    public static void tick(MinecraftServer server) {
        if (!DesktopWorld.isEnabled(server)) return;
        long now = CHANGES.get();
        for (ServerPlayer player : List.copyOf(server.getPlayerList().getPlayers())) {
            var seen = SEEN.get(player.getUUID());
            if (seen != null && (seen.removed != now || seen.added != now)) tidy(player, seen, now);
        }
        if (!NEWS.isEmpty()) for (ServerPlayer player : server.getPlayerList().getPlayers())
            if (DesktopWorld.isHost(server, player)) {
                tell(player);
                break;
            }
    }

    /**
     * Brings one player's two inventories in step with My apps, if that is safe now. Not during a mode switch and
     * not with a container open, an item on the cursor or in the crafting grid: the moments a mode switch itself
     * refuses. Then nothing is touched and the work stays due.
     */
    private static void tidy(ServerPlayer player, Seen seen, long now) {
        var modes = ModeInventories.of(player);
        if (modes.pending() || modes.changingMode() || player.containerMenu != player.inventoryMenu
                || !player.inventoryMenu.getCarried().isEmpty() || !player.inventoryMenu.getCraftSlots().isEmpty()) return;
        var apps = AresOs.apps();
        if (seen.removed != now) {
            AppInventory.sweep(player, apps);
            try {
                modes.mapInactive(player, stack -> AppInventory.notHis(stack, apps) ? ItemStack.EMPTY : stack);
            } catch (RuntimeException error) {
                // A saved inventory that cannot be read is kept word for word (ModeInventories); trying again
                // every tick would not change that.
                AresOs.LOGGER.error("Could not take app items out of {}'s saved inventory; it stays as it was",
                        player.getName().getString(), error);
            }
            seen.removed = now;
        }
        // Items are only ever put into the Live inventory, and only while he holds it.
        if (seen.added != now && LiveMode.isLive(player)) {
            // Keep missing work due. While still full there is nothing to do; the first safe tick with room
            // retries without needing a catalogue edit or a login (also for a returned cursor item).
            if (seen.attempted == now && !seen.without.isEmpty()) {
                boolean room = false;
                for (int slot = 9; slot < 36; slot++) room |= player.getInventory().getItem(slot).isEmpty();
                if (!room) return;
            }
            var without = AppInventory.reconcile(player, apps);
            seen.attempted = now;
            if (without.isEmpty()) seen.added = now;
            var names = without.stream().filter(app -> !seen.without.contains(app.id())).map(AppDefinition::name).toList();
            seen.without = without.stream().map(AppDefinition::id).collect(Collectors.toUnmodifiableSet());
            if (!names.isEmpty()) player.sendSystemMessage(Component.literal("No free inventory slot: "
                    + String.join(", ", names) + (names.size() == 1 ? " has" : " have") + " no item for now."));
        }
    }

    private static void tell(ServerPlayer host) {
        for (int line = 0; line < NEWS_AT_ONCE; line++) {
            String news = NEWS.poll();
            if (news == null) return;
            host.sendSystemMessage(Component.literal(news));
        }
        int more = 0;
        while (NEWS.poll() != null) more++;
        if (more > 0) host.sendSystemMessage(Component.literal("And " + more + " more new programs joined My apps."));
    }
}
