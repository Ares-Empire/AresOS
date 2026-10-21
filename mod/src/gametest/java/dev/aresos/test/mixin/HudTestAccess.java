package dev.aresos.test.mixin;

import net.minecraft.client.gui.Hud;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(Hud.class)
public interface HudTestAccess {
    @Accessor("overlayMessageString") Component aresos$overlayMessage();
    @Accessor("overlayMessageTime") int aresos$overlayTime();
}
