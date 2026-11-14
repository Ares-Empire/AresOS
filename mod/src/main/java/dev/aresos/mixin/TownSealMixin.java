package dev.aresos.mixin;

import dev.aresos.hub.TownSeal;
import net.minecraft.world.level.storage.LevelStorageSource;
import net.minecraft.world.level.storage.WorldData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.UUID;

/**
 * The town's seal is written right after {@code level.dat} (dev.aresos.hub.TownSeal). In 26.2 every write of the level
 * data that stamps a new {@code LastPlayed} goes through this method: the server's saves
 * ({@code MinecraftServer.saveAllChunks}, also in a game-test server) and the writes before a server runs (opening a
 * world in the game, optimizing it, a dedicated server's start), which call it through {@code saveDataTag(WorldData)}.
 * A rename keeps {@code LastPlayed} and does not come here.
 */
@Mixin(LevelStorageSource.LevelStorageAccess.class)
public abstract class TownSealMixin {
    @Inject(method = "saveDataTag(Lnet/minecraft/world/level/storage/WorldData;Ljava/util/UUID;)V", at = @At("HEAD"))
    private void aresos$beforeLevelData(WorldData data, UUID player, CallbackInfo ci) {
        TownSeal.before((LevelStorageSource.LevelStorageAccess)(Object)this);
    }

    @Inject(method = "saveDataTag(Lnet/minecraft/world/level/storage/WorldData;Ljava/util/UUID;)V", at = @At("RETURN"))
    private void aresos$sealAfterLevelData(WorldData data, UUID player, CallbackInfo ci) {
        TownSeal.after((LevelStorageSource.LevelStorageAccess)(Object)this);
    }
}
