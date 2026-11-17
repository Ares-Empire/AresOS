package dev.aresos.test.mixin;

import dev.aresos.test.ScreenLog;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.screens.Screen;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Package 48: records each screen right where {@code Gui.setScreen} stores it, after every redirect of ours. */
@Mixin(Gui.class)
public abstract class ScreenLogMixin {
    @Inject(method = "setScreen", at = @At(value = "FIELD", opcode = Opcodes.PUTFIELD,
            target = "Lnet/minecraft/client/gui/Gui;screen:Lnet/minecraft/client/gui/screens/Screen;", shift = At.Shift.AFTER))
    private void aresos$record(Screen screen, CallbackInfo ci) {
        ScreenLog.set(((Gui) (Object) this).screen());
    }
}
