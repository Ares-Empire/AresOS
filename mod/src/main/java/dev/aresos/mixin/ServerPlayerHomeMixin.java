package dev.aresos.mixin;

import dev.aresos.world.NetherHome;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.ValueInput;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.Vec3;
import dev.aresos.world.DesktopWorld;

@Mixin(ServerPlayer.class)
public abstract class ServerPlayerHomeMixin {
    @Inject(method = "findRespawnPositionAndUseSpawnBlock", at = @At("HEAD"), cancellable = true)
    private void aresos$exactHomeRespawn(boolean consumeSpawnBlock, TeleportTransition.PostTeleportTransition post,
                                        CallbackInfoReturnable<TeleportTransition> cir) {
        var player = (ServerPlayer) (Object) this;
        var server = player.level().getServer();
        var home = NetherHome.get(server);
        if (home == null || !home.hasExactHome() || !DesktopWorld.isEnabled(server)) return;
        var target = home.home();
        var level = server.getLevel(target.dimension());
        if (level != null) cir.setReturnValue(new TeleportTransition(level, target.position(), Vec3.ZERO,
                target.yaw(), target.pitch(), post));
    }

    @Inject(method = "loadAndSpawnParentVehicle", at = @At("HEAD"), cancellable = true)
    private void aresos$leaveVehicleAtOrigin(ValueInput input, CallbackInfo ci) {
        if (NetherHome.restoreVehicleWithoutMount((ServerPlayer) (Object) this, input)) ci.cancel();
    }
}
