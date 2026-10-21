package dev.aresos.test.mixin;

import com.mojang.blaze3d.platform.Window;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(Window.class)
public interface WindowTestAccess {
    @Accessor("focused") void aresos$setFocused(boolean focused);
}
