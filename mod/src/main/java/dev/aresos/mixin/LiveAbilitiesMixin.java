package dev.aresos.mixin;

import dev.aresos.mode.LiveMode;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerPlayerGameMode;
import net.minecraft.world.level.GameType;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Every path that sets a player's game mode ends in this setter, which also resets his abilities to the mode's own:
 * the constructor, loading his save, the respawn's copy and every switch. Live mode's flight, invulnerability and the
 * desktop speed are put back right after it ({@link LiveMode#applyDesktopAbilities}).
 */
@Mixin(ServerPlayerGameMode.class)
public abstract class LiveAbilitiesMixin {
    @Shadow @Final protected ServerPlayer player;
    @Unique private boolean aresos$wasFlying;

    @Inject(method = "setGameModeForPlayer", at = @At("HEAD"))
    private void aresos$rememberFlight(GameType mode, GameType previous, CallbackInfo ci) {
        aresos$wasFlying = player.getAbilities().flying;
    }

    @Inject(method = "setGameModeForPlayer", at = @At("TAIL"))
    private void aresos$desktopAbilities(GameType mode, GameType previous, CallbackInfo ci) {
        LiveMode.applyDesktopAbilities(player, aresos$wasFlying);
    }
}
