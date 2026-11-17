package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(net.minecraft.world.level.storage.LevelStorageSource.LevelStorageAccess.class)
public abstract class LevelSaveMixin {
    @Shadow public abstract java.nio.file.Path getLevelPath(net.minecraft.world.level.storage.LevelResource resource);

    @Inject(method = "saveLevelData(Lnet/minecraft/nbt/CompoundTag;)V", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V", remap = false))
    private void aresos$failure(CallbackInfo ci) {
        WorldSaveState.failure(getLevelPath(net.minecraft.world.level.storage.LevelResource.ROOT), "level.dat");
    }
}
