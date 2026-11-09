package dev.aresos.shell;

import com.google.gson.*;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.io.IOException;
import java.io.StringReader;
import java.net.StandardProtocolFamily;
import java.net.UnixDomainSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * The mod side of aresos-shell/1.0 (docs/design/OS-BASE.md Appendix B1): a client of the AresOS app helper on a
 * private Unix socket. It only ever names app IDs; the helper owns every launch definition, so the Linux mod never
 * runs a command itself. One background thread connects, says hello, lists apps and then reads replies and events,
 * reconnecting with backoff when the helper is missing or restarts.
 */
public final class ShellClient implements AutoCloseable {
    public static final String PROTOCOL = "aresos-shell/1.0";
    public static final int MAJOR = 1;
    public static final int MINOR = 0;
    public static final int MAX_MESSAGE = 64 * 1024;
    /** Wayland app_id and X11 class of the desktop window, so the helper can hand focus back to it. */
    public static final String DESKTOP_APP_ID = "aresos-desktop";
    static final List<String> CAPABILITIES = List.of("list_apps", "open_app", "app_state", "shell_focus",
            "world_ready", "heartbeat", "windows");
    static final List<String> REQUIRES = List.of("list_apps", "open_app");
    private static final Gson JSON = new Gson();
    private static final System.Logger LOG = System.getLogger("aresos");

    public record App(String id, String name, boolean available, String reason) { }
    public record Focus(boolean foreground, String reason, String appId, boolean activated) { }
    public record Launch(String requestId, String launchId, String state) { }
    public enum State { STARTING, CONNECTED, UNAVAILABLE, INCOMPATIBLE, CLOSED }
    public record Status(State state, String detail) { }
    public record Settings(Duration replyTimeout, Duration openTimeout, Duration heartbeat, Duration firstRetry,
                           Duration maxRetry) {
        /** The open timeout outlasts the helper's 30-second window wait, so a launch never hangs. */
        public static final Settings DEFAULT = new Settings(Duration.ofSeconds(5), Duration.ofSeconds(45),
                Duration.ofSeconds(5), Duration.ofMillis(500), Duration.ofSeconds(10));
    }

    /** Callbacks run on the client's background thread. */
    public interface Listener {
        default void apps(List<App> apps) { }
        default void focus(Focus focus) { }
        default void status(Status status) { }
    }

    /** A refusal carrying the helper's stable error code (B1), such as unknown_app, unavailable or no_window. */
    public static final class ShellException extends IOException {
        private final String code;

        public ShellException(String code, String message) {
            super(message);
            this.code = code;
        }

        public String code() { return code; }
    }

    private record PendingOpen(String id, String appId, CompletableFuture<Launch> future) { }

    private final Path socket;
    private final String instance;
    private final String nonce;
    private final String configProblem;
    private final Settings settings;
    private final String session;
    private final AtomicLong ids = new AtomicLong();
    private final List<Listener> listeners = new CopyOnWriteArrayList<>();
    private final Map<String, PendingOpen> opens = new ConcurrentHashMap<>();
    private final CompletableFuture<List<App>> firstAttempt = new CompletableFuture<>();
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor(
            task -> Thread.ofPlatform().daemon().name("aresos-shell-timer").unstarted(task));
    private volatile Status status = new Status(State.STARTING, "connecting to the app helper");
    private volatile List<App> apps = List.of();
    private volatile Connection connection;
    private volatile Connection attempt;
    private volatile boolean windows;
    private volatile String world;
    private volatile boolean closed;
    private Thread loop;

    public ShellClient(Path socket, String instance, String nonce, Settings settings) {
        this(socket, instance, nonce, settings, null);
    }

    private ShellClient(Path socket, String instance, String nonce, Settings settings, String configProblem) {
        this.socket = socket;
        this.instance = instance;
        this.nonce = nonce;
        this.settings = Objects.requireNonNull(settings);
        this.configProblem = configProblem;
        var random = new byte[4];
        new SecureRandom().nextBytes(random);
        // Request IDs must never repeat within a desktop instance's journal, even across game restarts.
        this.session = HexFormat.of().formatHex(random);
    }

