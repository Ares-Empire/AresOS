package dev.aresos.shell;

import com.google.gson.*;
import dev.aresos.config.SystemInfo;
import org.junit.jupiter.api.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;

/** The app list of aresos-shell/1.1 (docs/design/HUB.md 3.8) against the fake helper, and against 1.0. */
class ShellListTest {
    private static final Duration INTERVAL = Duration.ofMillis(300);
    private Path folder;
    private FakeHelper helper;
    private ShellClient client;
    private final List<List<ShellClient.App>> lists = new CopyOnWriteArrayList<>();

    @BeforeEach void start() throws IOException {
        folder = Files.createTempDirectory("al");
        helper = new FakeHelper(folder);
        helper.minor = 1;
    }

    @AfterEach void stop() throws IOException {
        if (client != null) client.close();
        helper.close();
        try (var files = Files.walk(folder)) {
            for (var path : files.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        }
    }

    private ShellClient begin() {
        client = helper.client(new ShellClient.Settings(Duration.ofSeconds(2), Duration.ofSeconds(3),
                Duration.ofMillis(200), Duration.ofMillis(50), Duration.ofMillis(200), INTERVAL));
        client.addListener(new ShellClient.Listener() {
            @Override public void apps(List<ShellClient.App> apps) { lists.add(apps); }
        });
        client.start();
        return client;
    }

    private ShellClient connect() throws IOException {
        begin().awaitApps(Duration.ofSeconds(5));
        return client;
    }

    private static List<JsonObject> programs(int count, String name) {
        var rows = new ArrayList<JsonObject>();
        for (int i = 0; i < count; i++)
            rows.add(FakeHelper.entry(String.format("app-%03d", i), name + " " + i, null, "system"));
        return rows;
    }

    private static boolean isList(JsonObject message) { return "list_apps".equals(FakeHelper.string(message, "op")); }

    @Test void aReallyFreshFileWithAOneZeroHelperOwnsAllThreeStartersWithoutABaseline() throws Exception {
        var file = folder.resolve("apps.json");
        assertFalse(Files.exists(file));
        dev.aresos.config.AppsConfig.load(file, true);
        helper.minor = 0;
        connect();
        var listed = dev.aresos.catalogue.LinuxAppCatalogue.definitions(client.apps());
        var first = dev.aresos.config.AppsConfig.merge(file, listed, client.detailed(), java.time.LocalDate.now());
        assertEquals(Set.of("browser", "terminal", "notepad"), first.apps().stream()
                .filter(dev.aresos.config.AppDefinition::mine).map(dev.aresos.config.AppDefinition::id)
                .collect(java.util.stream.Collectors.toSet()));
        assertNull(dev.aresos.config.AppsConfig.load(file).baseline());
        dev.aresos.config.AppsConfig.mine(file, Map.of("browser", false));
        var again = dev.aresos.config.AppsConfig.merge(file, listed, false, null);
        assertFalse(again.apps().stream().filter(app -> app.id().equals("browser")).findFirst().orElseThrow().mine());
        assertNull(again.baseline());
        // Upgrading to a detailed helper must respect that removal too.
        var detailed = dev.aresos.config.AppsConfig.merge(file, listed, true, java.time.LocalDate.now());
        assertFalse(detailed.apps().stream().filter(app -> app.id().equals("browser")).findFirst().orElseThrow().mine());
    }

    private List<String> cursors() {
        return helper.received("list_apps").stream().map(message -> FakeHelper.string(message, "cursor")).toList();
    }

    private static JsonObject example(String name) throws IOException {
        try (var input = ShellListTest.class.getResourceAsStream("/shell-1.1/" + name)) {
            return JsonParser.parseString(new String(input.readAllBytes(), StandardCharsets.UTF_8)).getAsJsonObject();
        }
    }

    private static JsonObject answer(JsonObject example, JsonObject request) {
        var reply = example.deepCopy();
        reply.addProperty("id", request.get("id").getAsString());
        return reply;
    }

    @Test void aOneOneHelperAgreesOnMinorOneAndEveryLaterMessageSaysSo() throws Exception {
        connect();
        var hello = helper.received("hello").getFirst();
        assertEquals("aresos-shell/1.1", hello.get("protocol").getAsString());
        assertEquals(1, hello.get("minor").getAsInt());
        var offered = hello.getAsJsonArray("capabilities").asList().stream().map(JsonElement::getAsString).toList();
        assertTrue(offered.containsAll(List.of("app_details", "apps_changed", "list_paging")), offered.toString());
        assertEquals(List.of("list_apps", "open_app"),
                hello.getAsJsonArray("requires").asList().stream().map(JsonElement::getAsString).toList());
        client.world("AresOS");
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "world_ready");
        for (var message : helper.received) assertEquals("aresos-shell/1.1", message.get("protocol").getAsString());
        assertTrue(client.detailed());
        // The default entries carry no 1.1 field: nothing is known about them, which is not the same as 1.0.
        assertEquals(new ShellClient.App("terminal", "Terminal", true, null, SystemInfo.UNKNOWN), client.apps().getFirst());
    }

