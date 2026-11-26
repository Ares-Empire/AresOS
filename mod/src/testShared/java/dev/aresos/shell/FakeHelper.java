package dev.aresos.shell;

import com.google.gson.*;
import java.io.*;
import java.net.StandardProtocolFamily;
import java.net.UnixDomainSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.Channels;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;

/**
 * A scripted aresos-shell helper on a real Unix socket. It never starts anything; it counts launches. It speaks 1.0
 * by default. Minor 1 adds catalogue details, paging and apps_changed. Minor 2 accepts publish_home and
 * minor 3 can offer the app window state and activation capabilities.
 *
 * It lives in its own source folder because the unit tests and the client game tests both use it (build.gradle).
 */
public final class FakeHelper implements AutoCloseable {
    private static final Gson JSON = new Gson();
    public static final String INSTANCE = "desk-test";
    public static final String NONCE = "nonce-for-tests-0123456789";
    public final Path path;
    public final List<JsonObject> received = new CopyOnWriteArrayList<>();
    public final AtomicInteger launches = new AtomicInteger();
    public final AtomicInteger connections = new AtomicInteger();
    public final Map<String, JsonObject> journal = new ConcurrentHashMap<>();
    public volatile List<String> capabilities = List.of("list_apps", "open_app", "app_state", "shell_focus", "world_ready",
            "heartbeat", "windows");
    public static final List<String> DETAIL_CAPABILITIES = List.of("app_details", "apps_changed", "list_paging");
    /** The helper's own minor version. The reply to hello names the lower of this and the client's. */
    public volatile int minor;
    public volatile boolean offerHome = true;
    /** An optional error code for an otherwise valid publish. */
    public volatile String refuseHome;
    public volatile boolean dropOnFirstHomePart;
    public final List<String> invalidHome = new CopyOnWriteArrayList<>();
    public final List<PublishedHome> homes = new CopyOnWriteArrayList<>();
    public record PublishedHome(String revision, JsonObject palette, Map<String, JsonObject> apps) {
        public PublishedHome { apps = Map.copyOf(apps); }
    }
    /** What the helper lists, in this order. Entries may carry the 1.1 fields. */
    public volatile List<JsonObject> entries = List.of(entry("terminal", "Terminal", null),
            entry("notepad", "Notepad", null), entry("browser", "Chrome", "not_installed"));
    public volatile String revision = "fixture";
    /** Entries per page for a 1.1 client; 0 puts everything on one page. */
    public volatile int pageSize;
    /** Overrides the reply to an operation; returning null sends nothing. */
    public volatile Function<JsonObject, JsonObject> override = message -> null;
    /** What a new launch reports first. */
    public volatile String launchState = "starting";
    public volatile boolean dropOnFirstOpen;
    /** The first connection stops reading right after list_apps, like a hung helper. */
    public volatile boolean stallFirstConnection;
    private final CountDownLatch released = new CountDownLatch(1);
    private final ServerSocketChannel server;
    private final Thread acceptor;
    private volatile SocketChannel current;
    private final Object writeLock = new Object();
    /** The minor each connection agreed to in hello. */
    private final Map<SocketChannel, Integer> negotiated = new ConcurrentHashMap<>();

    /** A starter as 1.0 lists it: {@code reason} null means available. */
    public static JsonObject entry(String id, String name, String reason) {
        var row = new JsonObject();
        row.addProperty("id", id);
        row.addProperty("name", name);
        row.addProperty("available", reason == null);
        if (reason == null) row.add("reason", JsonNull.INSTANCE);
        else row.addProperty("reason", reason);
        return row;
    }

    /** A program as 1.1 lists it; more optional fields can be added to the result. */
    public static JsonObject entry(String id, String name, String reason, String source) {
        var row = entry(id, name, reason);
        row.addProperty("source", source);
        return row;
    }

    private JsonObject listed(String id) {
        return entries.stream().filter(row -> id != null && id.equals(string(row, "id"))).findFirst().orElse(null);
    }

    public FakeHelper(Path folder) throws IOException {
        path = folder.resolve("s.sock");
        server = ServerSocketChannel.open(StandardProtocolFamily.UNIX);
        server.bind(UnixDomainSocketAddress.of(path));
        acceptor = Thread.ofPlatform().daemon().name("fake-helper").start(this::accept);
    }