    /** The supervisor (package 23) passes the socket, desktop instance and launch nonce in the environment. */
    public static ShellClient fromEnvironment(Map<String, String> environment, Settings settings) {
        String runtime = environment.get("XDG_RUNTIME_DIR"), override = environment.get("ARESOS_SHELL_SOCKET");
        String instance = environment.get("ARESOS_DESKTOP_INSTANCE"), nonce = environment.get("ARESOS_LAUNCH_NONCE");
        Path path = override != null && !override.isBlank() ? Path.of(override)
                : runtime != null && !runtime.isBlank() ? Path.of(runtime, "aresos", "shell.sock") : null;
        String problem = null;
        if (instance == null || instance.isBlank() || nonce == null || nonce.isBlank())
            problem = "this game was not started by the AresOS session (no launch nonce)";
        else if (path == null) problem = "XDG_RUNTIME_DIR is not set";
        return new ShellClient(path, instance, nonce, settings, problem);
    }

    public void addListener(Listener listener) { listeners.add(Objects.requireNonNull(listener)); }
    public Status status() { return status; }
    public List<App> apps() { return apps; }
    /** True when the helper confirms windows; otherwise a started process counts as opened, as on Windows. */
    public boolean tracksWindows() { return windows; }

    public synchronized void start() {
        if (loop != null || closed) return;
        if (configProblem != null) {
            setStatus(new Status(State.UNAVAILABLE, configProblem));
            firstAttempt.completeExceptionally(new ShellException("not_configured", configProblem));
            return;
        }
        loop = Thread.ofPlatform().daemon().name("aresos-shell").start(this::run);
        long period = settings.heartbeat().toMillis();
        timer.scheduleAtFixedRate(this::heartbeat, period, period, TimeUnit.MILLISECONDS);
    }

