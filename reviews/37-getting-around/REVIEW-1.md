Reviewed commit `8d1b7b200df6db633c9a72f021885ed0bf845593`. Review was read-only: files and git history/diffs only; no builds, tests, game execution or file changes.

| Point | Status | Reason |
|---|---|---|
| 1. `/go`, `/home`, arrival loading | OPEN | `/home` and H do not suppress walk-in detection. Arrival checks synchronously load terrain; the claimed one-chunk, one-tick bound is not established. |
| 2. Atomic swap/move | OPEN | Catalogue updates can invalidate preflight concurrently. Retained sign entities are treated differently before and after removal. Both can leave a partially completed arrangement. |
| 3. Owner’s world, freeze, loading, pictures | OK | Removal retains the existing provenance checks; frozen/refused towns reject changes first. Pictures are read off-thread, and construction/removal require loaded terrain and entities. The transaction failures are under point 2. |
| 4. Host-only commands and collisions | OK | `swap`/`move` have parse-time requirements and execution guards. `/go` and `/home` use `OwnedNodes`, including its protection against later registrations. |
| 5. Hand-set groups and compatibility | OK | Across-group swaps and moves save group keys and remove redundant overrides. Schema remains 4; package 35 preserves these fields, and package 36 understands them. No new downgrade-format change. |
| 6. H key | OK | Registered alongside G; gated on the integrated AresOS world, no screen, debug modifier not held, and payload availability. Server checks the host again. |
| 7. Test-only teardown and registration | OK | The Nether teardown removes only the test-created home when none existed. Production registers `/aresos app` for integrated servers; the new client test exercises a real typed swap without the server-test registration workaround. |
| 8. `/apps` and place wording | OK | Shared group/direction definitions, outward-facing sides, one-based displayed rows and correct ordinal handling, including 11th–13th. |
| 9. Tests and suite safety | OPEN | Useful success/refusal coverage, separate batches, plot-relative locations, own tickets and the new client test last. Missing transaction regressions and frozen/refused command tests; timeout paths can leak test tickets. |

1. **FIX — `/home` and H can open an app on arrival.**  
   `mod/src/main/java/dev/aresos/world/HomeCommands.java:52`

   In Build mode, set home inside an app’s doorway, leave it, switch to Live mode and run `/home` or press H. Setting home permits this because it checks safe ground, not zone membership. `goHome` teleports without calling `WalkInZones.arrived`; the next walk-in tick sees a newly entered zone and sends its launch payload.

   This breaches rule 1 even though the same behavior was inherited from `/aresos home`. Apply arrival suppression in the shared home/teleport path. Test home inside a zone, wait several ticks, assert no launch, then verify a genuine exit and re-entry still launches.

2. **FIX — the catalogue can change between preflight and the town pass.**  
   `mod/src/main/java/dev/aresos/hub/TownMoves.java:229` and `:233`; `mod/src/main/java/dev/aresos/AresOs.java:118`

   Start a checked swap of Chrome and Discord. Before the save/pass, a helper refresh changes Chrome’s icon path. The helper listener runs on the shell thread and updates `AresOs.apps`; only individual catalogue/save operations are synchronized.

   `change` then saves the places and obtains a fresh catalogue for `keeper.keep`. The pass removes both displaced logos before consulting their pictures. Chrome’s cached picture no longer matches its new path, so Chrome waits while Discord is built at its destination. The command reaches “The town did not finish” despite everything occurring within one server tick.

   This breaches rule 2. Serialize catalogue updates with the complete check/save/pass operation, or use a revision-checked transaction whose inputs cannot change after validation. Add a deterministic test that changes the icon path between preflight and commit.

3. **FIX — preflight ignores a retained sign that the actual build rejects.**  
   `mod/src/main/java/dev/aresos/hub/Town.java:71`; `mod/src/main/java/dev/aresos/zone/GateBuilder.java:191`

   Move a recorded logo’s text-display sign with `/data` into the middle of a voxel that the incoming logo would occupy, then swap that app with another. This is an owner-edited entity that the existing town rules explicitly preserve.

   Preflight’s `Gone` models blocks and zones, but entity checks still use the current `Neighbors.signs` UUID set. Consequently, they ignore that display. Removal correctly leaves the moved display, then drops the old logo record. During the actual build its UUID is no longer exempt, so the build refuses. The apps file has already changed and the logos have already come down; subsequent rounds can assign another place instead.

   This breaches rule 2 without concurrent world changes. Model which signs actually disappear and which entities remain during preflight. Test that this swap refuses before any file, record or world change.

4. **SHOULD — establish cold-arrival behavior instead of claiming a one-tick, one-chunk load.**  
   `mod/src/main/java/dev/aresos/world/GettingAround.java:154`; `mod/src/main/java/dev/aresos/world/HomeSites.java:83`; `docs/design/HUB.md:43`

   `/go` checks up to six positions through synchronous block reads and collision checks. A player’s bounding box can cross a chunk boundary, and all candidates can fail, leaving loaded terrain even though no teleport occurs. These calls happen before the teleport in the same command; there is no one-tick scheduling boundary or bounded wait.

   No explicit ticket is added. However, cold disk reads or generation can hold up the server thread. This read-only review cannot establish the duration of an owner-visible stall, so I am not asserting a measured performance failure. Add cold/unloaded and wholly obstructed arrival coverage, establish the loading behavior, and correct the documentation’s stronger claim.

5. **SHOULD — chunk-load timeout bypasses ticket cleanup.**  
   `mod/src/gametest/java/dev/aresos/test/GettingAroundGameTests.java:241`

   Each test acquires its tickets before `thenWaitUntil`; cleanup is inside later guarded steps or the success path. If chunk loading times out, neither runs, leaving those tickets held for the remainder of the shared server run.

   `LOAD_TICKS = 4_000_000` is finite, so it does not itself create an infinite test. It also provides no wall-clock bound if ticks slow or stop. Register cleanup for test failure/timeout as well as success, and add an independent practical timeout. This is a suite reliability issue, below the owner-world FIX bar.

6. **SHOULD — pin frozen/refused behavior at the command boundary.**  
   `mod/src/gametest/java/dev/aresos/test/GettingAroundGameTests.java:523`; `reviews/37-getting-around/REPORT.md:313`

   The new tests do not exercise swap/move against frozen or refused town data, nor `/go` to recorded and unrecorded destinations in those states. The existing package 36 tests verify its keeper protections, but would not catch a future command-specific bypass.

   Add these cases with unchanged apps-file bytes, town records, zones and blocks. The report’s untested “town did not finish” path also needs the concrete regression cases in findings 2 and 3; its reachability does not require another server tick.

VERDICT: CHANGES-NEEDED