package dev.aresos.test;

import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;

import java.util.concurrent.atomic.AtomicReference;

/** One real region write fails after serialization and after vanilla cleared the chunk's dirty flag. */
public final class SaveFaults {
    private record Target(RegionStorageInfo info, ChunkPos pos) { }
    private static final AtomicReference<Target> NEXT = new AtomicReference<>();

    public static void once(RegionStorageInfo info, ChunkPos pos) { NEXT.set(new Target(info, pos)); }
    public static void clear() { NEXT.set(null); }
    public static boolean armed() { return NEXT.get() != null; }
    public static boolean take(RegionStorageInfo info, ChunkPos pos) {
        var target = NEXT.get();
        return target != null && target.info().equals(info) && target.pos().equals(pos) && NEXT.compareAndSet(target, null);
    }
}
