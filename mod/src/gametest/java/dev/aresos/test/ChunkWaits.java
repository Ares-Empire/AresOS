package dev.aresos.test;

import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/**
 * How a server game test waits for chunks of its own: it holds them with a ticket of its own, and its waits end by
 * themselves, releasing those tickets, before the framework's limit (package 37's review fixes 1 and 2; package 39b
 * gave the town's and the gate's tests the same). A timeout of the framework runs none of the test's code, so it
 * would leave the tickets held. Only for waits in a sequence ({@code thenWaitUntil}): a test that runs through
 * {@code helper.onEachTick} cannot take a framework limit this large, as that registers one callback per tick up to it.
 */
final class ChunkWaits {
    /**
     * How long a wait may last in ticks: so many that {@link #WAIT_NANOS} always comes first. The test server ticks
     * without pause while tests wait: about 70,000 times a second when nothing else runs, 8.4 million ticks in 120
     * seconds (400,000 ticks passed in 8 seconds on the laptop while another build ran, too short to load a town on new
     * ground). Package 37 counted 4,000,000, under a minute on an idle server; package 39b made it ten times that, so
     * a test fails by the clock and this bound only catches a clock that stands still.
     */
    static final int LOAD_TICKS = 40_000_000;
    /**
     * Next to {@link #LOAD_TICKS}, how long a wait may last on the wall clock: a test whose ticks slow down fails and
     * lets go of its tickets. This bound works only while the server ticks: the test's own waits check it, each tick.
     * A server that stops ticking runs none of them; that ends the whole run through Gradle's limits, and no watchdog
     * thread releases tickets, since that is not safe off the server thread.
     */
    static final long WAIT_NANOS = TimeUnit.SECONDS.toNanos(120);

    private ChunkWaits() { }

    /**
     * The chunks of the box between two corners, in any order (package 37's review fixes 2: the far spots of
     * {@code /go far} run north, and from the larger corner to the smaller this was empty wherever they straddle a
     * chunk border).
     */
    static Set<Long> chunks(BlockPos from, BlockPos to) {
        var chunks = new HashSet<Long>();
        for (int x = Math.min(from.getX(), to.getX()) >> 4; x <= Math.max(from.getX(), to.getX()) >> 4; x++)
            for (int z = Math.min(from.getZ(), to.getZ()) >> 4; z <= Math.max(from.getZ(), to.getZ()) >> 4; z++) chunks.add(ChunkPos.pack(x, z));
        return chunks;
    }

    /**
     * Holds or lets go of these chunks with a ticket of the test's own. The framework forces the chunks of every test
     * structure and releases them when that test ends, so forcing and releasing them here would take a neighbouring
     * test's chunks away.
     */
    static void hold(ServerLevel level, Set<Long> chunks, boolean held) {
        for (long chunk : chunks) {
            if (held) level.getChunkSource().addTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
            else level.getChunkSource().removeTicketWithRadius(TicketType.DRAGON, ChunkPos.unpack(chunk), 2);
        }
    }

    /** Whether these chunks are loaded with their entities, as they are around a player. */
    static boolean loaded(ServerLevel level, Set<Long> chunks) {
        return chunks.stream().allMatch(chunk -> level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) && level.areEntitiesLoaded(chunk));
    }

    /**
     * A wait of a test that holds tickets, for {@code thenWaitUntil}: passes once {@code done}; fails, after running
     * {@code cleanup} and releasing the tickets of {@code held} ({@link #hold}), after {@link #LOAD_TICKS} ticks or
     * {@link #WAIT_NANOS} on the wall clock, whichever comes first. Its own failure, before the framework's.
     */
    static Runnable waitFor(GameTestHelper helper, ServerLevel level, Set<Long> held, BooleanSupplier done, String what, Runnable cleanup) {
        return waitFor(helper, level, held, done, what, cleanup, LOAD_TICKS, WAIT_NANOS);
    }

    /** {@link #waitFor} with its own bounds: a test forces the timeout path with small ones (package 37's review fixes 2, point 3). */
    static Runnable waitFor(GameTestHelper helper, ServerLevel level, Set<Long> held, BooleanSupplier done, String what, Runnable cleanup,
                            int maxTicks, long maxNanos) {
        var clock = new Object() { long start; int ticks; };
        return () -> {
            if (done.getAsBoolean()) return;
            long now = System.nanoTime();
            if (clock.ticks++ == 0) clock.start = now;
            if (now - clock.start > maxNanos || clock.ticks >= maxTicks) {
                try {
                    cleanup.run();
                } finally {
                    hold(level, held, false);
                }
                throw new AssertionError(what + " after " + (now - clock.start) / 1_000_000 + " ms and " + clock.ticks
                        + " ticks; the test's tickets were released");
            }
            helper.assertTrue(false, what);
        };
    }
}
