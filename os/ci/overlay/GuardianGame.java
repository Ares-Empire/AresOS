// Package 25, the check build's VM: a stand-in for Minecraft with the AresOS mod. A real JVM, started by the
// pinned Java through the real wrapper (aresos-desktop-java), that speaks the lifecycle channel as the mod's
// LifecycleClient does: only with the gate, a hello first, a new hello after a closed connection, and one
// world_saved for a save_world.
//
//   GuardianGame.java save <ms> [marker [port]]   answers each save after <ms>, and ends with 143 on SIGTERM, as the
//                                          real game does (reviews/25-guardian, step 6)
//   GuardianGame.java hang <ms> [marker [port]]   never answers and ignores SIGTERM
//
// It says what happens to it on its standard output, one line each, beginning GUARDIAN_GAME: never its nonce, its
// instance or its environment. The marker wakes the lid watcher. The optional virtio port tells the host when
// to photograph the screen, even when the serial console is busy or its journal follower is gone.
import java.io.IOException;
import java.io.OutputStream;
import java.net.StandardProtocolFamily;
import java.net.UnixDomainSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class GuardianGame {
    private static final Pattern ID = Pattern.compile("\"id\"\\s*:\\s*(\\d+)");

    private static void say(String text) {
        System.out.println("GUARDIAN_GAME " + text);
        System.out.flush();
    }

    private static void cue(OutputStream camera, String event) {
        try {
            camera.write((event + "\n").getBytes(StandardCharsets.US_ASCII));
        } catch (IOException error) {
            // The host fails a missing cue. The fixture still owes the supervisor its save response.
            say("camera_failed");
        }
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "save";
        long delay = args.length > 1 ? Long.parseLong(args[1]) : 5000;
        Path marker = args.length > 2 ? Path.of(args[2]) : null;
        String runtime = System.getenv("XDG_RUNTIME_DIR");
        String instance = System.getenv("ARESOS_DESKTOP_INSTANCE");
        String nonce = System.getenv("ARESOS_LAUNCH_NONCE");
        if (!"1".equals(System.getenv("ARESOS_DESKTOP_LIFECYCLE")) || runtime == null || instance == null
                || nonce == null) {
            say("no_gate");  // the wrapper gave this JVM no lifecycle gate or no launch identity
            System.exit(2);
        }
        if (mode.equals("hang")) {
            sun.misc.Signal.handle(new sun.misc.Signal("TERM"), signal -> say("sigterm_ignored"));
        } else {
            // SIGTERM runs the JVM's shutdown hooks and ends it with 143, as it ends Minecraft.
            Runtime.getRuntime().addShutdownHook(new Thread(() -> say("closing")));
        }
        say("started mode=" + mode);
        UnixDomainSocketAddress address = UnixDomainSocketAddress.of(Path.of(runtime, "aresos", "desktop.sock"));
        byte[] hello = ("{\"op\":\"lifecycle_hello\",\"major\":1,\"minor\":0,\"instance\":\"" + instance
                + "\",\"nonce\":\"" + nonce + "\",\"capabilities\":[\"save_world\"]}\n")
                .getBytes(StandardCharsets.UTF_8);
        // Open once while the guest is up. No device lookup during teardown.
        try (OutputStream camera = args.length > 3 ? Files.newOutputStream(Path.of(args[3]), StandardOpenOption.WRITE)
                                                   : OutputStream.nullOutputStream()) {
            cue(camera, "ready");
            while (true) {
                try (SocketChannel channel = SocketChannel.open(StandardProtocolFamily.UNIX)) {
                    channel.connect(address);
                    channel.write(ByteBuffer.wrap(hello));
                    say("hello_sent");
                    serve(channel, mode, delay, marker, camera);
                    say("connection_closed");
                } catch (IOException error) {
                    // No supervisor yet, or it closed the connection (a hello before it knew this JVM): try again.
                }
                Thread.sleep(500);
            }
        }
    }

    private static void serve(SocketChannel channel, String mode, long delay, Path marker, OutputStream camera) throws Exception {
        ByteBuffer buffer = ByteBuffer.allocate(65536);
        StringBuilder text = new StringBuilder();
        while (channel.read(buffer) >= 0) {
            buffer.flip();
            text.append(StandardCharsets.UTF_8.decode(buffer));
            buffer.clear();
            int end;
            while ((end = text.indexOf("\n")) >= 0) {
                String line = text.substring(0, end);
                text.delete(0, end + 1);
                Matcher id = ID.matcher(line);
                if (!line.contains("\"save_world\"") || !id.find()) {
                    continue;
                }
                say("save_asked id=" + id.group(1));
                if (marker != null) {
                    Files.writeString(marker, id.group(1) + "\n");
                }
                cue(camera, "saving");
                if (mode.equals("hang")) {
                    continue;
                }
                Thread.sleep(delay);
                String answer = "{\"op\":\"world_saved\",\"id\":" + id.group(1) + ",\"ok\":true,\"ms\":" + delay
                        + ",\"world\":{\"id\":\"AresHub\",\"desktop\":true}}\n";
                cue(camera, "answering");
                ByteBuffer reply = ByteBuffer.wrap(answer.getBytes(StandardCharsets.UTF_8));
                while (reply.hasRemaining()) {
                    channel.write(reply);
                }
                say("save_answered id=" + id.group(1));
            }
        }
    }
}
