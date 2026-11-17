package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(PlayerList.class)
public abstract class PlayerSaveRetentionMixin {
    @Shadow @Final private MinecraftServer server;

    @Inject(method = "remove", at = @At("RETURN"))
    private void aresos$left(ServerPlayer player, CallbackInfo ci) {
        var failures = WorldSaveState.of(server).failures;
        if (failures.needsRewrite()) failures.lost("player left before a full repair; player-data retention cannot be proved");
    }
}
