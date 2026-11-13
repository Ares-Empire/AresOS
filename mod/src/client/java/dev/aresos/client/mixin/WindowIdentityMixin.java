package dev.aresos.client.mixin;

import com.mojang.blaze3d.platform.Window;
import com.mojang.blaze3d.systems.GpuBackend;
import dev.aresos.shell.ShellClient;
import org.lwjgl.glfw.GLFW;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.Locale;

/**
 * On Linux, names the desktop window so the AresOS app helper can find it among the compositor's windows and hand
 * focus back to it when an app closes. Window titles are not a reliable identity (OS-BASE.md B2). The hints are
 * set only on Linux and only change the window's app_id/class; Windows is untouched.
 */
@Mixin(Window.class)
public abstract class WindowIdentityMixin {
    @Inject(method = "createGlfwWindow", at = @At(value = "INVOKE",
            target = "Lorg/lwjgl/glfw/GLFW;glfwCreateWindow(IILjava/lang/CharSequence;JJ)J"))
    private static void aresos$identifyDesktopWindow(int width, int height, String title, long monitor,
                                                     GpuBackend backend, CallbackInfoReturnable<Long> info) {
        if (!System.getProperty("os.name").toLowerCase(Locale.ROOT).startsWith("linux")) return;
        GLFW.glfwWindowHintString(GLFW.GLFW_WAYLAND_APP_ID, ShellClient.DESKTOP_APP_ID);
        GLFW.glfwWindowHintString(GLFW.GLFW_X11_CLASS_NAME, ShellClient.DESKTOP_APP_ID);
        GLFW.glfwWindowHintString(GLFW.GLFW_X11_INSTANCE_NAME, ShellClient.DESKTOP_APP_ID);
    }
}
