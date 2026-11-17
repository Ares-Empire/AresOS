package dev.aresos.shell;

import com.google.gson.*;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.StringReader;
import java.net.StandardProtocolFamily;
import java.net.UnixDomainSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Package 46: the mod's end of the guardian's lifecycle channel (docs/design/OS-BASE.md B1, the {@code save_world}
 * row). The supervisor asks the desktop world to be saved before a backup, a shutdown or an update; the mod saves as
 * {@code save-all flush} does, without a pause, a screen or leaving the world, and answers.
 *
 * <p>It is a direct connection to the supervisor's {@code desktop.sock}, not an {@code aresos-shell} message, so a dead
 * app helper can't stop saving. It opens only when the supervisor set {@link #GATE} in the game's environment; an older
 * supervisor never sees it. One background thread connects, says {@code lifecycle_hello} and reads requests, and
 * reconnects with a backoff when the socket goes away and comes back, each time with a fresh hello, so the supervisor
 * checks the peer again. It only logs; nothing reaches the chat.
 *
 * <p>Joining: a request joins a save that has not yet started on the server thread. One that arrives after a save
 * began gets one follow-up save, which every later request joins. So at most one save runs and one waits, and "saved"
 * always covers everything up to the request. The mod never aborts a running save: the supervisor owns the deadline.
 */
public final class LifecycleClient implements AutoCloseable {
    /** The supervisor (package 25) sets it to 1 in the game's environment; without it the mod never connects. */
    public static final String GATE = "ARESOS_DESKTOP_LIFECYCLE";
    public static final int MAJOR = 1;
    public static final int MINOR = 0;
    public static final int MAX_MESSAGE = 64 * 1024;
    static final List<String> CAPABILITIES = List.of("save_world");
    /** Every reason a refused save may give. Anything else the game says is answered as {@code error}. */
    public static final Set<String> REASONS = Set.of("no_world", "not_desktop_world", "server_stopping", "error");
    private static final Gson JSON = new Gson();
    private static final System.Logger LOG = System.getLogger("aresos");

    /** What one save came to: saved, with its own duration and the world's identity, or refused with a reason. */
    public record Saved(String reason, long ms, String world) {
        public static Saved done(long ms, String world) { return new Saved(null, ms, Objects.requireNonNull(world)); }
        public static Saved refused(String reason) { return new Saved(Objects.requireNonNull(reason), 0, null); }
        public boolean ok() { return reason == null; }
    }

    /** The game as this channel sees it: it saves the open world when asked. */
    public interface Game {
        /** A temporary refusal, checked before joining a batch and again before writing its answer. */
        default String refusal() { return null; }

        /**
         * Asks for one save of the open world, the equivalent of {@code save-all flush}, and returns at once. Runs
         * {@code starting} on the server thread right before the save itself begins: a request that arrives after it
         * gets a save of its own. The stage completes with the answer: {@link Saved#done} once the chunks are on disk,
         * or {@link Saved#refused} with one of {@link #REASONS}.
         */
        CompletionStage<Saved> save(Runnable starting);
    }

    /** The reconnect backoff: the first wait, doubled after each failed try up to the longest. */
    public record Settings(Duration firstRetry, Duration maxRetry) {
        public static final Settings DEFAULT = new Settings(Duration.ofMillis(500), Duration.ofSeconds(10));
    }

    /** One save asked of the game, and every request that joined it. */
    private static final class Pending {
        final CompletableFuture<Saved> answer = new CompletableFuture<>();
    }

    private final Path socket;
    private final String instance;
    private final String nonce;
    private final Game game;
    private final Settings settings;
    // Answers are written on their own thread: the game completes saves on the server thread, which must never wait
    // for the supervisor's socket.
    private final ExecutorService writer = Executors.newSingleThreadExecutor(
            task -> Thread.ofPlatform().daemon().name("aresos-lifecycle-writer").unstarted(task));
    private final Object saves = new Object();
    // Guarded by saves: the save that has not yet started on the server thread, which new requests join.
    private Pending waiting;
    private final AtomicInteger handled = new AtomicInteger();
    private volatile Connection connection;
    private volatile boolean closed;
    private String logged;
    private Thread loop;

    public LifecycleClient(Path socket, String instance, String nonce, Game game, Settings settings) {
        this.socket = Objects.requireNonNull(socket);
        this.instance = Objects.requireNonNull(instance);
        this.nonce = Objects.requireNonNull(nonce);
        this.game = Objects.requireNonNull(game);
        this.settings = Objects.requireNonNull(settings);
    }

