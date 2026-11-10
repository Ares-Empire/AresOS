package dev.aresos.client.launch;

import java.util.List;
import dev.aresos.config.AppDefinition;
import java.util.concurrent.CompletionStage;

@FunctionalInterface
public interface AppLauncher {
    CompletionStage<Void> launch(List<String> command);
    default CompletionStage<Void> launch(AppDefinition app) {
        return launch("url".equals(app.type()) ? List.of(app.url()) : app.command());
    }

    /**
     * Like {@link #launch(AppDefinition)}, and names the launch when its platform can still report a failure after
     * it counted as done (AresOS without window tracking). Null elsewhere.
     */
    default CompletionStage<String> launchTracked(AppDefinition app) {
        return launch(app).thenApply(ignored -> null);
    }
}
