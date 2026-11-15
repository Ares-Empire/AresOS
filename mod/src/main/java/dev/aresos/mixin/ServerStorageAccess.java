package dev.aresos.mixin;

import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelStorageSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** The world storage a server saves through, so the town's seal knows whose save it is (dev.aresos.hub.TownSeal). */
@Mixin(MinecraftServer.class)
public interface ServerStorageAccess {
    @Accessor("storageSource")
    LevelStorageSource.LevelStorageAccess aresos$storageSource();
}
