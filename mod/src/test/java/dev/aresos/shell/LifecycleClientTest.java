package dev.aresos.shell;

import com.google.gson.JsonObject;
import dev.aresos.shell.LifecycleClient.Saved;
import org.junit.jupiter.api.*;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;

/** Package 46: the lifecycle channel against a fake supervisor on a real Unix socket and a scripted game. */
class LifecycleClientTest {
    private Path folder;
    private FakeSupervisor supervisor;
    private ScriptedGame game;
    private LifecycleClient client;

    /** A game whose saves the test starts and finishes by hand, as the server thread would. */
    static final class ScriptedGame implements LifecycleClient.Game {
        record Call(Runnable starting, CompletableFuture<Saved> result) {
            /** The server thread takes the save: requests from now on get a follow-up. */
            void begin() { starting.run(); }
            void finish(Saved saved) { result.complete(saved); }
        }
        final BlockingQueue<Call> calls = new LinkedBlockingQueue<>();
        final List<Call> all = new CopyOnWriteArrayList<>();
        volatile java.util.function.Function<Runnable, CompletionStage<Saved>> answer;

        @Override public CompletionStage<Saved> save(Runnable starting) {
            var scripted = answer;
            if (scripted != null) return scripted.apply(starting);
            var call = new Call(starting, new CompletableFuture<>());
            all.add(call);
            calls.add(call);
            return call.result();
        }

        Call next() throws InterruptedException {
            var call = calls.poll(5, TimeUnit.SECONDS);
            assertNotNull(call, "The game was not asked for a save");
            return call;
        }
    }

    @BeforeEach void start() throws IOException {
        // Unix socket paths are short (about 100 bytes), so use a short folder name.
        folder = Files.createTempDirectory("al");
        supervisor = new FakeSupervisor(folder.resolve("desktop.sock"));
        game = new ScriptedGame();
    }

