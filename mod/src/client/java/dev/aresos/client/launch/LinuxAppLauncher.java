package dev.aresos.client.launch;

import dev.aresos.catalogue.LinuxAppCatalogue;
import dev.aresos.config.AppDefinition;
import java.util.List;
import java.util.concurrent.*;

/** No direct-command fallback: only a future compatible helper may open an app on Linux. */
public final class LinuxAppLauncher implements AppLauncher {
    @Override public CompletionStage<Void> launch(List<String> command) { return unavailable(); }
    @Override public CompletionStage<Void> launch(AppDefinition app) { return unavailable(); }
    private static CompletionStage<Void> unavailable() {
        return CompletableFuture.failedFuture(new IllegalStateException(LinuxAppCatalogue.UNAVAILABLE));
    }
}
