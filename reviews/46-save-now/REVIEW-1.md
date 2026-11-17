**Blocking — failed saves can be reported as successful.**  
Where: [WorldSaves.java:117](/var/home/ares/AresOS-46-save-now/mod/src/client/java/dev/aresos/client/WorldSaves.java:117), particularly the unconditional conversion of a `true` return into `Saved.done(...)`.

Minecraft 26.2’s `saveEverything` return value does **not** certify successful persistence. Reading the cached game bytecode confirms that:

- `saveAllChunks` sets its return value when it visits a level.
- Chunk serialization failures can be caught and reported through `reportChunkSaveFailure` without escaping.
- Player-data, `level.dat`, and saved-data writes catch and log failures internally.

Consequently, a failed write can leave stale or missing world data while this code sends `world_saved` with `ok:true`. The supervisor can then treat an incomplete save as suitable for backup, shutdown, or update. The surrounding `RuntimeException` catch cannot detect swallowed failures.

**Fix:** observe and retain failures from the underlying save operations, including asynchronous writes, and return `ok:false, reason:"error"` when persistence failed. Account for Minecraft clearing dirty flags before writes succeed: merely resetting an error flag on the next request could falsely report recovery. Add fault-injection coverage through the real `WorldSaves` path; the scripted unit-test `error` replies and successful block readback do not exercise this failure.

I found no additional actionable defect in request joining, server-thread dispatch, lifecycle refusal handling, or the saving-indicator suppression within the reviewed scope. The three deferred package-48 integration items are excluded.

Reviewed head `f308ee60` read-only. No build, Gradle, tests, or game was run; files were unchanged.

CHANGES-NEEDED