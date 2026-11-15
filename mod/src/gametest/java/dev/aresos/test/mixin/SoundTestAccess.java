package dev.aresos.test.mixin;

import net.minecraft.client.sounds.SoundEngine;
import net.minecraft.client.sounds.SoundManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Package 40, review fixes 1: the home screen test reads which sounds play and which are paused. */
@Mixin(SoundManager.class)
public interface SoundTestAccess {
    @Accessor("soundEngine") SoundEngine aresos$soundEngine();
}
