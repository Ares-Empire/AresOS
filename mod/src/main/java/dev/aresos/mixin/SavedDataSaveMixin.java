package dev.aresos.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import dev.aresos.save.SaveRepair;
import dev.aresos.save.WorldSaveState;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import net.minecraft.world.level.storage.SavedDataStorage;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

@Mixin(SavedDataStorage.class)
public abstract class SavedDataSaveMixin implements SaveRepair {
    @Shadow @Final private Path dataFolder;
    @Shadow @Final private Map<SavedDataType<?>, Optional<SavedData>> cache;

    @WrapMethod(method = "scheduleSave")
    private CompletableFuture<?> aresos$encoding(Operation<CompletableFuture<?>> original) {
        var state = WorldSaveState.at(dataFolder);
        if (state == null) return original.call();
        var future = state.encoding(null, "saved data serialization", true, original::call);
        state.failures.watch(future, ok -> {
            if (!ok) state.failures.failure("saved data asynchronous save");
        });
        return future;
    }

    @Inject(method = "tryWrite", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V", remap = false))
    private void aresos$failure(CallbackInfo ci) {
        WorldSaveState.failure(dataFolder, "saved data in " + dataFolder.getFileName());
    }

    @Override public void aresos$rewrite() { cache.values().forEach(data -> data.ifPresent(SavedData::setDirty)); }
}