    public ShellClient client(ShellClient.Settings settings) {
        return new ShellClient(path, INSTANCE, NONCE, settings);
    }

    public static ShellClient.Settings fast() {
        return new ShellClient.Settings(java.time.Duration.ofSeconds(2), java.time.Duration.ofSeconds(3),
                java.time.Duration.ofMillis(200), java.time.Duration.ofMillis(50), java.time.Duration.ofMillis(200));
    }

    public List<JsonObject> received(String op) {
        return received.stream().filter(message -> op.equals(string(message, "op"))).toList();
    }

    private void accept() {
        while (server.isOpen()) {
            try {
                var channel = server.accept();
                connections.incrementAndGet();
                current = channel;
                Thread.ofPlatform().daemon().name("fake-helper-peer").start(() -> serve(channel));
            } catch (IOException closed) {
                return;
            }
        }
    }

    private void serve(SocketChannel channel) {
        try (var reader = new BufferedReader(new InputStreamReader(Channels.newInputStream(channel), StandardCharsets.UTF_8))) {
            FakeHome publishing = null;
            String line;
            while ((line = reader.readLine()) != null) {
                var message = JsonParser.parseString(line).getAsJsonObject();
                received.add(message);
                var reply = override.apply(message);
                if (reply == null && "publish_home".equals(string(message, "op"))) {
                    try {
                        if (negotiated.getOrDefault(channel, 0) < 2 || !offerHome)
                            throw new IllegalArgumentException("publish_home was not negotiated");
                        publishing = FakeHome.receive(publishing, message, line.getBytes(StandardCharsets.UTF_8).length + 1);
                        if (dropOnFirstHomePart && !message.get("last").getAsBoolean()) {
                            dropOnFirstHomePart = false;
                            channel.close();
                            return;
                        }
                        if (refuseHome != null) {
                            publishing = null;
                            reply = homeReply(message, refuseHome, "the test refused this home");
                        } else {
                            if (message.get("last").getAsBoolean()) {
                                homes.add(publishing.published());
                                publishing = null;
                            }
                            reply = homeReply(message, null, null);
                        }
                    } catch (IllegalArgumentException invalid) {
                        invalidHome.add(invalid.getMessage());
                        publishing = null;
                        reply = homeReply(message, "malformed", invalid.getMessage());
                    }
                } else if (reply == null) reply = standard(channel, message);
                if (reply != null) send(channel, reply);
                if (stallFirstConnection && "list_apps".equals(string(message, "op"))) {
                    stallFirstConnection = false;
                    released.await();
                    return;
                }
            }
        } catch (IOException | RuntimeException closed) {
            // The client went away or the test dropped the connection.
        } catch (InterruptedException stopped) {
            Thread.currentThread().interrupt();
        }
    }

    private static JsonObject homeReply(JsonObject request, String error, String message) {
        var reply = new JsonObject();
        reply.add("id", request.get("id"));
        reply.addProperty("ok", error == null);
        if (error != null) {
            reply.addProperty("error", error);
            reply.addProperty("message", message);
        }
        return reply;
    }

