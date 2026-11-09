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

/** A scripted aresos-shell/1.0 helper on a real Unix socket. It never starts anything; it counts launches. */
final class FakeHelper implements AutoCloseable {
    static final String INSTANCE = "desk-test";
    static final String NONCE = "nonce-for-tests-0123456789";
    final Path path;
    final List<JsonObject> received = new CopyOnWriteArrayList<>();
    final AtomicInteger launches = new AtomicInteger();
    final AtomicInteger connections = new AtomicInteger();
    final Map<String, JsonObject> journal = new ConcurrentHashMap<>();
    volatile List<String> capabilities = List.of("list_apps", "open_app", "app_state", "shell_focus", "world_ready",
            "heartbeat", "windows");
    volatile List<String[]> apps = List.of(new String[] {"terminal", "Terminal", null},
            new String[] {"notepad", "Notepad", null}, new String[] {"browser", "Chrome", "not_installed"});
    /** Overrides the reply to an operation; returning null sends nothing. */
    volatile Function<JsonObject, JsonObject> override = message -> null;
    /** What a new launch reports first. */
    volatile String launchState = "starting";
    volatile boolean dropOnFirstOpen;
    private final ServerSocketChannel server;
    private final Thread acceptor;
    private volatile SocketChannel current;
    private final Object writeLock = new Object();

    FakeHelper(Path folder) throws IOException {
        path = folder.resolve("s.sock");
        server = ServerSocketChannel.open(StandardProtocolFamily.UNIX);
        server.bind(UnixDomainSocketAddress.of(path));
        acceptor = Thread.ofPlatform().daemon().name("fake-helper").start(this::accept);
    }

    ShellClient client(ShellClient.Settings settings) {
        return new ShellClient(path, INSTANCE, NONCE, settings);
    }

    static ShellClient.Settings fast() {
        return new ShellClient.Settings(java.time.Duration.ofSeconds(2), java.time.Duration.ofSeconds(3),
                java.time.Duration.ofMillis(200), java.time.Duration.ofMillis(50), java.time.Duration.ofMillis(200));
    }

    List<JsonObject> received(String op) {
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
            String line;
            while ((line = reader.readLine()) != null) {
                var message = JsonParser.parseString(line).getAsJsonObject();
                received.add(message);
                var reply = override.apply(message);
                if (reply == null) reply = standard(channel, message);
                if (reply != null) send(channel, reply);
            }
        } catch (IOException | RuntimeException closed) {
            // The client went away or the test dropped the connection.
        }
    }

    private JsonObject standard(SocketChannel channel, JsonObject message) throws IOException {
        String op = string(message, "op"), id = string(message, "id");
        var reply = new JsonObject();
        reply.addProperty("id", id);
        reply.addProperty("ok", true);
        switch (op) {
            case "hello" -> {
                reply.addProperty("major", 1);
                reply.addProperty("minor", 0);
                var offered = new JsonArray();
                capabilities.forEach(offered::add);
                reply.add("capabilities", offered);
            }
            case "list_apps" -> {
                reply.addProperty("revision", "fixture");
                var rows = new JsonArray();
                for (var app : apps) {
                    var row = new JsonObject();
                    row.addProperty("id", app[0]);
                    row.addProperty("name", app[1]);
                    row.addProperty("available", app[2] == null);
                    if (app[2] == null) row.add("reason", JsonNull.INSTANCE);
                    else row.addProperty("reason", app[2]);
                    rows.add(row);
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
                    if (apps.stream().noneMatch(row -> row[0].equals(app))) {
                        known.addProperty("state", "failed");
                        known.addProperty("error", "unknown_app");
                    } else if (apps.stream().anyMatch(row -> row[0].equals(app) && row[2] != null)) {
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
            default -> {
                if (!Set.of("heartbeat", "world_ready").contains(op)) {
                    reply.addProperty("ok", false);
                    reply.addProperty("error", "unknown_operation");
                }
            }
        }
        return reply;
    }

    void event(String event, Map<String, Object> fields) throws IOException {
        var message = new JsonObject();
        message.addProperty("id", "e-" + UUID.randomUUID());
        message.addProperty("event", event);
        fields.forEach((key, value) -> {
            if (value instanceof Boolean flag) message.addProperty(key, flag);
            else message.addProperty(key, String.valueOf(value));
        });
        send(current, message);
    }

    void raw(String line) throws IOException {
        synchronized (writeLock) {
            var buffer = ByteBuffer.wrap((line + "\n").getBytes(StandardCharsets.UTF_8));
            while (buffer.hasRemaining()) current.write(buffer);
        }
    }

    void drop() throws IOException {
        current.close();
    }

    private void send(SocketChannel channel, JsonObject message) throws IOException {
        if (!message.has("protocol")) {
            var stamped = new JsonObject();
            stamped.addProperty("protocol", "aresos-shell/1.0");
            message.entrySet().forEach(entry -> stamped.add(entry.getKey(), entry.getValue()));
            message = stamped;
        }
        synchronized (writeLock) {
            var buffer = ByteBuffer.wrap((message + "\n").getBytes(StandardCharsets.UTF_8));
            while (buffer.hasRemaining()) channel.write(buffer);
        }
    }

    static String string(JsonObject object, String key) {
        var value = object.get(key);
        return value == null || value.isJsonNull() ? null : value.getAsString();
    }

    static void await(java.util.function.BooleanSupplier condition, String what) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (!condition.getAsBoolean()) {
            if (System.nanoTime() > deadline) throw new AssertionError("Timed out waiting for " + what);
            Thread.sleep(10);
        }
    }

    @Override public void close() throws IOException {
        server.close();
        var channel = current;
        if (channel != null) channel.close();
        Files.deleteIfExists(path);
    }
}
