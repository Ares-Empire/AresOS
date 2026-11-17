package dev.aresos.mixin;

import dev.aresos.save.SaveRepair;
import dev.aresos.save.WorldSaveState;
import it.unimi.dsi.fastutil.longs.Long2ObjectMap;
import it.unimi.dsi.fastutil.longs.LongLinkedOpenHashSet;
import net.minecraft.core.SectionPos;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.SectionStorage;
import net.minecraft.world.level.chunk.storage.SimpleRegionStorage;
import net.minecraft.world.level.chunk.storage.ChunkIOErrorReporter;
import net.minecraft.server.MinecraftServer;
import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import com.mojang.serialization.DataResult;
import java.util.Optional;
import java.util.function.Consumer;

@Mixin(SectionStorage.class)
public abstract class PoiSaveMixin implements SaveRepair {
    @Shadow @Final private Long2ObjectMap<?> storage;
    @Shadow @Final private LongLinkedOpenHashSet dirtyChunks;
    @Shadow @Final private SimpleRegionStorage simpleRegionStorage;
    @Shadow @Final private ChunkIOErrorReporter errorReporter;

    @WrapMethod(method = "writeChunk(Lnet/minecraft/world/level/ChunkPos;)V")
    private void aresos$encoding(ChunkPos pos, Operation<Void> original) {
        if (errorReporter instanceof MinecraftServer server)
            WorldSaveState.of(server).encoding(null, "POI serialization", false, () -> original.call(pos));
        else original.call(pos);
    }

    @Inject(method = "writeChunk(Lnet/minecraft/world/level/ChunkPos;)V", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;)V", remap = false))
    private void aresos$badTag(CallbackInfo ci) {
        // The unexpected tag has no safe retry contract. Report it through the world's existing reporter below.
        WorldSaveState.encodingProblem("produced no compound tag");
    }

    @Redirect(method = "writeChunk(Lnet/minecraft/world/level/ChunkPos;Lcom/mojang/serialization/DynamicOps;)Lcom/mojang/serialization/Dynamic;", at = @At(value = "INVOKE", target = "Lcom/mojang/serialization/DataResult;resultOrPartial(Ljava/util/function/Consumer;)Ljava/util/Optional;", remap = false))
    private <T> Optional<T> aresos$partial(DataResult<T> result, Consumer<String> logger) {
        return result.resultOrPartial(problem -> {
            WorldSaveState.encodingProblem(problem);
            logger.accept(problem);
        });
    }

    @Override public void aresos$rewrite() {
        for (long section : storage.keySet())
            dirtyChunks.add(ChunkPos.pack(SectionPos.x(section), SectionPos.z(section)));
    }

    @Override public void aresos$flush() { simpleRegionStorage.synchronize(true).join(); }
}
