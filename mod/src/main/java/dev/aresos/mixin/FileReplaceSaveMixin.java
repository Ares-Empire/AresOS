package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import net.minecraft.util.Util;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.nio.file.Path;

@Mixin(Util.class)
public abstract class FileReplaceSaveMixin {
    @Inject(method = "safeReplaceOrMoveFile", at = @At("RETURN"))
    private static void aresos$failure(Path current, Path replacement, Path backup, boolean move, CallbackInfoReturnable<Boolean> cir) {
        if (!cir.getReturnValue()) WorldSaveState.failure(current, "file replacement for " + current.getFileName());
    }
}
