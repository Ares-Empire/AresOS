package dev.aresos.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import dev.aresos.save.WorldSaveState;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.entity.ChunkEntities;
import net.minecraft.world.level.chunk.storage.EntityStorage;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;

@Mixin(EntityStorage.class)
public abstract class EntitySaveMixin {
    @Shadow @Final private ServerLevel level;

    @WrapMethod(method = "storeEntities")
    private void aresos$encoding(ChunkEntities<Entity> entities, Operation<Void> original) {
        WorldSaveState.of(level.getServer()).encoding(null, "entity serialization", false, () -> original.call(entities));
    }
}