    @AfterEach void stop() throws IOException {
        if (client != null) client.close();
        supervisor.close();
        try (var files = Files.walk(folder)) {
            for (var path : files.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        }
    }

    private LifecycleClient connect() throws InterruptedException {
        client = supervisor.client(game);
        client.start();
        FakeHelper.await(() -> !supervisor.received("lifecycle_hello").isEmpty(), "lifecycle_hello");
        return client;
    }

    private void taken(int requests) throws InterruptedException {
        FakeHelper.await(() -> client.handled() >= requests, requests + " requests taken in");
    }

    private static Set<String> keys(JsonObject object) { return object.keySet(); }

    @Test void helloCarriesExactlyTheContractsFields() throws Exception {
        connect();
        var hello = supervisor.received.getFirst().message();
        assertEquals(Set.of("op", "major", "minor", "instance", "nonce", "capabilities"), keys(hello));
        assertEquals("lifecycle_hello", hello.get("op").getAsString());
        assertEquals(1, hello.get("major").getAsInt());
        assertEquals(0, hello.get("minor").getAsInt());
        assertEquals(FakeSupervisor.INSTANCE, hello.get("instance").getAsString());
        assertEquals(FakeSupervisor.NONCE, hello.get("nonce").getAsString());
        assertEquals(List.of("save_world"), hello.getAsJsonArray("capabilities").asList().stream()
                .map(value -> value.getAsString()).toList());
        assertEquals(1, supervisor.received.size(), "The mod said more than its hello: " + supervisor.received);
        assertTrue(client.connected());
    }

    @Test void theGateAloneOpensTheChannel() throws Exception {
        // The real place: $XDG_RUNTIME_DIR/aresos/desktop.sock.
        supervisor.close();
        Path runtime = Files.createDirectory(folder.resolve("r"));
        supervisor = new FakeSupervisor(Files.createDirectory(runtime.resolve("aresos")).resolve("desktop.sock"));
        var session = Map.of("XDG_RUNTIME_DIR", runtime.toString(), "ARESOS_DESKTOP_INSTANCE", FakeSupervisor.INSTANCE,
                "ARESOS_LAUNCH_NONCE", FakeSupervisor.NONCE);
        for (String gate : new String[] {null, "", "0", "true", "yes", " 1"}) {
            var environment = new HashMap<>(session);
            if (gate != null) environment.put(LifecycleClient.GATE, gate);
            assertNull(LifecycleClient.fromEnvironment(environment, game, FakeSupervisor.fast()), "Gate " + gate);
        }
        // The gate without what the hello needs opens nothing either.
        for (String missing : session.keySet()) {
            var environment = new HashMap<>(session);
            environment.put(LifecycleClient.GATE, "1");
            environment.remove(missing);
            assertNull(LifecycleClient.fromEnvironment(environment, game, FakeSupervisor.fast()), "Without " + missing);
        }
        Thread.sleep(300);
        assertEquals(0, supervisor.connections.get(), "Something connected without the gate");

        var environment = new HashMap<>(session);
        environment.put(LifecycleClient.GATE, "1");
        client = LifecycleClient.fromEnvironment(environment, game, FakeSupervisor.fast());
        assertNotNull(client);
        client.start();
        FakeHelper.await(() -> supervisor.received("lifecycle_hello").size() == 1, "lifecycle_hello");
        assertEquals(1, supervisor.connections.get());
    }

    @Test void aSaveIsAnsweredWithItsTimeAndTheWorldReadyIdentity() throws Exception {
        connect();
        supervisor.save(7, "backup");
        var call = game.next();
        call.begin();
        call.finish(Saved.done(123, "AresHub"));
        var answer = supervisor.answer(7, 5);
        assertEquals(Set.of("op", "id", "ok", "ms", "world"), keys(answer));
        assertEquals("world_saved", answer.get("op").getAsString());
        assertTrue(answer.get("id").getAsJsonPrimitive().isNumber(), "The id did not come back as the number it was");
        assertEquals(7, answer.get("id").getAsInt());
        assertTrue(answer.get("ok").getAsBoolean());
        assertEquals(123, answer.get("ms").getAsLong());
        // The same object world_ready and heartbeats carry.
        assertEquals(ShellClient.worldObject("AresHub"), answer.getAsJsonObject("world"));
        assertEquals("{\"id\":\"AresHub\",\"desktop\":true}", answer.get("world").toString());
    }

    @Test void eachRefusalIsAnsweredWithItsReason() throws Exception {
        connect();
        int id = 0;
        for (String reason : List.of("no_world", "not_desktop_world", "server_stopping", "error")) {
            supervisor.save(++id, "shutdown");
            var call = game.next();
            if (!reason.equals("no_world")) call.begin();
            call.finish(Saved.refused(reason));
            var answer = supervisor.answer(id, 5);
            assertEquals(Set.of("op", "id", "ok", "reason"), keys(answer), "For " + reason);
            assertEquals("world_saved", answer.get("op").getAsString());
            assertFalse(answer.get("ok").getAsBoolean());
            assertEquals(reason, answer.get("reason").getAsString());
        }
        // A game that fails, throws or names no known reason is answered as an error, never as saved.
        supervisor.save(++id, "update");
        game.next().result().completeExceptionally(new IllegalStateException("disk full"));
        assertEquals("error", supervisor.answer(id, 5).get("reason").getAsString());
        supervisor.save(++id, "update");
        game.next().finish(Saved.refused("tired"));
        assertEquals("error", supervisor.answer(id, 5).get("reason").getAsString());
        game.answer = starting -> { throw new IllegalStateException("no server thread"); };
        supervisor.save(++id, "manual");
        var thrown = supervisor.answer(id, 5);
        assertFalse(thrown.get("ok").getAsBoolean());
        assertEquals("error", thrown.get("reason").getAsString());
        // A refusal that comes at once (no world) is answered too, and the next request asks again.
        game.answer = starting -> CompletableFuture.completedFuture(Saved.refused("no_world"));
        supervisor.save(++id, "backup");
        assertEquals("no_world", supervisor.answer(id, 5).get("reason").getAsString());
        game.answer = null;
        supervisor.save(++id, "backup");
        var call = game.next();
        call.begin();
        call.finish(Saved.done(4, "AresHub"));
        assertTrue(supervisor.answer(id, 5).get("ok").getAsBoolean());
    }

    @Test void requestsJoinASaveUntilItStartsThenShareOneFollowUp() throws Exception {
        connect();
        // Two requests before the server thread takes the save: one save for both.
        supervisor.save(1, "backup");
        supervisor.save(2, "manual");
        taken(2);
        var first = game.next();
        assertTrue(game.calls.isEmpty(), "A request that came before the save started got a save of its own");

        // The save started: the next request gets a follow-up, which every later one joins.
        first.begin();
        supervisor.save(3, "shutdown");
        taken(3);
        var second = game.next();
        supervisor.save(4, "update");
        supervisor.save(5, "backup");
        taken(5);
        assertTrue(game.calls.isEmpty(), "More than one save waited");
        assertTrue(supervisor.received("world_saved").isEmpty(), "Answered before any save ended");

        first.finish(Saved.done(10, "AresHub"));
        for (int id : new int[] {1, 2}) assertEquals(10, supervisor.answer(id, 5).get("ms").getAsLong());
        Thread.sleep(100);
        assertEquals(2, supervisor.received("world_saved").size(), "The follow-up's requests were answered by the first save");

        second.begin();
        second.finish(Saved.done(20, "AresHub"));
        for (int id : new int[] {3, 4, 5}) assertEquals(20, supervisor.answer(id, 5).get("ms").getAsLong());
        // After both ended, a new request is a new save.
        supervisor.save(6, "backup");
        game.next().finish(Saved.refused("not_desktop_world"));
        assertEquals("not_desktop_world", supervisor.answer(6, 5).get("reason").getAsString());
        assertEquals(3, game.all.size());
        for (int id = 1; id <= 6; id++) assertEquals(1, supervisor.answers(id).size(), "Request " + id + " answered twice");
    }

    @Test void aRefusedSaveTakesNoLaterRequests() throws Exception {
        connect();
        supervisor.save(1, "backup");
        var refused = game.next();
        // Refused without starting (the world closed meanwhile): a later request must ask again, not inherit it.
        refused.finish(Saved.refused("server_stopping"));
        assertEquals("server_stopping", supervisor.answer(1, 5).get("reason").getAsString());
        supervisor.save(2, "backup");
        var next = game.next();
        next.begin();
        next.finish(Saved.done(3, "AresHub"));
        assertTrue(supervisor.answer(2, 5).get("ok").getAsBoolean());
    }

    @Test void joinedFollowUpAnswersForItsOwnFailureHistory() throws Exception {
        var failures = new dev.aresos.save.SaveFailures(unused -> { });
        connect();
        supervisor.save(1, "backup");
        var first = game.next();
        first.begin();
        var attempt = failures.begin();
        supervisor.save(2, "shutdown");
        supervisor.save(3, "update");
        taken(3);
        var followUp = game.next();
        failures.chunkFailure("overworld 1,2");
        first.finish(failures.finish(attempt, true) ? Saved.done(1, "AresHub") : Saved.refused("error"));
        assertEquals("error", supervisor.answer(1, 5).get("reason").getAsString());
        assertTrue(supervisor.answers(2).isEmpty());
        followUp.begin();
        var repair = failures.begin();
        assertTrue(repair.rewrite());
        followUp.finish(failures.finish(repair, true) ? Saved.done(2, "AresHub") : Saved.refused("error"));
        assertTrue(supervisor.answer(2, 5).get("ok").getAsBoolean());
        assertTrue(supervisor.answer(3, 5).get("ok").getAsBoolean());
    }

    @Test void linesThatAreNoRequestChangeNothing() throws Exception {
        // The real supervisor replies to every line it reads; those replies come back to the mod.
        supervisor.reply = new JsonObject();
        supervisor.reply.addProperty("ok", true);
        connect();
        supervisor.raw("not json");
        supervisor.raw("[1, 2]");
        supervisor.raw("{\"ok\": false, \"error\": \"unknown_operation\"}");
        supervisor.raw("{\"op\": \"prepare_stop\", \"id\": 1, \"reason\": \"shutdown\"}");
        supervisor.raw("{\"op\": \"save_world\", \"reason\": \"backup\"}");
        supervisor.raw("{\"op\": \"save_world\", \"id\": {\"n\": 1}, \"reason\": \"backup\"}");
        supervisor.raw("{\"op\": \"save_world\", \"id\": null}");
        supervisor.raw("{\"op\": \"save_world\", \"id\": 1} trailing");
        // A request with an id as text, and one without a reason, still save; the id comes back as it was.
        supervisor.save("b-9", "backup");
        supervisor.raw("{\"op\": \"save_world\", \"id\": 10}");
        taken(2);
        var call = game.next();
        assertTrue(game.calls.isEmpty(), "A line that is no valid request asked for a save");
        call.begin();
        call.finish(Saved.done(5, "AresHub"));
        var text = supervisor.answer("b-9", 5);
        assertTrue(text.get("id").getAsJsonPrimitive().isString());
        assertTrue(supervisor.answer(10, 5).get("ok").getAsBoolean());
        assertEquals(2, supervisor.received("world_saved").size(), "Answered a line that was no request");
        assertEquals(1, supervisor.connections.get(), "A line that was no request cost the connection");
        assertTrue(client.connected());
    }

    @Test void reconnectsWithAFreshHelloWhenTheSocketGoesAwayAndComesBack() throws Exception {
        connect();
        // The supervisor drops the connection: a new one, with a new hello.
        supervisor.drop();
        FakeHelper.await(() -> supervisor.received("lifecycle_hello").size() == 2, "a second hello");
        assertEquals(2, supervisor.connections.get());

        // The supervisor goes away (its socket file too) and comes back.
        supervisor.stop();
        FakeHelper.await(() -> !client.connected(), "the connection to end");
        Thread.sleep(500);
        supervisor.listen();
        FakeHelper.await(() -> supervisor.received("lifecycle_hello").size() == 3, "a hello after the supervisor came back");
        assertEquals(3, supervisor.connections.get());
        for (var line : supervisor.received) assertEquals("lifecycle_hello", line.message().get("op").getAsString());
        var hellos = supervisor.received.stream().map(FakeSupervisor.Line::connection).toList();
        assertEquals(List.of(1, 2, 3), hellos, "Each connection starts with its own hello");

        // Requests work on the new connection.
        supervisor.save(1, "backup");
        var call = game.next();
        call.begin();
        call.finish(Saved.done(8, "AresHub"));
        assertEquals(8, supervisor.answer(1, 5).get("ms").getAsLong());
    }

    @Test void anAnswerForAConnectionThatEndedIsNotSentOnTheNextOne() throws Exception {
        connect();
        supervisor.save(1, "shutdown");
        var call = game.next();
        call.begin();
        supervisor.drop();
        FakeHelper.await(() -> supervisor.received("lifecycle_hello").size() == 2, "a second hello");
        // The save is never aborted: it ends, but its answer belonged to the old connection.
        call.finish(Saved.done(9, "AresHub"));
        Thread.sleep(200);
        assertTrue(supervisor.received("world_saved").isEmpty(), "An old request was answered on a new connection");
    }

    @Test void anOversizedLineEndsTheConnectionAndTheModComesBack() throws Exception {
        connect();
        supervisor.raw("{\"op\": \"save_world\", \"id\": 1, \"pad\": \"" + "x".repeat(LifecycleClient.MAX_MESSAGE) + "\"}");
        FakeHelper.await(() -> supervisor.received("lifecycle_hello").size() == 2, "a hello after the oversized line");
        assertTrue(game.calls.isEmpty(), "An oversized line asked for a save");
    }

    @Test void closingStopsReconnecting() throws Exception {
        connect();
        client.close();
        FakeHelper.await(() -> !client.connected(), "the connection to close");
        Thread.sleep(400);
        assertEquals(1, supervisor.connections.get(), "A closed client connected again");
    }
}
