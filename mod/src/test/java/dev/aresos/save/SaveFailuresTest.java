package dev.aresos.save;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.*;

class SaveFailuresTest {
    private final ArrayList<String> log = new ArrayList<>();
    private final SaveFailures failures = new SaveFailures(log::add);

    @Test void failureDuringRequestRequiresAnotherFullSave() {
        var request = failures.begin();
        failures.failure("level.dat");
        assertFalse(failures.finish(request, true));
        var repair = failures.begin();
        assertTrue(repair.rewrite());
        assertTrue(failures.finish(repair, true));
        assertFalse(failures.begin().rewrite());
        assertEquals("level.dat", log.getFirst());
    }

    @Test void autosaveFailureIsNotForgottenAtRequestStart() {
        var write = failures.writing("overworld 1,2");
        failures.written(write, false);
        var request = failures.begin();
        assertTrue(request.rewrite(), "must rewrite even though vanilla cleared the dirty flag");
        assertTrue(failures.finish(request, true));
    }

    @Test void failedChunkLeavingMemoryCannotBeRecoveredByReloadingTheSamePosition() {
        failures.chunkFailure("overworld 1,2");
        failures.unloaded("overworld 1,2");
        var newCopy = failures.writing("overworld 1,2");
        failures.written(newCopy, true);
        assertFalse(failures.finish(failures.begin(), true));
        assertFalse(failures.finish(failures.begin(), true));
        assertTrue(log.stream().anyMatch(line -> line.contains("reopened")));
        assertTrue(new SaveFailures(log::add).finish(new SaveFailures.Attempt(0, false), true));
    }

    @Test void lateAsyncFailureAfterUnloadAlsoLatchesEvenIfThePositionIsLoadedAgain() {
        var old = failures.writing("overworld 1,2");
        failures.unloaded("overworld 1,2");
        var replacement = failures.writing("overworld 1,2");
        failures.written(replacement, true);
        failures.written(old, false);
        assertFalse(failures.finish(failures.begin(), true));
    }

    @Test void successfulUnloadAndUnrelatedUnloadDoNotPoisonARepair() {
        var good = failures.writing("nether 1,2");
        failures.unloaded("nether 1,2");
        failures.written(good, true);
        failures.chunkFailure("overworld 1,2");
        assertTrue(failures.finish(failures.begin(), true));
    }

    @Test void lateSerializationDiagnosticAfterUnloadLatchesEvenWhenWriteFutureSucceeds() {
        var write = failures.writing("overworld 1,2");
        failures.unloaded("overworld 1,2");
        failures.chunkFailure("overworld 1,2");
        failures.written(write, true);
        assertFalse(failures.finish(failures.begin(), true));
    }

    @Test void joinedFollowUpHasItsOwnFailureBoundary() {
        var first = failures.begin();
        failures.failure("player data");
        assertFalse(failures.finish(first, true));
        var followUp = failures.begin();
        assertTrue(followUp.rewrite());
        failures.failure("saved data");
        assertFalse(failures.finish(followUp, true));
        assertTrue(failures.finish(failures.begin(), true));
    }

    @Test void failureInFirstSaveDoesNotPoisonSuccessfulFollowUp() {
        var first = failures.begin();
        failures.chunkFailure("overworld 1,2");
        assertFalse(failures.finish(first, true));
        assertTrue(failures.finish(failures.begin(), true));
    }

    @Test void barrierAccountsForAsyncErrorBeforeSaveCanSucceed() {
        var attempt = failures.begin();
        var io = new CompletableFuture<Void>();
        var write = failures.writing("overworld 1,2");
        failures.watch(io, ok -> failures.written(write, ok));
        io.completeExceptionally(new java.io.IOException("disk full"));
        failures.awaitWrites();
        assertFalse(failures.finish(attempt, true));
        assertTrue(failures.begin().rewrite());
    }

    @Test void unknownRetentionAndIncompletePipelineAlwaysRefuse() {
        failures.lost("entity write with unknown retention");
        assertFalse(failures.finish(failures.begin(), true));
        var fresh = new SaveFailures(log::add);
        assertFalse(fresh.finish(fresh.begin(), false));
        assertTrue(fresh.needsRewrite());
    }
}
