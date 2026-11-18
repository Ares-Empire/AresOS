package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(net.minecraft.stats.ServerStatsCounter.class)
public abstract class StatsSaveMixin {
    @Shadow @Final private java.nio.file.Path file;

    @Inject(method = "save", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V", remap = false))
    private void aresos$failure(CallbackInfo ci) {
        WorldSaveState.failure(file, "player statistics");
    }
}
