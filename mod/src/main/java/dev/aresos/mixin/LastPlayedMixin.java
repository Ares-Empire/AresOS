package dev.aresos.mixin;

import dev.aresos.hub.TownSeal;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.storage.PrimaryLevelData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * The {@code LastPlayed} the game stamps into the level data it is about to write as {@code level.dat}: 26.2 puts it
 * there in this one method, called from {@code PrimaryLevelData.createTag}, which {@code saveDataTag} calls first. The
 * town's seal holds exactly this value ({@link TownSealMixin}).
 */
@Mixin(PrimaryLevelData.class)
public abstract class LastPlayedMixin {
    @Inject(method = "writeLastPlayed(Lnet/minecraft/nbt/CompoundTag;)V", at = @At("TAIL"))
    private static void aresos$lastPlayed(CompoundTag tag, CallbackInfo ci) {
        tag.getLong("LastPlayed").ifPresent(TownSeal::lastPlayed);
    }
}
