package dev.aresos.mixin;

import dev.aresos.mode.ModeInventories;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin({ItemEntity.class, ExperienceOrb.class})
public abstract class PendingPickupMixin {
    @Inject(method = "playerTouch", at = @At("HEAD"), cancellable = true)
    private void aresos$leavePendingPickupInWorld(Player player, CallbackInfo ci) {
        // XP pickup spends the orb even when its value goes into mending rather than the XP bar.
        if (player instanceof ServerPlayer serverPlayer && ModeInventories.of(serverPlayer).blocksInsertions()) ci.cancel();
    }
}
