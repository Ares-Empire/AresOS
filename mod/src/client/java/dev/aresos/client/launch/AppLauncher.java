package dev.aresos.client.launch;

import java.util.List;
import java.util.concurrent.CompletionStage;

@FunctionalInterface
public interface AppLauncher {
    CompletionStage<Void> launch(List<String> command);
}
