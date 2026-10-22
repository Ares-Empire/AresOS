package dev.aresos.client.mixin;

import dev.aresos.client.RuntimeIconPack;
import net.minecraft.client.Minecraft;
import net.minecraft.server.packs.repository.RepositorySource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import java.util.Arrays;

@Mixin(Minecraft.class)
public abstract class IconPackMixin {
    @ModifyArg(method = "<init>", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/packs/repository/PackRepository;<init>([Lnet/minecraft/server/packs/repository/RepositorySource;)V"), index = 0)
    private RepositorySource[] aresos$icons(RepositorySource[] sources) {
        var extended = Arrays.copyOf(sources, sources.length + 1);
        extended[sources.length] = RuntimeIconPack.source();
        return extended;
    }
}
