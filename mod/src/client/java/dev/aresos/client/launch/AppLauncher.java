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
}
