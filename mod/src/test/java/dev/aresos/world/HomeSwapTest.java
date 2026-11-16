package dev.aresos.world;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

class HomeSwapTest {
    private static final LocalDateTime NOW = LocalDateTime.of(2026, 11, 16, 17, 30, 5, 123_000_000);

    @TempDir Path saves;

    @Test
    void theNewHomeTakesThePlaceAndTheOldOneKeepsADatedName() throws IOException {
        Path home = folder("AresHub", "old");
        Path staging = HomeSwap.freshStaging(saves, NOW);
        Files.writeString(staging.resolve("marker"), "new");
        long[] gap = {-1};
        Path archived = HomeSwap.swap(saves, staging, NOW, HomeSwap.FILES, gap);
        assertEquals("AresHub-2026-11-16_17-30-05-123", archived.getFileName().toString());
        assertEquals("new", Files.readString(home.resolve("marker")));
        assertEquals("old", Files.readString(archived.resolve("marker")));
        assertFalse(Files.exists(staging));
        assertTrue(gap[0] >= 0, "the moment without an AresHub was not measured");
    }

    @Test
    void aFailedSecondRenameBringsTheOldHomeBack() throws IOException {
        Path home = folder("AresHub", "old");
        Path staging = HomeSwap.freshStaging(saves, NOW);
        HomeSwap.Mover second = (from, to) -> {
            if (from.equals(staging)) throw new IOException("injected");
            HomeSwap.FILES.move(from, to);
        };
        var error = assertThrows(IOException.class, () -> HomeSwap.swap(saves, staging, NOW, second, new long[1]));
        assertEquals("injected", error.getMessage());
        assertEquals("old", Files.readString(home.resolve("marker")));
        assertTrue(Files.isDirectory(staging), "the staging folder is kept");
        try (var entries = Files.list(saves)) {
            assertEquals(2, entries.count(), "an archive was left behind");
        }
    }

    @Test
    void aFailedFirstRenameMovesNothing() throws IOException {
        Path home = folder("AresHub", "old");
        Path staging = HomeSwap.freshStaging(saves, NOW);
        HomeSwap.Mover none = (from, to) -> { throw new IOException("busy"); };
        assertThrows(IOException.class, () -> HomeSwap.swap(saves, staging, NOW, none, new long[1]));
        assertEquals("old", Files.readString(home.resolve("marker")));
        assertTrue(Files.isDirectory(staging));
    }

    @Test
    void anUndoThatFailsSaysWhereTheOldHomeIs() throws IOException {
        folder("AresHub", "old");
        Path staging = HomeSwap.freshStaging(saves, NOW);
        int[] calls = {0};
        HomeSwap.Mover onlyFirst = (from, to) -> {
            if (calls[0]++ > 0) throw new IOException("stuck");
            HomeSwap.FILES.move(from, to);
        };
        var error = assertThrows(HomeSwap.UndoFailed.class, () -> HomeSwap.swap(saves, staging, NOW, onlyFirst, new long[1]));
        assertEquals("old", Files.readString(error.archived.resolve("marker")));
        // Restoring later puts it back.
        HomeSwap.restore(saves, error.archived, staging, HomeSwap.FILES);
        assertEquals("old", Files.readString(saves.resolve("AresHub/marker")));
    }

    @Test
    void restorePutsTheNewHomeBackUnderItsStagingName() throws IOException {
        folder("AresHub", "old");
        Path staging = HomeSwap.freshStaging(saves, NOW);
        Files.writeString(staging.resolve("marker"), "new");
        Path archived = HomeSwap.swap(saves, staging, NOW, HomeSwap.FILES, new long[1]);
        HomeSwap.restore(saves, archived, staging, HomeSwap.FILES);
        assertEquals("old", Files.readString(saves.resolve("AresHub/marker")));
        assertEquals("new", Files.readString(staging.resolve("marker")));
        assertFalse(Files.exists(archived));
    }

    @Test
    void namesAreNeverReused() throws IOException {
        Path first = HomeSwap.freshStaging(saves, NOW);
        Path second = HomeSwap.freshStaging(saves, NOW);
        assertEquals("AresHub-new-2026-11-16_17-30-05-123", first.getFileName().toString());
        assertEquals("AresHub-new-2026-11-16_17-30-05-123-1", second.getFileName().toString());
        folder("AresHub-2026-11-16_17-30-05-123", "taken");
        assertEquals("AresHub-2026-11-16_17-30-05-123-1",
                HomeSwap.datedName(saves, HomeSwap.ARCHIVE_PREFIX, NOW).getFileName().toString());
    }

    @Test
    void theCheckWantsWhatTheSupervisorWants() throws IOException {
        Path world = completeWorld();
        HomeSwap.checkComplete(world);

        Files.writeString(world.resolve(NetherHome.PROVISIONED), "started\n");
        assertMessage(world, "the hub build was not finished");
        Files.writeString(world.resolve(NetherHome.PROVISIONED), "complete\n");

        Files.delete(world.resolve(NetherHome.MANIFEST));
        assertMessage(world, "the hub manifest is missing");
        Files.writeString(world.resolve(NetherHome.MANIFEST), "version=1\n");

        saveData(world.resolve("data/aresos/desktop.dat"), marker(false));
        assertMessage(world, "the desktop marker is switched off");
        saveData(world.resolve("data/aresos/desktop.dat"), marker(true));

        var home = homeData();
        home.remove("yaw");
        saveData(world.resolve("data/aresos/nether_home.dat"), home);
        assertMessage(world, "the saved home is incomplete");
        saveData(world.resolve("data/aresos/nether_home.dat"), homeData());

        Files.delete(world.resolve("level.dat"));
        assertMessage(world, "the level cannot be read");
        var level = new CompoundTag();
        level.put("Data", new CompoundTag());
        NbtIo.writeCompressed(level, world.resolve("level.dat_old"));
        HomeSwap.checkComplete(world);

        Files.writeString(world.resolve("level.dat_old"), "not gzip");
        assertMessage(world, "the level cannot be read");
    }

    private Path completeWorld() throws IOException {
        Path world = Files.createDirectories(saves.resolve("AresHub-new-x/data/aresos")).getParent().getParent();
        var level = new CompoundTag();
        level.put("Data", new CompoundTag());
        NbtIo.writeCompressed(level, world.resolve("level.dat"));
        saveData(world.resolve("data/aresos/desktop.dat"), marker(true));
        saveData(world.resolve("data/aresos/nether_home.dat"), homeData());
        Files.writeString(world.resolve(NetherHome.PROVISIONED), "complete\n");
        Files.writeString(world.resolve(NetherHome.MANIFEST), "version=1\n");
        return world;
    }

    private static CompoundTag marker(boolean enabled) {
        var data = new CompoundTag();
        data.putBoolean("enabled", enabled);
        return data;
    }

    private static CompoundTag homeData() {
        var data = new CompoundTag();
        data.putLong("seed", 50);
        data.putInt("x", 1);
        data.putInt("y", 64);
        data.putInt("z", 2);
        data.putFloat("yaw", 0);
        return data;
    }

    private static void saveData(Path file, CompoundTag data) throws IOException {
        var root = new CompoundTag();
        root.put("data", data);
        NbtIo.writeCompressed(root, file);
    }

    private static void assertMessage(Path world, String message) {
        var error = assertThrows(IOException.class, () -> HomeSwap.checkComplete(world));
        assertEquals(message, error.getMessage());
    }

    private Path folder(String name, String marker) throws IOException {
        Path folder = Files.createDirectory(saves.resolve(name));
        Files.writeString(folder.resolve("marker"), marker);
        return folder;
    }
}
