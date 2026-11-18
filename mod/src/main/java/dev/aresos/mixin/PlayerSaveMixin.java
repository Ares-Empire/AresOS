package dev.aresos.mixin;

import dev.aresos.save.WorldSaveState;
import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(net.minecraft.world.level.storage.PlayerDataStorage.class)
public abstract class PlayerSaveMixin {
    @Shadow @Final private java.io.File playerDir;

    @WrapMethod(method = "save")
    private void aresos$encoding(Player player, Operation<Void> original) {
        var state = WorldSaveState.at(playerDir.toPath());
        if (state == null) original.call(player);
        else state.encoding(null, "player serialization", true, () -> original.call(player));
    }

    @Inject(method = "save", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;)V", remap = false))
    private void aresos$failure(CallbackInfo ci) {
        WorldSaveState.failure(playerDir.toPath(), "player data");
    }
}
