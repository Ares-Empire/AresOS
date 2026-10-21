package dev.aresos.mixin;

import dev.aresos.world.NetherHome;
import net.minecraft.network.Connection;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.players.PlayerList;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(PlayerList.class)
public abstract class PlayerListHomeMixin {
    @Inject(method = "placeNewPlayer", at = @At("HEAD"))
    private void aresos$homeBeforeLogin(Connection connection, ServerPlayer player, CommonListenerCookie cookie, CallbackInfo ci) {
        NetherHome.arrive(player);
    }
}
