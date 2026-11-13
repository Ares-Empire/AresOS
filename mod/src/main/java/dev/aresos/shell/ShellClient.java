package dev.aresos.shell;

import com.google.gson.*;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import dev.aresos.config.SystemInfo;
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
 * The mod side of aresos-shell (docs/design/OS-BASE.md Appendix B1, and docs/design/HUB.md 3.8 for 1.1): a client
 * of the AresOS app helper on a private Unix socket. It only ever names app IDs; the helper owns every launch
 * definition, so the Linux mod never runs a command itself. One background thread connects, says hello, lists apps
 * and then reads replies and events, reconnecting with backoff when the helper is missing or restarts.
 *
 * The client offers minor 1 and works with a 1.0 helper as before. When the helper answers with minor 1, the list
 * comes in pages with what the system knows about each program, and an apps_changed event makes the client list
 * again. Listeners only ever get a complete list.
 */
public final class ShellClient implements AutoCloseable {
    public static final int MAJOR = 1;
    public static final int MINOR = 1;
    /** The client's own version. hello carries it; later messages carry the minor the helper agreed to. */
    public static final String PROTOCOL = protocol(MINOR);
    public static final int MAX_MESSAGE = 64 * 1024;
    /** A list the helper changes between two pages is started over this often; then the old list is kept. */
    public static final int LIST_RESTARTS = 3;
    /** Bounds of one list, far above the about 200 programs of a real system: a helper that pages forever is cut off. */
    public static final int MAX_PAGES = 64;
    public static final int MAX_APPS = 1024;
    /** Wayland app_id and X11 class of the desktop window, so the helper can hand focus back to it. */
    public static final String DESKTOP_APP_ID = "aresos-desktop";
    // The last three are 1.1's. The helper sends an event only to a client that offered its name, so apps_changed
    // must be offered; none of the three is required, which keeps a 1.0 helper compatible.
    static final List<String> CAPABILITIES = List.of("list_apps", "open_app", "app_state", "shell_focus",
            "world_ready", "heartbeat", "windows", "app_details", "apps_changed", "list_paging");
    static final List<String> REQUIRES = List.of("list_apps", "open_app");
    private static final Gson JSON = new Gson();
    private static final System.Logger LOG = System.getLogger("aresos");

    /** One listed program. {@code system} is null when the helper speaks 1.0, which says nothing more about it. */
    public record App(String id, String name, boolean available, String reason, SystemInfo system) {
        public App(String id, String name, boolean available, String reason) { this(id, name, available, reason, null); }
    }
    public record Focus(boolean foreground, String reason, String appId, boolean activated) { }
    public record Launch(String requestId, String launchId, String state) { }
    public enum State { STARTING, CONNECTED, UNAVAILABLE, INCOMPATIBLE, CLOSED }
    public record Status(State state, String detail) { }
    public record Settings(Duration replyTimeout, Duration openTimeout, Duration heartbeat, Duration firstRetry,
                           Duration maxRetry, Duration relistInterval) {
        /** The open timeout outlasts the helper's 30-second window wait, so a launch never hangs. */
        public static final Settings DEFAULT = new Settings(Duration.ofSeconds(5), Duration.ofSeconds(45),
                Duration.ofSeconds(5), Duration.ofMillis(500), Duration.ofSeconds(10));

        /** After apps_changed the client lists again at most once every two seconds (HUB.md 3.8). */
        public Settings(Duration replyTimeout, Duration openTimeout, Duration heartbeat, Duration firstRetry,
                        Duration maxRetry) {
            this(replyTimeout, openTimeout, heartbeat, firstRetry, maxRetry, Duration.ofSeconds(2));
        }
    }

