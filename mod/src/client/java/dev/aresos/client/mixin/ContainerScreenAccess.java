package dev.aresos.client.mixin;

import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Package 40, review fixes 1: a drag out of the Apps screen ends in the inventory. A container screen skips the first
 * button release it gets after it was made (the release of the click that opened it), so the drag's own release would
 * not put the item down where it is let go.
 */
@Mixin(AbstractContainerScreen.class)
public interface ContainerScreenAccess {
    @Accessor("skipNextRelease") void aresos$setSkipNextRelease(boolean skip);
}
