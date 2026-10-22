package dev.aresos.test.mixin;

import dev.aresos.mode.ModeInventories;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(ModeInventories.class)
public interface ModeSyncTestAccess {
    @Invoker("sync")
    static void aresos$release(ServerPlayer player) { throw new AssertionError(); }
}
