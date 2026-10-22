package dev.aresos.mixin;

import dev.aresos.mode.ModeInventories;
import dev.aresos.mode.ModeInventoryAccess;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ServerPlayer.class)
public abstract class ModeInventoryMixin implements ModeInventoryAccess {
    @Unique private final ModeInventories aresos$inventories = new ModeInventories();

    @Override public ModeInventories aresos$modeInventories() { return aresos$inventories; }

    @Inject(method = "readAdditionalSaveData", at = @At("TAIL"))
    private void aresos$loadInventories(ValueInput input, CallbackInfo ci) { aresos$inventories.read(input); }

    @Inject(method = "addAdditionalSaveData", at = @At("TAIL"))
    private void aresos$saveInventories(ValueOutput output, CallbackInfo ci) { aresos$inventories.write(output); }

    @Inject(method = "restoreFrom", at = @At("TAIL"))
    private void aresos$copyInventories(ServerPlayer previous, boolean keepEverything, CallbackInfo ci) {
        aresos$inventories.copyFrom(ModeInventories.of(previous));
    }
}
