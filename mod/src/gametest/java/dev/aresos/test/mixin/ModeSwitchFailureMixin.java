package dev.aresos.test.mixin;

import dev.aresos.test.ModeSwitchFaults;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(ServerPlayer.class)
public abstract class ModeSwitchFailureMixin {
    @Inject(method = "setGameMode", at = @At("TAIL"))
    private void aresos$failAfterModeChange(GameType mode, CallbackInfoReturnable<Boolean> cir) {
        if (((ServerPlayer) (Object) this).getUUID().equals(ModeSwitchFaults.failAfterModeChange)) {
            ModeSwitchFaults.failAfterModeChange = null;
            throw new IllegalStateException("Injected failure after vanilla changed game mode");
        }
    }
}