    /** Callbacks run on the client's background thread. */
    public interface Listener {
        /** A complete list: after connecting and after every apps_changed. Never a part of one. */
        default void apps(List<App> apps) { }
        default void focus(Focus focus) { }
        default void status(Status status) { }
        /** Without window tracking an open already counted as done; the helper reported its failure afterwards. */
        default void launchFailed(String appId, String requestId, ShellException error) { }
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
    private final Map<String, PendingOpen> watching = new ConcurrentHashMap<>();
    // Writes can block when the helper stops reading, so they get their own thread; the watchdog never writes,
    // so it can always notice a stalled write and close the connection, which unblocks the writer.
    private final ExecutorService writer = Executors.newSingleThreadExecutor(
            task -> Thread.ofPlatform().daemon().name("aresos-shell-writer").unstarted(task));
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor(
            task -> Thread.ofPlatform().daemon().name("aresos-shell-watchdog").unstarted(task));
    private volatile Status status = new Status(State.STARTING, "connecting to the app helper");
    private volatile List<App> apps = List.of();
    private volatile boolean detailed;
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
    /** The last complete list; it is kept while the helper is away or its list will not hold still. */
    public List<App> apps() { return apps; }
    /** True when the last complete list said where each program came from (a 1.1 helper). */
    public boolean detailed() { return detailed; }

    static String protocol(int minor) { return "aresos-shell/" + MAJOR + "." + minor; }
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
        timer.scheduleAtFixedRate(this::watch, period, period, TimeUnit.MILLISECONDS);
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
            writer.execute(task);
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
        writer.shutdownNow();
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
            case "journal_full" -> "too many launches just now, try again shortly";
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
            var hello = request("h", "hello");
            hello.addProperty("major", MAJOR);
            hello.addProperty("minor", MINOR);
            hello.add("capabilities", JSON.toJsonTree(CAPABILITIES));
            hello.add("requires", JSON.toJsonTree(REQUIRES));
            hello.addProperty("instance", instance);
            hello.addProperty("nonce", nonce);
            var reply = timedCall(current, hello);
            if (!bool(reply, "ok")) {
                String code = text(reply, "error");
                throw new ShellException(code, "the app helper refused this desktop (" + clip(String.valueOf(code)) + ")");
            }
            var offered = new HashSet<String>();
            if (reply.get("capabilities") instanceof JsonArray array)
                for (var value : array) if (value.isJsonPrimitive()) offered.add(value.getAsString());
            if (number(reply, "major") != MAJOR || !offered.containsAll(REQUIRES))
                throw new ShellException("incompatible_version", "the app helper lacks " + protocol(0) + " list/open");
            // The reply names the lower minor of the two sides. A helper that claims more than ours is held to ours.
            current.minor = Math.clamp(number(reply, "minor"), 0, MINOR);
            windows = offered.contains("windows") && offered.contains("app_state");
            var listed = firstList(current);
            if (listed != null) keep(current, listed);
            connection = current;
            setStatus(new Status(State.CONNECTED, windows ? "tracking windows" : "without window tracking"));
            if (listed != null) announce(listed);
            // Without a complete list nothing is known yet; whoever waits must not take an empty list for one.
            else firstAttempt.completeExceptionally(new ShellException("list_incomplete",
                    "the app helper's app list did not hold still"));
            synchronized (current) { current.listing = false; }
            scheduleRefresh(current);
            // Requests the old connection may have carried: the helper answers a known ID without launching again.
            // The writer sends them, so this thread starts reading at once and can never block both directions.
            for (var open : opens.values()) later(() -> {
                if (open.future().isDone()) return;
                try { current.send(openRequest(open)); }
                catch (IOException lost) { current.close(); }
            });
            // Watched launches too: a failure the helper recorded while we were away comes back as their answer.
            for (var open : watching.values()) later(() -> {
                if (!watching.containsKey(open.id())) return;
                try { current.send(openRequest(open)); }
                catch (IOException lost) { current.close(); }
            });
            later(() -> sendWorld(current));
            try {
                while (!closed) dispatch(current, current.read());
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

    /** The protocol field is a placeholder here: {@link Connection#send} writes the connection's own version. */
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
            dispatch(current, reply);
        }
    }

    /** {@link #call} with the reply timeout: a helper that stops answering drops the connection. */
    private JsonObject timedCall(Connection current, JsonObject message) throws IOException {
        var watchdog = timer.schedule(current::expire, settings.replyTimeout().toMillis(), TimeUnit.MILLISECONDS);
        try { return call(current, message); }
        finally { watchdog.cancel(false); }
    }

    // ------------------------------------------------------------ the app list

    private JsonObject listRequest(Listing listing) {
        var message = request("l", "list_apps");
        if (listing.cursor() != null) message.addProperty("cursor", listing.cursor());
        return message;
    }

