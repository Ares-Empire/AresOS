package dev.aresos.shell;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
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

/**
 * Package 46: a scripted session supervisor's lifecycle end on a real Unix socket ({@code desktop.sock}). It records
 * every line the mod sends, with the connection it came on, and sends {@code save_world} requests. Its socket can go
 * away and come back, as the real one does when the supervisor restarts.
 *
 * <p>It lives in the shared test folder because the unit tests and the client game tests both use it (build.gradle).
 */
public final class FakeSupervisor implements AutoCloseable {
    public static final String INSTANCE = FakeHelper.INSTANCE;
    public static final String NONCE = FakeHelper.NONCE;

    /** One line the mod sent, and the number of the connection it came on (1 for the first). */
    public record Line(int connection, JsonObject message) { }

    public final Path path;
    public final List<Line> received = new CopyOnWriteArrayList<>();
    public final AtomicInteger connections = new AtomicInteger();
    /** Replies the real supervisor gives to every line it reads; null sends nothing back. */
    public volatile JsonObject reply;
    private final Object writeLock = new Object();
    private volatile ServerSocketChannel server;
    private volatile SocketChannel current;

    public FakeSupervisor(Path path) throws IOException {
        this.path = path;
        listen();
    }

    public LifecycleClient client(LifecycleClient.Game game) {
        return new LifecycleClient(path, INSTANCE, NONCE, game, fast());
    }

    public static LifecycleClient.Settings fast() {
        return new LifecycleClient.Settings(java.time.Duration.ofMillis(50), java.time.Duration.ofMillis(200));
    }

    /** Binds the socket (again). */
    public synchronized void listen() throws IOException {
        var channel = ServerSocketChannel.open(StandardProtocolFamily.UNIX);
        channel.bind(UnixDomainSocketAddress.of(path));
        server = channel;
        Thread.ofPlatform().daemon().name("fake-supervisor").start(() -> accept(channel));
    }

    /** The supervisor goes away: its socket closes and its file is gone, and so is the open connection. */
    public synchronized void stop() throws IOException {
        server.close();
        Files.deleteIfExists(path);
        drop();
    }

    private void accept(ServerSocketChannel channel) {
        while (channel.isOpen()) {
            try {
                var peer = channel.accept();
                int number = connections.incrementAndGet();
                current = peer;
                Thread.ofPlatform().daemon().name("fake-supervisor-peer").start(() -> serve(peer, number));
            } catch (IOException closed) {
                return;
            }
        }
    }

    private void serve(SocketChannel channel, int number) {
        try (var reader = new BufferedReader(new InputStreamReader(Channels.newInputStream(channel), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                received.add(new Line(number, JsonParser.parseString(line).getAsJsonObject()));
                var answer = reply;
                if (answer != null) write(channel, answer + "\n");
            }
        } catch (IOException | RuntimeException closed) {
            // The mod went away or the test dropped the connection.
        }
    }

    /** Asks the mod on the open connection to save. */
    public void save(Object id, String reason) throws IOException {
        var message = new JsonObject();
        message.addProperty("op", "save_world");
        if (id instanceof Number number) message.addProperty("id", number);
        else message.addProperty("id", String.valueOf(id));
        message.addProperty("reason", reason);
        raw(message.toString());
    }

    public void raw(String line) throws IOException {
        write(current, line + "\n");
    }

    private void write(SocketChannel channel, String text) throws IOException {
        synchronized (writeLock) {
            var buffer = ByteBuffer.wrap(text.getBytes(StandardCharsets.UTF_8));
            while (buffer.hasRemaining()) channel.write(buffer);
        }
    }

    public void drop() throws IOException {
        var channel = current;
        if (channel != null) channel.close();
    }

    public List<JsonObject> received(String op) {
        return received.stream().map(Line::message).filter(message -> op.equals(FakeHelper.string(message, "op"))).toList();
    }

    /** The mod's world_saved for this request ID, waiting up to {@code seconds} for it. */
    public JsonObject answer(Object id, int seconds) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds);
        while (true) {
            for (var message : received("world_saved"))
                if (message.has("id") && message.get("id").getAsString().equals(String.valueOf(id))) return message;
            if (System.nanoTime() > deadline) throw new AssertionError("No world_saved for request " + id);
            Thread.sleep(5);
        }
    }

    public List<JsonObject> answers(Object id) {
        return received("world_saved").stream()
                .filter(message -> message.has("id") && message.get("id").getAsString().equals(String.valueOf(id))).toList();
    }

    @Override public void close() throws IOException {
        server.close();
        drop();
        Files.deleteIfExists(path);
    }
}
