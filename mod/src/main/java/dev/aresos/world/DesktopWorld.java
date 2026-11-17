package dev.aresos.world;

import com.mojang.serialization.Codec;
import dev.aresos.AresOs;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import net.minecraft.world.level.storage.LevelResource;

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

    /**
     * The world's identity on the wire (OS-BASE B1): its save folder's name. {@code world_ready} and heartbeats name the
     * desktop world by it, and so does the lifecycle channel's {@code world_saved} (package 46).
     */
    public static String saveName(MinecraftServer server) {
        var folder = server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().getFileName();
        return folder == null ? "world" : folder.toString();
    }

    public static boolean isHost(MinecraftServer server, ServerPlayer player) {
        return server.isSingleplayer() && server.isSingleplayerOwner(player.nameAndId());
    }

    public static void setEnabled(MinecraftServer server, boolean enabled) {
        var marker = server.getDataStorage().computeIfAbsent(TYPE);
        boolean was = marker.enabled;
        marker.enabled = enabled;
        marker.setDirty();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            // Turning it off gives back the game's abilities once; a world that stays vanilla is left alone.
            if (enabled || was) LiveMode.markerChanged(player, enabled);
            if (enabled) {
                dev.aresos.item.AppInventory.populate(player);
                LiveMode.protect(player);
            }
        }
    }
}
