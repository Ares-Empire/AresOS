d8035ead1b14cb095ce892cfde3a5c696ac7264a reviewed read-only: no file was changed, nothing was built, tested or run. I read the files, used git log/diff/show, and read the builder's game-test logs in `mod/build/run/gameTest/logs`.

# Review 1: package 36b, "The town's tests own their town" (PR #63)

| Point | Status | Reason |
|---|---|---|
| 1. The cause | OK | The code supports the geometry. The inspection around W0L0 reaches z +17, and the old box reached +16. When home z mod 16 = 15, block +17 falls in a chunk outside the box. That chunk is never waited for, so `Town.build` throws `NotLoaded`, the pass is marked pending and says nothing. The reproduction forces this condition and fails with exactly "A newcomer: []". The orchestrator's guess is wrong: nothing in the server run can set `complete`. Whether the 2026-11-14 failure had this plot can't be shown, and the report says so. |
| 2. The fix | OK | The +32 box covers everything the three town tests build in and everything `prepare` inspects around it. Every cell `prepare` inspects lies inside the cells `withinTown` checks. The places passed to `withinTown` are all the places each test builds in. Tickets: the same set is taken and released, release paths are unchanged, and no box overlaps another test's ground. |
| 3. `Host` check | OK | Server and client game tests run in separate JVMs. In the server run `complete` stays false. The typed swap and move checks already ran on every server run, and now they can never be skipped. |
| 4. Anything else | OK (known limits) | Hub records outliving their test and the SlashNames host without a check are both older than this PR. Neither can cause a failure that comes and goes today. No production code changed. |

## 1. The cause

**Geometry, checked against `Place`, `HubLayout`, `AppGroup`, `GatePlan` and `GateBuilder.prepare`:**
- W0L0 faces west, and the "right" side points north. Side L, k 0 puts the logo's columns at sideways −15..−4, which is z +4..+15. The front layers are at x −20..−22.
- `prepare` inspects:
  - the solid blocks plus 2 → z +17;
  - the lights plus 4 (columns 2 and 9 sit at z +13 and +6, one layer in front at x −19) → z +17;
  - the sign space (centre z +10, radius 6.1 blocks) → z +3..+16.
- The farthest inspected block is z +17, as the report says. `Neighbors.footprint` never reaches further sideways than its radius.
- The old box was `chunks(column−(48,·,60), column+(48,·,16))`. With home z = 16k+15, block +16 falls in chunk k+1 and block +17 in chunk k+2, outside the box. That happens only when z mod 16 = 15.
- Each held chunk gets a DRAGON ticket with radius 2, so held chunks sit at level 31 and the next chunk out at level 32. That chunk loads eventually, but nothing waits for it.

**Silent wait:**
- `blocked()` treats `NotLoaded` as free, so the plan puts Spotify at W0L0.
- `Town.build` then throws `NotLoaded`, which sets `pending` and adds no line.
- Every other path to an empty pass is closed:
  - the fake always has a picture;
  - the fake passes `complete = true`;
  - the steps just before use the same hub;
  - a real blocker would add a "blocked … so … stands at" line.
- No tick runs inside `keepingNear`, and entity loading only advances in `ServerLevel.tick`.

**Random plots, confirmed from logs:** I couldn't read the 26.2 bytecode read-only, but the builder's logs show it:
- the plot z was −5489193, −4293599 and 4108695 in three runs;
- the batch order differs between runs (compare `2026-11-14-1.log.gz` and `-5.log.gz`).

**Reproduction:** `repro.diff` moves home to z mod 16 = 15 and holds with radius 0, so the outside chunk is reliably unloaded. Its logs match the report's table:

| Run | Log | Result |
|---|---|---|
| Repro 1 (radius 2) | `-1.log.gz` | 1 chunk outside the box, loaded in time; passed |
| Repro 2 (radius 0) | `-2.log.gz` | 2 chunks outside, `hasChunk false`; `AssertionError: A newcomer: []` |
| Fix with radius 0 | `-3.log.gz` | 0 chunks outside; passed |
| Guard check | `-4.log.gz` | `withinTown` fails at −19, 0, 15 |

The three final runs (`-5`, `-6`, `latest.log`) show "All 98 required tests passed" and no diagnostic lines. `git diff 921522c5 HEAD -- mod/` is empty.

So the reproduction shows the mechanism with the chunk forced unloaded, not the radius-2 race itself. That is enough: the fix removes the mechanism whatever the race odds.

**The orchestrator's guess:**
- `complete` is set only in `TownKeeper.listed()`. The chain is `listed()` ← `MyAppsGame.listed(merged)` ← `AresOs.takeIn` ← `mergeHelperApps` ← the helper listener.
- That listener is registered only in `startHelper`, which runs only in the CLIENT environment. `runGameTest` also sets `aresos.disableDiscovery`.
- `AppsTestAccess`, the `startHelper` invoker, is only in `aresos.test.client.mixins.json`.
- Server tests call only `MyAppsGame.add/remove/tick/changed`, in `MyAppsGameTests` and `SlashNamesGameTests`.
- So in the server run:
  - `tick` never calls `step`;
  - `run`, `rebuild` and `TownMoves` see `complete == false` and do nothing or answer "waits";
  - `step` would also stop without a host, and the town tests have no player.
