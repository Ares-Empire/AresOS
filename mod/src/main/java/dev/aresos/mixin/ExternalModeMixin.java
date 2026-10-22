package dev.aresos.mixin;

import dev.aresos.mode.ModeInventories;
import dev.aresos.world.DesktopWorld;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerPlayerGameMode;
import net.minecraft.world.level.GameType;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(ServerPlayerGameMode.class)
public abstract class ExternalModeMixin {
    @Shadow @Final protected ServerPlayer player;

    private boolean aresos$route() {
        // Vanilla attaches the old connection before restoring a replacement player's mode and inventories.
        return player.connection != null && player.connection.player == player && DesktopWorld.isEnabled(player.level().getServer())
                && !ModeInventories.of(player).changingMode();
    }

    @Inject(method = "changeGameModeForPlayer", at = @At("HEAD"), cancellable = true)
    private void aresos$externalChange(GameType target, CallbackInfoReturnable<Boolean> cir) {
        if (aresos$route()) cir.setReturnValue(ModeInventories.of(player).switchTo(player, target, true));
    }

    // Also cover mods invoking the protected setter. Login initialization has no connection yet.
    @Inject(method = "setGameModeForPlayer", at = @At("HEAD"), cancellable = true)
    private void aresos$externalSetter(GameType target, GameType previous, CallbackInfo ci) {
        if (aresos$route()) {
            ModeInventories.of(player).switchTo(player, target, true);
            ci.cancel();
        }
    }
}
