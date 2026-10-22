package dev.aresos.client.launch;

import java.util.List;
import dev.aresos.config.AppDefinition;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;

public final class WindowsAppLauncher implements AppLauncher {
    @Override public CompletionStage<Void> launch(AppDefinition app) {
        if ("helper".equals(app.type())) return CompletableFuture.failedFuture(new IllegalStateException("OS helper app unavailable on Windows"));
        if (!"url".equals(app.type())) return launch(app.command());
        return CompletableFuture.runAsync(() -> {
            try { java.awt.Desktop.getDesktop().browse(java.net.URI.create(app.url())); }
            catch (java.io.IOException error) { throw new java.util.concurrent.CompletionException(error); }
        });
    }
    @Override
    public CompletionStage<Void> launch(List<String> command) {
        return ProcessLaunch.start(command);
    }
}