    @Test void aOneZeroHelperIsSpokenToAsBeforeEvenIfItSendsOneOneThings() throws Exception {
        helper.minor = 0;
        helper.override = message -> {
            if (!isList(message)) return null;
            var reply = new JsonObject();
            reply.addProperty("id", message.get("id").getAsString());
            reply.addProperty("ok", true);
            reply.addProperty("revision", "r1");
            var row = FakeHelper.entry("terminal", "Terminal", null, "user");
            row.addProperty("icon", "/tmp/terminal.png");
            var rows = new JsonArray();
            rows.add(row);
            reply.add("apps", rows);
            reply.addProperty("next", "p1");
            return reply;
        };
        connect();
        assertEquals("aresos-shell/1.1", helper.received("hello").getFirst().get("protocol").getAsString());
        assertFalse(client.detailed());
        assertEquals(List.of(new ShellClient.App("terminal", "Terminal", true, null)), client.apps());
        helper.event("apps_changed", Map.of("revision", "r2"));
        client.world("AresOS");
        FakeHelper.await(() -> !helper.received("world_ready").isEmpty(), "world_ready");
        Thread.sleep(INTERVAL.toMillis() * 2);
        assertEquals(Collections.singletonList((String) null), cursors(), "one list request, without a cursor");
        for (var message : helper.received) if (!"hello".equals(FakeHelper.string(message, "op")))
            assertEquals("aresos-shell/1.0", message.get("protocol").getAsString());
        assertEquals(1, lists.size());
    }

    @Test void aLongListComesInPagesAndReachesTheGameOnce() throws Exception {
        helper.entries = programs(150, "Program");
        helper.pageSize = 40;
        var apps = connect().apps();
        assertEquals(150, apps.size());
        for (int i = 0; i < 150; i++) {
            assertEquals(String.format("app-%03d", i), apps.get(i).id());
            assertEquals("system", apps.get(i).system().source());
        }
        assertEquals(Arrays.asList(null, "p40", "p80", "p120"), cursors());
        assertEquals(List.of(apps), lists);
    }

    @Test void aRevisionChangeBetweenPagesStartsTheListOver() throws Exception {
        helper.entries = programs(100, "Old");
        helper.revision = "r1";
        helper.pageSize = 40;
        var requests = new AtomicInteger();
        helper.override = message -> {
            // The list changes while the client is between its first and second page.
            if (isList(message) && requests.incrementAndGet() == 2) {
                helper.entries = programs(90, "New");
                helper.revision = "r2";
            }
            return null;
        };
        var apps = connect().apps();
        assertEquals(90, apps.size());
        assertTrue(apps.stream().allMatch(app -> app.name().startsWith("New ")), "a list mixed from two revisions");
        assertEquals(Arrays.asList(null, "p40", null, "p40", "p80"), cursors());
        assertEquals(1, lists.size(), "only the complete list reaches the game");
    }