- The fake's keeper is its own `new TownKeeper()`. The production keepers live in `KEEPERS`, one per server, and share none of its state.

## 2. The fix

**Coverage of the +32 box:**
- Every cell `prepare` inspects (space, sign space, walkway, doormat surround, floor, the three footprints) lies inside `withinTown`'s cells plus 4 blocks.
- The other checks also stay inside that area:
  - `Neighbors.check`'s entity boxes (one block around a cell);
  - `HomeSites.isSafe` at the exit point;
  - `Town.prepare`'s floor check;
  - removal footprints, which are built from blocks the town placed.
- Home and column share x and z, and a chunk-aligned box always covers at least the blocks between its corners. So `withinTown` passing means the inspection is held in every run.
- The lists of places are complete:
  - **first town test:** builds N0R0 and checks N0L0 and N1L0.
  - **keeping test:**
    - builds N0L0, N0R0, W0L0 and N1R0;
    - checks N1L0;
    - plans only those places, plus N40L0, which has its own box.
  - **sealing test:** builds N0L0 and N0R0. After trust, Mail takes N0R0, because `blocked()` does not count a place that holds the town's own logo, and Discord's logo comes down first.
- Other reads also fall inside the box now:
  - the north road to `avenueEnd(1)` = 38;
  - the names at ±20;
  - `FlatHub.build`'s roads to 24;
  - `refusal(home+(30,−1,30))`.
- The south name and the end of the south road were outside the old box on some plots. That never broke anything, because `FlatHub.build` loads them on the spot.

**Tickets:**
- The same captured set is added and removed, with the same radius 2.
- Release paths are unchanged (`inTown`'s `finally`, and `keeping` when last or failed).
- Each town test is alone in its batch, and batches run one after another.
- No box overlaps another test's ground: the town tests sit at plot +15000/17000/21000 (±48), getting-around at +23000 and beyond, flat-home at 3000, 6000 and z 8000.
- Older than this PR, and unchanged by it: a town test that times out in `thenWaitUntil` keeps its tickets, because it has no `waitFor` like getting-around has.

## 3. `Host`

- The check at `GettingAroundGameTests.java:224` runs before the constructor changes anything. If it throws, `state.host` is still null, so `guarded` only releases the tickets.
- `runGameTest` and `runClientGameTest` are separate run tasks (`fabricApi.configureTests`), so they run in separate JVMs. No client test uses `Host` or calls into the two changed test classes.
- In the server run `complete` is always false. So the swap and move checks at lines 1116–1122:
  - already ran on every server run before this PR;
  - can no longer be skipped;
  - have no path to failing.

## 4. Open points

- **Hub record outliving its test** (`TownGameTests.java:174, :445`; `GettingAroundGameTests.java:296`).
  - The keeper is idle, so a leftover record changes only what `Whereabouts` says.
  - The tests that could see it allow for it:
    - `goWithoutATownAndHomeFromTheNether` stores a hub of other rules first;
    - `SlashNamesGameTests`' `/apps` checks only look for "System & Tools", "/discord, /dc" and "Discord  not installed", which appear either way.
  - The batch order is random each run and the suite has passed under several orders.
  - Known limit.
- **SlashNames host without a check:** see NIT 3. It cannot act while `complete` is false.

## Findings

**NIT 1: the report's arithmetic for package 37's move box is wrong.** `reviews/36b-town-test-isolation/REPORT.md:45`, about `GettingAroundGameTests.java:1148`.
- The report says W1L0 reaches "x −40, exactly at the edge with the margin; the real inspection reaches −38".
- In fact the sign space alone reaches x −40: the sign's centre is at x −33.5 and its radius is 6.1, so the space reaches −39.6, which is block −40.
- With `withinTown`'s 4-block margin it would reach −44, outside that box.
- No effect on the tests now: the move test's home sits in the middle of its chunk, so the box edge is exactly −40 in every run and the inspection stays inside, with no blocks to spare.
- But `withinTown` could not be reused for that test as it stands, and the sentence should be corrected.

**NIT 2: `withinTown` relies on a hand-kept list and a copied constant.** `TownGameTests.java:111` (`LOOKS = 4`) and `:190, :470, :881` (the lists of places).
- If a later step builds in a place not on the list (for example W0R0 or S0L0), or `GateBuilder`'s private `LIGHT_MELTS` grows past 4, the 1-in-16 failure returns and the check doesn't notice.
- This does not meet the FIX bar: the lists are complete and the margin is right today.
- Cheap hardening:
  - at the end of `keepingNear`, check that every place in `hub.logos()` was on the list;
  - point `LOOKS` at a shared constant.

**NIT 3: `SlashNamesGameTests.Fixture` creates a host without `Host`'s check.** `SlashNamesGameTests.java:66`.
- If a future server test ever completed the program list, the real keeper could act on a leftover hub record with SlashNames' apps file.
- No such path exists today. It was outside the brief's list, and the report documents it.
- Adding the same one-line check there would keep the two fixtures consistent.

VERDICT: SAFE with documented known limits
