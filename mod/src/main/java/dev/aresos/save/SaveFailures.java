package dev.aresos.save;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/** A world's write history, including autosaves. IO callbacks and the server thread share this journal. */
public final class SaveFailures {
    public record Attempt(long revision, boolean rewrite) { }

    public static final class Write {
        private final String chunk;
        private boolean unloaded;

        private Write(String chunk) { this.chunk = chunk; }
    }

    private final Consumer<String> log;
    private final Set<Write> writes = new HashSet<>();
    private final Set<String> failedChunks = new HashSet<>();
    private final Set<CompletableFuture<Void>> pending = new HashSet<>();
    private long revision;
    private boolean rewrite;
    private String lost;

    public SaveFailures(Consumer<String> log) { this.log = log; }

    public synchronized void failure(String part) {
        revision++;
        rewrite = true;
        log.accept(part);
    }

    /** When retention cannot be proved, only reopening the world starts a new history. */
    public synchronized void lost(String part) {
        failure(part);
        lost = part;
    }

    public synchronized void chunkFailure(String chunk) {
        failedChunks.add(chunk);
        failure("chunk " + chunk);
        // A codec can report an incomplete tag and still complete the write future successfully.
        if (writes.stream().anyMatch(write -> write.chunk.equals(chunk) && write.unloaded))
            lost("failed chunk " + chunk + " left memory before serialization reported its failure");
    }

    public synchronized Write writing(String chunk) {
        var write = new Write(chunk);
        writes.add(write);
        return write;
    }

    public synchronized void written(Write write, boolean ok) {
        writes.remove(write);
        if (!ok) {
            chunkFailure(write.chunk);
            if (write.unloaded) lost("failed chunk " + write.chunk + " left memory before its write completed");
        }
    }

    /** Called at actual removal, including protochunks and a failure on the unload's own write. */
    public synchronized void unloaded(String chunk) {
        writes.stream().filter(write -> write.chunk.equals(chunk)).forEach(write -> write.unloaded = true);
        if (failedChunks.contains(chunk)) lost("failed chunk " + chunk + " left memory");
    }

    /** The barrier completes after accounting, even when vanilla discards a dependent failure callback. */
    public void watch(CompletableFuture<?> future, Consumer<Boolean> completion) {
        var barrier = new CompletableFuture<Void>();
        synchronized (this) { pending.add(barrier); }
        future.whenComplete((unused, error) -> {
            try { completion.accept(error == null); }
            finally {
                barrier.complete(null);
                synchronized (this) { pending.remove(barrier); }
            }
        });
    }

    public void awaitWrites() {
        while (true) {
            CompletableFuture<?>[] snapshot;
            synchronized (this) { snapshot = pending.toArray(CompletableFuture[]::new); }
            if (snapshot.length == 0) return;
            CompletableFuture.allOf(snapshot).join();
        }
    }

    public synchronized Attempt begin() { return new Attempt(revision, rewrite); }

    public synchronized boolean finish(Attempt attempt, boolean saved) {
        if (!saved) failure("save pipeline did not finish");
        if (lost != null) log.accept("save cannot certify persistence until the world is reopened: " + lost);
        if (!saved || lost != null || revision != attempt.revision()) return false;
        rewrite = false;
        failedChunks.clear();
        return true;
    }

    public synchronized boolean needsRewrite() { return rewrite; }
}
