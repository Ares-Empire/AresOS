package dev.aresos.test.mixin;

import net.minecraft.gametest.framework.GameTestServer;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.players.NameAndId;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** GameTestServer otherwise always says false, even when a test sets a singleplayer profile. */
@Mixin(GameTestServer.class)
public abstract class SlashNamesHostMixin {
    @Inject(method = "isSingleplayerOwner", at = @At("HEAD"), cancellable = true)
    private void aresos$testOwner(NameAndId player, CallbackInfoReturnable<Boolean> ci) {
        var profile = ((MinecraftServer)(Object)this).getSingleplayerProfile();
        if (profile != null) ci.setReturnValue(profile.id().equals(player.id()));
    }
}
