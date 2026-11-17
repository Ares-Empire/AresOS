**Blocking — failed entity deletions can still produce `ok:true`.**  
Where: [RegionSaveMixin.java:31](/var/home/ares/AresOS-46-save-now/mod/src/main/java/dev/aresos/mixin/RegionSaveMixin.java:31).

The observer hooks only `SimpleRegionStorage.write(ChunkPos, CompoundTag)`. Minecraft 26.2’s `EntityStorage.storeEntities` uses the separate `write(ChunkPos, Supplier)` overload with `IOWorker.STORE_EMPTY` when a chunk becomes empty. That path bypasses the hook.

A concrete failure sequence:

1. The last saved entity is removed, and an autosave attempts to clear its entity-region entry.
2. Minecraft adds the position to `emptyChunks` **before** the asynchronous write succeeds.
3. The write fails. Vanilla logs/reports it, but this fix neither records nor awaits that failure.
4. A later `save_world` skips retrying the deletion because `emptyChunks` already contains the position. Its flush can succeed because the earlier failed write has left the pending queue.

The request can therefore answer `ok:true` while stale entities remain on disk. This leaves the original false-success finding open.

**Fix:** observe the shared `Supplier` overload, through which the `CompoundTag` overload also delegates. Apply the existing asynchronous barrier and conservative entity-failure latch there. Add fault-injection coverage through `WorldSaves` for an empty-entity write failing during autosave, followed by another request; it must remain `error` under the chosen reopen-only policy.

I found no additional actionable issue in the reviewed terrain-chunk failure/unload accounting, dirty-state repair, player-data/`level.dat`/saved-data hooks, or joined follow-up boundaries. The existing terrain fault test does use the real `WorldSaves` path. Excluding the main merge, the changes stay within the permitted scope.

Reviewed head `490bfc99` read-only using files, cached bytecode listings, and git. No build, Gradle, client test, or game was run; no files changed.

CHANGES-NEEDED