package dev.aresos.shell;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.*;

class HomePublishTest {
    @TempDir Path directory;

    private static HomeState.App row(String id, String name, String shortName, String place, Integer slot, String block) {
        return new HomeState.App(id, name, shortName, "system_tools", place, slot,
                Collections.nCopies(144, block), place != null);
    }

    private static HomeState town(String name) {
        return new HomeState(List.of(row("notepad", "Notepad", name, "S0L0", 2, "white_wool")));
    }

    private static HomeState largeTown(String end) {
        return new HomeState(IntStream.range(0, 200)
                .mapToObj(i -> new HomeState.App("fixture-" + "x".repeat(53) + String.format("%03d", i), "Fixture " + i,
                        "\u2028".repeat(63) + end, "g".repeat(64), "N" + "0".repeat(31), null,
                        Collections.nCopies(144, "white_wool"), true))
                .toList());
    }

    private static ShellClient connect(FakeHelper helper, int minor) throws Exception {
        helper.minor = minor;
        var client = helper.client(FakeHelper.fast());
        client.start();
        return client;
    }

    private static JsonObject example(String file) throws Exception {
        try (var reader = new InputStreamReader(HomePublishTest.class.getResourceAsStream("/shell-1.2/" + file),
                StandardCharsets.UTF_8)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        }
    }

    private static void sameExample(JsonObject example, JsonObject message, boolean single) {
        example.add("id", message.get("id"));
        if (single) example.getAsJsonObject("palette").remove("b"); // The example also lists a spare colour.
        assertEquals(example, message);
    }

    @Test void matchesSingleAndMultipartExamples() throws Exception {
        var publish = new HomePublish(Map.of("first-white", 0xe9ecec, "second-blue", 0x2389c6));
        var notepad = row("notepad", "Notepad", "notepad", "S0L0", 2, "first-white");
        var terminal = row("terminal", "Terminal", "term", null, null, "second-blue");
        var ids = new AtomicInteger();
        java.util.function.Supplier<JsonObject> request = () -> {
            var envelope = new JsonObject();
            envelope.addProperty("protocol", "aresos-shell/1.2");
            envelope.addProperty("id", "p-" + ids.incrementAndGet());
            envelope.addProperty("op", "publish_home");
            return envelope;
        };
        var single = publish.messages(new HomeState(List.of(notepad)), "17", request, ShellClient.MAX_MESSAGE);
        assertEquals(1, single.size());
        sameExample(example("publish-home-request.json"), single.getFirst(), true);
        for (var message : single) assertNotNull(FakeHome.receive(null, message, ShellClient.wireBytes(message).length));

        var split = publish.messages(new HomeState(List.of(notepad, terminal)), "18", request, 430);
        assertEquals(2, split.size());
        sameExample(example("publish-home-part-0-request.json"), split.get(0), false);
        sameExample(example("publish-home-part-1-request.json"), split.get(1), false);
        var pending = FakeHome.receive(null, split.getFirst(), ShellClient.wireBytes(split.getFirst()).length);
        assertEquals(2, FakeHome.receive(pending, split.getLast(), ShellClient.wireBytes(split.getLast()).length)
                .published().apps().size());
    }

    @ParameterizedTest
    @ValueSource(ints = {0, 1, 2})
    void needsMinorTwoAndHomeCapability(int minor) throws Exception {
        try (var helper = new FakeHelper(directory)) {
            helper.offerHome = minor < 2;
            try (var client = connect(helper, minor)) {
                client.awaitApps(Duration.ofSeconds(3));
                client.home(town("notepad"));
                int heartbeats = helper.received("heartbeat").size();
                FakeHelper.await(() -> helper.received("heartbeat").size() >= heartbeats + 2, "legacy messages");
                assertEquals(3, helper.received("hello").getFirst().get("minor").getAsInt());
                assertFalse(client.tracksHome());
                assertTrue(helper.received("publish_home").isEmpty());
            }
        }
    }

