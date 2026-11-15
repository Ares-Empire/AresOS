package dev.aresos.client.launch;

import dev.aresos.catalogue.LinuxAppCatalogue;
import dev.aresos.config.AppDefinition;
import dev.aresos.shell.ShellClient;
import java.util.List;
import java.util.concurrent.*;
import java.util.function.Supplier;

/**
 * Opens apps by asking the AresOS app helper (aresos-shell). There is no direct-command fallback: without a
 * compatible helper nothing starts, whatever the app's type or saved command.
 */
public final class LinuxAppLauncher implements AppLauncher {
    private final Supplier<ShellClient> shell;

    public LinuxAppLauncher() { this(() -> null); }

    public LinuxAppLauncher(Supplier<ShellClient> shell) { this.shell = shell; }

    @Override public CompletionStage<Void> launch(List<String> command) {
        return CompletableFuture.failedFuture(new IllegalStateException(LinuxAppCatalogue.UNAVAILABLE));
    }

    @Override public CompletionStage<Void> launch(AppDefinition app) {
        return launchTracked(app).thenApply(ignored -> null);
    }

    /** The request ID lets a failure reported after the launch counted as done find this launch again. */
    @Override public CompletionStage<String> launchTracked(AppDefinition app) {
        var client = shell.get();
        if (client == null) return launch(List.<String>of()).thenApply(ignored -> null);
        return client.open(app.id()).thenApply(ShellClient.Launch::requestId);
    }

    /** Why a launch failed, in a few words for the action bar. */
    public static String reason(Throwable error) {
        return ShellClient.describe(error);
    }
}
