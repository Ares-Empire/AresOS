package dev.aresos.test.mixin;

import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(Minecraft.class)
public interface MinecraftTestAccess {
    @Accessor("lastActiveTime") void aresos$setLastActiveTime(long time);
    @Invoker("pauseIfInactive") void aresos$pauseIfInactive();

    /** Fabric's test-task pump, also used by its disconnect busy-wait hook. */
    @Invoker(value = "postRunTasks", remap = false) void aresos$runTestTasks();
}
