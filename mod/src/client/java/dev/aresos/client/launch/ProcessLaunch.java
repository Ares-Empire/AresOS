package dev.aresos.client.launch;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CompletableFuture;

final class ProcessLaunch {
    private ProcessLaunch() { }

    static CompletableFuture<Void> start(List<String> command) {
        var result = new CompletableFuture<Void>();
        Thread.ofVirtual().name("aresos-launch").start(() -> {
            try {
                // No shell, inherited console, output pipes, or waitFor: the app outlives this task.
                Process process = new ProcessBuilder(command)
                        .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                        .redirectError(ProcessBuilder.Redirect.DISCARD).start();
                process.getOutputStream().close();
                result.complete(null);
            } catch (IOException | RuntimeException error) {
                result.completeExceptionally(error);
            }
        });
        return result;
    }
}
