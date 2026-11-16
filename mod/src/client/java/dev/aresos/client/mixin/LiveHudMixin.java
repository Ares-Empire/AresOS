package dev.aresos.client.mixin;

import dev.aresos.client.AresOsClient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.MultiPlayerGameMode;
import net.minecraft.world.level.GameType;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Live mode shows only the hotbar, as creative does (package 40): nothing can hurt or starve him there, so hearts,
 * armour, air, hunger and the experience bar mean nothing. The game asks these two questions only to decide what the
 * HUD draws.
 */
@Mixin(MultiPlayerGameMode.class)
public abstract class LiveHudMixin {
    @Shadow @Final private Minecraft minecraft;
    @Shadow private GameType localPlayerMode;

    @Inject(method = {"canHurtPlayer", "hasExperience"}, at = @At("HEAD"), cancellable = true)
    private void aresos$liveShowsOnlyTheHotbar(CallbackInfoReturnable<Boolean> cir) {
        if (localPlayerMode == GameType.SURVIVAL && AresOsClient.acceptsAppCommands(minecraft)) cir.setReturnValue(false);
    }
}
