package dev.aresos.item;

import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.Level;

public final class AppItem extends Item {
    public AppItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        // Client input activates apps after hotbar selection, before vanilla target interactions.
        return InteractionResult.CONSUME;
    }
}
