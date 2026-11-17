package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import net.minecraft.util.ProblemReporter;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ProblemReporter.ScopedCollector.class)
public abstract class SerializationProblemMixin {
    @Inject(method = "close", at = @At("HEAD"))
    private void aresos$problems(CallbackInfo ci) {
        var collector = (ProblemReporter.ScopedCollector) (Object) this;
        if (!collector.isEmpty()) WorldSaveState.encodingProblem(collector.getTreeReport());
    }
}
