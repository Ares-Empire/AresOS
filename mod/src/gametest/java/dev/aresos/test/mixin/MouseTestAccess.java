package dev.aresos.test.mixin;

import net.minecraft.client.MouseHandler;
import net.minecraft.client.input.MouseButtonInfo;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(MouseHandler.class)
public interface MouseTestAccess {
    @Invoker("onButton") void aresos$onButton(long handle, MouseButtonInfo button, int action);
    @Invoker("onScroll") void aresos$onScroll(long handle, double xoffset, double yoffset);
}
