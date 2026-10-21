package dev.aresos.test.mixin;

import dev.aresos.test.ProvisioningAudit;
import dev.aresos.world.NetherHome;
import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = NetherHome.class, remap = false)
public abstract class ProvisioningAuditMixin {
    @Inject(method = "initialize", at = @At("HEAD"))
    private static void aresos$before(MinecraftServer server, NetherHome.Site site, boolean placeholder, CallbackInfo ci) {
        ProvisioningAudit.start(server, placeholder);
    }

    @Inject(method = "initialize", at = @At("RETURN"))
    private static void aresos$after(MinecraftServer server, NetherHome.Site site, boolean placeholder, CallbackInfo ci) {
        ProvisioningAudit.finish(server, placeholder);
    }
}
