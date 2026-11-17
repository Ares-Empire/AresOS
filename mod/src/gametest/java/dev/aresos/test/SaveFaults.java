package dev.aresos.test;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;

import java.util.concurrent.atomic.AtomicReference;

/** An IO fault after vanilla has already cleared a chunk's dirty flag or cached an empty entity chunk. */
public final class SaveFaults {
    private record Target(RegionStorageInfo info, ChunkPos pos, boolean emptyOnly) { }
    private static final AtomicReference<Target> NEXT = new AtomicReference<>();

    public static void once(RegionStorageInfo info, ChunkPos pos) { NEXT.set(new Target(info, pos, false)); }
    public static void onceEmpty(RegionStorageInfo info, ChunkPos pos) { NEXT.set(new Target(info, pos, true)); }
    public static void clear() { NEXT.set(null); }
    public static boolean armed() { return NEXT.get() != null; }
    public static boolean take(RegionStorageInfo info, ChunkPos pos, CompoundTag data) {
        var target = NEXT.get();
        return target != null && target.info().equals(info) && target.pos().equals(pos)
                && (!target.emptyOnly() || data == null) && NEXT.compareAndSet(target, null);
    }
}
