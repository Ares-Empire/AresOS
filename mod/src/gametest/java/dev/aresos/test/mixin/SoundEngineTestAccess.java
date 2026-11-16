package dev.aresos.test.mixin;

import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.client.sounds.ChannelAccess;
import net.minecraft.client.sounds.SoundEngine;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.Map;

/** Package 40, review fixes 1: each playing sound's channel, to ask the sound thread whether it plays. */
@Mixin(SoundEngine.class)
public interface SoundEngineTestAccess {
    @Accessor("instanceToChannel") Map<SoundInstance, ChannelAccess.ChannelHandle> aresos$channels();
}
