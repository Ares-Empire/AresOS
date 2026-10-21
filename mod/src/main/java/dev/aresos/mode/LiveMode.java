package dev.aresos.mode;

import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
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
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
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
        }
    }

    public static boolean toggleForHost(MinecraftServer server, ServerPlayer player) {
        if (!DesktopWorld.isEnabled(server)) {
            player.sendSystemMessage(Component.literal("Not an AresOS world"), true);
            return false;
        }
        if (!DesktopWorld.isHost(server, player)) return false;
        GameType mode = player.gameMode.getGameModeForPlayer();
        if (mode != GameType.SURVIVAL && mode != GameType.CREATIVE) return false;
        player.setGameMode(mode == GameType.CREATIVE ? GameType.SURVIVAL : GameType.CREATIVE);
        if (isLive(player)) AppItems.placePinned(player, AresOs.apps());
        protect(player);
        return true;
    }
}
