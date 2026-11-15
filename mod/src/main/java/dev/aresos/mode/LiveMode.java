package dev.aresos.mode;

import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.GameType;

public final class LiveMode {
    private LiveMode() { }

    public static boolean isLive(ServerPlayer player) {
        return DesktopWorld.isEnabled(player.level().getServer())
                && player.gameMode.getGameModeForPlayer() == GameType.SURVIVAL;
    }

    public static void register() {
        ServerLivingEntityEvents.ALLOW_DAMAGE.register((entity, source, amount) ->
                !(entity instanceof ServerPlayer player && isLive(player)));
        ServerLivingEntityEvents.ALLOW_DEATH.register((entity, source, amount) -> {
            if (entity instanceof ServerPlayer player && isLive(player)) {
                player.setHealth(player.getMaxHealth());
                return false;
            }
            return true;
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            // A switch timeout can disconnect and remove a player during this loop.
            for (ServerPlayer player : java.util.List.copyOf(server.getPlayerList().getPlayers())) {
                ModeInventories.of(player).tick(player);
                protect(player);
            }
        });
    }

    public static void protect(ServerPlayer player) {
        if (!isLive(player)) return;
        player.getFoodData().setFoodLevel(20);
        player.getFoodData().setSaturation(20);
        if (player.getY() < player.level().getMinY()) {
            player.teleport(player.findRespawnPositionAndUseSpawnBlock(false,
                    net.minecraft.world.level.portal.TeleportTransition.DO_NOTHING));
            player.fallDistance = 0;
            dev.aresos.zone.WalkInZones.arrived(player);
            // Moved by the mod: a /go still loading is no longer his wish (review fixes 2, point 2).
            dev.aresos.world.Arrivals.cancel(player);
        }
    }

    public static boolean toggleForHost(MinecraftServer server, ServerPlayer player) {
        if (!DesktopWorld.isEnabled(server)) {
            player.sendSystemMessage(Component.literal("Not an AresOS world"), true);
            return false;
        }
        if (!DesktopWorld.isHost(server, player)) return false;
        GameType mode = ModeInventories.of(player).activeInventory(player);
        if (!ModeInventories.of(player).switchTo(player,
                mode == GameType.CREATIVE ? GameType.SURVIVAL : GameType.CREATIVE, true)) return false;
        protect(player);
        return true;
    }
}