    @Test void malformedRevisionsNeverPublishOrChangeTheAppsFile() throws Exception {
        helper.launchState = "focused";
        connect();
        var file = folder.resolve("apps.json");
        dev.aresos.config.AppsConfig.load(file, true);
        dev.aresos.config.AppsConfig.merge(file, dev.aresos.catalogue.LinuxAppCatalogue.definitions(client.apps()),
                true, java.time.LocalDate.now());
        String before = Files.readString(file);
        var published = client.apps();
        client.addListener(new ShellClient.Listener() {
            @Override public void apps(List<ShellClient.App> apps) {
                try { dev.aresos.config.AppsConfig.merge(file, dev.aresos.catalogue.LinuxAppCatalogue.definitions(apps),
                        true, java.time.LocalDate.now()); }
                catch (IOException error) { throw new java.io.UncheckedIOException(error); }
            }
        });
        var invalid = Arrays.asList(null, JsonNull.INSTANCE, new JsonPrimitive(7), new JsonObject(), new JsonPrimitive(""));
        for (var revision : invalid) for (boolean onSecondPage : List.of(false, true)) {
            var requests = new AtomicInteger();
            helper.override = message -> {
                if (!isList(message)) return null;
                boolean first = requests.incrementAndGet() == 1;
                var reply = new JsonObject();
                reply.addProperty("id", FakeHelper.string(message, "id"));
                reply.addProperty("ok", true);
                if (onSecondPage && first) reply.addProperty("revision", "new-list");
                else if (revision != null) reply.add("revision", revision);
                var rows = new JsonArray();
                rows.add(FakeHelper.entry(first ? "new-a" : "new-b", "New", null, "user"));
                reply.add("apps", rows);
                if (first) reply.addProperty("next", "p1");
                return reply;
            };
            helper.event("apps_changed", Map.of("revision", "new-list"));
            FakeHelper.await(() -> requests.get() == (onSecondPage ? 2 : 1), "the malformed revision");
            // A later round trip lets the reader finish processing the invalid page before these assertions.
            client.open("notepad").get(5, TimeUnit.SECONDS);
            assertSame(published, client.apps(), "A malformed revision replaced the published list");
            assertEquals(1, lists.size(), "An incomplete list reached a listener");
            assertEquals(before, Files.readString(file), "A malformed revision changed the apps file or baseline");
        }
    }

    @Test void malformedInitialRevisionsNeverSetABaseline() throws Exception {
        var invalid = Arrays.asList(null, JsonNull.INSTANCE, new JsonPrimitive(7), new JsonObject(), new JsonPrimitive(""));
        int index = 0;
        for (var revision : invalid) {
            var file = folder.resolve("fresh-" + index++ + ".json");
            dev.aresos.config.AppsConfig.load(file, true);
            String before = Files.readString(file);
            helper.override = message -> {
                if (!isList(message)) return null;
                var reply = new JsonObject();
                reply.addProperty("id", FakeHelper.string(message, "id"));
                reply.addProperty("ok", true);
                if (revision != null) reply.add("revision", revision);
                var rows = new JsonArray();
                rows.add(FakeHelper.entry("user-program", "User program", null, "user"));
                reply.add("apps", rows);
                return reply;
            };
            client = helper.client(FakeHelper.fast());
            client.addListener(new ShellClient.Listener() {
                @Override public void catalogue(ShellClient.AppList listed) {
                    try { dev.aresos.config.AppsConfig.merge(file, dev.aresos.catalogue.LinuxAppCatalogue.definitions(listed.apps()),
                            listed.detailed(), java.time.LocalDate.now()); }
                    catch (IOException error) { throw new java.io.UncheckedIOException(error); }
                }
            });
            client.start();
            assertEquals("list_incomplete", assertThrows(ShellClient.ShellException.class,
                    () -> client.awaitCatalogue(Duration.ofSeconds(5))).code());
            assertTrue(client.apps().isEmpty());
            assertEquals(before, Files.readString(file));
            assertNull(dev.aresos.config.AppsConfig.load(file).baseline());
            client.close();
        }
    }

    @Test void anOlderSnapshotKeepsItsOwnProtocolDetailsAfterReconnect() throws Exception {
        helper.minor = 0;
        connect();
        var initial = client.awaitCatalogue(Duration.ofSeconds(1));
        assertFalse(initial.detailed());
        helper.minor = 1;
        helper.drop();
        FakeHelper.await(client::detailed, "a detailed list after reconnect");
        assertFalse(initial.detailed(), "The older list acquired the newer connection's protocol details");
        assertTrue(initial.apps().stream().allMatch(app -> app.system() == null));
        assertTrue(client.apps().stream().allMatch(app -> app.system() != null));
    }

