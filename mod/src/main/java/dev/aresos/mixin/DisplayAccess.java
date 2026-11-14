package dev.aresos.mixin;

import com.mojang.math.Transformation;
import net.minecraft.world.entity.Display;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** A display's size, which the game keeps private: a group name built at an older scale takes today's (HUB.md 3.2). */
@Mixin(Display.class)
public interface DisplayAccess {
    @Invoker("setTransformation") void aresos$setTransformation(Transformation transformation);
}