    private JsonObject standard(SocketChannel channel, JsonObject message) throws IOException {
        String op = string(message, "op"), id = string(message, "id");
        var reply = new JsonObject();
        reply.addProperty("id", id);
        reply.addProperty("ok", true);
        switch (op) {
            case "hello" -> {
                var asked = message.get("minor");
                int agreed = Math.min(minor, asked != null && asked.isJsonPrimitive() ? asked.getAsInt() : 0);
                negotiated.put(channel, agreed);
                reply.addProperty("major", 1);
                reply.addProperty("minor", agreed);
                var offered = new JsonArray();
                capabilities.forEach(capability -> {
                    if (!Set.of("apps_state", "activate_app").contains(capability)
                            || agreed >= 3 && message.getAsJsonArray("capabilities").contains(new JsonPrimitive(capability)))
                        offered.add(capability);
                });
                if (minor >= 1) DETAIL_CAPABILITIES.forEach(offered::add);
                if (agreed >= 2) {
                    offered.add("views");
                    if (offerHome) offered.add("home_state");
                    offered.add("apps_running");
                    // It plays a helper with window tracking: shell_focus and windows are offered too.
                    offered.add("shell_search");
                }
                reply.add("capabilities", offered);
            }
            case "list_apps" -> {
                reply.addProperty("revision", revision);
                var rows = new JsonArray();
                if (negotiated.getOrDefault(channel, 0) < 1) {
                    // A 1.0 client gets what it gets today: the starters with the four fields, in one reply.
                    for (var row : entries) {
                        String source = string(row, "source");
                        if (source == null || source.equals("image"))
                            rows.add(entry(string(row, "id"), string(row, "name"), string(row, "reason")));
                    }
                } else {
                    var all = entries;
                    String cursor = string(message, "cursor");
                    int from = cursor == null ? 0 : Integer.parseInt(cursor.substring(1));
                    int to = pageSize <= 0 ? all.size() : Math.min(all.size(), from + pageSize);
                    for (var row : all.subList(from, to)) rows.add(row);
                    if (to < all.size()) reply.addProperty("next", "p" + to);
                }
                reply.add("apps", rows);
            }
            case "open_app" -> {
                String app = string(message, "app_id");
                var known = journal.get(id);
                if (known == null) {
                    known = new JsonObject();
                    known.addProperty("request_id", id);
                    known.addProperty("app_id", app);
                    var row = listed(app);
                    if (row == null) {
                        known.addProperty("state", "failed");
                        known.addProperty("error", "unknown_app");
                    } else if (!row.get("available").getAsBoolean()) {
                        known.addProperty("state", "failed");
                        known.addProperty("error", "unavailable");
                        known.addProperty("reason", "not_installed");
                    } else {
                        launches.incrementAndGet();
                        known.addProperty("launch_id", "launch-" + launches.get());
                        known.addProperty("state", launchState);
                    }
                    journal.put(id, known);
                    if (dropOnFirstOpen) {
                        // The helper started the app, then the connection broke before it could answer.
                        dropOnFirstOpen = false;
                        channel.close();
                        return null;
                    }
                }
                for (var field : known.entrySet()) reply.add(field.getKey(), field.getValue());
                reply.addProperty("ok", !"failed".equals(string(known, "state")));
            }
            case "activate_app" -> {
                if (negotiated.getOrDefault(channel, 0) < 3 || !capabilities.contains(op)) {
                    reply.addProperty("ok", false);
                    reply.addProperty("error", "unknown_operation");
                } else {
                    reply.addProperty("state", "activated");
                }
            }
            default -> {
                if (!Set.of("heartbeat", "world_ready").contains(op)) {
                    reply.addProperty("ok", false);
                    reply.addProperty("error", "unknown_operation");
                }
            }
        }
        return reply;
    }

    public void event(String event, Map<String, Object> fields) throws IOException {
        var message = new JsonObject();
        message.addProperty("id", "e-" + UUID.randomUUID());
        message.addProperty("event", event);
        fields.forEach((key, value) -> message.add(key, JSON.toJsonTree(value)));
        send(current, message);
    }

    public void raw(String line) throws IOException {
        synchronized (writeLock) {
            var buffer = ByteBuffer.wrap((line + "\n").getBytes(StandardCharsets.UTF_8));
            while (buffer.hasRemaining()) current.write(buffer);
        }
    }

    public void drop() throws IOException {
        current.close();
    }

    private void send(SocketChannel channel, JsonObject message) throws IOException {
        if (!message.has("protocol")) {
            var stamped = new JsonObject();
            // Like the real helper: its own minor until hello, then the one both sides agreed to.
            stamped.addProperty("protocol", "aresos-shell/1." + negotiated.getOrDefault(channel, minor));
            message.entrySet().forEach(entry -> stamped.add(entry.getKey(), entry.getValue()));
            message = stamped;
        }
        synchronized (writeLock) {
            var buffer = ByteBuffer.wrap((message + "\n").getBytes(StandardCharsets.UTF_8));
            while (buffer.hasRemaining()) channel.write(buffer);
        }
    }

    public static String string(JsonObject object, String key) {
        var value = object.get(key);
        return value == null || value.isJsonNull() ? null : value.getAsString();
    }

    public static void await(java.util.function.BooleanSupplier condition, String what) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (!condition.getAsBoolean()) {
            if (System.nanoTime() > deadline) throw new AssertionError("Timed out waiting for " + what);
            Thread.sleep(10);
        }
    }

    @Override public void close() throws IOException {
        released.countDown();
        server.close();
        var channel = current;
        if (channel != null) channel.close();
        Files.deleteIfExists(path);
    }
}
