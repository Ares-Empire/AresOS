package dev.aresos.mixin;

import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Display;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** The text of a text display, which the game keeps private: the group names show their counts (HUB.md 2.6). */
@Mixin(Display.TextDisplay.class)
public interface TextDisplayAccess {
    @Invoker("getText") Component aresos$text();
    @Invoker("setText") void aresos$setText(Component text);
}
