package dev.aresos.mixin;

import com.mojang.brigadier.tree.CommandNode;
import com.mojang.brigadier.tree.LiteralCommandNode;
import com.mojang.brigadier.tree.ArgumentCommandNode;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import java.util.Map;

/** Brigadier has addChild but no removeChild. Remove all indexes, only for nodes this mod owns. */
@Mixin(value = CommandNode.class, remap = false)
public interface CommandNodeAccess<S> {
    @Accessor("children") Map<String, CommandNode<S>> aresos$children();
    @Accessor("literals") Map<String, LiteralCommandNode<S>> aresos$literals();
    @Accessor("arguments") Map<String, ArgumentCommandNode<S, ?>> aresos$arguments();
}
