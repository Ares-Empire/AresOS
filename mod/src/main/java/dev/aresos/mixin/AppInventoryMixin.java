package dev.aresos.mixin;

import dev.aresos.item.AppInventory;
import dev.aresos.item.AppMenuPins;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.*;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import java.util.Set;

@Mixin(AbstractContainerMenu.class)
public abstract class AppInventoryMixin implements AppMenuPins {
    @Unique private Set<String> aresos$before;
    @Override public void aresos$beginMove(Set<String> before) { if (aresos$before == null) aresos$before = before; }
    @Inject(method = "clicked", at = @At("HEAD"))
    private void aresos$start(int slot, int button, ContainerInput input, Player player, CallbackInfo ci) {
        if (player instanceof ServerPlayer serverPlayer && LiveMode.isLive(serverPlayer)
                && DesktopWorld.isHost(serverPlayer.level().getServer(), serverPlayer))
            aresos$beginMove(AppInventory.hotbar(serverPlayer));
    }
    @Inject(method = "clicked", at = @At("TAIL"))
    private void aresos$finish(int slot, int button, ContainerInput input, Player player, CallbackInfo ci) { aresos$finishMove(player); }
    @Inject(method = "removed", at = @At("TAIL"))
    private void aresos$close(Player player, CallbackInfo ci) { aresos$finishMove(player); }
    @Unique private void aresos$finishMove(Player player) {
        var menu = (AbstractContainerMenu)(Object)this;
        if (aresos$before != null && menu.getCarried().isEmpty()) {
            if (player instanceof ServerPlayer serverPlayer) AppInventory.savePins(serverPlayer, aresos$before);
            aresos$before = null;
        }
    }
}
