package dev.aresos.test.mixin;

import dev.aresos.test.SaveFaults;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.RegionFileStorage;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.io.IOException;

@Mixin(RegionFileStorage.class)
public abstract class SaveFailureTestMixin {
    @Shadow @Final private RegionStorageInfo info;

    @Inject(method = "write", at = @At("HEAD"))
    private void aresos$fail(ChunkPos pos, CompoundTag data, CallbackInfo ci) throws IOException {
        if (SaveFaults.take(info, pos, data)) throw new IOException("Package 46 test: injected region write failure");
    }
}