    @Test void aListThatNeverHoldsStillIsGivenUpAndTriedAgainAtTheNextChange() throws Exception {
        helper.entries = programs(100, "Program");
        helper.pageSize = 40;
        helper.launchState = "focused";
        var revisions = new AtomicInteger();
        helper.override = message -> {
            if (isList(message) && message.has("cursor")) helper.revision = "r" + revisions.incrementAndGet();
            return null;
        };
        var error = assertThrows(ShellClient.ShellException.class, () -> begin().awaitApps(Duration.ofSeconds(5)));
        assertEquals("list_incomplete", error.code());
        // The first try and three more, two pages each; then the client stops asking.
        assertEquals(Arrays.asList(null, "p40", null, "p40", null, "p40", null, "p40"), cursors());
        FakeHelper.await(() -> client.status().state() == ShellClient.State.CONNECTED, "the connection to stay up");
        assertEquals(List.of(), client.apps());
        assertTrue(lists.isEmpty(), "an incomplete list reached the game");
        assertEquals("focused", client.open("app-000").get(10, TimeUnit.SECONDS).state());

        helper.override = message -> null;
        helper.event("apps_changed", Map.of("revision", helper.revision));
        FakeHelper.await(() -> lists.size() == 1, "the list after the next change");
        assertEquals(100, client.apps().size());
        assertEquals(1, helper.connections.get());
    }

    @Test void aListThatNeverEndsOrIsFarTooLongIsCutOff() throws Exception {
        var pages = new AtomicInteger();
        helper.override = message -> {
            if (!isList(message)) return null;
            int page = pages.incrementAndGet();
            var reply = new JsonObject();
            reply.addProperty("id", message.get("id").getAsString());
            reply.addProperty("ok", true);
            reply.addProperty("revision", "r1");
            var rows = new JsonArray();
            rows.add(FakeHelper.entry("app-" + page, "Program " + page, null, "system"));
            reply.add("apps", rows);
            reply.addProperty("next", "p" + page);
            return reply;
        };
        assertEquals("list_incomplete",
                assertThrows(ShellClient.ShellException.class, () -> begin().awaitApps(Duration.ofSeconds(10))).code());
        Thread.sleep(200);
        assertEquals(ShellClient.MAX_PAGES, helper.received("list_apps").size());
        assertEquals(ShellClient.State.CONNECTED, client.status().state());
        assertTrue(lists.isEmpty());
        client.close();

        helper.received.clear();
        helper.override = message -> null;
        helper.entries = programs(ShellClient.MAX_APPS + 200, "P");
        helper.pageSize = 500;
        assertEquals("list_incomplete",
                assertThrows(ShellClient.ShellException.class, () -> begin().awaitApps(Duration.ofSeconds(10))).code());
        assertEquals(3, helper.received("list_apps").size());
        assertTrue(lists.isEmpty());
    }

