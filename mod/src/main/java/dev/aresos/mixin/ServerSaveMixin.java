package dev.aresos.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import dev.aresos.save.WorldSaveState;
import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;

@Mixin(MinecraftServer.class)
public abstract class ServerSaveMixin {
    @WrapMethod(method = "saveEverything")
    private boolean aresos$encoding(boolean quiet, boolean flush, boolean force, Operation<Boolean> original) {
        var state = WorldSaveState.of((MinecraftServer) (Object) this);
        try { return state.encoding(null, "world/player serialization", true, () -> original.call(quiet, flush, force)); }
        catch (RuntimeException error) {
            state.failures.failure("save pipeline threw " + error);
            throw error;
        }
    }
}
