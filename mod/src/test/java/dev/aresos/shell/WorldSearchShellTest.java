package dev.aresos.shell;

import static org.junit.jupiter.api.Assertions.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Comparator;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Package 53d: Super's shell_search and open_app's "screen": "world" on the mod's side, against a fake 1.2 helper. */
class WorldSearchShellTest {
    private Path folder;
    private FakeHelper helper;
    private ShellClient client;
    private final AtomicInteger searches = new AtomicInteger();

    @BeforeEach void start() throws IOException {
        folder = Files.createTempDirectory("as");
        helper = new FakeHelper(folder);
        helper.minor = 2;
        helper.launchState = "focused";
    }

    @AfterEach void stop() throws IOException {
        if (client != null) client.close();
        helper.close();
        try (var files = Files.walk(folder)) {
            for (var path : files.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        }
    }

    private void connect() throws IOException {
        client = helper.client(FakeHelper.fast());
        client.addListener(new ShellClient.Listener() {
            @Override public void search() { searches.incrementAndGet(); }
        });
        client.start();
        client.awaitApps(Duration.ofSeconds(5));
    }

    private static JsonObject example(String name) throws IOException {
        try (var reader = new InputStreamReader(WorldSearchShellTest.class.getResourceAsStream("/shell-1.2/" + name + ".json"),
                StandardCharsets.UTF_8)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        }
    }

    @Test void minor2IsNegotiatedAndShellSearchOfferedBothWays() throws Exception {
        connect();
        var hello = helper.received("hello").getFirst();
        assertEquals(3, hello.get("minor").getAsInt());
        assertTrue(hello.getAsJsonArray("capabilities").contains(new com.google.gson.JsonPrimitive("shell_search")));
        // The 1.2 fixture still describes the whole hello apart from the two optional 1.3 additions.
        var offered = example("desktop-hello-request").getAsJsonArray("capabilities");
        offered.add("apps_state");
        offered.add("activate_app");
        assertEquals(offered, hello.getAsJsonArray("capabilities"));
        FakeHelper.await(() -> !helper.received("heartbeat").isEmpty(), "first negotiated message");
        assertEquals("aresos-shell/1.2", FakeHelper.string(helper.received("heartbeat").getFirst(), "protocol"));
        assertTrue(example("desktop-hello-reply").getAsJsonArray("capabilities").contains(new com.google.gson.JsonPrimitive("shell_search")));
    }

    @Test void theEventReachesListenersOnMinor2() throws Exception {
        connect();
        helper.raw(example("shell-search-event").toString());
        FakeHelper.await(() -> searches.get() == 1, "the example shell_search");
        helper.event("shell_search", Map.of());
        FakeHelper.await(() -> searches.get() == 2, "a second shell_search");
    }

    @Test void anOlderConnectionNeverActsOnIt() throws Exception {
        helper.minor = 1;
        connect();
        helper.event("shell_search", Map.of());
        // A later event on the same connection arrives after it: by then the first was dropped, not delayed.
        var covered = new AtomicInteger();
        client.addListener(new ShellClient.Listener() {
            @Override public void covered(boolean now) { covered.incrementAndGet(); }
        });
        helper.event("shell_covered", Map.of("covered", true));
        FakeHelper.await(() -> covered.get() == 1, "the event after it");
        assertEquals(0, searches.get());
    }

    @Test void theWorldScreenIsNamedOnlyOnMinor2AsTheExampleShows() throws Exception {
        connect();
        client.open("notepad", ShellClient.SCREEN_WORLD).get(10, TimeUnit.SECONDS);
        client.open("terminal").get(10, TimeUnit.SECONDS);
        var opens = helper.received("open_app");
        var request = example("open-app-world-request");
        for (var key : new String[] {"protocol", "op", "app_id", "screen"}) assertEquals(request.get(key), opens.get(0).get(key), key);
        assertFalse(opens.get(1).has("screen"));
        assertThrows(IllegalArgumentException.class, () -> client.open("notepad", "laptop"));
    }

    @Test void anOlderHelperNeverSeesTheKey() throws Exception {
        helper.minor = 1;
        connect();
        client.open("notepad", ShellClient.SCREEN_WORLD).get(10, TimeUnit.SECONDS);
        assertFalse(helper.received("open_app").getFirst().has("screen"));
    }

    @Test void theHintIsKeptOnAResendAfterAReconnect() throws Exception {
        helper.dropOnFirstOpen = true;
        connect();
        var launch = client.open("notepad", ShellClient.SCREEN_WORLD).get(10, TimeUnit.SECONDS);
        var opens = helper.received("open_app");
        assertEquals(2, opens.size(), "the open was resent after the reconnect");
        assertEquals(1, helper.launches.get());
        for (var open : opens) {
            assertEquals(launch.requestId(), open.get("id").getAsString());
            assertEquals(ShellClient.SCREEN_WORLD, open.get("screen").getAsString());
        }
    }

    /**
     * Review 1, should-fix 3: a quick reload of the same save. The watchdog's heartbeat, queued before the world went
     * away, runs while it is gone and says not ready, which takes Super away on the helper's side; the same save is
     * ready again before the writer reports the change. It must still send world_ready again, or Super stays off.
     */
    @Test void theSameSaveIsReportedAgainAfterANotReadyHeartbeat() throws Exception {
        connect();
        client.world("AresHub");
        FakeHelper.await(() -> helper.received("world_ready").size() == 1, "the first world_ready");
        // Heartbeats from before the world was ready said not ready too.
        long notReady = notReadyHeartbeats();
        var first = new CountDownLatch(1);
        var second = new CountDownLatch(1);
        // Hold the writer, so its tasks run in this order: the heartbeat, then the reports of the world's changes.
        assertTrue(client.later(() -> hold(first)));
        assertTrue(client.later(client::heartbeatNow));
        assertTrue(client.later(() -> hold(second)));
        client.world(null);
        first.countDown();
        FakeHelper.await(() -> notReadyHeartbeats() > notReady, "the not-ready heartbeat");
        client.world("AresHub");
        second.countDown();
        FakeHelper.await(() -> helper.received("world_ready").size() == 2, "world_ready again for the same save");
        assertEquals("AresHub", helper.received("world_ready").get(1).getAsJsonObject("world").get("id").getAsString());
    }

    private long notReadyHeartbeats() {
        return helper.received("heartbeat").stream().filter(beat -> !beat.get("ready").getAsBoolean()).count();
    }

    private static void hold(CountDownLatch latch) {
        try { latch.await(10, TimeUnit.SECONDS); }
        catch (InterruptedException stopped) { Thread.currentThread().interrupt(); }
    }
}
