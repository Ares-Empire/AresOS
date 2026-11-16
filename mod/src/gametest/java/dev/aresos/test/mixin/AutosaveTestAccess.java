package dev.aresos.test.mixin;

import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Package 46, owner fix 1: the countdown to the game's own autosave, so a test can make it come at the next tick. */
@Mixin(MinecraftServer.class)
public interface AutosaveTestAccess {
    @Accessor("ticksUntilAutosave") int aresos$ticksUntilAutosave();
    @Accessor("ticksUntilAutosave") void aresos$setTicksUntilAutosave(int ticks);
}
