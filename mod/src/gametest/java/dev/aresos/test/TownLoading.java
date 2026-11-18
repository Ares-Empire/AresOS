package dev.aresos.test;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;

import java.util.function.BiPredicate;

/** Test-only loading delays; never makes an unloaded place appear safe to build. */
public final class TownLoading {
    public static volatile BiPredicate<ServerLevel, BlockPos> delayed;

    public static boolean delayed(ServerLevel level, Iterable<BlockPos> cells) {
        var rule = delayed;
        if (rule == null) return false;
        for (var cell : cells) if (rule.test(level, cell)) return true;
        return false;
    }
}