    @Test void helloWaitsForHomeAndReconnectReplaysTheReadyHome() throws Exception {
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            FakeHelper.await(client::tracksHome, "home capability");
            FakeHelper.await(() -> !helper.received("heartbeat").isEmpty(), "heartbeat after hello");
            assertTrue(helper.received("publish_home").isEmpty());
            client.home(town("notepad"));
            FakeHelper.await(() -> helper.homes.size() == 1, "ready home");
            String before = helper.homes.getFirst().revision();
            helper.drop();
            FakeHelper.await(() -> helper.homes.size() == 2, "replayed home");
            var replay = helper.homes.getLast();
            assertTrue(Long.parseLong(replay.revision()) > Long.parseLong(before));
            assertEquals(helper.homes.getFirst().apps(), replay.apps());
            assertValid(helper);
        }
    }

    @Test void tenChangesCoalesceAndTheLastChangeIsSent() throws Exception {
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            client.home(town("notepad"));
            FakeHelper.await(() -> helper.homes.size() == 1, "first home");
            for (int change = 0; change < 10; change++) client.home(town("note" + change));
            FakeHelper.await(() -> "note9".equals(shortName(helper.homes.getLast())), "last change of burst");
            int heartbeats = helper.received("heartbeat").size();
            FakeHelper.await(() -> helper.received("heartbeat").size() >= heartbeats + 6, "idle heartbeats");
            assertTrue(helper.homes.size() <= 2);
            assertValid(helper);
        }
    }

    @Test void capsAppsByPlaceThenSlotThenNameAndSkipsOnlyBadRows() throws Exception {
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            var rows = new ArrayList<>(IntStream.range(0, 199)
                    .mapToObj(i -> row("unplaced-" + i, String.format("App %03d", i), "app" + i, null, null, "white_wool")).toList());
            rows.add(row("z-placed", "Z place", "placed", "S0R0", null, "white_wool"));
            rows.add(row("z-pinned", "Z pin", "pinned", "?", 5, "white_wool"));
            rows.add(row("x".repeat(65), "Very long ID", "longid", "S0L0", null, "white_wool"));
            rows.add(row("nameless", "Nameless", "", "S1L0", null, "white_wool"));
            client.home(new HomeState(rows));
            FakeHelper.await(() -> helper.homes.size() == 1, "bounded home");
            var apps = helper.homes.getFirst().apps();
            assertEquals(200, apps.size());
            assertFalse(apps.containsKey("unplaced-198"));
            assertFalse(apps.containsKey("x".repeat(65)));
            assertFalse(apps.containsKey("nameless"));
            assertEquals("S0R0", apps.get("z-placed").get("place").getAsString());
            assertEquals(5, apps.get("z-pinned").get("slot").getAsInt());
            assertFalse(apps.get("z-pinned").has("place"));

            rows.removeIf(app -> app.id().equals("nameless"));
            rows.add(row("nameless", "Nameless", "named", "S1L0", null, "white_wool"));
            client.home(new HomeState(rows));
            FakeHelper.await(() -> helper.homes.size() == 2, "named app");
            assertEquals("named", helper.homes.getLast().apps().get("nameless").get("short").getAsString());
            assertValid(helper);
        }
    }

    @Test void keepsThe62MostUsedColoursAndMapsRareColoursByRgbDistance() {
        var blocks = new ArrayList<String>();
        var colours = new HashMap<String, Integer>();
        for (int i = 0; i < 62; i++) {
            String block = "main-" + i;
            colours.put(block, (i * 4) * 0x010101);
            blocks.add(block);
            blocks.add(block);
        }
        for (int i = 0; i < 8; i++) {
            String block = "extra-" + i;
            colours.put(block, colours.get("main-" + i) + 1);
            blocks.add(block);
        }
        while (blocks.size() < 144) blocks.add("");
        var row = new HomeState.App("app", "App", "app", "system_tools", null, null, blocks, false);
        var message = new HomePublish(colours)
                .messages(new HomeState(List.of(row)), "1", JsonObject::new, ShellClient.MAX_MESSAGE).getFirst();
        var home = FakeHome.receive(null, message, ShellClient.wireBytes(message).length).published();
        assertEquals(62, home.palette().size());
        var cells = home.apps().get("app").get("cells").getAsString();
        for (int i = 0; i < 62; i++) {
            assertEquals("#%06x".formatted(colours.get("main-" + i)),
                    home.palette().get(cells.substring(i * 2, i * 2 + 1)).getAsString());
        }
        for (int i = 0; i < 8; i++) assertEquals(cells.charAt(i * 2), cells.charAt(124 + i));
        assertEquals(".".repeat(12), cells.substring(132));
    }

    @Test void disconnectMidPublishRestartsAtZeroWithANewRevision() throws Exception {
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            client.home(town("notepad"));
            FakeHelper.await(() -> helper.homes.size() == 1, "previous complete home");
            helper.dropOnFirstHomePart = true;
            client.home(largeTown("光"));
            FakeHelper.await(() -> helper.homes.size() == 2, "completed replay of multipart town");
            assertEquals(2, helper.connections.get());
            var parts = helper.received("publish_home");
            var dropped = parts.get(1);
            var replay = parts.subList(2, parts.size());
            assertEquals(0, dropped.get("part").getAsInt());
            assertFalse(dropped.get("last").getAsBoolean());
            assertNotEquals(dropped.get("revision"), replay.getFirst().get("revision"));
            assertTrue(replay.size() >= 3);
            assertSequence(replay);
            assertEquals(200, helper.homes.getLast().apps().size());
            assertValid(helper);
        }
    }

    @Test void changeAfterPartZeroWaitsForConsecutivePartsThenPublishesLatest() throws Exception {
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            var release = new CountDownLatch(1);
            var first = new AtomicBoolean(true);
            helper.override = message -> {
                if ("publish_home".equals(FakeHelper.string(message, "op")) && first.getAndSet(false)) {
                    try { assertTrue(release.await(2, TimeUnit.SECONDS)); }
                    catch (InterruptedException error) { throw new AssertionError(error); }
                }
                return null;
            };
            client.home(largeTown("光"));
            try {
                FakeHelper.await(() -> helper.received("publish_home").size() == 1, "part 0 awaiting its reply");
                client.home(town("latest"));
                assertTrue(helper.homes.isEmpty());
            } finally { release.countDown(); }
            FakeHelper.await(() -> helper.homes.size() == 2, "multipart revision and latest");
            assertEquals(200, helper.homes.getFirst().apps().size());
            assertEquals("latest", shortName(helper.homes.getLast()));
            var parts = helper.received("publish_home");
            assertSequence(parts.subList(0, parts.size() - 1));
            assertSequence(parts.subList(parts.size() - 1, parts.size()));
            assertValid(helper);
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"invalid_state", "malformed"})
    void refusalLogsTheHelperMessageKeepsTheConnectionAndTheNextChangePublishes(String refusal) throws Exception {
        var logger = Logger.getLogger("aresos");
        var warning = new AtomicReference<String>();
        String prefix = "AresOS app helper refused publish_home (" + refusal + "): ";
        var handler = new Handler() {
            @Override public void publish(LogRecord record) {
                if (record.getLevel() == Level.WARNING && record.getMessage().startsWith(prefix))
                    warning.set(record.getMessage());
            }
            @Override public void flush() { }
            @Override public void close() { }
        };
        logger.addHandler(handler);
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            helper.refuseHome = refusal;
            helper.launchState = "focused";
            client.home(largeTown("光"));
            FakeHelper.await(() -> warning.get() != null, "warning for refused part 0");
            assertEquals(prefix + "the test refused this home", warning.get());
            client.open("notepad").get(3, TimeUnit.SECONDS);
            assertTrue(helper.homes.isEmpty());
            assertEquals(1, helper.received("publish_home").size(), "stops sending the refused revision");
            helper.refuseHome = null;
            client.home(town("again"));
            FakeHelper.await(() -> helper.homes.size() == 1, "publish after refusal");
            assertEquals("again", shortName(helper.homes.getLast()));
            assertEquals(1, helper.connections.get());
            assertValid(helper);
        } finally {
            logger.removeHandler(handler);
        }
    }

    @Test void eachPublishedFieldChangeGetsANewRevision() throws Exception {
        var notepad = town("notepad").apps().getFirst();
        var terminal = row("terminal", "Terminal", "term", null, null, "white_wool");
        try (var helper = new FakeHelper(directory); var client = connect(helper, 2)) {
            var states = List.of(town("notepad"), new HomeState(List.of(notepad, terminal)), town("notepad"),
                    town("notes"),
                    new HomeState(List.of(row("notepad", "Notepad", "notes", "S1L0", 2, "white_wool"))),
                    new HomeState(List.of(row("notepad", "Notepad", "notes", "S1L0", 8, "white_wool"))),
                    new HomeState(List.of(row("notepad", "Notepad", "notes", "S1L0", 8, "blue_ice"))));
            var revisions = new HashSet<String>();
            for (int i = 0; i < states.size(); i++) {
                var state = states.get(i);
                int count = i + 1;
                client.home(state);
                FakeHelper.await(() -> helper.homes.size() == count, "home change " + i);
                var home = helper.homes.getLast();
                assertTrue(revisions.add(home.revision()));
                assertEquals(state.apps().size(), home.apps().size());
                var source = state.apps().getFirst();
                var actual = home.apps().get("notepad");
                assertEquals(source.shortName(), FakeHelper.string(actual, "short"));
                assertEquals(source.place(), FakeHelper.string(actual, "place"));
                assertEquals(source.slot().intValue(), actual.get("slot").getAsInt());
                assertEquals(i == 6 ? "#74a8fd" : "#eaeced", home.palette().get("a").getAsString());
            }
            assertValid(helper);
        }
    }

    private static String shortName(FakeHelper.PublishedHome home) {
        return FakeHelper.string(home.apps().get("notepad"), "short");
    }

    private static void assertSequence(List<JsonObject> parts) {
        for (int i = 0; i < parts.size(); i++) {
            var part = parts.get(i);
            assertEquals(parts.getFirst().get("revision"), part.get("revision"));
            assertEquals(i, part.get("part").getAsInt());
            assertEquals(i == 0, part.has("palette"));
            assertEquals(i == parts.size() - 1, part.get("last").getAsBoolean());
        }
    }

    private static void assertValid(FakeHelper helper) {
        assertTrue(helper.invalidHome.isEmpty(), helper.invalidHome::toString);
        for (var part : helper.received("publish_home"))
            assertTrue(ShellClient.wireBytes(part).length < ShellClient.MAX_MESSAGE);
    }
}
