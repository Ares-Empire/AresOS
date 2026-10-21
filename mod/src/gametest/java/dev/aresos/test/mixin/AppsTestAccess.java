package dev.aresos.test.mixin;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

@Mixin(AresOs.class)
public interface AppsTestAccess {
    @Accessor("apps")
    static void aresos$setApps(List<AppDefinition> apps) {
        throw new AssertionError("Test accessor was not transformed");
    }
}
