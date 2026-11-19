package dev.aresos.test.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import net.fabricmc.fabric.impl.client.gametest.threading.ThreadingImpl;
import net.minecraft.client.server.IntegratedServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/** The test barrier must also advance while 26.2's halt waits for its initial server task. */
@Mixin(IntegratedServer.class)
public abstract class IntegratedServerTestMixin {
    @WrapOperation(method = "halt", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/client/server/IntegratedServer;executeBlocking(Ljava/lang/Runnable;)V"))
    private void aresos$haltAcrossTestBarrier(IntegratedServer server, Runnable task, Operation<Void> original) {
        var client = ThreadingImpl.unsafeClientInstance;
        if (ThreadingImpl.testThread == null || client == null || !client.isSameThread()) {
            original.call(server, task);
            return;
        }
        // Fabric pumps this barrier in disconnect's later shutdown wait, but halt blocks before reaching it.
        // Submit the same task on its server thread and pump until it finishes; keep its failure visible.
        var done = server.submit(task);
        while (!done.isDone()) ((MinecraftTestAccess) client).aresos$runTestTasks();
        done.join();
    }
}