    /** Waits for the first connection attempt; later reconnects refresh apps through {@link Listener#apps}. */
    public List<App> awaitApps(Duration timeout) throws IOException {
        try {
            return firstAttempt.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (ExecutionException error) {
            if (error.getCause() instanceof IOException io) throw io;
            throw new IOException(error.getCause());
        } catch (TimeoutException error) {
            throw new ShellException("helper_unavailable", "no answer from the app helper");
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IOException(error);
        }
    }

    /** One deliberate action, one request ID. A reconnect resends it under the same ID, so it never launches twice. */
    public CompletableFuture<Launch> open(String appId) {
        var future = new CompletableFuture<Launch>();
        if (connection == null) {
            future.completeExceptionally(notConnected());
            return future;
        }
        var open = new PendingOpen("o-" + session + "-" + ids.incrementAndGet(), appId, future);
        opens.put(open.id(), open);
        future.orTimeout(settings.openTimeout().toMillis(), TimeUnit.MILLISECONDS)
                .whenComplete((result, error) -> opens.remove(open.id()));
        // Writes never run on the render thread: a stalled helper must not freeze the game.
        boolean queued = later(() -> {
            var current = connection;
            if (current == null || future.isDone()) return;
            try { current.send(openRequest(open)); }
            catch (IOException lost) { current.close(); }
        });
        if (!queued) future.completeExceptionally(notConnected());
        return future;
    }

    /** The desktop world is loaded with usable input (its save folder name), or null when it is not. */
    public void world(String id) {
        if (Objects.equals(id, world)) return;
        world = id;
        later(() -> {
            var current = connection;
            if (current != null) sendWorld(current);
        });
    }

    private boolean later(Runnable task) {
        try {
            timer.execute(task);
            return true;
        } catch (RejectedExecutionException closedAlready) {
            return false;
        }
    }

    @Override public void close() {
        closed = true;
        setStatus(new Status(State.CLOSED, "closed"));
        for (var current : new Connection[] {connection, attempt}) if (current != null) current.close();
        if (loop != null) loop.interrupt();
        timer.shutdownNow();
        var error = new ShellException("closed", "app helper connection closed");
        opens.values().forEach(open -> open.future().completeExceptionally(error));
        firstAttempt.completeExceptionally(error);
    }

    /** A short reason for the action bar, such as "not installed" or "app helper unavailable". */
    public static String describe(Throwable error) {
        var cause = error;
        while ((cause instanceof CompletionException || cause instanceof ExecutionException) && cause.getCause() != null)
            cause = cause.getCause();
        if (cause instanceof TimeoutException) return "no answer from the app helper";
        if (cause instanceof ShellException shell) return shell.getMessage();
        return "app helper unavailable";
    }

    static String reason(String code, String detail) {
        if (code == null) return "app helper error";
        return switch (code) {
            case "unknown_app" -> "not an app on AresOS";
            case "unavailable" -> "not_installed".equals(detail) ? "not installed"
                    : "unavailable" + (detail == null ? "" : " (" + clip(detail) + ")");
            case "launch_failed" -> "it failed to start";
            case "no_window" -> "no window appeared";
            case "launch_uncertain" -> "the app helper restarted while opening it";
            case "incompatible_version", "not_authorized" -> "app helper incompatible";
            default -> "app helper error (" + clip(code) + ")";
        };
    }

    private static String clip(String text) {
        var clean = text.replaceAll("[^\\x20-\\x7e]", "?");
        return clean.length() <= 48 ? clean : clean.substring(0, 48);
    }

    private ShellException notConnected() {
        var current = status;
        return current.state() == State.INCOMPATIBLE
                ? new ShellException("incompatible_version", "app helper incompatible")
                : new ShellException("helper_unavailable", "app helper unavailable");
    }

    private void setStatus(Status next) {
        var previous = status;
        status = next;
        if (previous.state() != next.state() || !previous.detail().equals(next.detail())) {
            LOG.log(next.state() == State.CONNECTED ? System.Logger.Level.INFO : System.Logger.Level.WARNING,
                    "AresOS app helper: " + next.state() + " (" + next.detail() + ")");
            for (var listener : listeners) {
                try { listener.status(next); }
                catch (RuntimeException error) { LOG.log(System.Logger.Level.ERROR, "Shell listener failed", error); }
            }
        }
    }

    // ------------------------------------------------------------ connection loop

    private void run() {
        long retry = settings.firstRetry().toMillis();
        while (!closed) {
            Status failure;
            ShellException first;
            try {
                session();
                retry = settings.firstRetry().toMillis();
                failure = new Status(State.UNAVAILABLE, "lost the connection to the app helper");
                first = null;
            } catch (ShellException refused) {
                failure = new Status(State.INCOMPATIBLE, refused.getMessage());
                first = refused;
            } catch (IOException | RuntimeException error) {
                failure = new Status(State.UNAVAILABLE, error.getMessage() == null ? error.toString() : error.getMessage());
                first = new ShellException("helper_unavailable", "app helper unavailable: " + failure.detail());
            }
            if (closed) return;
            setStatus(failure);
            // Status first: whoever waits on the first attempt must see why it failed.
            if (first != null) firstAttempt.completeExceptionally(first);
            // An incompatible helper only changes with an image update, so retry it slowly.
            long wait = failure.state() == State.INCOMPATIBLE ? Math.max(30_000, settings.maxRetry().toMillis()) : retry;
            retry = Math.min(retry * 2, settings.maxRetry().toMillis());
            try { Thread.sleep(wait); }
            catch (InterruptedException interrupted) { return; }
        }
    }

    private void session() throws IOException {
        var current = new Connection(SocketChannel.open(StandardProtocolFamily.UNIX));
        attempt = current;
        try {
            current.channel.connect(UnixDomainSocketAddress.of(socket));
            var watchdog = timer.schedule(current::expire, settings.replyTimeout().toMillis(), TimeUnit.MILLISECONDS);
            List<App> listed;
            try {
                var hello = request("h", "hello");
                hello.addProperty("major", MAJOR);
                hello.addProperty("minor", MINOR);
                hello.add("capabilities", JSON.toJsonTree(CAPABILITIES));
                hello.add("requires", JSON.toJsonTree(REQUIRES));
                hello.addProperty("instance", instance);
                hello.addProperty("nonce", nonce);
                var reply = call(current, hello);
                if (!bool(reply, "ok")) {
                    String code = text(reply, "error");
                    throw new ShellException(code, "the app helper refused this desktop (" + clip(String.valueOf(code)) + ")");
                }
                var offered = new HashSet<String>();
                if (reply.get("capabilities") instanceof JsonArray array)
                    for (var value : array) if (value.isJsonPrimitive()) offered.add(value.getAsString());
                if (number(reply, "major") != MAJOR || !offered.containsAll(REQUIRES))
                    throw new ShellException("incompatible_version", "the app helper lacks " + PROTOCOL + " list/open");
                windows = offered.contains("windows") && offered.contains("app_state");
                listed = parseApps(call(current, request("l", "list_apps")));
            } finally {
                watchdog.cancel(false);
            }
            apps = listed;
            connection = current;
            setStatus(new Status(State.CONNECTED, windows ? "tracking windows" : "without window tracking"));
            for (var listener : listeners) {
                try { listener.apps(listed); }
                catch (RuntimeException error) { LOG.log(System.Logger.Level.ERROR, "Shell listener failed", error); }
            }
            firstAttempt.complete(listed);
            // Requests the old connection may have carried: the helper answers a known ID without launching again.
            for (var open : opens.values()) current.send(openRequest(open));
            sendWorld(current);
            try {
                while (!closed) dispatch(current.read());
            } catch (IOException lost) {
                if (!closed) LOG.log(System.Logger.Level.WARNING, "AresOS app helper connection lost: " + lost.getMessage());
            }
        } catch (IOException error) {
            if (current.expired) throw new IOException("no answer from the app helper");
            throw error;
        } finally {
            if (connection == current) connection = null;
            if (attempt == current) attempt = null;
            current.close();
        }
    }

    private JsonObject request(String prefix, String operation) {
        var message = new JsonObject();
        message.addProperty("protocol", PROTOCOL);
        message.addProperty("id", prefix + "-" + session + "-" + ids.incrementAndGet());
        message.addProperty("op", operation);
        return message;
    }

    private JsonObject openRequest(PendingOpen open) {
        var message = new JsonObject();
        message.addProperty("protocol", PROTOCOL);
        message.addProperty("id", open.id());
        message.addProperty("op", "open_app");
        message.addProperty("app_id", open.appId());
        return message;
    }

    /** Sends a request and reads until its reply; anything else that arrives meanwhile is dispatched normally. */
    private JsonObject call(Connection current, JsonObject message) throws IOException {
        String id = text(message, "id");
        current.send(message);
        while (true) {
            var reply = current.read();
            if (id.equals(text(reply, "id")) && reply.has("ok") && !reply.has("event")) return reply;
            dispatch(reply);
        }
    }

    private void sendWorld(Connection current) {
        String id = world;
        try {
            if (id == null) current.send(heartbeatMessage(false));
            else {
                var message = request("w", "world_ready");
                message.addProperty("instance", instance);
                message.addProperty("nonce", nonce);
                message.add("world", worldObject(id));
                current.send(message);
            }
        } catch (IOException lost) { current.close(); }
    }

    private void heartbeat() {
        var current = connection;
        if (current == null) return;
        // A helper that stops answering (even heartbeats) is treated like one that went away.
        if (System.nanoTime() - current.lastReceived > settings.heartbeat().toNanos() * 3 + settings.replyTimeout().toNanos()) {
            LOG.log(System.Logger.Level.WARNING, "AresOS app helper stopped answering; reconnecting");
            current.close();
            return;
        }
        try { current.send(heartbeatMessage(world != null)); }
        catch (IOException | RuntimeException lost) { current.close(); }
    }

    private JsonObject heartbeatMessage(boolean ready) {
        var message = request("b", "heartbeat");
        message.addProperty("instance", instance);
        message.addProperty("nonce", nonce);
        message.addProperty("ready", ready);
        String id = world;
        if (ready && id != null) message.add("world", worldObject(id));
        return message;
    }

    private static JsonObject worldObject(String id) {
        var object = new JsonObject();
        object.addProperty("id", id);
        object.addProperty("desktop", true);
        return object;
    }

    private void dispatch(JsonObject message) {
        if (message.has("event")) {
            switch (String.valueOf(text(message, "event"))) {
                case "app_state" -> {
                    var open = opens.get(String.valueOf(text(message, "request_id")));
                    if (open != null) update(open, message);
                }
                case "shell_focus" -> {
                    var focus = new Focus("foreground".equals(text(message, "focus")), text(message, "reason"),
                            text(message, "app_id"), bool(message, "activated"));
                    for (var listener : listeners) {
                        try { listener.focus(focus); }
                        catch (RuntimeException error) { LOG.log(System.Logger.Level.ERROR, "Shell listener failed", error); }
                    }
                }
                default -> { }
            }
            return;
        }
        var open = opens.get(String.valueOf(text(message, "id")));
        if (open != null) update(open, message);
    }

    private void update(PendingOpen open, JsonObject message) {
        String state = text(message, "state"), error = text(message, "error");
        if (state == null || "failed".equals(state)) {
            open.future().completeExceptionally(new ShellException(String.valueOf(error), reason(error, text(message, "reason"))));
            return;
        }
        boolean opened = switch (state) {
            case "focused", "background", "closed" -> true;
            case "starting" -> !windows;
            default -> false;
        };
        if (opened) open.future().complete(new Launch(open.id(), text(message, "launch_id"), state));
    }

    private static List<App> parseApps(JsonObject reply) throws IOException {
        if (!bool(reply, "ok") || !(reply.get("apps") instanceof JsonArray rows))
            throw new ShellException(String.valueOf(text(reply, "error")), "the app helper could not list apps");
        var result = new ArrayList<App>();
        var seen = new HashSet<String>();
        for (var row : rows) {
            if (!(row instanceof JsonObject app)) continue;
            String id = text(app, "id"), name = text(app, "name");
            // Same rules as apps.json; a bad row is skipped rather than breaking the whole catalogue.
            if (id == null || !id.matches("[a-z0-9_-]{1,64}") || name == null || name.isBlank() || !seen.add(id)) continue;
            result.add(new App(id, name.length() > 64 ? name.substring(0, 64) : name, bool(app, "available"),
                    text(app, "reason")));
        }
        return List.copyOf(result);
    }

    private static String text(JsonObject object, String key) {
        var value = object.get(key);
        return value instanceof JsonPrimitive primitive && primitive.isString() ? primitive.getAsString() : null;
    }

    private static boolean bool(JsonObject object, String key) {
        var value = object.get(key);
        return value instanceof JsonPrimitive primitive && primitive.isBoolean() && primitive.getAsBoolean();
    }

    private static int number(JsonObject object, String key) {
        var value = object.get(key);
        return value instanceof JsonPrimitive primitive && primitive.isNumber() ? primitive.getAsInt() : -1;
    }

    /** One socket connection: line framing, the size limit and a write lock. */
    private static final class Connection {
        final SocketChannel channel;
        private final ByteBuffer input = ByteBuffer.allocate(8192).flip();
        private final Object writeLock = new Object();
        private byte[] line = new byte[1024];
        private int length;
        volatile long lastReceived = System.nanoTime();
        volatile boolean expired;

        Connection(SocketChannel channel) { this.channel = channel; }

        void send(JsonObject message) throws IOException {
            byte[] bytes = (JSON.toJson(message) + "\n").getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_MESSAGE) throw new IOException("outgoing message too large");
            synchronized (writeLock) {
                var buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) channel.write(buffer);
            }
        }

