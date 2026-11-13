// Diagnostic for a pre-existing startup replay race; outside the mod source sets.
package dev.aresos.shell;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;

public class StartupReplayProbe {
    public static void main(String[] args) throws Exception {
        Path folder = Files.createTempDirectory(Path.of(args[0]), "p");
        try (var helper = new FakeHelper(folder); var client = helper.client(FakeHelper.fast())) {
            client.addListener(new ShellClient.Listener() {
                @Override public void apps(List<ShellClient.App> apps) {
                    client.open("notepad");
                    try { FakeHelper.await(() -> helper.received("open_app").size() == 1, "initial send"); }
                    catch (InterruptedException e) { throw new RuntimeException(e); }
                }
            });
            client.start();
            client.awaitApps(Duration.ofSeconds(5));
            FakeHelper.await(() -> helper.received("open_app").size() == 2, "startup replay");
            var opens = helper.received("open_app");
            System.out.println("connections=" + helper.connections.get());
            System.out.println("open_app wire requests=" + opens.size());
            System.out.println("unique request IDs=" + opens.stream().map(m -> m.get("id").getAsString()).distinct().count());
            System.out.println("actual launches=" + helper.launches.get());
            if (helper.connections.get() != 1 || opens.size() != 2 || helper.launches.get() != 1)
                throw new AssertionError("Unexpected probe result");
        } finally { Files.delete(folder); }
    }
}