    /** The session's first list, page by page. Null when it did not hold still: the list from before is kept. */
    private List<App> firstList(Connection current) throws IOException {
        var listing = new Listing(current.minor >= 1);
        synchronized (current) { current.listStarted = System.nanoTime(); }
        while (true) {
            switch (listing.accept(timedCall(current, listRequest(listing)))) {
                case DONE -> { return listing.apps(); }
                case GIVE_UP -> {
                    LOG.log(System.Logger.Level.WARNING, "AresOS app helper: " + listing.problem() + "; app list kept as it was");
                    return null;
                }
                case NEXT -> { }
            }
        }
    }

    private void keep(Connection current, List<App> listed) {
        apps = listed;
        detailed = current.minor >= 1;
    }

    private void announce(List<App> listed) {
        for (var listener : listeners) {
            try { listener.apps(listed); }
            catch (RuntimeException error) { LOG.log(System.Logger.Level.ERROR, "Shell listener failed", error); }
        }
        firstAttempt.complete(listed);
    }

    /** The helper said its list or a picture changed. Only a helper that agreed to 1.1 may say so. */
    private void appsChanged(Connection current) {
        if (current.minor < 1) return;
        synchronized (current) { current.changed = true; }
        scheduleRefresh(current);
    }

    /**
     * Lists again if a change is waiting, no list is running and none is planned, and no sooner than the interval
     * after the last list began. Changes that arrive meanwhile share that one list.
     */
    private void scheduleRefresh(Connection current) {
        long wait;
        synchronized (current) {
            if (!current.changed || current.listing || current.scheduled) return;
            current.scheduled = true;
            wait = settings.relistInterval().toNanos() - (System.nanoTime() - current.listStarted);
        }
        try { timer.schedule(() -> startRefresh(current), Math.max(0, wait), TimeUnit.NANOSECONDS); }
        catch (RejectedExecutionException closedAlready) { }
    }

    private void startRefresh(Connection current) {
        synchronized (current) {
            current.scheduled = false;
            current.changed = false;
            current.listing = true;
            current.listStarted = System.nanoTime();
            current.refresh = new Listing(true);
        }
        requestPage(current);
    }

    /** Asks for the refresh's next page. The reply comes back through {@link #dispatch}; the watchdog never writes. */
    private void requestPage(Connection current) {
        var message = listRequest(current.refresh);
        String id = text(message, "id");
        synchronized (current) { current.refreshId = id; }
        try {
            // A page that never comes must not block every later refresh.
            timer.schedule(() -> { if (claim(current, id)) endRefresh(current, null, "a page of the app list never came"); },
                    settings.replyTimeout().toMillis(), TimeUnit.MILLISECONDS);
        } catch (RejectedExecutionException closedAlready) {
            return;
        }
        later(() -> {
            try { current.send(message); }
            catch (IOException lost) { current.close(); }
        });
    }

    /** True for exactly one caller per page request: its reply, or its timeout. */
    private static boolean claim(Connection current, String id) {
        synchronized (current) {
            if (!id.equals(current.refreshId)) return false;
            current.refreshId = null;
            return true;
        }
    }

    private void refreshPage(Connection current, JsonObject reply) {
        var listing = current.refresh;
        Listing.Step step;
        try { step = listing.accept(reply); }
        catch (ShellException refused) {
            endRefresh(current, null, refused.getMessage());
            return;
        }
        switch (step) {
            case NEXT -> requestPage(current);
            case DONE -> endRefresh(current, listing.apps(), null);
            case GIVE_UP -> endRefresh(current, null, listing.problem());
        }
    }

    private void endRefresh(Connection current, List<App> listed, String problem) {
        synchronized (current) {
            current.listing = false;
            current.refresh = null;
        }
        if (listed == null) LOG.log(System.Logger.Level.WARNING, "AresOS app helper: " + problem + "; app list kept as it was");
        else if (connection == current) {
            keep(current, listed);
            announce(listed);
        }
        scheduleRefresh(current);
    }

    /** Runs on the writer only, so reports on one connection never race; each change is reported once. */
    private void sendWorld(Connection current) {
        String id = world;
        if (Objects.equals(id, current.reportedWorld)) return;
        try {
            if (id == null) current.send(heartbeatMessage(false));
            else {
                var message = request("w", "world_ready");
                message.addProperty("instance", instance);
                message.addProperty("nonce", nonce);
                message.add("world", worldObject(id));
                current.send(message);
            }
            current.reportedWorld = id;
        } catch (IOException lost) { current.close(); }
    }

