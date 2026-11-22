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

/** The mod side of aresos-shell against a fake 1.0 helper on a real Unix socket. ShellListTest covers 1.1. */
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
        // hello carries the client's own version; after a 1.0 helper's reply everything else says 1.0.
        assertEquals("aresos-shell/1.2", hello.get("protocol").getAsString());
        assertEquals(1, hello.get("major").getAsInt());
        assertEquals(2, hello.get("minor").getAsInt());
        assertEquals(FakeHelper.INSTANCE, hello.get("instance").getAsString());
        assertEquals(FakeHelper.NONCE, hello.get("nonce").getAsString());
        var capabilities = hello.getAsJsonArray("capabilities").asList().stream().map(value -> value.getAsString()).toList();
        assertTrue(capabilities.containsAll(List.of("open_app", "app_state", "shell_focus", "world_ready", "heartbeat")));
        assertEquals(List.of("list_apps", "open_app"),
                hello.getAsJsonArray("requires").asList().stream().map(value -> value.getAsString()).toList());
        client.world("AresOS");
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "world_ready");
        for (var message : helper.received) {
            assertEquals(message == hello ? "aresos-shell/1.2" : "aresos-shell/1.0", message.get("protocol").getAsString());
            assertTrue(message.get("id").getAsString().matches("[A-Za-z0-9._:-]{1,128}"));
        }
        assertFalse(client.detailed());
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
        assertEquals(List.of("minecraft:black_concrete", "minecraft:writable_book", "minecraft:compass"),
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
        assertTrue(failure.getCause().getMessage().contains("aresos-shell/1.2"));
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

    @Test void anOpenSentInsideTheStartupCallbackIsNotSentAgainByReplay() throws Exception {
        var received = new CountDownLatch(1);
        var resume = new CountDownLatch(1);
        var opened = new CompletableFuture<CompletableFuture<ShellClient.Launch>>();
        // Keep the future pending until the writer barrier: an early focused reply could hide replay's duplicate.
        helper.launchState = "starting";
        helper.override = message -> {
            if ("open_app".equals(FakeHelper.string(message, "op"))) received.countDown();
            return null;
        };
        client = helper.client(FakeHelper.fast());
        client.world("startup-barrier");
        // Drain world()'s pre-start task while disconnected. Only session's post-replay task may send world_ready.
        var writerField = ShellClient.class.getDeclaredField("writer");
        writerField.setAccessible(true);
        var drained = new CountDownLatch(1);
        ((ExecutorService) writerField.get(client)).execute(drained::countDown);
        assertTrue(drained.await(5, TimeUnit.SECONDS), "The pre-start writer task did not drain");
        client.addListener(new ShellClient.Listener() {
            @Override public void apps(List<ShellClient.App> apps) {
                opened.complete(client.open("notepad"));
                try {
                    if (!received.await(5, TimeUnit.SECONDS) || !resume.await(5, TimeUnit.SECONDS))
                        throw new AssertionError("Startup send barrier timed out");
                } catch (InterruptedException error) { throw new AssertionError(error); }
            }
        });
        client.start();
        try { assertTrue(received.await(5, TimeUnit.SECONDS), "The normal send never reached the helper"); }
        finally { resume.countDown(); }
        client.awaitApps(Duration.ofSeconds(5));
        // Startup queues world_ready after replay on the same writer, so receiving it is a writer barrier.
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "the startup replay writer barrier");
        assertFalse(join(opened).isDone(), "The open must remain pending through startup replay");
        assertEquals(1, helper.connections.get());
        var ids = helper.received("open_app").stream().map(message -> FakeHelper.string(message, "id")).toList();
        assertEquals(1, ids.size(), "An ID was sent twice on one connection: " + ids);
        helper.event("app_state", Map.of("request_id", ids.getFirst(), "launch_id", "launch-1",
                "app_id", "notepad", "state", "focused"));
        assertEquals(ids.getFirst(), join(join(opened)).requestId());
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

    private CopyOnWriteArrayList<String> lateFailures() {
        var failures = new CopyOnWriteArrayList<String>();
        client.addListener(new ShellClient.Listener() {
            @Override public void launchFailed(String appId, String requestId, ShellClient.ShellException error) {
                failures.add(appId + " " + requestId + ": " + error.code() + ": " + ShellClient.describe(error));
            }
        });
        return failures;
    }

    @Test void withoutWindowTrackingALaterFailureStillReachesThePlayer() throws Exception {
        helper.capabilities = List.of("list_apps", "open_app", "app_state", "world_ready", "heartbeat");
        connect();
        var failures = lateFailures();
        var launch = join(client.open("terminal"));
        assertEquals("starting", launch.state());
        helper.event("app_state", Map.of("request_id", "o-unknown", "state", "failed", "error", "launch_failed"));
        helper.event("app_state", Map.of("request_id", launch.requestId(), "launch_id", launch.launchId(),
                "app_id", "terminal", "state", "failed", "error", "launch_failed"));
        FakeHelper.await(() -> !failures.isEmpty(), "the late failure");
        Thread.sleep(100);
        assertEquals(List.of("terminal " + launch.requestId() + ": launch_failed: it failed to start"), failures);
        // Reported once: a second failure event for the same launch is ignored.
        helper.event("app_state", Map.of("request_id", launch.requestId(), "state", "failed", "error", "launch_failed"));
        Thread.sleep(100);
        assertEquals(1, failures.size());
    }

    @Test void aLateFailureNamesItsOwnLaunchWhenTheSameAppRunsTwice() throws Exception {
        helper.capabilities = List.of("list_apps", "open_app", "app_state", "world_ready", "heartbeat");
        connect();
        var failures = lateFailures();
        var first = join(client.open("notepad"));
        var second = join(client.open("notepad"));
        assertNotEquals(first.requestId(), second.requestId());
        helper.event("app_state", Map.of("request_id", first.requestId(), "app_id", "notepad", "state", "failed",
                "error", "launch_failed"));
        FakeHelper.await(() -> !failures.isEmpty(), "the first launch's failure");
        Thread.sleep(100);
        assertEquals(List.of("notepad " + first.requestId() + ": launch_failed: it failed to start"), failures);
    }

    @Test void aFailureWhileDisconnectedStillReachesThePlayerOnce() throws Exception {
        helper.capabilities = List.of("list_apps", "open_app", "app_state", "world_ready", "heartbeat");
        connect();
        var failures = lateFailures();
        var launch = join(client.open("terminal"));
        // The helper records the failure but the event never arrives: the connection breaks first.
        var recorded = helper.journal.get(launch.requestId());
        recorded.addProperty("state", "failed");
        recorded.addProperty("error", "launch_failed");
        helper.drop();
        FakeHelper.await(() -> !failures.isEmpty(), "the failure after reconnecting");
        assertEquals(List.of("terminal " + launch.requestId() + ": launch_failed: it failed to start"), failures);
        assertEquals(2, helper.received("open_app").size(), "the watched request is asked again, once");
        assertEquals(launch.requestId(), helper.received("open_app").get(1).get("id").getAsString());
        helper.event("app_state", Map.of("request_id", launch.requestId(), "state", "failed", "error", "launch_failed"));
        helper.drop();
        FakeHelper.await(() -> helper.connections.get() == 3 && client.status().state() == ShellClient.State.CONNECTED,
                "a second reconnect");
        Thread.sleep(200);
        assertEquals(1, failures.size());
        assertEquals(1, helper.launches.get());
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

    @Test void aLateListenerReceivesFocusReportedDuringTheHandshake() throws Exception {
        helper.override = message -> {
            if ("hello".equals(FakeHelper.string(message, "op"))) try {
                helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
            } catch (IOException error) { throw new java.io.UncheckedIOException(error); }
            return null;
        };
        connect();
        var focus = new CopyOnWriteArrayList<ShellClient.Focus>();
        client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) { focus.add(event); }
        });
        assertEquals(List.of(new ShellClient.Focus(false, "app_activated", "notepad", false)), focus);
    }

    @Test void aFocusReplayCannotArriveAfterANewerFocusEvent() throws Exception {
        connect();
        var first = new CopyOnWriteArrayList<ShellClient.Focus>();
        client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) { first.add(event); }
        });
        helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
        FakeHelper.await(() -> first.size() == 1, "initial focus received");
        var replaying = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        var focus = new CopyOnWriteArrayList<ShellClient.Focus>();
        var subscribed = CompletableFuture.runAsync(() -> client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) {
                if (!event.foreground()) {
                    replaying.countDown();
                    try { assertTrue(release.await(5, TimeUnit.SECONDS)); }
                    catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new RuntimeException(error); }
                }
                focus.add(event);
            }
        }));
        try {
            assertTrue(replaying.await(5, TimeUnit.SECONDS));
            helper.event("shell_focus", Map.of("focus", "foreground", "reason", "desktop_activated"));
            helper.launchState = "focused";
            var opened = client.open("terminal");
            // Its reply is behind the focus event on the same socket: neither may overtake the blocked replay.
            assertThrows(TimeoutException.class, () -> opened.get(100, TimeUnit.MILLISECONDS));
            release.countDown();
            subscribed.get(5, TimeUnit.SECONDS);
            opened.get(5, TimeUnit.SECONDS);
            assertEquals(List.of(new ShellClient.Focus(false, "app_activated", "notepad", false),
                    new ShellClient.Focus(true, "desktop_activated", null, false)), focus);
        } finally { release.countDown(); }
    }

    @Test void aLostConnectionDoesNotReplayItsOldFocusToANewListener() throws Exception {
        connect();
        var first = new CopyOnWriteArrayList<ShellClient.Focus>();
        client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) { first.add(event); }
        });
        helper.event("shell_focus", Map.of("focus", "background", "reason", "app_activated", "app_id", "notepad"));
        FakeHelper.await(() -> first.size() == 1, "initial focus received");
        helper.override = message -> "hello".equals(FakeHelper.string(message, "op")) ? new JsonObject() : null;
        helper.drop();
        FakeHelper.await(() -> client.status().state() != ShellClient.State.CONNECTED, "connection lost");
        var replayed = new CopyOnWriteArrayList<ShellClient.Focus>();
        client.addListener(new ShellClient.Listener() {
            @Override public void focus(ShellClient.Focus event) { replayed.add(event); }
        });
        assertTrue(replayed.isEmpty());
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

    /** Package 40: a program that started but showed no window of its own is said as that, not as a silent helper. */
    @Test void aStartedProgramWithoutAWindowIsNotReportedAsAMissingAnswer() throws Exception {
        connect();
        var refused = refusal(client.open("notepad"));  // the fake helper answers "starting" and nothing more
        assertEquals("no_window", refused.code());
        assertEquals("it started, but no window of it appeared", ShellClient.describe(refused));
    }

    /** Package 40: what the helper says about covering reaches listeners once per change; a lost helper uncovers. */
    @Test void coveredReachesListenersAndALostHelperUncovers() throws Exception {
        connect();
        var covered = new CopyOnWriteArrayList<Boolean>();
        client.addListener(new ShellClient.Listener() {
            @Override public void covered(boolean now) { covered.add(now); }
        });
        var offered = helper.received("hello").getFirst().getAsJsonArray("capabilities").asList();
        assertTrue(offered.stream().anyMatch(value -> value.getAsString().equals("shell_covered")));
        try (var input = ShellClientTest.class.getResourceAsStream("/shell-1.1/shell-covered-event.json")) {
            // The example says covered; a 1.0 helper's envelope is accepted like any other 1.x.
            var example = com.google.gson.JsonParser.parseString(new String(input.readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
            example.addProperty("protocol", "aresos-shell/1.0");
            helper.raw(example.toString());
        }
        helper.event("shell_covered", Map.of("covered", true));  // no change, no call
        helper.event("shell_covered", Map.of("covered", false));
        helper.event("shell_covered", Map.of("covered", true));
        FakeHelper.await(() -> covered.size() == 3, "three changes");
        helper.drop();
        FakeHelper.await(() -> covered.size() == 4, "uncovered when the helper went away");
        assertEquals(List.of(true, false, true, false), covered);
    }

    /**
     * Package 40, linux-aresos's condition: package 23's supervisor takes missing heartbeats for a dead world. Covering
     * pauses the world, so the helper must go on hearing ready heartbeats with the world, and no new world_ready.
     */
    @Test void heartbeatsKeepSayingReadyWhileCovered() throws Exception {
        connect();
        var covered = new CopyOnWriteArrayList<Boolean>();
        client.addListener(new ShellClient.Listener() {
            @Override public void covered(boolean now) { covered.add(now); }
        });
        client.world("AresOS");
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "world_ready");
        helper.event("shell_covered", Map.of("covered", true));
        FakeHelper.await(() -> covered.equals(List.of(true)), "covered");
        int before = helper.received("heartbeat").size();
        FakeHelper.await(() -> helper.received("heartbeat").size() >= before + 5, "five heartbeats while covered");
        var beats = helper.received("heartbeat");
        for (var beat : beats.subList(before, beats.size())) {
            assertTrue(beat.get("ready").getAsBoolean(), beat.toString());
            assertEquals("AresOS", beat.getAsJsonObject("world").get("id").getAsString());
        }
        assertEquals(1, helper.received("world_ready").size());
        assertEquals(List.of(true), covered);
    }

    /** Package 40: only a game the AresOS session started is the desktop window. */
    @Test void onlyAGameTheSessionStartedIsADesktopSession() {
        assertTrue(ShellClient.configured(Map.of("XDG_RUNTIME_DIR", "/run/user/1001",
                "ARESOS_DESKTOP_INSTANCE", "desk", "ARESOS_LAUNCH_NONCE", "abcdefghijklmnop")));
        assertTrue(ShellClient.configured(Map.of("ARESOS_SHELL_SOCKET", "/run/user/1001/dev/shell.sock",
                "ARESOS_DESKTOP_INSTANCE", "desk", "ARESOS_LAUNCH_NONCE", "abcdefghijklmnop")));
        assertFalse(ShellClient.configured(Map.of("XDG_RUNTIME_DIR", "/run/user/1001")));
        assertFalse(ShellClient.configured(Map.of("XDG_RUNTIME_DIR", "/run/user/1001",
                "ARESOS_DESKTOP_INSTANCE", "desk", "ARESOS_LAUNCH_NONCE", " ")));
        assertFalse(ShellClient.configured(Map.of("ARESOS_DESKTOP_INSTANCE", "desk",
                "ARESOS_LAUNCH_NONCE", "abcdefghijklmnop")));
    }
}
