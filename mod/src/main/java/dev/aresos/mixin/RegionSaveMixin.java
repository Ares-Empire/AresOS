package dev.aresos.mixin;

import com.mojang.datafixers.DataFixer;
import dev.aresos.save.WorldSaveState;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.util.datafix.DataFixTypes;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.IOWorker;
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
import java.util.function.Supplier;

@Mixin(SimpleRegionStorage.class)
public abstract class RegionSaveMixin {
    @Unique private Path aresos$directory;
    @Unique private String aresos$type;

    @Inject(method = "<init>", at = @At("RETURN"))
    private void aresos$location(RegionStorageInfo info, Path directory, DataFixer fixer, boolean sync, DataFixTypes type, CallbackInfo ci) {
        aresos$directory = directory;
        aresos$type = info.type();
    }

    // Both the tag overload and EntityStorage's STORE_EMPTY deletion pass through here exactly once.
    @Inject(method = "write(Lnet/minecraft/world/level/ChunkPos;Ljava/util/function/Supplier;)Ljava/util/concurrent/CompletableFuture;", at = @At("RETURN"))
    private void aresos$watch(ChunkPos pos, Supplier<CompoundTag> data, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
        // Terrain uses this superclass too, but ChunkSaveMixin accounts for its writes with precise unload tracking.
        if ((Object) this instanceof ChunkMap) return;
        var state = WorldSaveState.at(aresos$directory);
        if (state != null) state.failures.watch(cir.getReturnValue(), ok -> {
            // Entity unload and POI eviction have independent lifetimes. Do not claim recovery from a stale copy.
            if (!ok) state.failures.lost(aresos$type + " " + pos + (data == IOWorker.STORE_EMPTY
                    ? ": empty-entry deletion was cached before the write succeeded; retry cannot be proved"
                    : ": retention cannot be proved"));
        });
    }
}