    @Test void whatTheSystemKnowsIsReadAndBrokenValuesCountAsNotKnown() throws Exception {
        var hostile = FakeHelper.entry("hostile", "Hostile", null, "root");
        hostile.addProperty("icon", "relative/icon.png");
        var categories = new JsonArray();
        categories.add("Net work");
        categories.add("x".repeat(33));
        categories.add(7);
        for (int i = 0; i < 1000; i++) categories.add("C" + i);
        hostile.add("categories", categories);
        hostile.addProperty("generic_name", "g".repeat(65));
        var keywords = new JsonArray();
        keywords.add(1);
        keywords.add(true);
        keywords.add("ok");
        keywords.add("k".repeat(33));
        keywords.add("");
        keywords.add("two\nlines");
        hostile.add("keywords", keywords);
        hostile.addProperty("desktop_id", "d".repeat(129));
        hostile.addProperty("exec_name", "/usr/bin/evil");
        hostile.addProperty("terminal", "yes");
        hostile.addProperty("command", "rm -rf /");

        var wrongTypes = FakeHelper.entry("wrong-types", "Wrong types", null);
        wrongTypes.addProperty("source", 7);
        var list = new JsonArray();
        list.add("/a.png");
        wrongTypes.add("icon", list);
        wrongTypes.addProperty("categories", "Game");
        wrongTypes.add("generic_name", new JsonObject());
        wrongTypes.add("keywords", new JsonObject());
        wrongTypes.addProperty("desktop_id", 5);
        wrongTypes.addProperty("exec_name", true);
        wrongTypes.addProperty("terminal", 1);

        var oversized = FakeHelper.entry("oversized", "n".repeat(80), null, "user");
        oversized.addProperty("icon", "/" + "a".repeat(5000));
        oversized.addProperty("generic_name", "tab\there");
        oversized.addProperty("exec_name", "e".repeat(129));

        var noName = FakeHelper.entry("no-name", "x", null);
        noName.remove("name");
        var badId = FakeHelper.entry("Bad ID", "Bad", null);
        helper.entries = List.of(example("entry-full.json"), hostile, wrongTypes, oversized, noName, badId,
                example("entry-full.json"), example("entry-minimal.json"));
        var apps = connect().apps();

        var first16 = new ArrayList<String>();
        for (int i = 0; i < 16; i++) first16.add("C" + i);
        assertEquals(List.of(
                new ShellClient.App("com-discordapp-discord", "Discord", true, null, new SystemInfo("flatpak-user",
                        "/run/user/1000/aresos/icons/com-discordapp-discord.png", List.of("Network", "InstantMessaging"),
                        "Internet Messenger", List.of("chat", "voice", "messaging"), "com.discordapp.Discord.desktop",
                        "com.discordapp.Discord", false)),
                new ShellClient.App("hostile", "Hostile", true, null,
                        new SystemInfo(null, null, first16, null, List.of("ok"), null, null, null)),
                new ShellClient.App("wrong-types", "Wrong types", true, null, SystemInfo.UNKNOWN),
                new ShellClient.App("oversized", "n".repeat(64), true, null,
                        new SystemInfo("user", null, null, null, null, null, null, null)),
                new ShellClient.App("terminal", "Terminal", true, null, SystemInfo.UNKNOWN)), apps);
        assertTrue(SystemInfo.UNKNOWN.isEmpty());
        assertFalse(apps.getFirst().system().isEmpty());
    }

    @Test void appsChangedListsAgainButNotMoreOftenThanTheInterval() throws Exception {
        var times = new CopyOnWriteArrayList<Long>();
        helper.override = message -> {
            if (!isList(message)) return null;
            times.add(System.nanoTime());
            // Five changes while the first list is still on its way: they must share one new list.
            if (times.size() == 1) for (int i = 0; i < 5; i++) {
                try { helper.event("apps_changed", Map.of("revision", "r" + i)); }
                catch (IOException error) { throw new IllegalStateException(error); }
            }
            return null;
        };
        connect();
        FakeHelper.await(() -> lists.size() == 2, "the list after a burst of changes");
        // One more change at once: its list has to wait until the interval since the second list is over.
        helper.entries = programs(4, "Program");
        helper.event("apps_changed", Map.of("revision", "r9"));
        FakeHelper.await(() -> lists.size() == 3, "the list after one more change");
        assertEquals(4, client.apps().size());
        Thread.sleep(INTERVAL.toMillis() * 2);
        assertEquals(3, times.size(), "six changes must make two more lists, not six");
        // Half the interval allows for a slow test machine; without the limit the gaps are a millisecond or two.
        for (int i = 1; i < times.size(); i++)
            assertTrue(times.get(i) - times.get(i - 1) >= INTERVAL.toNanos() / 2, "lists " + i + " came too close together");
        assertEquals(1, helper.connections.get());
    }

    @Test void aChangeDuringARefreshListsOnceMore() throws Exception {
        helper.entries = programs(100, "Program");
        helper.pageSize = 40;
        var requests = new AtomicInteger();
        helper.override = message -> {
            // The fourth request is the first page of the refresh: the list changes again while it runs.
            if (isList(message) && requests.incrementAndGet() == 4) {
                try { helper.event("apps_changed", Map.of("revision", helper.revision)); }
                catch (IOException error) { throw new IllegalStateException(error); }
            }
            return null;
        };
        connect();
        assertEquals(3, requests.get());
        helper.event("apps_changed", Map.of("revision", helper.revision));
        FakeHelper.await(() -> lists.size() == 3, "the refresh and the one after it");
        Thread.sleep(INTERVAL.toMillis() * 2);
        assertEquals(9, requests.get());
        assertEquals(3, lists.size());
    }