    /**
     * The lifecycle channel this game's environment asks for, or null: without {@code ARESOS_DESKTOP_LIFECYCLE=1} the
     * mod never connects. The socket is {@code $XDG_RUNTIME_DIR/aresos/desktop.sock}; instance and nonce are the
     * helper hello's ({@code ARESOS_DESKTOP_INSTANCE}, {@code ARESOS_LAUNCH_NONCE}).
     */
    public static LifecycleClient fromEnvironment(Map<String, String> environment, Game game, Settings settings) {
        if (!"1".equals(environment.get(GATE))) return null;
        String runtime = environment.get("XDG_RUNTIME_DIR");
        String instance = environment.get("ARESOS_DESKTOP_INSTANCE"), nonce = environment.get("ARESOS_LAUNCH_NONCE");
        String problem = blank(runtime) ? "XDG_RUNTIME_DIR is not set"
                : blank(instance) || blank(nonce) ? "this game was not started by the AresOS session (no launch nonce)" : null;
        if (problem != null) {
            LOG.log(System.Logger.Level.WARNING, "AresOS lifecycle channel: not opened, " + problem);
            return null;
        }
        return new LifecycleClient(Path.of(runtime, "aresos", "desktop.sock"), instance, nonce, game, settings);
    }

    private static boolean blank(String value) { return value == null || value.isBlank(); }

    public synchronized void start() {
        if (loop != null || closed) return;
        loop = Thread.ofPlatform().daemon().name("aresos-lifecycle").start(this::run);
    }

    /** True while a connection to the supervisor is open. */
    public boolean connected() { return connection != null; }

    /** Requests read so far; tests wait on it to know a request was taken in. */
    int handled() { return handled.get(); }

    @Override public void close() {
        closed = true;
        var current = connection;
        if (current != null) current.close();
        Thread thread;
        synchronized (this) { thread = loop; }
        if (thread != null) thread.interrupt();
        writer.shutdownNow();
    }

    // ------------------------------------------------------------ connection loop

    private void run() {
        long retry = settings.firstRetry().toMillis();
        while (!closed) {
            long opened = System.nanoTime();
            boolean reached = false;
            try {
                reached = session();
                if (closed) return;
                report("lost the connection to the supervisor", true);
            } catch (IOException | RuntimeException error) {
                if (closed) return;
                report("unavailable (" + (error.getMessage() == null ? error.toString() : error.getMessage()) + ")", true);
            }
            // A connection that held starts the backoff over: the supervisor restarted. One that ends at once (a
            // supervisor that refuses this peer) keeps backing off.
            if (reached && System.nanoTime() - opened >= settings.maxRetry().toNanos()) retry = settings.firstRetry().toMillis();
            long wait = retry;
            retry = Math.min(retry * 2, settings.maxRetry().toMillis());
            try { Thread.sleep(wait); }
            catch (InterruptedException interrupted) { return; }
        }
    }

    /** One connection, from the hello until it ends. True when it was reached at all. */
    private boolean session() throws IOException {
        var current = new Connection(SocketChannel.open(StandardProtocolFamily.UNIX));
        connection = current;
        try {
            if (closed) return false;
            current.channel.connect(UnixDomainSocketAddress.of(socket));
            // Nothing else writes on a new connection before its hello: no request has been read on it yet.
            current.send(hello());
            report("connected to the supervisor", false);
            try {
                while (!closed) handle(current, current.read());
            } catch (IOException lost) {
                if (!closed) LOG.log(System.Logger.Level.DEBUG, "AresOS lifecycle connection ended: " + lost.getMessage());
            }
            return true;
        } finally {
            if (connection == current) connection = null;
            current.close();
        }
    }

    private JsonObject hello() {
        var hello = new JsonObject();
        hello.addProperty("op", "lifecycle_hello");
        hello.addProperty("major", MAJOR);
        hello.addProperty("minor", MINOR);
        hello.addProperty("instance", instance);
        hello.addProperty("nonce", nonce);
        hello.add("capabilities", JSON.toJsonTree(CAPABILITIES));
        return hello;
    }

    /** A log line when the channel's state changes, never one per retry. */
    private synchronized void report(String state, boolean problem) {
        if (state.equals(logged)) return;
        logged = state;
        LOG.log(problem ? System.Logger.Level.WARNING : System.Logger.Level.INFO, "AresOS lifecycle channel: " + state);
    }

    // ------------------------------------------------------------ requests

    /**
     * One line from the supervisor. Only {@code save_world} is a request; anything else (its replies to our own lines,
     * an operation this mod does not offer) is left alone, so the supervisor's own deadline decides.
     */
    private void handle(Connection current, JsonObject message) {
        String op = text(message, "op");
        if (!"save_world".equals(op)) {
            if (op != null) LOG.log(System.Logger.Level.DEBUG, "AresOS lifecycle channel: ignored op " + clip(op));
            return;
        }
        var id = message.get("id");
        if (!(id instanceof JsonPrimitive primitive) || !(primitive.isNumber() || primitive.isString())) {
            LOG.log(System.Logger.Level.WARNING, "AresOS lifecycle channel: ignored a save_world without an id");
            return;
        }
        // The reason says why the supervisor asks; the save is the same for each, so an unknown one still saves.
        String reason = String.valueOf(text(message, "reason"));
        String refusal = game.refusal();
        if (refusal != null) {
            handled.incrementAndGet();
            later(() -> answer(current, primitive, clip(reason), Saved.refused(refusal)));
            return;
        }
        Pending pending;
        boolean start = false;
        synchronized (saves) {
            pending = waiting;
            if (pending == null || pending.answer.isDone()) {
                pending = waiting = new Pending();
                start = true;
            }
        }
        if (start) start(pending);
        handled.incrementAndGet();
        pending.answer.thenAccept(saved -> later(() -> answer(current, primitive, clip(reason), saved)));
    }

