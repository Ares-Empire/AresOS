# 36b: the town's tests own their town (builder's report)

Builder: Claude agent on Opus 5.5, one step. Branch `pkg/36b-town-test-isolation`, from main `b07b86a7`.
Claude builders cannot create `REPORT.md`; this is the full report text.

## Cause

**`theTownKeepsInStepWithHisApps` did not hold all the ground it builds on, and the run's random plot decided whether that mattered.** I am highly sure of the mechanism and fairly sure it caused the 2026-11-14 failure. That run's log, with its plot position, was not available to me.

- The test holds (DRAGON tickets, radius 2) and waits for the chunks of a box from 48 west to 48 east and from 60 north to **16 south** of its home column.
- Spotify's logo at **W0L0** covers 4 to 15 blocks south of home (`Place.sideways`: side L of the west group lies to the south). `GateBuilder.prepare` inspects 2 blocks around the logo's blocks and 4 around its lights, so its ground reaches **17 blocks south**. Its build refuses with `NotLoaded` unless every inspected chunk has `hasChunk` and `areEntitiesLoaded`.
- The game test server puts the test grid at a **random x and z in every run**: `GameTestServer` calls `RandomSource.nextIntBetweenInclusive` twice and passes the result to `StructureGridSpawner`, as the 26.2 bytecode shows. So the home column's z mod 16 is random. When it is 15 (one run in sixteen), the 17th block south lies in the chunk just outside the held box. That chunk is loaded only because it borders the box's tickets (ticket level 32, a lower priority than the held chunks' 31). Its entities load on their own schedule, and the test never waits for that chunk.
- `keepingNear` runs whole inside one `thenExecute`, in the same tick the held chunks are ready. In the newcomer step, `TownKeeper.blocked` treats a `NotLoaded` place as free, so the plan puts Spotify at W0L0. `Town.build` then throws `NotLoaded`, and the pass marks itself `pending` and says no line. Result: **"A newcomer: []"**, the exact failure. This is the only path I found by which that pass says nothing and builds nothing. The other paths (an incomplete list, no hub, a hub of other rules, refused or frozen) cannot happen there: the fake passes `complete = true`, and the steps just before it in the same tick used the same hub.
- The newcomer step is the **first step of the test that builds south of home**: everything before it builds in the north group. A failure there and nowhere earlier is what this cause predicts.

### Made on purpose (uncommitted changes, discarded with `git checkout`)

| Run | Code | Result |
|---|---|---|
| Repro 1 | `80c3ca55` with the test's home column moved so that z mod 16 = 15, plus log lines | Exit 0, "All 98 required tests passed", BUILD SUCCESSFUL in 2m 17s. The log shows W0L0's ground in 1 chunk outside the held box, loaded in time in this run (the race was won). `TownKeeper.complete() false`, 0 players. |
| Repro 2 | Same, plus the near box held with ticket radius 0, so the chunk just outside the box is not loaded, as when its loading lags | **Exit 1, `java.lang.AssertionError: A newcomer: []`** at `keepingNear`, `:runGameTest FAILED`, BUILD FAILED in 19s. The log shows W0L0's ground in 2 chunks outside the box, `hasChunk false, entities loaded false`, `complete() false`, 0 players. |
| After the fix | The fix (commit 1's `TownGameTests`) with the same throwaway as Repro 2 | Exit 0, "All 98 required tests passed", BUILD SUCCESSFUL in 1m 37s. The log shows W0L0's ground in 0 chunks outside the held box. |
| Guard check | The fix with the box's south edge set back to 16 (no plot moved) | Exit 1, `AssertionError: Fixture: the logo at W0L0 reaches past the ground the test holds, at -19, 0, 15 from home`, BUILD FAILED in 13s. It fails in every run, wherever the plot falls. |

The throwaway changes are saved outside the repo; the reviewer can rebuild them from the table.

### The orchestrator's guess, checked: it does not hold for the server tests

- `TownKeeper.complete` becomes true only through `TownKeeper.listed()`. Its only caller is `MyAppsGame.listed(merged)`, whose only caller is `AresOs.takeIn`, which runs on the app helper's list. The server test run has no helper: `AresOs` starts the helper only in the client environment, and `runGameTest` sets `aresos.disableDiscovery`. No server test calls `listed` or the `AppsTestAccess` invokers; only client tests do. Both reproduction runs logged `TownKeeper.complete() false` at the newcomer step. So the production tick (`if (complete) keeper(server).step(server)`) never steps in the server run.
- Even with `complete`, `step` returns before it reads pictures or runs a pass unless a host is present. `DesktopWorld.isHost` needs `server.isSingleplayer()`, and the town tests have no player at all (0 logged).
- The test's fake keeper is its own `new TownKeeper()`: its pictures, `said`, refused places and pending work are fields of that instance, not of `TownKeeper.keeper(server)`.
- No tick runs between the steps of `keepingNear`, so nothing could act between `fake.change` and `fake.pass`.

## Done

1. **`TownGameTests` (commit `faf0b5c9`):**
   - One box of ground for the three town tests that build around a home (`TOWN_FROM`/`TOWN_TO`, `town(column)`): 48 west and east, 60 north, now **32 south**. The 32 adds one row of chunks per test.
   - A fixture check, `withinTown(hub, app, picture, places...)`. For each place a test builds in, every cell of its plan (box, the space in front, sign space, walkway, doormat and its surroundings, floor, blocks, lights) plus 4 blocks around it must lie inside that box, measured in blocks from home. It holds or fails the same way in every run, wherever the plot falls. The keeping test checks N0L0, N0R0, N1L0, N1R0 and W0L0; the first town test checks N0R0, N0L0 and N1L0; the sealing test checks N0L0 and N0R0. The far place (N40L0) keeps its own box.
2. **`GettingAroundGameTests` (commit `921522c5`):** its `Host` makes a real singleplayer host, and with a complete list the game's own keeper would act in that test's town between its steps, reading the test's apps file and saving places into it. `Host` now checks `!TownKeeper.complete()` before it changes anything. The typed swap and move that ran only `if (!TownKeeper.complete())` now always run and check the town's "waits" line.
3. **No production code changed.**

### Checked, no change needed

- **Package 34's My apps server tests:** they never complete the list, never set a singleplayer profile (the players they place are not the host), and do not touch the town. `MyAppsGame`'s news comes only from `listed()`.
- **Package 37's held boxes, worked out by hand:** TOWN (-48..48, -60..30) holds N0L0, N0R0, E0L0 and W1R1 (to x -40, z -33 with the 4-block margin); N40L0 has its own box. NO_TOWN (±32) holds N0L0. SWAP (±48) holds N0, E0 and S0L0 (to z +26). MOVE (-40..39) holds W0L0, W1L0 (to x -40, exactly at the edge with the margin; the real inspection reaches -38), W0R0, E0, S0L0 and N0. Avenues reach `avenueEnd(1)` = 38 out. These tests do not assert `pending`.
- **`stepThree`** holds ±80 around its home: S0, E1L0, W0R0 and N2L1 all lie well inside.

## Verified

| Run | Commit | Exit | Tests | Gradle |
|---|---|---|---|---|
| Final 1 | `921522c5` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 38s |
| Final 2 | `921522c5` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 36s |
| Final 3 | `921522c5` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 34s |

All through `mod/dev/build.sh` from the worktree root, each started with at least 6 GiB of memory available. The runs that made the failure happen on purpose are in the table under "Cause". `client-test.sh` was not run, because no client test changed.

## Not verified

- That the 2026-11-14 run's plot had z mod 16 = 15: its log was not available to me, and the plot position is not logged. The mechanism is shown; that it was this run's cause is inferred.
- How often the neighbouring chunk lags in practice. In Repro 1 it loaded in time. The real failure rate is one run in sixteen times that chance.
- `withinTown` was not added to package 37's tests (their boxes were checked by hand, above).

## JUDGMENT-CALL

- **A fixture check that holds or fails in every run, beside the larger box.** With only the larger box, the next place that reaches past the held ground would again fail in some runs only. The check costs about 25 lines of test code.
- **The check's margin is 4 blocks around every cell.** `GateBuilder` looks 2 blocks around a logo's blocks and 4 only around its lights. The stricter margin is simpler and does not copy `GateBuilder`'s private footprint shapes; at worst it asks a test for a little more ground than strictly needed.
- **One box for the three town tests**, although only the keeping test builds south. It gives one definition of the town's ground at the cost of one more row of chunks for two tests.
- **A check in `Host` rather than holding the production tick off.** Holding it off would need a hook in `TownKeeper`, a production change, and restoring `complete` needs one too. Nothing in the server run sets `complete`, so a check that keeps it that way is enough, and it fails loudly if a future test feeds a helper list.

## PLAN-GAP / open

- **A test's hub record can outlive it.** The town and getting-around tests put back the previous record only when there was one (`if (previous != null)`). The first such test therefore leaves its own record as the server's for the rest of the run. Nothing depends on that today: the keeper is idle, and the towns lie far from every plot. Removing a record would need a production change (`HubData` has no removal), so I left it.
- **`SlashNamesGameTests` (package 35) also sets a singleplayer profile**, so it has a host too. With the list never complete, the keeper stays idle there. If a server test ever completed the list, the keeper would act there on whatever hub record was left. It has no check like `Host`'s, because it is outside this brief's list.
