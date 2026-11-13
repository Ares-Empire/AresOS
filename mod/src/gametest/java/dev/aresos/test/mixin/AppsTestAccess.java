package dev.aresos.test.mixin;

import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.shell.ShellClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import org.spongepowered.asm.mixin.gen.Invoker;

import java.util.List;

@Mixin(AresOs.class)
public interface AppsTestAccess {
    @Accessor("apps")
    static void aresos$setApps(List<AppDefinition> apps) {
        throw new AssertionError("Test accessor was not transformed");
    }

    /** With {@link #aresos$mergeHelperApps} a test hands the game its own helper connection, wired as at startup. */
    @Accessor("shell")
    static void aresos$setShell(ShellClient shell) {
        throw new AssertionError("Test accessor was not transformed");
    }

    /** What the game does with every complete program list from the helper. */
    @Invoker("mergeHelperApps")
    static void aresos$mergeHelperApps(List<ShellClient.App> listed) {
        throw new AssertionError("Test accessor was not transformed");
    }
}
