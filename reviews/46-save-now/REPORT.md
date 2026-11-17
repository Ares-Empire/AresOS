# Package 46: report

Builder: a Claude agent (Opus 5.5), in two steps, then owner fix 1 (`briefs/46-owner-fix-1.md`, another Opus agent).
Brief: `briefs/46-save-now.md`. Branch `pkg/46-save-now`, PR #92.


Package 46, branch `pkg/46-save-now`: the mod saves the home world when the OS supervisor asks, over a lifecycle
channel of its own. Builder: Claude agents on Opus (step 1, then step 2). The supervisor's side is `linux-aresos`'s
package 25; nothing under `os/` changed.

## Done

- **The lifecycle channel** (`mod/src/main/java/dev/aresos/shell/LifecycleClient.java`).
  - Connects only when the launch environment has `ARESOS_DESKTOP_LIFECYCLE=1`, to `$XDG_RUNTIME_DIR/aresos/desktop.sock`,
    one JSON object per line. Without `XDG_RUNTIME_DIR` or the launch nonce and instance it logs one warning and stays
    off.
  - First line `lifecycle_hello` with `major` 1, `minor` 0, the helper hello's `instance` and `nonce`, and
    `capabilities: ["save_world"]`.
  - `save_world` gets `world_saved` with the `id` as sent, `ok`, `ms` and `world` (`world_ready`'s identity), or
    `ok:false` with `reason`.
  - Joining as the contract says: a request joins a save that has not started yet. One that arrives after a save began
    gets one follow-up save, which later requests join.
  - Reconnects when the socket goes away and comes back: backoff from 0.5 s doubling to 10 s, a fresh hello each time,
    a log line per change of state, nothing in the chat.
- **The game's side** (`mod/src/client/java/dev/aresos/client/WorldSaves.java`).
  - Runs `saveEverything(true, true, true)` (what `save-all flush` runs) on the integrated server's thread. It works
    while playing, with the Esc menu open and while a window covers the world: the server takes tasks while paused.
  - `ms` is the save's own time on the server thread.
  - Refusals:
    - `no_world`: no started server, also while a world is still loading.
    - `not_desktop_world`.
    - `server_stopping`: from the start of the server's stop until it stopped. A save still queued when the stop
      begins is refused and never runs.
    - `error`: the save saved nothing, or something threw before or during it.
- **Wiring.**
  - `DesktopWorld.saveName(server)` is the world identity; `ShellFocusClient.readyWorld` uses it too, so `world_saved`
    names the world exactly as `world_ready` does.
  - `AresOsClient` registers `WorldSaves` and starts the channel.
- **`docs/design/OS-BASE.md` B1:** a `save_world` (lifecycle channel) row: its gate, hello, request and answer. Marked
  as the mod's side built and the supervisor's side waiting for package 25.
- **Tests:**
  - `LifecycleClientTest`: 11 unit tests against `FakeSupervisor`, a fake `desktop.sock` in `mod/src/testShared`.
  - `SaveNowClientGameTest`: client game test, last but one in the client list, no screenshots.
  - `SaveTimesClientGameTest`: the measurement, last in the list. It measures only with
    `mod/dev/client-test.sh -PmeasureSaves`; otherwise it logs one line and does nothing.
  - Step 2 made the measurement work: the 40 apps are counted as the town counts them, and the test waits only for the
    chunks that arrived (see PLAN-GAP). Step 2 also added the saving-indicator observation (see JUDGMENT-CALL).
- **Owner fix 1: no "Saving world" text in the home screen** (the owner's answer to the JUDGMENT-CALL, "Hide it",
  board #331).
  - `HomeScreen.home(client)`: a game the session started (`session()`) in a desktop world, whether or not the app
    helper is connected. Package 48's Esc menu has the same condition in its brief.
  - `SavingIndicatorMixin` (client mixin on `Hud`): at the head of `extractSavingIndicator`, the HUD's drawing of the
    corner text, it skips the drawing when `HomeScreen.home` holds. It hides the text for every save: `save_world`,
    the autosave, the save on each pause. The saves, the server's saving flag, the indicator's fade in the HUD's tick
    and the player's own "Autosave Indicator" option are untouched; outside the home screen the text behaves as in
    Minecraft.
  - `SaveNowClientGameTest`: the observation became assertions (see Verified). Test helpers: `SavingText` with
    `SavingTextTestMixin` (counts the frames that draw the text, and lets every save reach a client tick, see
    PLAN-GAP) and `AutosaveTestAccess` (brings the game's own autosave to the next tick).
  - `docs/design/HUB.md`, package 40's corrections: one line that the home screen shows no "Saving world" text.

## Review fix 1

Builder: Codex `gpt-6.1-sol xhigh`; brief `briefs/46-review-fix-1.md`, finding in `REVIEW-1.md`.

**Done:** `world_saved ok:true` now depends on a per-world history of observed persistence failures, rather than
`saveEverything`'s boolean. The history starts at server startup and includes autosaves. Nothing resets it at request
start, on reconnect, or when the test simulates a refused stop. Actual world closure discards it.

### Swallow points in Minecraft 26.2

Read with Java 25's `javap -c -p -classpath <cached minecraft-common-deobf-26.2.jar> <class>` from the Gradle cache;
also inspected the client/server save call sites. The actual request order is **players first**, then each level's
saved data, chunks/POIs and entities, then `level.dat`, the town seal, and server-wide saved data. These are the
write/serialization failures that can otherwise be swallowed:

| Where | How vanilla catches or hides it | How this fix observes it |
|---|---|---|
| `PlayerDataStorage.save` | Catches `Exception`, warns, and returns normally, including failed temp-file creation/compression | `PlayerSaveMixin` at that catch's `Logger.warn` |
| `ServerStatsCounter.save` | Catches `IOException` / `JsonIOException`, logs and returns | `StatsSaveMixin` at the catch's `Logger.error` |
| `PlayerAdvancements.save` | Same IO/JSON catch and normal return | `AdvancementsSaveMixin` at the catch's `Logger.error` |
| Per-level and server-wide `SavedDataStorage.tryWrite` | Catches `IOException` on the IO executor, logs and returns; dirty bits were already cleared in `collectDirtyTagsToSave` | `SavedDataSaveMixin` at the catch's logging call; watches `scheduleSave`'s completion too, including exceptional asynchronous failures |
| `ChunkMap.save` | `tryMarkSaved` clears the dirty bit first; catches synchronous serialization/write-submission `Exception` and calls `reportChunkSaveFailure` | `ChunkSaveMixin` intercepts that reporting call |
| `ChunkMap.save`'s asynchronous write | Serialization supplier / `IOWorker.runStore` complete the write future exceptionally; `lambda$save$0` reports and consumes it, without making the enclosing save fail | `ChunkSaveMixin` watches the original write future and retains its outcome independently of vanilla's discarded dependent callback |
| `SectionStorage` (POIs) | Codec `resultOrPartial` may log and omit a section; a non-compound tag only logs; asynchronous write failures are consumed by `lambda$writeChunk$0` after reporting | `PoiSaveMixin` observes both serialization cases; `write(ChunkPos, CompoundTag)` delegates to the shared `Supplier` overload, where `RegionSaveMixin` watches the original future once |
| `EntityStorage`, nonempty chunk | Asynchronous entity-region failures are consumed by `reportSaveFailureIfPresent` after logging / `reportChunkSaveFailure` | The tag write delegates to the shared `Supplier` overload observed by `RegionSaveMixin`; `EntitySaveMixin` scopes serialization diagnostics |
| `EntityStorage`, empty chunk (review fix 2) | `storeEntities` adds the position to `emptyChunks` before calling `write(ChunkPos, Supplier)` with `IOWorker.STORE_EMPTY`; its asynchronous failure is reported and consumed, and later saves skip the cached deletion | `RegionSaveMixin` now watches that shared `Supplier` overload directly, awaits accounting through the existing barrier, and latches the failure until reopening |
| Player, block-entity and entity serialization | `ProblemReporter.ScopedCollector.close` logs diagnostics and permits an incomplete tag to be written | `SerializationProblemMixin` observes nonempty collectors only inside scoped save encoders; chunk encoding is scoped on both the server thread and its asynchronous serialization supplier |
| `LevelStorageAccess.saveLevelData(CompoundTag)` | Catches `Exception`, logs and returns after a failed temp-file/compressed write | `LevelSaveMixin` at that catch's `Logger.error` |
| `Util.safeReplaceFile` for player data / `level.dat` | Discards `safeReplaceOrMoveFile`'s false result after retry exhaustion (rename/delete/check helpers log and return false) | `FileReplaceSaveMixin` observes that false result by destination path, including replacement failures that never reach the outer catches |
| AresOS `TownSeal.before` / `after` | Our existing code logs caught read/write failures and returns | Explicit failure accounting at those catches, associated with the world storage path |

`IOWorker`'s region synchronization logs **and rethrows** failures; they escape through the joined future and fail
the request. It is not another silent-success catch. The mod also explicitly synchronizes POI storage: vanilla's
`flushAll` only queues those writes. Saved-data and region-write barriers finish only after failure accounting, so
vanilla's successful return cannot race ahead of an asynchronous error notification.

### Rules as built

- Every request takes a failure revision after draining prior writes. Any new failure during its own save makes
  it answer `ok:false, reason:"error"`, with the failed part named in the log. An escaped exception or a save that
  saved nothing also requires repair.
- After any failure, the next request rewrites all retained serializable chunks, including holders skipped by
  vanilla's accessibility filter and pending unloads; marks all cached saved data and retained POIs dirty; then runs
  the normal player, chunk, entity, metadata and saved-data save with flush. No block edit is needed to restore a
  cleared dirty flag. Only a clean completed save clears the repair requirement.
- A failed chunk leaving memory latches `error` until reopening. In-flight chunk writes carry their unload history,
  so a failure reported **after** the unload also latches. Reloading that coordinate cannot erase the old lost write.
- Conservative uncertainty: an entity/POI failure latches until reopening, because those stores have independent
  unload/eviction histories. A player leaving before a required repair does likewise. These cases still attempt the
  full rewrite, but never certify recovery from a potentially stale in-memory copy. Supporting recovery there later
  needs store-specific retention tracking; it does not change the wire protocol. This follows the brief's "If unsure:
  answer error" rule.
- Each joined follow-up uses its own revision and repair pass. It can succeed after repairing the preceding save's
  failure, or fail for its own write error. The lifecycle channel's joining and refusal behavior is unchanged.

**Tests:** ten `SaveFailuresTest` cases cover request and autosave failures, repair, actual and late unloads (including an incomplete serialization with a successful write future),
replacement chunks at the same coordinate, successful/unrelated unloads, follow-up boundaries, barriers and uncertain
retention. A further `LifecycleClientTest` exercises joined requests over the fake supervisor socket with this
journal. `SaveNowClientGameTest` injects one real `RegionFileStorage.write` IOException after serialization and dirty-bit
clearing, asserts the real `WorldSaves` reply is `error`, then checks the next successful request puts the unchanged
block on disk. It repeats the fault during the game's own autosave and checks the next request repairs that too.
The fault mixin and its arm exist only in the game-test mod. No screenshot numbering changes.

## Review fix 2

Builder: Codex `gpt-6.1-sol xhigh`; brief `briefs/46-review-fix-2.md`, finding in `REVIEW-2.md`.

**Done:** moved `RegionSaveMixin`'s observer from the `CompoundTag` overload to the shared
`write(ChunkPos, Supplier<CompoundTag>)` overload. Both normal entity/POI tags and empty-entity deletions now
register exactly one barrier on the original write future. Failure accounting finishes before the barrier permits
`WorldSaves` to answer. `ChunkMap` inherits this method too: it is explicitly excluded from the generic observer,
because `ChunkSaveMixin` already watches terrain writes with their precise unload history. This avoids counting
terrain twice or replacing its established in-place repair with the entity/POI reopen-only policy.

**Failed empty-entity writes require reopening.** The log names the storage type and chunk position and explains
that the empty-entry deletion was cached before its write succeeded, so retry cannot be proved. Every later
request answers `ok:false, reason:"error"` until the world closes and is opened again. Chosen because vanilla's
`emptyChunks` cache suppresses the very deletion that a generic full rewrite would need to retry. Clearing a
failure flag or marking terrain dirty cannot repair that. A store-specific deletion retry could support recovery
later, but would need its own lifecycle and fault tests; this fix keeps the existing conservative entity policy.
Reopening starts a history for the world actually loaded from disk; it does not restore a deletion that was lost.

**Swallow-point recheck:** regenerated bytecode listings from the cached Minecraft 26.2 common jar with Java 25's
`javap -c -p` and inspected the callers of `SimpleRegionStorage`, `IOWorker`, and `RegionFileStorage`. The table
above is updated with the two entity routes and POI's delegation. Additional overload/storage checks:

| Path checked | Coverage or explanation |
|---|---|
| Terrain `ChunkMap.save` → inherited `write(ChunkPos, Supplier)` | Already watched by `ChunkSaveMixin`, including asynchronous serialization, failed futures and unload history; excluded only from the generic region observer |
| POI `PoiManager` → `SectionStorage.writeChunk` → tag overload → supplier overload | Same observer and barrier as entity writes, plus the existing `PoiSaveMixin` serialization diagnostics and explicit `synchronize(true)` in `WorldSaves`; no second write overload bypass |
| Both `IOWorker.store` overloads → `runStore` → `RegionFileStorage.write` | The tag overload delegates to the supplier overload; the low-level writer either writes NBT or calls `RegionFile.clear` for a null tag. Its IO failure completes the observed future exceptionally; no separate live-world deletion writer |
| `RegionFileStorage.flush` / `IOWorker.synchronize` | Flush failures propagate; `IOWorker` logs and rethrows. The existing request catch returns `error` |
| `RecreatingSimpleRegionStorage.write(ChunkPos, Supplier)` | Overrides the method and uses a separate write worker, but belongs to `RegionStorageUpgrader`'s offline conversion/recreation path. Neither integrated-server construction nor `saveEverything` uses it |
| `ChunkNbt` / `StructureCheck` | File-fix utility writes use the delegating tag overload; structure checks only scan/read storage. Neither supplies another writer in a running world's save pipeline |
| Player data, stats, advancements, saved data, `level.dat`, safe file replacement and town seal | Rechecked against the original swallow-point list; their existing hooks and accounting remain as listed above. No new alternate save writer was found |

**Regression test:** extended `SaveNowClientGameTest` without changing the client test list or screenshot numbers.
It saves one armor stand and confirms it exists in a copy of the entity-region file, removes the last entity, and
injects an actual `RegionFileStorage.write` IOException only for the resulting null-tag deletion during vanilla's
autosave. After the failed future drains, two real lifecycle requests through `WorldSaves` must each answer
`error`; disk readback after each confirms stale entity data remains. The test then closes and reopens the same
save and requires a clean request to answer `ok:true`. The existing terrain request/autosave repair tests still run.
The fault selector and injection remain confined to the game-test mod.

**Existing client fixture synchronization:** the first full client run stopped in `MyAppsClientGameTest.commands`
before reaching the save test, with `Apps picked up a copy while crafting was occupied`. The preceding Apps test
waited for the client's inventory screen to close, then immediately filled the server's crafting slot. Its still-pending
close-container packet could clear that newly filled slot before `TakeAppPayload` arrived. Minecraft 26.2's
`handleContainerClose` calls `doCloseContainer`, and `InventoryMenu.removed` clears the crafting container on the
server. Added `waitForServerboundPackets()` before the server fixture is installed. All original assertions remain;
no product inventory behavior changed.

## Verified

- **Review fix 2 (2026-11-17):** all game/build runs use the approved dev scripts, headless, with no force or daemon
  stop option. Logs and copied suite screenshots are in the ignored `.work/review-fix-2/` directory.

  | Command/run | Result |
  |---|---|
  | `mod/dev/build.sh`, initial patch before the terrain observer exclusion | exit 0, `BUILD SUCCESSFUL in 2m 16s`; 258 unit tests, 0 failures/errors, 6 expected Windows skips; "All 104 required tests passed" |
  | `mod/dev/client-test.sh --keep-screenshots .work/review-fix-2/client-1-screenshots build` | exit 1, `BUILD FAILED in 8m`; existing My apps crafting fixture raced the previous close packet, before the save test. Added the packet barrier described above; no assertion changed |
  | `mod/dev/client-test.sh --keep-screenshots .work/review-fix-2/client-2-screenshots build`, final code (`62b0e0b6`) | exit 0, `BUILD SUCCESSFUL in 12m 54s`; 21 "checks passed" lines; terrain fault recovery and the empty-entity autosave failure/two refusals/same-world reopen checks passed. 258 unit tests, 0 failures/errors, 6 expected skips; "All 104 required tests passed" |
  | `mod/dev/client-test.sh --keep-screenshots .work/review-fix-2/client-3-screenshots build`, same final code | exit 0, `BUILD SUCCESSFUL in 12m 3s`; 21 "checks passed" lines again, including both terrain repairs and the empty-entity failure/reopen regression; "All 104 required tests passed". Unit task `UP-TO-DATE`, reusing the preceding green results |
  | `mod/dev/build.sh`, final code | exit 0, `BUILD SUCCESSFUL in 1m 43s`; "All 104 required tests passed"; unit task `UP-TO-DATE`, retaining the 258-test green results (0 failures/errors, 6 expected skips) |

  Both final-code combined build/client runs passed without further edits. The deletion fault logged
  `entities [0, 0]: empty-entry deletion was cached before the write succeeded; retry cannot be proved`, followed by
  two `save cannot certify persistence until the world is reopened` messages. Each run then printed
  `46 entity-deletion failure checks passed` after reopening the same save. The My apps test and its unchanged
  crafting assertions passed in both runs too.

  No new screenshots are needed for this persistence-only change; the regression checks copies of real region
  files. Preserved the suite's screenshots under the three `.work/review-fix-2/client-*-screenshots/` directories,
  then restored 51 tracked images and removed 25 generated images outside this package. `git diff --check` passed.
  Final `.work/` files over 500 MB: **none**. No large download or extracted image was created.

- **Review fix 1 (2026-11-17):** all commands below ran from this worktree through the approved dev scripts.
  `origin/main` through `968727d2` was merged before the final checks; package 48 was not merged.

  | Command/run | Result |
  |---|---|
  | `mod/dev/build.sh`, initial implementation / partial test additions | `BUILD SUCCESSFUL in 2m 13s`; 256 unit tests, 0 failures, 6 skipped; "All 104 required tests passed" |
  | `mod/dev/build.sh`, updated fault fixture | `BUILD FAILED in 8s`: three compilation errors because 26.2's `Blocks.COPPER_BLOCK` is a weathering collection. Changed the fixture to amethyst; no assertion was weakened |
  | `mod/dev/build.sh`, before the late-serialization edge fix (`5d9ed7c8` sources) | `BUILD SUCCESSFUL in 2m 16s`; 257 unit tests, 0 failures/errors, 6 expected Windows skips; "All 104 required tests passed" |
  | `mod/dev/client-test.sh`, before the late-serialization edge fix | exit 0, `BUILD SUCCESSFUL in 10m 13s`, headless NVIDIA RTX 4060, 20 "checks passed" lines; both injected IO faults and their disk-readback recoveries passed |

  Final-code build: `mod/dev/build.sh` at `76de2c29` exited 0, `BUILD SUCCESSFUL in 2m 19s`; 258 unit tests,
  zero failures/errors, six expected skips; "All 104 required tests passed".

  Client run 1: the failed requested write answered `error`; the next request (`id:12`) rewrote the unchanged chunk in
  430 ms. The failed autosave was repaired by `id:13` in 240 ms. The suite also retained all original package-46
  pause/cover/indicator/refusal assertions. The subsequent edge fix adds coverage for a late serialization diagnostic
  after unload even when the IO future succeeds; repeat runs below cover that final code.

  Final-code repeat 1: `mod/dev/client-test.sh build` at `76de2c29` exited 0, `BUILD SUCCESSFUL in 11m 52s`;
  headless NVIDIA RTX 4060, 20 "checks passed" lines, both real IO fault/recovery checks passed (330 ms / 250 ms
  for the two repairs). The full server suite printed "All 104 required tests passed" again; the unit task was
  `UP-TO-DATE` from the successful 258-test run above.

  Final-code repeat 2: `mod/dev/client-test.sh` at `76de2c29` exited 0, `BUILD SUCCESSFUL in 10m 20s`;
  headless NVIDIA RTX 4060, 20 "checks passed" lines. The two unchanged-chunk repairs took 696 ms / 289 ms.
  Final sources therefore passed the full client suite twice and the full build twice. No tests/assertions were
  weakened or removed. No new screenshots were needed for these disk/answer assertions; the existing suite's
  regenerated screenshots were restored to their committed versions, and its generated untracked captures removed.

  `git diff --check` passed. A Python recursive file-size inventory of `.work/` (>500 MiB) printed no files;
  no large downloads or extracted images remain there. Dev scripts used single-use Gradle processes and cleaned
  up their own scopes; no `--stop` or `--force` was used.

- **Owner fix 1** (headless compositor, RTX 4060):

  | Run | Code | Result |
  |---|---|---|
  | `build.sh` 1 | the fix's first code, uncommitted on 6e728b99 | failed in a server game test this fix does not reach, `flat_home_game_tests_no_mob_appears_in_ten_minutes`: "Fixture: the ground around home did not load within 6000 ticks", while package 48's build ran its server game tests at the same time |
  | `build.sh` 2 | the same code, right after, alone | **green**, 2 min 39 s, 247 unit tests (0 failures, 6 skipped), "All 104 required tests passed" |
  | `client-test.sh` 1 | 01b5c149 | failed in `SaveNowClientGameTest` at its `save-all` case: "Unknown or incomplete command" (see PLAN-GAP). Every indicator check before it had passed. The case is dropped in 59cd0a54 |
  | `client-test.sh` 2 | 59cd0a54 | **green**, exit 0, 10 min 14 s, 19 "checks passed" lines |
  | `build.sh` 3 | 59cd0a54 | **green**, 1 min 39 s, "All 104 required tests passed"; the unit tests were up to date from run 2 (nothing they compile changed) |

  `SaveNowClientGameTest`'s "46 saving indicator" lines in client run 2 (the text rose for every save, so Minecraft
  would have shown it; "frames" counts the frames that drew it):

  | Save | Where | Rose to | Frames that drew it |
  |---|---|---|---|
  | 3, requested while playing (79 ms) | outside the home screen (session flag off) | 20 % | 59 |
  | 10, requested while playing (51 ms) | home screen | 20 % | 0 |
  | 4, requested under the Esc menu (26 ms) | home screen | 36 % | 0 |
  | 8, requested while covered (90 ms) | home screen | 36 % | 0 |
  | 7, requested after the refused stop (105 ms) | home screen | 20 % | 0 |
  | the game's own autosave | home screen | 20 % | 0 |

  Over the whole home-screen part, from turning the session flag on until the world had closed (the saves on
  pausing, covering and closing included), no frame drew the text. Client run 1 showed the same for every save before
  the `save-all` case (save 3 drawn in 60 frames, the others in 0).
- **`mod/dev/build.sh`** (full, at ba67fed2): BUILD SUCCESSFUL in 3 min 35 s.
  - 247 unit tests: 0 failures, 6 skipped (the Windows catalogue tests, skipped on Linux as before).
  - Server game tests: "All 104 required tests passed".
- **`mod/dev/client-test.sh`** (headless compositor, RTX 4060):

  | Run | Code | Result |
  |---|---|---|
  | 1 | 6938089b (step 1) | green, 10 min 36 s, 19 "checks passed" lines |
  | 2 | c4951ef7, with `-PmeasureSaves` | every client test passed (19 "checks passed"); the measurement test then timed out waiting for 40 apps (it counted 41, see PLAN-GAP) |
  | 2b | the count fixed, with `-PmeasureSaves` | every client test passed again; the measurement timed out in `waitForChunksRender` (see PLAN-GAP) |
  | 3 | ba67fed2's code, with `-PmeasureSaves` | **green**, exit 0, 12 min 34 s, 19 "checks passed" lines, measurement complete |
  | 4 | ba67fed2, plain | **green**, exit 0, 10 min 7 s, 19 "checks passed" lines |

  The final code passed the whole client suite twice (runs 3 and 4).
- **What `SaveNowClientGameTest` checks** (each run's line "46 save-now checks passed"):
  - The real `LifecycleClient` and `WorldSaves` against a fake supervisor save while playing, with the Esc menu open,
    and while covered (package 40's `shell_covered`).
  - Each time, a block placed just before the request is missing from a copy of its region file before
    `world_saved` and present after it.
  - The answer carries `world_ready`'s identity.
  - No screen opens, nothing pauses or unpauses, no chat line.
  - Refusals: `no_world` on the title screen and after closing, and `not_desktop_world`. `server_stopping` for a save
    still queued when the stop begins (it never runs afterwards) and for a request during the real stop.
  - Small test world, run 3: playing 81 ms, Esc menu 20 ms, covered 20 ms. Run 4: playing 82 ms, Esc menu 12 ms, covered 18 ms.
  - Since owner fix 1, the "Saving world" text: outside the home screen (session flag off) a requested save raises it
    and frames draw it. In the home screen (session flag on, desktop world) every save raises it and no frame draws
    it: requested saves while playing (one more, save 10), under the Esc menu and covered, save 7, the game's own
    autosave, and, counted over the whole part, the saves on pausing and closing. Fix client run 2: playing 79 ms,
    home screen 51 ms, Esc menu 26 ms, covered 90 ms.
- **What the unit tests check:**
  - The gate: no variable, no connection.
  - The hello's exact fields.
  - Each answer and each refusal reason, including a game that throws or names no known reason (answered `error`,
    never saved).
  - Joining: requests before a save starts share it; requests after it began share one follow-up save.
  - Lines that are no request change nothing.
  - Reconnect with a fresh hello after the socket goes away and comes back.
  - No stale answer on a new connection; an oversized line ends the connection and the mod comes back; closing stops
    the reconnecting.

## Measured save times

These are the original package measurements, before review fix 1; they were not remeasured for the fix.

Measured with `SaveTimesClientGameTest`, run 3. The setup:

- A flat home (the mod's real home creation) with a town of 40 test apps, in package 41's mix (6 Internet, 3 Games,
  3 Work & Media, 28 System & Tools).
- Render distance 8 and simulation distance 5, as the product sets them.
- Each `ms` is the mod's own answer through the real channel; one sample each.

| When | `ms` |
|---|---|
| **Right after joining the home again** | **103 ms** |
| **After a 60 s glide over new ground** (package 41's route and speed: 1.08 blocks a tick, north 15 s, south 30 s, north 15 s) | **116 ms** |
| After the same glide over that ground again | 458 ms |

- The log's "1849 chunks loaded" is the same each time: that is the 43 x 43 chunks the server holds around the player
  wherever he is.
- The glide did reach new ground: the world stored 2332 chunks, z from -32 to 31 against x from -21 to 21.
- Why the third save took four times longer is not known (one sample). A flush also waits for chunk writes still
  queued, for example of the chunks unloaded along the route.
- All three are far inside the contract's deadlines (about 60 s for a backup, about 10 s at shutdown).

## Not verified

- **Against the real supervisor:** package 25 isn't built. The real gate, socket path, peer check and deadlines are
  untested.
- **The mod's own channel in a dev run:** `client-test.sh` removes the AresOS launch variables, so `fromEnvironment`
  never opens the channel there. The tests construct `LifecycleClient` with a socket path, and the gate is unit-tested.
- **The owner's own home**, with his real apps and his disk busy with other work. The times come from a test home
  (40 fake apps, headless), one sample each.
- **The hidden "Saving world" text in real play** (owner fix 1). The client test shows that no frame draws it in the
  home screen, with its own fixture for the tick order (PLAN-GAP); nobody has looked at the corner during a save in
  the real session yet.
- **Minecraft's "Saving world" screen while a world closes** is a different thing: a whole screen, not the corner
  text, and owner fix 1 leaves it alone. Package 48 takes Save and Quit out of the home screen and gives its
  "New home…" a screen of its own; a shutdown still closes the world.
- **Other IO fault types in the game:** review fixes 1 and 2 inject actual asynchronous terrain-region and empty-entity
  deletion failures. Player, stats, advancements, metadata, saved-data, nonempty-entity and POI fault injection are not separately exercised;
  their required mixins load during the suites, and the accounting policy has unit coverage. Physical power loss
  and a real full filesystem were not simulated.
- **Hosted checks at report commit time:** they start on push; the PR gives the final-head run links and results.
- **Windows:** nothing changes there, because the gate is never set (unit test: no variable, no connection). There
  was no Windows run.

## JUDGMENT-CALL

**Review fix 1: refuse uncertain recovery.** Entity/POI failures and a player leaving before a full repair require
reopening the world before another `ok:true`. Their independent unload histories make a generic cleared error flag
unsafe. Chosen under the brief's explicit "If unsure: answer error" instruction; the alternative of allowing recovery
without proving retention could certify lost state. A later change needs per-store retention tracking and fault tests,
with no save-format or protocol migration. Terrain writes with a retained chunk do recover in place.

**Answered by the owner: "Hide it"** (board #331, 2026-11-16). In the home screen the "Saving world" text never
shows, for any save. Built in owner fix 1 (`briefs/46-owner-fix-1.md`):

- **How:** `SavingIndicatorMixin` skips the HUD's drawing of the text (`Hud.extractSavingIndicator`) while
  `HomeScreen.home` holds: a game the session started, in a desktop world, with or without the app helper. In effect
  it is the alternative below of turning off the Autosave Indicator, but only in the home screen and without touching
  his `options.txt`: outside it his own option decides as before.
- **Not the quiet save:** `WorldSaves` still calls `saveEverything`, so nothing has to be copied from Minecraft by
  hand, and the autosave's text and the pause's are hidden too, which the quiet save would not have done.
- **Cost of changing later:** one mixin and one condition; removing the mixin brings the text back.

The analysis the owner answered, as written before:

**Vanilla's small "Saving world" text can show in the corner for a moment during a requested save.**

- **What happens.**
  - The save is vanilla's `saveEverything`, which the brief names. It is the same call as `/save-all flush`, the
    autosave every 5 minutes, and the save each time the game pauses.
  - It raises the server's "saving" flag. Twenty times a second the game checks that flag. While it is raised, a small
    white "Saving world" text in the bottom-right corner fades in a fifth of the way to full; afterwards it fades out a
    fifth per tick. It is drawn on top of everything, the Esc menu included.
- **What he would see in play.** This is worked out from the game's code with the measured times:

  | Save | Brightest | Clearly visible (over 10 %) | Then a faint trace |
  |---|---|---|---|
  | About 0.1 s (the 40-app home: 103 and 116 ms) | about 36 % (49 % if a third tick catches it) | about 0.35 s | about 1 s |
  | 458 ms (the slow one) | about 87 % | about 0.9 s | about 0.7 s |
  | About 20 ms (small world) | 20 % in about 2 of 5 saves, else nothing | about 0.2 s | about 0.7 s |

  - He sees the same text today at every autosave (every 5 minutes) and when he presses Esc.
  - While an app window covers the world, the text is hidden behind the window.
- **What the client test saw** ("46 saving indicator" lines, run 3).
  - Under the Esc menu and while covered (20 ms saves) it faded in to 22 %. One tick caught the flag, on top of the
    trace the pause's own save had left. It was then drawn for 18 more ticks, 14 of them under 10 %: about 0.2 s
    clearly and 0.7 s faint at play's 20 ticks a second.
  - While playing (81 ms) and for the save after the refused stop (41 ms) it did not show.
  - In the test the client and server tick in lockstep, so whether a tick catches the flag depends on their order, not
    on how long the save takes. In play it depends on the length, as in the table.
  - Run 4 showed the same: 22 % and 18 ticks (14 faint) under the Esc menu and while covered; nothing while playing
    (82 ms) or for save 7 (43 ms).
- **Chosen:** keep `saveEverything`, as the brief names it. The text behaves exactly like the autosave's text that he
  already sees every 5 minutes.
- **Alternatives:**
  - **A quiet save.** It would run the same steps without raising the flag: `PlayerList.saveAll()` and
    `saveAllChunks(true, true, true)`, plus the low-disk-space warning through a small invoker mixin, because that
    method is protected.
    - In Minecraft 26.2 nothing reads the flag except this text (checked in the game's code), so the data on disk
      would be the same.
    - Cost: about ten lines in `WorldSaves`, the mixin, and a client-test check that the text stays off.
    - Risk: a later Minecraft version that adds a step to `saveEverything` must be copied by hand, or a requested save
      silently misses it.
  - **Turning off vanilla's own "Autosave Indicator" option** by default in AresOS. That hides the text for every
    save, autosaves included. It is a different package's decision.
- **Recommendation:** keep it. Our save adds one more brief appearance of a text that the autosave already shows every
  5 minutes. If he wants no saving text at all, turning off the option hides all of them in one place, which the quiet
  save would not do.
- **Cost of changing later:** small and local either way. Only `WorldSaves` (and the options default) would change,
  with no protocol change.

## PLAN-GAP

- **"Nothing on screen" and `saveEverything`.** The brief asks for both, and they conflict slightly, because of the
  text above. See JUDGMENT-CALL.
- **Contract readings.** The contract doesn't settle these points; this is what the mod does. `linux-aresos` should
  confirm them for package 25.
  - The supervisor's reply to `lifecycle_hello` is unspecified. The mod waits for nothing and ignores every line that
    is not a `save_world` request. (The real supervisor answers every line it reads; see `on_peer` and `reply` in
    `os/config/usr/libexec/aresos-desktop`.)
  - The request's `reason` is only logged. An unknown or missing reason still saves.
  - `id` comes back exactly as sent, number or text. A request without a usable `id` is ignored.
  - Unknown ops, such as a later `prepare_stop`, get no answer; the hello's `capabilities` say what this mod does.
  - `ms` is the save's own time on the server thread, not the wait before it.
  - `server_stopping` covers the whole stop, from `SERVER_STOPPING` to `SERVER_STOPPED`; after it the answer is
    `no_world`. A request while the world is still loading (before `SERVER_STARTED`) is answered `no_world`.
  - The backoff starts over only after a connection that lasted at least 10 s. A supervisor that refuses the peer by
    closing at once is therefore retried at most every 10 s, and the log notes only changes of state.
  - There is no override variable for the lifecycle socket (the contract names none).
- **Test tooling.** Fabric's `waitForChunksRender()` waits for every chunk in the full square of the render distance,
  but the server sends a round area (`ChunkTrackingView`). Above render distance 6 the square's corners never come and
  the wait never ends. The suite's other tests run at 5. A later test at the product's distance should use
  `waitForChunksRender(false)`.
- **Counting "his" apps in a test.** A fresh apps file starts with Notepad as his. When the helper doesn't list
  Notepad, it stays his but absent, so counting "mine" alone gives one more than the town builds. Count what is his and
  present, as `TownKeeper.wanted` does.
- **Seeing the "Saving world" text in a client test** (owner fix 1). The text rises only while a client tick finds
  the server saving. Fabric's client test runs the client's and the server's tick side by side in one step and then
  waits for the test, so whether a tick catches a save depends on their order in that step, not on the save's length:
  an 81 ms save was never caught (JUDGMENT-CALL). In play the client ticks every 50 ms on its own, so a save of 50 ms
  or more always shows. The test's `SavingTextTestMixin` therefore lets the client's next tick count every save that
  began since its last tick (Fabric's `BEFORE_SAVE`, which fires inside the save while the saving flag is up). Then
  the text rises for every save, and the test checks that it rose and whether a frame drew it. It is on only during
  `SaveNowClientGameTest`.
- **`save-all` in the home screen** (owner fix 1). The fix's brief names "a vanilla autosave or a `save-all`".
  `save-all` is registered only on a dedicated server (Minecraft's `Commands`), so in the home screen's integrated
  server it is an unknown command (the first client run: "Unknown or incomplete command"). The test covers the
  autosave; the saves on pausing and closing are covered by the frame count over the whole home-screen part.
- **Vanilla already saves on every pause.** That includes a window covering the world, through package 40's pause.
  It isn't flushed or forced, so it doesn't replace `save_world`. But a requested save soon after a pause has little
  left to write.

## Open questions

- **For the owner:** answered ("Hide it", board #331); built in owner fix 1.
- **For `linux-aresos`:**
  - Do the contract readings above match package 25's supervisor? In particular: no hello reply is needed, `reason` is
    only logged, and unknown ops are not answered.
  - Is one save of up to about 0.5 s comfortable for the shutdown budget? Package 25 may want its own measurement on
    the real home once its side exists.
- **Open technically:** the third save's 458 ms (the same glide again, four times the first glide's time) is
  unexplained; there was one sample each.