    /** The watchdog. It never writes, so a write blocked on a helper that stopped reading cannot stop it. */
    private void watch() {
        try {
            long now = System.nanoTime();
            for (var current : new Connection[] {connection, attempt}) {
                if (current != null && current.writing && now - current.writeStarted > settings.replyTimeout().toNanos()) {
                    LOG.log(System.Logger.Level.WARNING, "AresOS app helper stopped reading; reconnecting");
                    current.close();
                }
            }
            var current = connection;
            if (current == null) return;
            // A helper that stops answering (even heartbeats) is treated like one that went away.
            if (now - current.lastReceived > settings.heartbeat().toNanos() * 3 + settings.replyTimeout().toNanos()) {
                LOG.log(System.Logger.Level.WARNING, "AresOS app helper stopped answering; reconnecting");
                current.close();
                return;
            }
            later(() -> {
                try { current.send(heartbeatMessage(world != null)); }
                catch (IOException | RuntimeException lost) { current.close(); }
            });
        } catch (RuntimeException error) {
            LOG.log(System.Logger.Level.ERROR, "AresOS app helper watchdog failed", error);
        }
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

    private void dispatch(Connection current, JsonObject message) {
        if (message.has("event")) {
            switch (String.valueOf(text(message, "event"))) {
                case "apps_changed" -> appsChanged(current);
                case "app_state" -> {
                    String id = String.valueOf(text(message, "request_id"));
                    var open = opens.get(id);
                    if (open != null) update(open, message);
                    else if (watching.containsKey(id)) lateUpdate(id, message);
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
        String id = String.valueOf(text(message, "id"));
        if (claim(current, id)) {
            refreshPage(current, message);
            return;
        }
        var open = opens.get(id);
        if (open != null) update(open, message);
        else if (watching.containsKey(id)) lateUpdate(id, message);
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
        if (!opened) return;
        if ("starting".equals(state)) {
            // Counted as opened without a window to confirm it; a failure may still follow (systemd-run failing).
            watching.put(open.id(), open);
            try { timer.schedule(() -> watching.remove(open.id()), settings.openTimeout().toMillis(), TimeUnit.MILLISECONDS); }
            catch (RejectedExecutionException closedAlready) { watching.remove(open.id()); }
        }
        open.future().complete(new Launch(open.id(), text(message, "launch_id"), state));
    }

    private void lateUpdate(String id, JsonObject message) {
        String state = text(message, "state");
        if (!"failed".equals(state) && !"closed".equals(state)) return;
        var open = watching.remove(id);
        if (open == null || !"failed".equals(state)) return;
        String error = text(message, "error");
        var failure = new ShellException(String.valueOf(error), reason(error, text(message, "reason")));
        for (var listener : listeners) {
            try { listener.launchFailed(open.appId(), open.id(), failure); }
            catch (RuntimeException problem) { LOG.log(System.Logger.Level.ERROR, "Shell listener failed", problem); }
        }
    }

    /** One list_apps in progress, fed page by page: the session's first list and every later refresh. */
    private static final class Listing {
        enum Step { NEXT, DONE, GIVE_UP }

        private final boolean details;
        private final List<App> rows = new ArrayList<>();
        private final Set<String> seen = new HashSet<>();
        private String revision, cursor, problem;
        private int pages, restarts;

        /** @param details the helper agreed to 1.1: follow {@code next} and read what the system knows */
        Listing(boolean details) { this.details = details; }

        /** The cursor of the page to ask for; null asks for the first page. */
        String cursor() { return cursor; }
        String problem() { return problem; }
        List<App> apps() { return List.copyOf(rows); }

        /** Takes one reply. NEXT: ask for {@link #cursor}. DONE: {@link #apps} is the complete list. */
        Step accept(JsonObject reply) throws ShellException {
            if (!bool(reply, "ok") || !(reply.get("apps") instanceof JsonArray page))
                throw new ShellException(String.valueOf(text(reply, "error")), "the app helper could not list apps");
            String now = text(reply, "revision");
            if (pages == 0) revision = now;
            else if (!Objects.equals(revision, now)) {
                // The list changed between two pages, so what was collected mixes two lists. Start over.
                if (restarts++ == LIST_RESTARTS) return giveUp("its app list changed during every try");
                rows.clear();
                seen.clear();
                pages = 0;
                cursor = null;
                return Step.NEXT;
            }
            pages++;
            for (var row : page) {
                // Same rules as apps.json; a bad row is skipped rather than breaking the whole catalogue.
                var app = row instanceof JsonObject object ? entry(object, details) : null;
                if (app == null || !seen.add(app.id())) continue;
                if (rows.size() == MAX_APPS) return giveUp("its app list has more than " + MAX_APPS + " programs");
                rows.add(app);
            }
            var next = details ? reply.get("next") : null;
            if (next == null || next.isJsonNull()) return Step.DONE;
            String value = text(reply, "next");
            if (value == null || value.isEmpty() || value.length() > 64) return giveUp("it sent a cursor that is not one");
            if (pages == MAX_PAGES) return giveUp("its app list does not end");
            cursor = value;
            return Step.NEXT;
        }

        private Step giveUp(String why) {
            problem = why;
            return Step.GIVE_UP;
        }
    }

    private static App entry(JsonObject app, boolean details) {
        String id = text(app, "id"), name = text(app, "name");
        if (id == null || !id.matches("[a-z0-9_-]{1,64}") || name == null || name.isBlank()) return null;
        return new App(id, name.length() > 64 ? name.substring(0, 64) : name, bool(app, "available"),
                text(app, "reason"), details ? system(app) : null);
    }

    /**
     * The optional fields of a 1.1 entry (HUB.md 3.8). A field that is missing or breaks its rule is "not known";
     * in a list, a bad word is skipped and words past the sixteenth are ignored. Nothing here is ever run or opened
     * except the icon, which the icon pack reads under its own limits.
     */
    private static SystemInfo system(JsonObject app) {
        String source = text(app, "source"), icon = line(app, "icon", 4096), exec = line(app, "exec_name", 128);
        var terminal = app.get("terminal");
        return new SystemInfo(source != null && SystemInfo.SOURCES.contains(source) ? source : null,
                icon != null && icon.startsWith("/") ? icon : null,
                words(app.get("categories"), "[A-Za-z0-9-]{1,32}"), line(app, "generic_name", 64),
                words(app.get("keywords"), "[^\\p{Cntrl}]{1,32}"), line(app, "desktop_id", 128),
                exec != null && exec.indexOf('/') < 0 ? exec : null,
                terminal instanceof JsonPrimitive flag && flag.isBoolean() ? flag.getAsBoolean() : null);
    }

    /** A text of at most {@code limit} characters on one line, or null. */
    private static String line(JsonObject object, String key, int limit) {
        String value = text(object, key);
        return value == null || value.isBlank() || value.length() > limit
                || value.chars().anyMatch(Character::isISOControl) ? null : value;
    }

    private static List<String> words(JsonElement value, String rule) {
        if (!(value instanceof JsonArray array)) return null;
        var result = new ArrayList<String>();
        for (var element : array) {
            if (result.size() == 16) break;
            if (element instanceof JsonPrimitive word && word.isString() && word.getAsString().matches(rule)
                    && !word.getAsString().isBlank())
                result.add(word.getAsString());
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
        volatile boolean writing;
        volatile long writeStarted;
        volatile String reportedWorld;
        volatile boolean expired;
        /** Our own minor until the helper's hello reply, then the one both sides speak. */
        volatile int minor = MINOR;
        // The app list on this connection, guarded by the connection: a list is running (the first one starts with
        // the session), an apps_changed is waiting for a list, and that list is planned.
        boolean listing = true, changed, scheduled;
        long listStarted = System.nanoTime();
        String refreshId;
        volatile Listing refresh;

        Connection(SocketChannel channel) { this.channel = channel; }

        void send(JsonObject message) throws IOException {
            message.addProperty("protocol", protocol(minor));
            byte[] bytes = (JSON.toJson(message) + "\n").getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_MESSAGE) throw new IOException("outgoing message too large");
            synchronized (writeLock) {
                writeStarted = System.nanoTime();
                writing = true;
                try {
                    var buffer = ByteBuffer.wrap(bytes);
                    while (buffer.hasRemaining()) channel.write(buffer);
                } finally {
                    writing = false;
                }
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
