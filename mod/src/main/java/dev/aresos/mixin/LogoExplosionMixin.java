package dev.aresos.mixin;

import dev.aresos.hub.HubData;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.ZoneData;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ServerExplosion;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.HashSet;
import java.util.List;

@Mixin(ServerExplosion.class)
public abstract class LogoExplosionMixin {
    @Inject(method = "interactWithBlocks", at = @At("HEAD"))
    private void aresos$preserveLogos(List<BlockPos> affected, CallbackInfo ci) {
        var level = ((ServerExplosion)(Object)this).level();
        if (!DesktopWorld.isEnabled(level.getServer())) return;
        var protectedBlocks = new HashSet<BlockPos>();
        for (var zone : ZoneData.get(level.getServer()).zones())
            if (zone.dimension().equals(level.dimension())) protectedBlocks.addAll(zone.blocks());
        // Explosions are never an edit gesture, including while the owner is building.
        affected.removeIf(protectedBlocks::contains);
        // The flat home's pad and roads follow their own rule: Build mode may change anything (brief 32).
        var hub = HubData.get(level.getServer());
        if (hub != null && HubData.protectsFromExplosions(level.getServer())) affected.removeIf(pos -> hub.holds(level, pos));
    }
}