        /** Blocks for the next well-formed message. Malformed lines are skipped; an oversized one drops the link. */
        JsonObject read() throws IOException {
            while (true) {
                while (input.hasRemaining()) {
                    byte next = input.get();
                    if (next == '\n') {
                        lastReceived = System.nanoTime();
                        var message = parse(ByteBuffer.wrap(line, 0, length));
                        length = 0;
                        if (message != null) return message;
                        continue;
                    }
                    if (length >= MAX_MESSAGE) throw new IOException("oversized message from the app helper");
                    if (length == line.length) line = Arrays.copyOf(line, Math.min(MAX_MESSAGE, line.length * 2));
                    line[length++] = next;
                }
                input.clear();
                int read = channel.read(input);
                input.flip();
                if (read < 0) throw new IOException("the app helper closed the connection");
            }
        }

        private static JsonObject parse(ByteBuffer bytes) {
            try {
                var reader = new JsonReader(new StringReader(StandardCharsets.UTF_8.newDecoder().decode(bytes).toString()));
                reader.setStrictness(Strictness.STRICT);
                var value = JsonParser.parseReader(reader);
                if (reader.peek() != JsonToken.END_DOCUMENT || !(value instanceof JsonObject object)) return null;
                String version = text(object, "protocol");
                if (version == null || !version.matches("aresos-shell/1\\.\\d{1,3}")) return null;
                return object;
            } catch (RuntimeException | IOException malformed) {
                LOG.log(System.Logger.Level.WARNING, "Ignored a malformed message from the AresOS app helper");
                return null;
            }
        }

        void expire() {
            expired = true;
            close();
        }

        void close() {
            try { channel.close(); }
            catch (IOException ignored) { }
        }
    }
}
