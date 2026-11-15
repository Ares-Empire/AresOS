package dev.aresos.test.mixin;

import net.minecraft.client.sounds.MusicManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Package 40, review fixes 1: the countdown to the next song stands still while the home screen is covered. */
@Mixin(MusicManager.class)
public interface MusicManagerTestAccess {
    @Accessor("nextSongDelay") int aresos$nextSongDelay();
    @Accessor("nextSongDelay") void aresos$setNextSongDelay(int ticks);
}
