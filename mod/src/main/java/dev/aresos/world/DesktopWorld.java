package dev.aresos.world;

import com.mojang.serialization.Codec;
import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;

/** One marker for the whole save, including all of its dimensions. */
public final class DesktopWorld extends SavedData {
    private static final Codec<DesktopWorld> CODEC = Codec.BOOL.fieldOf("enabled")
            .xmap(DesktopWorld::new, data -> data.enabled).codec();
    private static final SavedDataType<DesktopWorld> TYPE = new SavedDataType<>(
            AresOs.id("desktop"), () -> new DesktopWorld(false), CODEC, null);
    private boolean enabled;

    private DesktopWorld(boolean enabled) {
        this.enabled = enabled;
    }

    public static boolean isEnabled(MinecraftServer server) {
        var marker = server.getDataStorage().get(TYPE);
        return marker != null && marker.enabled;
    }

    public static boolean isHost(MinecraftServer server, ServerPlayer player) {
        return server.isSingleplayer() && server.isSingleplayerOwner(player.nameAndId());
    }

    public static void setEnabled(MinecraftServer server, boolean enabled) {
        var marker = server.getDataStorage().computeIfAbsent(TYPE);
        marker.enabled = enabled;
        marker.setDirty();
        if (enabled) {
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                AppItems.placePinned(player, AresOs.apps());
                LiveMode.protect(player);
            }
        }
    }
}
