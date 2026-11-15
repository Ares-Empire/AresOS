package dev.aresos.test.mixin;

import net.minecraft.client.gui.screens.ChatScreen;
import net.minecraft.client.gui.components.CommandSuggestions;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.network.chat.Style;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(ChatScreen.class)
public interface SlashChatTestAccess {
    @Accessor("input") EditBox aresos$input();
    @Accessor("commandSuggestions") CommandSuggestions aresos$suggestions();
    @Invoker("handleComponentClicked") boolean aresos$click(Style style, boolean insertion);
}
