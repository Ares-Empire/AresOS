package dev.aresos.test;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class HomePublishTestSaveTest {
    @TempDir Path directory;
    private Path home;
    private Path scratch;

    @BeforeEach void setUp() throws IOException {
        home = Files.createDirectory(directory.resolve("saves")).resolve("AresHub");
        scratch = Files.createDirectory(directory.resolve("a53b"));
    }

    private static Path world(Path path, String contents) throws IOException {
        return Files.writeString(Files.createDirectory(path).resolve("keep.txt"), contents);
    }

    @Test void aFailedMoveLeavesTheOriginalSaveAndScratchAlone() throws IOException {
        var original = world(home, "original");
        var scratchFile = Files.writeString(scratch.resolve("keep.txt"), "scratch");
        var failure = new IOException("move failed");

        assertSame(failure, assertThrows(IOException.class, () -> HomePublishTestSave.prepare(home, scratch, (from, to) -> {
            assertEquals(home, from);
            assertEquals(home.getParent(), to.getParent());
            assertTrue(Files.notExists(to));
            throw failure;
        })));
        assertEquals("original", Files.readString(original));
        assertEquals("scratch", Files.readString(scratchFile));
    }

    @Test void restoresTheOriginalAfterAFailingTestAndMovesOnlyTheCreatedHomeToScratch() throws IOException {
        var original = world(home, "original");
        var failure = new AssertionError("test failed");
        assertSame(failure, assertThrows(AssertionError.class, () -> {
            try (var save = HomePublishTestSave.prepare(home, scratch)) {
                assertTrue(Files.notExists(home));
                world(home, "test save");
                save.created();
                throw failure;
            }
        }));
        assertEquals("original", Files.readString(original));
        assertEquals("test save", Files.readString(scratch.resolve("finished-home/keep.txt")));
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void restoresInterruptedBackupsAndKeepsAnUnclaimedHome(boolean legacy) throws IOException {
        Path interrupted = legacy ? scratch.resolve("previous-home")
                : home.resolveSibling("AresHub-53b-backup-" + UUID.randomUUID());
        world(interrupted, "original");
        world(home, "unclaimed save");

        try (var save = HomePublishTestSave.prepare(home, scratch)) {
            assertTrue(Files.notExists(home));
            assertTrue(Files.notExists(interrupted));
        }

        assertEquals("original", Files.readString(home.resolve("keep.txt")));
        try (var recovered = Files.newDirectoryStream(home.getParent(), "AresHub-53b-recovered-*")) {
            var paths = recovered.iterator();
            assertEquals("unclaimed save", Files.readString(paths.next().resolve("keep.txt")));
            assertFalse(paths.hasNext());
        }
    }
}