    private void start(Pending pending) {
        CompletionStage<Saved> stage;
        try {
            stage = game.save(() -> began(pending));
        } catch (RuntimeException error) {
            LOG.log(System.Logger.Level.ERROR, "AresOS lifecycle channel: could not ask for a save", error);
            stage = CompletableFuture.completedFuture(Saved.refused("error"));
        }
        stage.whenComplete((saved, error) -> {
            // A save that ended without starting (refused) takes no more requests either.
            began(pending);
            if (error != null) LOG.log(System.Logger.Level.ERROR, "AresOS lifecycle channel: the save failed", error);
            pending.answer.complete(error != null || saved == null ? Saved.refused("error") : saved);
        });
    }

    /** The save left the waiting place: from now on a request gets a follow-up save. */
    private void began(Pending pending) {
        synchronized (saves) {
            if (waiting == pending) waiting = null;
        }
    }

    /** Writer only. An answer for a connection that ended is dropped: a new supervisor asks again. */
    private void answer(Connection current, JsonPrimitive id, String reason, Saved saved) {
        String refusal = game.refusal();
        if (refusal != null) saved = Saved.refused(refusal);
        var message = new JsonObject();
        message.addProperty("op", "world_saved");
        message.add("id", id);
        boolean ok = saved.ok();
        message.addProperty("ok", ok);
        if (ok) {
            message.addProperty("ms", saved.ms());
            message.add("world", ShellClient.worldObject(saved.world()));
        } else {
            message.addProperty("reason", REASONS.contains(saved.reason()) ? saved.reason() : "error");
        }
        LOG.log(System.Logger.Level.INFO, "AresOS lifecycle channel: save_world " + clip(id.getAsString()) + " (" + reason
                + ") " + (ok ? "saved in " + saved.ms() + " ms" : "refused: " + message.get("reason").getAsString()));
        try { current.send(message); }
        catch (IOException lost) { current.close(); }
    }

    private void later(Runnable task) {
        try { writer.execute(task); }
        catch (RejectedExecutionException closedAlready) { }
    }

    private static String clip(String text) {
        var clean = text.replaceAll("[^\\x20-\\x7e]", "?");
        return clean.length() <= 48 ? clean : clean.substring(0, 48);
    }

    private static String text(JsonObject object, String key) {
        var value = object.get(key);
        return value instanceof JsonPrimitive primitive && primitive.isString() ? primitive.getAsString() : null;
    }

    /** One socket connection: line framing, the size limit and a write lock. */
    private static final class Connection {
        final SocketChannel channel;
        private final ByteBuffer input = ByteBuffer.allocate(8192).flip();
        private final ByteArrayOutputStream line = new ByteArrayOutputStream();
        private final Object writeLock = new Object();

        Connection(SocketChannel channel) { this.channel = channel; }

        void send(JsonObject message) throws IOException {
            byte[] bytes = (JSON.toJson(message) + "\n").getBytes(StandardCharsets.UTF_8);
            synchronized (writeLock) {
                var buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) channel.write(buffer);
            }
        }

        /** Blocks for the next JSON object. Malformed lines are skipped; an oversized one ends the connection. */
        JsonObject read() throws IOException {
            while (true) {
                while (input.hasRemaining()) {
                    byte next = input.get();
                    if (next == '\n') {
                        var message = parse(line.toByteArray());
                        line.reset();
                        if (message != null) return message;
                        continue;
                    }
                    if (line.size() >= MAX_MESSAGE) throw new IOException("oversized message from the supervisor");
                    line.write(next);
                }
                input.clear();
                int read = channel.read(input);
                input.flip();
                if (read < 0) throw new IOException("the supervisor closed the connection");
            }
        }

        private static JsonObject parse(byte[] bytes) {
            try {
                var text = StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();
                var reader = new JsonReader(new StringReader(text));
                reader.setStrictness(Strictness.STRICT);
                var value = JsonParser.parseReader(reader);
                if (reader.peek() != JsonToken.END_DOCUMENT || !(value instanceof JsonObject object)) return null;
                return object;
            } catch (RuntimeException | IOException malformed) {
                LOG.log(System.Logger.Level.WARNING, "AresOS lifecycle channel: ignored a malformed message");
                return null;
            }
        }

        void close() {
            try { channel.close(); }
            catch (IOException ignored) { }
        }
    }
}
