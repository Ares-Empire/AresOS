package dev.aresos.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import dev.aresos.save.SaveRepair;
import dev.aresos.save.WorldSaveState;
import it.unimi.dsi.fastutil.longs.Long2ObjectLinkedOpenHashMap;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ChunkHolder;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.thread.BlockableEventLoop;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.HashSet;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;

@Mixin(ChunkMap.class)
public abstract class ChunkSaveMixin implements SaveRepair {
    @Shadow @Final private ServerLevel level;
    @Shadow @Final private Long2ObjectLinkedOpenHashMap<ChunkHolder> updatingChunkMap;
    @Shadow private volatile Long2ObjectLinkedOpenHashMap<ChunkHolder> visibleChunkMap;
    @Shadow @Final private Long2ObjectLinkedOpenHashMap<ChunkHolder> pendingUnloads;
    @Shadow @Final private BlockableEventLoop<Runnable> mainThreadExecutor;
    @Shadow private boolean save(ChunkAccess chunk) { throw new AssertionError(); }

    @Unique private String aresos$key(ChunkPos pos) {
        return WorldSaveState.chunk(level.dimension().identifier().toString(), pos);
    }

    @WrapMethod(method = "save")
    private boolean aresos$encoding(ChunkAccess chunk, Operation<Boolean> original) {
        return WorldSaveState.of(level.getServer()).encoding(aresos$key(chunk.getPos()), "chunk serialization", true,
                () -> original.call(chunk));
    }

    @Redirect(method = "save", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/level/ChunkMap;write(Lnet/minecraft/world/level/ChunkPos;Ljava/util/function/Supplier;)Ljava/util/concurrent/CompletableFuture;"))
    private CompletableFuture<Void> aresos$write(ChunkMap map, ChunkPos pos, Supplier<CompoundTag> data) {
        var failures = WorldSaveState.of(level.getServer()).failures;
        var write = failures.writing(aresos$key(pos));
        try {
            var state = WorldSaveState.of(level.getServer());
            var future = map.write(pos, () -> state.encoding(aresos$key(pos), "asynchronous chunk serialization", true, data));
            failures.watch(future, ok -> failures.written(write, ok));
            return future;
        } catch (RuntimeException error) {
            failures.written(write, false);
            throw error;
        }
    }

    // The synchronous serialization catch; asynchronous failures are accounted before our own barrier completes.
    @Redirect(method = "save", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/MinecraftServer;reportChunkSaveFailure(Ljava/lang/Throwable;Lnet/minecraft/world/level/chunk/storage/RegionStorageInfo;Lnet/minecraft/world/level/ChunkPos;)V"))
    private void aresos$serializationFailure(MinecraftServer server, Throwable error, RegionStorageInfo info, ChunkPos pos) {
        WorldSaveState.of(server).failures.chunkFailure(aresos$key(pos));
        server.reportChunkSaveFailure(error, info, pos);
    }

    @Inject(method = "lambda$scheduleUnload$0", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/level/ChunkMap;save(Lnet/minecraft/world/level/chunk/ChunkAccess;)Z", shift = At.Shift.AFTER))
    private void aresos$unloaded(ChunkHolder holder, CompletableFuture<?> future, long pos, CallbackInfo ci) {
        WorldSaveState.of(level.getServer()).failures.unloaded(aresos$key(ChunkPos.unpack(pos)));
    }

    @Override public void aresos$rewrite() {
        // Include holders vanilla's accessibility filter skips and those waiting for actual unloading.
        var holders = new HashSet<>(updatingChunkMap.values());
        holders.addAll(visibleChunkMap.values());
        holders.addAll(pendingUnloads.values());
        for (var holder : holders) {
            mainThreadExecutor.managedBlock(holder::isReadyForSaving);
            var chunk = holder.getLatestChunk();
            if (chunk != null && chunk.canBeSerialized()) {
                chunk.markUnsaved();
                save(chunk);
            }
        }
    }
}
