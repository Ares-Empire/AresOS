package dev.aresos.mixin;

import com.mojang.datafixers.DataFixer;
import dev.aresos.save.WorldSaveState;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.util.datafix.DataFixTypes;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;
import net.minecraft.world.level.chunk.storage.SimpleRegionStorage;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.nio.file.Path;
import java.util.concurrent.CompletableFuture;

@Mixin(SimpleRegionStorage.class)
public abstract class RegionSaveMixin {
    @Unique private Path aresos$directory;
    @Unique private String aresos$type;

    @Inject(method = "<init>", at = @At("RETURN"))
    private void aresos$location(RegionStorageInfo info, Path directory, DataFixer fixer, boolean sync, DataFixTypes type, CallbackInfo ci) {
        aresos$directory = directory;
        aresos$type = info.type();
    }

    @Inject(method = "write(Lnet/minecraft/world/level/ChunkPos;Lnet/minecraft/nbt/CompoundTag;)Ljava/util/concurrent/CompletableFuture;", at = @At("RETURN"))
    private void aresos$watch(ChunkPos pos, CompoundTag tag, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
        var state = WorldSaveState.at(aresos$directory);
        if (state != null) state.failures.watch(cir.getReturnValue(), ok -> {
            // Entity unload and POI eviction have independent lifetimes. Do not claim recovery from a stale copy.
            if (!ok) state.failures.lost(aresos$type + " " + pos + ": retention cannot be proved");
        });
    }
}
