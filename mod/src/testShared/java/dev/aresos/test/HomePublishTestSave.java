package dev.aresos.test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.UUID;

import static java.nio.file.LinkOption.NOFOLLOW_LINKS;

/** Keeps the publication test's canonical save separate from any save already in the test profile. */
final class HomePublishTestSave implements AutoCloseable {
    @FunctionalInterface
    interface Move { void move(Path source, Path target) throws IOException; }

    private final Path home;
    private final Path scratch;
    private final Path backup;
    private boolean created;

    private HomePublishTestSave(Path home, Path scratch, Path backup) {
        this.home = home;
        this.scratch = scratch;
        this.backup = backup;
    }

    static HomePublishTestSave prepare(Path home, Path scratch) throws IOException {
        return prepare(home, scratch, Files::move);
    }

    static HomePublishTestSave prepare(Path home, Path scratch, Move move) throws IOException {
        var interrupted = new ArrayList<Path>();
        Path legacy = scratch.resolve("previous-home");
        if (!Files.notExists(legacy, NOFOLLOW_LINKS)) interrupted.add(legacy);
        String prefix = home.getFileName() + "-53b-backup-";
        try (var backups = Files.newDirectoryStream(home.getParent(), prefix + "*")) {
            backups.forEach(interrupted::add);
        }
        if (interrupted.size() > 1) throw new IOException("Several 53b home backups need recovery: " + interrupted);
        if (!interrupted.isEmpty()) restore(home, interrupted.getFirst());

        Path backup = null;
        if (!Files.notExists(home, NOFOLLOW_LINKS)) {
            backup = home.resolveSibling(prefix + UUID.randomUUID());
            move.move(home, backup);
        }
        return new HomePublishTestSave(home, scratch, backup);
    }

    void created() { created = true; }

    @Override public void close() throws IOException {
        try {
            if (created) Files.move(home, scratch.resolve("finished-home"));
        } finally {
            if (backup != null) restore(home, backup);
        }
    }

    private static void restore(Path home, Path backup) throws IOException {
        // An interrupted run can leave a world at AresHub. Keep it too, since its ownership is uncertain.
        if (!Files.notExists(home, NOFOLLOW_LINKS))
            Files.move(home, home.resolveSibling(home.getFileName() + "-53b-recovered-" + UUID.randomUUID()));
        Files.move(backup, home);
    }
}