    @Test void aRefreshPageThatNeverComesDoesNotBlockTheNextRefresh() throws Exception {
        connect();
        var swallowed = new AtomicInteger();
        helper.override = message -> isList(message) && swallowed.getAndIncrement() == 0 ? new JsonObject() : null;
        helper.event("apps_changed", Map.of("revision", "r1"));
        FakeHelper.await(() -> swallowed.get() == 1, "the refresh the helper never answers");
        // The reply timeout (2 s here) ends that refresh; the change that came meanwhile then gets its list.
        helper.event("apps_changed", Map.of("revision", "r2"));
        FakeHelper.await(() -> lists.size() == 2, "the list after the stuck refresh");
        assertEquals(1, helper.connections.get());
    }

    @Test void theExampleMessagesAreWhatTheClientSendsAndReads() throws Exception {
        var first = example("list-apps-reply-first-page.json");
        var last = example("list-apps-reply-last-page.json");
        helper.override = message -> switch (String.valueOf(FakeHelper.string(message, "op"))) {
            case "hello" -> answer(readExample("hello-reply.json"), message);
            case "list_apps" -> answer(message.has("cursor") ? last : first, message);
            default -> null;
        };
        var apps = connect().apps();
        assertTrue(client.detailed());

        var hello = helper.received("hello").getFirst();
        var helloExample = example("hello-request.json");
        assertEquals(helloExample.keySet(), hello.keySet());
        for (String same : List.of("protocol", "op", "major", "minor", "capabilities", "requires"))
            assertEquals(helloExample.get(same), hello.get(same), same);
        var requests = helper.received("list_apps");
        assertEquals(2, requests.size());
        var firstExample = example("list-apps-request-first.json");
        var nextExample = example("list-apps-request-next.json");
        assertEquals(firstExample.keySet(), requests.get(0).keySet());
        assertEquals(nextExample.keySet(), requests.get(1).keySet());
        assertEquals(first.get("next"), requests.get(1).get("cursor"));
        assertEquals(nextExample.get("cursor"), requests.get(1).get("cursor"));
        for (var request : requests) {
            assertEquals(firstExample.get("protocol"), request.get("protocol"));
            assertEquals(firstExample.get("op"), request.get("op"));
        }

        assertEquals(List.of("browser", "com-discordapp-discord", "lunarclient", "notepad", "org-kde-dolphin",
                "org-kde-okular", "steam", "terminal"), apps.stream().map(ShellClient.App::id).toList());
        assertEquals(List.of("image", "flatpak-user", "user", "image", "system", "flatpak-system", "system", "image"),
                apps.stream().map(app -> app.system().source()).toList());
        assertEquals(new ShellClient.App("browser", "Chrome", true, null, new SystemInfo("image",
                "/run/user/1000/aresos/icons/browser.png", List.of("Network", "WebBrowser"), "Web Browser",
                List.of("internet", "www", "web"), "google-chrome.desktop", null, null)), apps.getFirst());
        assertEquals(new ShellClient.App("steam", "Steam", true, null, new SystemInfo("system",
                "/run/user/1000/aresos/icons/steam.png", List.of("Network", "FileTransfer", "Game"), "Game Store",
                null, "steam.desktop", "bazzite-steam", false)), apps.get(6));
        // The full entry is the first page's Discord, and the minimal one says nothing beyond 1.0.
        assertEquals(example("entry-full.json"), first.getAsJsonArray("apps").get(1));
        assertEquals(Set.of("id", "name", "available", "reason"), example("entry-minimal.json").keySet());

        helper.raw(new Gson().toJson(example("apps-changed-event.json")));
        FakeHelper.await(() -> lists.size() == 2, "the list after the example apps_changed");
        assertEquals(4, helper.received("list_apps").size());
    }

    private static JsonObject readExample(String name) {
        try { return example(name); }
        catch (IOException error) { throw new IllegalStateException(error); }
    }
}
