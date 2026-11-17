# 46, review fix 2: the entity-deletion write

`reviews/46-save-now/REVIEW-2.md` (Codex `gpt-6-astra` `high`, head `490bfc99`) checked review fix 1 and found one blocking gap. Everything else in fix 1 held:
- the terrain chunk accounting;
- the dirty-state repair;
- the player data, `level.dat` and saved-data hooks;
- the joined follow-ups.

**The gap:** `RegionSaveMixin` observes only `SimpleRegionStorage.write(ChunkPos, CompoundTag)`. When a chunk's last entity goes, `EntityStorage.storeEntities` uses the `write(ChunkPos, Supplier)` overload with `IOWorker.STORE_EMPTY` instead, and that path bypasses the hook. Minecraft adds the position to `emptyChunks` before the asynchronous write succeeds. If the write then fails, a later `save_world` skips the deletion and can answer `ok:true` while stale entities remain on disk.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context, checking only this fix and what it touches.

## What changes

- Observe the shared `Supplier` overload, which the `CompoundTag` overload also delegates to. Apply fix 1's asynchronous barrier and its failure accounting there, so both overloads are covered once (no double counting).
- **A failed empty-entity write:** the position is already in `emptyChunks`, so no later save retries it. Treat the failure like a failed chunk that has left memory: answer `error` until the world is opened again, and log why. If a later save can actually rewrite that entry, a full repair is allowed instead. Say in the report which one you built and why.
- Check fix 1's list of swallow points against 26.2 once more for any other path that writes through a different overload or a different storage class (POI storage, for example). Add each to the report's list, covered or explained.

## Tests

- **A fault-injection test through `WorldSaves`:**
  - an empty-entity write fails during an autosave;
  - the next `save_world` answers `ok:false, reason:"error"`, and so does the one after it;
  - after the world is opened again, a request answers `ok:true`.
- **The existing tests** stay green.
- **Runs:** one full `mod/dev/client-test.sh` and one `mod/dev/build.sh`, both green.

## Docs

`reviews/46-save-now/REPORT.md`:
- a "Review fix 2" section;
- the updated swallow-point list;
- the run results.

## Rules

As in `briefs/46-review-fix-1.md`: same worktree and branch (PR #92), the same paths, the lock and exit-75 rule, and the hold on `rpm-ostree`, `bootc`, `ostree`, the owner test modules and mounting disks.
- End each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- Commit, push, and comment on PR #92. Never merge, never push to main, never `--no-verify`.
