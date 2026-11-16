package dev.aresos.world;

import net.minecraft.nbt.ByteTag;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.FloatTag;
import net.minecraft.nbt.IntTag;
import net.minecraft.nbt.LongTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Package 48: the files of a new home made from the AresOS menu. The new home is built under a staging name, checked
 * as the supervisor's {@code check_world} will check it, and only then moved into place: the old AresHub goes to a
 * dated name and the staging folder becomes AresHub, two renames in one folder. A game that dies while the new home is
 * being made so leaves the old AresHub as it was, never a half-made one that the next start would call damaged.
 */
public final class HomeSwap {
    /** The dated name an old home is kept under, as the title screen's "New home" has always named it. */
    public static final String ARCHIVE_PREFIX = NetherHome.SAVE_FOLDER + "-";
    /** Where a new home is built before it becomes AresHub. */
    public static final String STAGING_PREFIX = NetherHome.SAVE_FOLDER + "-new-";
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss-SSS");

    /** One rename; a test puts a failing one in its place. */
    public interface Mover { void move(Path from, Path to) throws IOException; }

    /** No replacement option: a name that is taken or a rename that fails leaves both folders alone. */
    public static final Mover FILES = (from, to) -> Files.move(from, to);

    /** The second rename failed and so did putting the first one back: the old home is at {@link #archived}. */
    public static final class UndoFailed extends IOException {
        public final transient Path archived;

        UndoFailed(Path archived, IOException cause) {
            super("the old home could not be moved back from " + archived.getFileName(), cause);
            this.archived = archived;
        }
    }

    private HomeSwap() { }

    /** A dated name under {@code saves} that nothing has: {@code <prefix><date>}, or with -1, -2 if that is taken. */
    public static Path datedName(Path saves, String prefix, LocalDateTime now) {
        String name = prefix + now.format(DATE);
        Path target = saves.resolve(name);
        for (int suffix = 1; Files.exists(target, LinkOption.NOFOLLOW_LINKS); suffix++) target = saves.resolve(name + "-" + suffix);
        return target;
    }

    /** Makes a new, empty staging folder; never one that was there before, even if another process took the name. */
    public static Path freshStaging(Path saves, LocalDateTime now) throws IOException {
        for (int attempt = 0; ; attempt++) {
            Path candidate = datedName(saves, STAGING_PREFIX, now);
            try {
                return Files.createDirectory(candidate);
            } catch (FileAlreadyExistsException taken) {
                if (attempt >= 100) throw taken;
            }
        }
    }

    /**
     * The new home goes into place: AresHub to a dated name, then the staging folder to AresHub. If the second rename
     * fails, the first is undone, so AresHub is the old home again and the exception says why. Returns where the old
     * home now is. {@code gapNanos[0]} gets how long no AresHub was on disk.
     */
    public static Path swap(Path saves, Path staging, LocalDateTime now, Mover mover, long[] gapNanos) throws IOException {
        Path home = saves.resolve(NetherHome.SAVE_FOLDER);
        Path archived = datedName(saves, ARCHIVE_PREFIX, now);
        long before = System.nanoTime();
        mover.move(home, archived);
        try {
            mover.move(staging, home);
        } catch (IOException failed) {
            try {
                mover.move(archived, home);
            } catch (IOException undo) {
                undo.addSuppressed(failed);
                throw new UndoFailed(archived, undo);
            } finally {
                gapNanos[0] = System.nanoTime() - before;
            }
            throw failed;
        }
        gapNanos[0] = System.nanoTime() - before;
        return archived;
    }

    /**
     * After a swap whose new home then failed: the new home goes back to its staging name and the old one becomes
     * AresHub again. If AresHub is missing (a swap whose undo failed) only the second rename is done.
     */
    public static void restore(Path saves, Path archived, Path staging, Mover mover) throws IOException {
        Path home = saves.resolve(NetherHome.SAVE_FOLDER);
        if (Files.exists(home, LinkOption.NOFOLLOW_LINKS)) mover.move(home, staging);
        mover.move(archived, home);
    }

    /**
     * What the supervisor's {@code check_world} wants before it calls a home sound (os/config/usr/libexec/aresos-desktop):
     * a real folder, a readable level (level.dat or level.dat_old), the desktop marker switched on, the saved home,
     * a finished hub build and the manifest. Throws with the first thing that is missing.
     */
    public static void checkComplete(Path world) throws IOException {
        if (Files.isSymbolicLink(world) || !Files.isDirectory(world, LinkOption.NOFOLLOW_LINKS))
            throw new IOException(world.getFileName() + " is not a folder");
        IOException unreadable = null;
        boolean level = false;
        for (String name : new String[]{"level.dat", "level.dat_old"}) {
            try {
                if (read(world.resolve(name)).get("Data") instanceof CompoundTag) { level = true; break; }
                unreadable = new IOException(name + " has no level data");
            } catch (IOException error) {
                unreadable = error;
            }
        }
        if (!level) throw new IOException("the level cannot be read", unreadable);
        CompoundTag marker = data(world, "data/aresos/desktop.dat", "the desktop marker");
        if (!(marker.get("enabled") instanceof ByteTag(byte enabled)) || enabled != 1)
            throw new IOException("the desktop marker is switched off");
        CompoundTag home = data(world, "data/aresos/nether_home.dat", "the saved home");
        if (!(home.get("seed") instanceof LongTag) || !(home.get("x") instanceof IntTag) || !(home.get("y") instanceof IntTag)
                || !(home.get("z") instanceof IntTag) || !(home.get("yaw") instanceof FloatTag(float yaw)) || !Float.isFinite(yaw))
            throw new IOException("the saved home is incomplete");
        String provisioned;
        try (Reader reader = Files.newBufferedReader(world.resolve(NetherHome.PROVISIONED), StandardCharsets.UTF_8)) {
            char[] start = new char[64];
            int length = Math.max(0, reader.read(start));
            provisioned = new String(start, 0, length);
        } catch (IOException error) {
            throw new IOException("the hub build has no completion record", error);
        }
        if (!provisioned.equals("complete\n")) throw new IOException("the hub build was not finished");
        if (!Files.isRegularFile(world.resolve(NetherHome.MANIFEST))) throw new IOException("the hub manifest is missing");
    }

    private static CompoundTag data(Path world, String relative, String what) throws IOException {
        try {
            if (read(world.resolve(relative)).get("data") instanceof CompoundTag data) return data;
        } catch (IOException error) {
            throw new IOException(what + " (" + relative + ") is missing or unreadable", error);
        }
        throw new IOException(what + " (" + relative + ") has no data");
    }

    private static CompoundTag read(Path file) throws IOException {
        if (!Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS)) throw new IOException(file.getFileName() + " is not a file");
        try {
            return NbtIo.readCompressed(file, NbtAccounter.create(1L << 24));
        } catch (RuntimeException error) {
            throw new IOException(file.getFileName() + " is not readable", error);
        }
    }
}
