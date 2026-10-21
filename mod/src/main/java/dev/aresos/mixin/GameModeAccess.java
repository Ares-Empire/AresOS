package dev.aresos.mixin;

import net.minecraft.server.level.ServerPlayerGameMode;
import net.minecraft.world.level.GameType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(ServerPlayerGameMode.class)
public interface GameModeAccess {
    @Invoker("setGameModeForPlayer")
    void aresos$setMode(GameType mode, GameType previousMode);
}
