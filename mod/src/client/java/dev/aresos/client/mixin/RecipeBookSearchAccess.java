package dev.aresos.client.mixin;

import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.recipebook.RecipeBookComponent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Package 53d, review 2: Super replaces the inventory only while nothing is typed in it. The recipe book's search box
 * is not among the screen's widgets (the book draws and feeds it itself), so the search over the world reads it here.
 * Null until the book was first shown.
 */
@Mixin(RecipeBookComponent.class)
public interface RecipeBookSearchAccess {
    @Accessor("searchBox") EditBox aresos$searchBox();
}
