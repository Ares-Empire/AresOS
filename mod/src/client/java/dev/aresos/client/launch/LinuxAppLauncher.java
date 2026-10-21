package dev.aresos.client.launch;

import java.util.List;
import java.util.concurrent.CompletionStage;

public final class LinuxAppLauncher implements AppLauncher {
    @Override
    public CompletionStage<Void> launch(List<String> command) {
        return ProcessLaunch.start(command);
    }
}
