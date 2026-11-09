package dev.aresos.shell;

import com.google.gson.JsonObject;
import dev.aresos.catalogue.LinuxAppCatalogue;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.*;
import java.io.IOException;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;

/** The mod side of aresos-shell/1.0 against a fake helper on a real Unix socket. */
class ShellClientTest {
    private Path folder;
    private FakeHelper helper;
    private ShellClient client;

    @BeforeEach void start() throws IOException {
        // Unix socket paths are short (about 100 bytes), so use a short folder name.
        folder = Files.createTempDirectory("as");
        helper = new FakeHelper(folder);
    }

    @AfterEach void stop() throws IOException {
        if (client != null) client.close();
        helper.close();
        try (var files = Files.walk(folder)) {
            for (var path : files.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        }
    }

    private ShellClient connect() throws IOException {
        client = helper.client(FakeHelper.fast());
        client.start();
        client.awaitApps(Duration.ofSeconds(5));
        return client;
    }

    private static <T> T join(CompletableFuture<T> future) throws Exception {
        return future.get(10, TimeUnit.SECONDS);
    }

    private static ShellClient.ShellException refusal(CompletableFuture<?> future) {
        var error = assertThrows(ExecutionException.class, () -> future.get(10, TimeUnit.SECONDS));
        return assertInstanceOf(ShellClient.ShellException.class, error.getCause());
    }

    @Test void handshakeSendsVersionCapabilitiesInstanceAndNonceThenListsApps() throws Exception {
        var apps = connect().apps();
        var hello = helper.received("hello").getFirst();
        assertEquals("aresos-shell/1.0", hello.get("protocol").getAsString());
        assertEquals(1, hello.get("major").getAsInt());
        assertEquals(0, hello.get("minor").getAsInt());
        assertEquals(FakeHelper.INSTANCE, hello.get("instance").getAsString());
        assertEquals(FakeHelper.NONCE, hello.get("nonce").getAsString());
        var capabilities = hello.getAsJsonArray("capabilities").asList().stream().map(value -> value.getAsString()).toList();
        assertTrue(capabilities.containsAll(List.of("open_app", "app_state", "shell_focus", "world_ready", "heartbeat")));
        assertEquals(List.of("list_apps", "open_app"),
                hello.getAsJsonArray("requires").asList().stream().map(value -> value.getAsString()).toList());
        for (var message : helper.received) {
            assertEquals("aresos-shell/1.0", message.get("protocol").getAsString());
            assertTrue(message.get("id").getAsString().matches("[A-Za-z0-9._:-]{1,128}"));
        }
        assertEquals(ShellClient.State.CONNECTED, client.status().state());
        assertTrue(client.tracksWindows());
        assertEquals(List.of(new ShellClient.App("terminal", "Terminal", true, null),
                new ShellClient.App("notepad", "Notepad", true, null),
                new ShellClient.App("browser", "Chrome", false, "not_installed")), apps);

        var definitions = new LinuxAppCatalogue(client, Duration.ofSeconds(1)).listApps();
        for (var app : definitions) {
            assertEquals("helper", app.type());
            assertTrue(app.command().isEmpty(), "The mod never holds a Linux command");
            assertFalse(app.pinned());
        }
        assertEquals(List.of("minecraft:command_block", "minecraft:writable_book", "minecraft:compass"),
                definitions.stream().map(AppDefinition::look).toList());
    }

    @Test void incompatibleHelpersBlockLaunches() throws Exception {
        for (var refusal : List.<java.util.function.Function<JsonObject, JsonObject>>of(
                message -> reply(message, false, "incompatible_version"),
                message -> reply(message, false, "not_authorized"),
                message -> { var reply = reply(message, true, null); reply.addProperty("major", 2); return reply; })) {
            helper.override = message -> "hello".equals(FakeHelper.string(message, "op")) ? refusal.apply(message) : null;
            var shell = helper.client(FakeHelper.fast());
            shell.start();
            var error = assertThrows(ShellClient.ShellException.class, () -> shell.awaitApps(Duration.ofSeconds(5)));
            assertEquals(ShellClient.State.INCOMPATIBLE, shell.status().state());
            assertEquals("app helper incompatible", ShellClient.describe(refusal(shell.open("notepad"))));
            assertNotNull(error.code());
            shell.close();
        }
        // A helper without open_app cannot open anything, so it is incompatible too.
        helper.override = message -> null;
        helper.capabilities = List.of("list_apps", "heartbeat");
        var shell = helper.client(FakeHelper.fast());
        shell.start();
        assertThrows(ShellClient.ShellException.class, () -> shell.awaitApps(Duration.ofSeconds(5)));
        assertEquals(ShellClient.State.INCOMPATIBLE, shell.status().state());
        shell.close();
        assertTrue(helper.received("open_app").isEmpty());
    }

    @Test void missingHelperOrSessionFailsClosedAtOnce() throws Exception {
        helper.close();
        client = helper.client(FakeHelper.fast());
        client.start();
        var error = assertThrows(ShellClient.ShellException.class, () -> client.awaitApps(Duration.ofSeconds(5)));
        assertTrue(error.getMessage().startsWith("app helper unavailable"), error.getMessage());
        long started = System.nanoTime();
        assertEquals("app helper unavailable", ShellClient.describe(refusal(client.open("notepad"))));
        assertTrue(System.nanoTime() - started < TimeUnit.SECONDS.toNanos(1), "A missing helper must fail at once");
        assertEquals(ShellClient.State.UNAVAILABLE, client.status().state());

        var unconfigured = ShellClient.fromEnvironment(Map.of("XDG_RUNTIME_DIR", "/run/user/1001"), FakeHelper.fast());
        unconfigured.start();
        assertEquals(ShellClient.State.UNAVAILABLE, unconfigured.status().state());
        assertTrue(unconfigured.status().detail().contains("not started by the AresOS session"));
        assertThrows(ShellClient.ShellException.class, () -> unconfigured.awaitApps(Duration.ofSeconds(1)));
        unconfigured.close();
        var launcher = new LinuxAppLauncher(() -> null);
        var app = new AppDefinition("notepad", "Notepad", List.of("notepad.exe"), "minecraft:paper", true);
        var failure = assertThrows(CompletionException.class, () -> launcher.launch(app).toCompletableFuture().join());
        assertTrue(failure.getCause().getMessage().contains("aresos-shell/1.0"));
        assertEquals("app helper unavailable", LinuxAppLauncher.reason(failure));
        assertThrows(IOException.class, () -> new LinuxAppCatalogue().listApps());
    }

    @Test void environmentNamesTheSocketInstanceAndNonce() {
        var shell = ShellClient.fromEnvironment(Map.of("XDG_RUNTIME_DIR", "/run/user/1001",
                "ARESOS_DESKTOP_INSTANCE", "desk", "ARESOS_LAUNCH_NONCE", "abcdefghijklmnop"), FakeHelper.fast());
        assertEquals(ShellClient.State.STARTING, shell.status().state());
        shell.close();
        var missingRuntime = ShellClient.fromEnvironment(Map.of("ARESOS_DESKTOP_INSTANCE", "desk",
                "ARESOS_LAUNCH_NONCE", "abcdefghijklmnop"), FakeHelper.fast());
        missingRuntime.start();
        assertTrue(missingRuntime.status().detail().contains("XDG_RUNTIME_DIR"));
        missingRuntime.close();
    }

    @Test void openWaitsForTheHelperToConfirmAWindow() throws Exception {
        connect();
        var open = client.open("notepad");
        FakeHelper.await(() -> helper.received("open_app").size() == 1, "open_app");
        Thread.sleep(100);
        assertFalse(open.isDone(), "starting is not success while the helper tracks windows");
        var request = helper.received("open_app").getFirst();
        assertEquals("notepad", request.get("app_id").getAsString());
        assertFalse(request.has("command") || request.has("argv"));
        helper.event("app_state", Map.of("request_id", request.get("id").getAsString(), "launch_id", "launch-1",
                "app_id", "notepad", "state", "focused"));
        var launch = join(open);
        assertEquals("launch-1", launch.launchId());
        assertEquals("focused", launch.state());

        var late = client.open("terminal");
        FakeHelper.await(() -> helper.received("open_app").size() == 2, "second open_app");
        helper.event("app_state", Map.of("request_id", helper.received("open_app").get(1).get("id").getAsString(),
                "launch_id", "launch-2", "app_id", "terminal", "state", "failed", "error", "no_window"));
        var refused = refusal(late);
        assertEquals("no_window", refused.code());
        assertEquals("no window appeared", ShellClient.describe(refused));
    }

    @Test void withoutWindowTrackingAStartedAppCountsAsOpened() throws Exception {
        helper.capabilities = List.of("list_apps", "open_app", "app_state", "world_ready", "heartbeat");
        connect();
        assertFalse(client.tracksWindows());
        assertEquals("starting", join(client.open("terminal")).state());
    }

    @Test void unknownAndUnavailableAppsShowTheHelpersReason() throws Exception {
        connect();
        var unknown = refusal(client.open("spotify"));
        assertEquals("unknown_app", unknown.code());
        assertEquals("not an app on AresOS", ShellClient.describe(unknown));
        var browser = refusal(client.open("browser"));
        assertEquals("unavailable", browser.code());
        assertEquals("not installed", ShellClient.describe(new CompletionException(browser)));
        assertEquals(0, helper.launches.get());
    }

    @Test void eachOpenIsOneRequestWithItsOwnId() throws Exception {
        helper.launchState = "focused";
        connect();
        var first = join(client.open("notepad"));
        var second = join(client.open("notepad"));
        assertNotEquals(first.requestId(), second.requestId());
        var ids = helper.received("open_app").stream().map(message -> message.get("id").getAsString()).toList();
        assertEquals(List.of(first.requestId(), second.requestId()), ids);
        assertEquals(2, helper.launches.get());
    }

    @Test void aRestartingHelperIsReconnectedAndAnUncertainOpenIsNeverLaunchedTwice() throws Exception {
        helper.launchState = "focused";
        helper.dropOnFirstOpen = true;
        var refreshed = new CopyOnWriteArrayList<List<ShellClient.App>>();
        client = helper.client(FakeHelper.fast());
        client.addListener(new ShellClient.Listener() {
            @Override public void apps(List<ShellClient.App> apps) { refreshed.add(apps); }
        });
        client.start();
        client.awaitApps(Duration.ofSeconds(5));
        var launch = join(client.open("notepad"));
        assertEquals(1, helper.launches.get(), "The same request ID must not start a second launch");
        var opens = helper.received("open_app");
        assertEquals(2, opens.size());
        assertEquals(opens.get(0).get("id").getAsString(), opens.get(1).get("id").getAsString());
        assertEquals(launch.requestId(), opens.get(0).get("id").getAsString());
        assertEquals(2, helper.connections.get());
        assertEquals(2, helper.received("hello").size());
        FakeHelper.await(() -> refreshed.size() == 2, "the app list to refresh after reconnecting");

        helper.drop();
        FakeHelper.await(() -> helper.connections.get() == 3 && client.status().state() == ShellClient.State.CONNECTED,
                "a reconnect after the helper restarted");
        assertEquals(1, helper.launches.get());
    }

    @Test void aHelperThatStopsReadingIsDetectedAndReconnectedDespiteABlockedWrite() throws Exception {
        helper.stallFirstConnection = true;
        helper.launchState = "focused";
        client = helper.client(new ShellClient.Settings(Duration.ofSeconds(1), Duration.ofSeconds(15),
                Duration.ofMillis(200), Duration.ofMillis(50), Duration.ofMillis(200)));
        client.start();
        client.awaitApps(Duration.ofSeconds(5));
        // Large requests fill the socket buffer of a helper that no longer reads, so the writer blocks.
        var stuck = new ArrayList<CompletableFuture<ShellClient.Launch>>();
        for (int i = 0; i < 12; i++) stuck.add(client.open("x".repeat(60_000)));
        FakeHelper.await(() -> helper.connections.get() >= 2 && client.status().state() == ShellClient.State.CONNECTED,
                "the watchdog to drop the stalled connection and reconnect");
        assertEquals("focused", join(client.open("terminal")).state());
        for (var open : stuck) assertEquals("unknown_app", refusal(open).code());
    }

    @Test void withoutWindowTrackingALaterFailureStillReachesThePlayer() throws Exception {
        helper.capabilities = List.of("list_apps", "open_app", "app_state", "world_ready", "heartbeat");
        connect();
        var failures = new CopyOnWriteArrayList<String>();
        client.addListener(new ShellClient.Listener() {
            @Override public void launchFailed(String appId, ShellClient.ShellException error) {
                failures.add(appId + ": " + error.code() + ": " + ShellClient.describe(error));
            }
        });
        var launch = join(client.open("terminal"));
        assertEquals("starting", launch.state());
        helper.event("app_state", Map.of("request_id", "o-unknown", "state", "failed", "error", "launch_failed"));
        helper.event("app_state", Map.of("request_id", launch.requestId(), "launch_id", launch.launchId(),
                "app_id", "terminal", "state", "failed", "error", "launch_failed"));
        FakeHelper.await(() -> !failures.isEmpty(), "the late failure");
        Thread.sleep(100);
        assertEquals(List.of("terminal: launch_failed: it failed to start"), failures);
        // Reported once: a second failure event for the same launch is ignored.
        helper.event("app_state", Map.of("request_id", launch.requestId(), "state", "failed", "error", "launch_failed"));
        Thread.sleep(100);
        assertEquals(1, failures.size());
    }

    @Test void focusEventsReachListenersInOrder() throws Exception {
        connect();
        var focus = new CopyOnWriteArrayList<ShellClient.Focus>();
        client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) { focus.add(event); }
        });
        helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
        helper.event("shell_focus", Map.of("focus", "foreground", "reason", "app_closed", "app_id", "notepad",
                "activated", true));
        helper.event("shell_focus", Map.of("focus", "foreground", "reason", "desktop_activated"));
        FakeHelper.await(() -> focus.size() == 3, "three focus events");
        assertEquals(List.of(new ShellClient.Focus(false, "app_activated", "notepad", false),
                new ShellClient.Focus(true, "app_closed", "notepad", true),
                new ShellClient.Focus(true, "desktop_activated", null, false)), focus);
    }

    @Test void aHelperThatNeverAnswersTimesOut() throws Exception {
        helper.override = message -> "open_app".equals(FakeHelper.string(message, "op")) ? new JsonObject() : null;
        // An empty object still gets the protocol stamp but no id: the client must ignore it and keep waiting.
        connect();
        long started = System.nanoTime();
        assertEquals("no answer from the app helper", ShellClient.describe(
                assertThrows(ExecutionException.class, () -> client.open("notepad").get(10, TimeUnit.SECONDS))));
        assertTrue(System.nanoTime() - started < TimeUnit.SECONDS.toNanos(6));

        helper.override = message -> "hello".equals(FakeHelper.string(message, "op")) ? new JsonObject() : null;
        var silent = helper.client(FakeHelper.fast());
        silent.start();
        var error = assertThrows(ShellClient.ShellException.class, () -> silent.awaitApps(Duration.ofSeconds(5)));
        assertTrue(error.getMessage().contains("no answer"), error.getMessage());
        silent.close();
    }

    @Test void malformedAndOversizedHelperOutputIsSurvived() throws Exception {
        connect();
        helper.raw("{not json");
        helper.raw("[1,2,3]");
        helper.raw("{\"protocol\":\"aresos-shell/9.0\",\"id\":\"x\",\"event\":\"shell_focus\",\"focus\":\"foreground\"}");
        helper.raw("ÿþ");
        helper.launchState = "focused";
        assertEquals("focused", join(client.open("terminal")).state());
        assertEquals(1, helper.connections.get());
        helper.raw("{\"pad\":\"" + "x".repeat(ShellClient.MAX_MESSAGE) + "\"}");
        FakeHelper.await(() -> helper.connections.get() == 2 && client.status().state() == ShellClient.State.CONNECTED,
                "a fresh connection after an oversized message");
    }

    @Test void worldReadyAndHeartbeatsCarryTheInstanceNonceAndWorld() throws Exception {
        connect();
        client.world("AresOS");
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "world_ready");
        var ready = helper.received("world_ready").getFirst();
        assertEquals(FakeHelper.INSTANCE, ready.get("instance").getAsString());
        assertEquals(FakeHelper.NONCE, ready.get("nonce").getAsString());
        assertEquals("AresOS", ready.getAsJsonObject("world").get("id").getAsString());
        assertTrue(ready.getAsJsonObject("world").get("desktop").getAsBoolean());
        FakeHelper.await(() -> helper.received("heartbeat").stream().anyMatch(beat -> beat.get("ready").getAsBoolean()),
                "a ready heartbeat");
        client.world(null);
        FakeHelper.await(() -> !helper.received("heartbeat").getLast().get("ready").getAsBoolean(), "a not-ready heartbeat");
        assertEquals(1, helper.received("world_ready").size());
    }

    private static JsonObject reply(JsonObject message, boolean ok, String error) {
        var reply = new JsonObject();
        reply.addProperty("id", message.get("id").getAsString());
        reply.addProperty("ok", ok);
        if (error != null) reply.addProperty("error", error);
        return reply;
    }
}
