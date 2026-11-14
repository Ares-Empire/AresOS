# 39b: Hub tidy, progress and report

Builder: one Claude agent on Opus 5.5, one step. Branch `pkg/39b-hub-tidy` from main `3d96d78e`.
Claude builders cannot create `REPORT.md`; this file holds the report (the orchestrator renames it).

## Done

### 1. The town's tests wait like package 37's (#257)

- **New `mod/src/gametest/java/dev/aresos/test/ChunkWaits.java`**: package 37's `waitFor` (both forms), `hold`,
  `loaded` and `chunks` (the any-corner-order form), moved out of `GettingAroundGameTests`, which now imports them.
  Nothing copied: every chunk-waiting test class uses the one class.
- **`LOAD_TICKS` is 40,000,000 (was 4,000,000 in package 37, 400,000 in the town and gate tests).** The brief asks
  for "a tick bound large enough never to be reached first". `GateGameTests` records that the test server ticks
  about 70,000 times a second when nothing else runs: 4,000,000 ticks are then 57 seconds, before the 120-second
  clock. At 40,000,000 the clock comes first up to about 330,000 ticks a second; the tick bound only catches a clock
  that stands still. Judgment call below.
- **`WAIT_NANOS` stays 120 s**, checked by the wait itself on each tick.
- **`TownGameTests`**: every wait (the four tests' chunk waits and the keeping test's far-place wait) is a
  `waitFor`. On timeout it releases the tickets: the first waits release the town's ground; the far wait also clears
  the town's zones, puts the previous hub record back and releases the far chunks (`letGo`, which `keeping` now
  shares). `MAX_TICKS = 2 × LOAD_TICKS + 1,000` (a town test waits at most twice). Success and failures in the steps
  release as before (`inTown`'s `finally`, `keeping`).
- `guarded` is not reused: it is built around `GettingAroundGameTests.Host` and its home record, which the town
  tests do not have; their own `inTown` and `keeping` already release on every way out of a step. Judgment call
  below.

**Other server test classes that wait for chunks with a fixed tick count**, now treated the same way:

| Class | Wait | Before | Now |
|---|---|---|---|
| `TownGameTests` | `inTown` (first test), keeping (near and far), rebuild, seal | 400,000 ticks, the framework's limit | `waitFor`, framework `2 × LOAD_TICKS + 1,000` |
| `GateGameTests` | `Site.run` (nine tests), `chunkBorderRefusesBeforeReadingTheUnloadedHalo` | `SITE_TICKS` 400,000, the framework's limit | `waitFor`, framework `LOAD_TICKS + 1,000`; the border test's radius-0 ticket released by its cleanup |
| `FlatHomeGameTests` | `noMobAppearsInTenMinutes`, the ground around home | 6,000 ticks, its own check | **unchanged (cannot be done as stated, see below)** |
| `GettingAroundGameTests` | (package 37) | `waitFor`, 4,000,000 | the shared `waitFor`, 40,000,000 |

**`FlatHomeGameTests` could not get the same treatment.** The no-mob test runs through `helper.onEachTick`, which
registers one callback for every tick up to the framework's limit, and the framework looks through all of them every
tick. With the limit at `LOAD_TICKS` its ten quiet minutes (12,000 ticks) ran for over 25 minutes in this branch's
first build (the server thread sat in `GameTestInfo.tickInternal`, iterating that map) and I stopped that build by
PID. A tick bound that never comes before the clock cannot go into that limit. Commit `5d6e7c2c` put its 6,000-tick
wait back and wrote down why (its `LOAD_LIMIT` comment; `ChunkWaits` says it is for waits in a sequence). It holds no
ticket of its own (the test player holds the ground), and its `restore` runs on every failure of its own. Giving it
the clock bound means restructuring the test (the ground wait as a `waitFor` step in a sequence, before the
`onEachTick` part, or a callback that schedules itself one tick on); that is left for the orchestrator.

Checked and not chunk waits: `SlashNamesGameTests` (waits for the command tree and a retry), `AresOsGameTests`,
`ModeInventoryGameTests`, `NetherHomeGameTests`, `ZoneSafetyGameTests` (fixed `runAtTickTime` steps, no chunks).
The client game tests are not server tests.

### 2. 36b's review NITs 2 and 3 (#252)

- **`LOOKS`** is `GateBuilder.LIGHT_MELTS`, now public (the constant `prepare` and `checkRemoval` use). No change to
  what the game does.
- **Places on the list**: `withinTown` returns the places it checked. `Fake.pass` records every place a logo stands
  in after each pass. At the end of each town test that uses `withinTown`, `allListed` checks that every place a
  logo of the test stood in was on its list:
  - first town test: the three logos it builds (all N0R0);
  - keeping test: every pass; N40L0 is allowed by name, as it stands on ground of its own (`fake.far`);
  - seal test: every pass.
  This checks more than `hub.logos()` at the very end, which is empty in all three tests by then (each takes its
  town down): a logo built and taken down half way through is caught too.
- **It found a gap at once** (second build, run, not from reading): after trust the seal test's Mail stands at N1L0,
  because his block left from Discord's logo keeps N0R0, and N1L0 was not on its list ("Fixture: logos stood at
  [N1L0], which withinTown did not check (it checked [N0L0, N0R0])"). The seal test's list now has N1L0, which
  `withinTown` confirms lies inside the held ground (commit `481852dc`). The 36b review's note that Mail takes N0R0
  after trust was wrong.
- **`SlashNamesGameTests.Fixture`** refuses, before it changes anything, when `TownKeeper.complete()`, as
  `GettingAroundGameTests.Host` does.

### 3. 39's review NITs (#258)

- **N1** (`GatePicture.mainColours`): when the largest group is under 1% (so every group is), no group is dropped and
  the smoothed-edge step is skipped; there are then more than a hundred groups, so the picture takes the
  many-coloured path. Before, `mains` was empty and `blocks` threw `ArrayIndexOutOfBoundsException`, which
  `GateBuilder.icon` caught (plain front). `CONVERTER` is not raised: the change draws a picture only for icons that
  threw before, and a logo whose picture changes is renewed by its picture hash anyway.
  - Test `GatePictureColoursTest.noiseWhoseColoursAreAllUnderOnePercentIsManyColoured`: 104 colours, every two more
    than 0.10 apart in Oklab (the fixture checks it), shuffled with a fixed seed over 96 × 96 pixels, 88 or 89 each
    (under 1%). It asserts 104 main colours, all under 1%, no exception, and more than six blocks.
  - Reachability: the review called this "practically unreachable". Groups are seeded more than 0.10 apart, so the
    path needs more than 100 colours that far apart in the sRGB gamut. A plain greedy pick finds 86; picking from the
    gamut's edge inwards finds 104, which is the fixture.
- **N2** HUB.md 3.6: "then the square root of `(0.5 × ΔL)² + Δa² + Δb²`".
- **N3** HUB.md 2.3 and 3.6, `mod/README.md`: a speck "is not drawn as a line: it shows only where it covers most of a
  cell".
- **N4** HUB.md 2.5 (the table row and the "first visit with converter 2" entry) and `mod/README.md`: the two
  exceptions (a place not loaded: drawn again when he comes near; a block of his in it: one place on, as with
  `hub rebuild`, his block stays).
- Also HUB.md 3.6 now says what N1 changed: when every group covers under 1%, none is dropped.
- **N5**:
  - `GatePictureTest.anEnlargedFigureIsCentredToTheHalfPixel`: an upright bar 10 × 29 on a plate gets a 35-pixel
    square whose left edge is at 30.5; asserts the square's middle is the bar's (48, 48.5) and the 12 × 12 cells are
    mirror-symmetric.
  - `GatePictureColoursTest.aColourOnUnderOnePercentIsNoMainColour`: a one-cell yellow square (0.7%) on red and blue
    halves; asserts two main colours, blocks {red wool, blue wool}, and red wool in the yellow square's cell.
  - `TownGameTests` seal test: after trust and the renewed seal, an older mod saves the world again; the world read
    back is frozen, and Chrome's logo is recorded as converter 1 (its only change). A pass while frozen says nothing
    and leaves converter 1; after `TownKeeper.trust` (what `/aresos hub trust` runs) the next pass says exactly "The
    logo of Chrome Browser was renewed.", records `CONVERTER` and keeps N0L0.

## Which tests fail without the change

- N1 test: run against a copy of the converter without the fallback (standalone `javac` in the scratchpad, the
  three converter classes only): `mainColours` gives 0 groups and `GatePicture.of` throws
  `ArrayIndexOutOfBoundsException: Index 0 out of bounds for length 0`. With the fallback: 104 groups, largest
  share 0.97%, 32 different blocks.
- Centring test: against a copy with converter 1's rounding (`Math.round`): the square's middle is 48.5, not 48, and
  the cells are not mirrored. Run, same way.
- 1% test: against a copy without the `removeIf`: three main colours (yellow `ffd800` too), blocks include yellow
  wool, and the square's cell is yellow wool. Run, same way.
- Seal test's N5 part: from reading. Without the converter comparison in `TownKeeper.changed()` the pass after
  trust would say nothing; without the freeze it would renew before trust.
- Point 2's `allListed`: run. It failed the seal test in build 2 (above) until N1L0 was listed.
- `Fixture`'s check: from reading; no server test makes the program list complete, so it cannot fail today.
- Point 1's timeouts: from reading; no run forced a timeout of the town, gate or flat-home waits. Package 37's
  forced-timeout check (in `GettingAroundGameTests`) now runs against the shared `waitFor`.

## Verified

All through `mod/dev/build.sh` from the worktree root, each after `free -g` showed 10 GiB available. No client test
changed, so `client-test.sh` did not run.

| Run | Code | Exit | Game tests | Gradle |
|---|---|---|---|---|
| Build 1 | point 1 only (with FlatHome changed) | stopped by me (PID of its game test JVM, exit 143) | the no-mob test ran over 25 min | BUILD FAILED in 27m 56s |
| Build 2 | points 1 to 3, FlatHome put back | 1 | seal test: "Fixture: logos stood at [N1L0], which withinTown did not check" | BUILD FAILED in 1m 42s |
| Build 3 | the final code (same files as `dd2ce9d2`) | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 2m 7s; 232 unit tests, 0 failed, 6 skipped (the Windows ones) |
| Final 1 | `dd2ce9d2` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 36s |
| Final 2 | `dd2ce9d2` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 37s |
| Final 3 | `dd2ce9d2` | 0 | All 98 required tests passed | BUILD SUCCESSFUL in 1m 35s |

The three new unit tests passed in build 3 (`anEnlargedFigureIsCentredToTheHalfPixel`,
`aColourOnUnderOnePercentIsNoMainColour`, `noiseWhoseColoursAreAllUnderOnePercentIsManyColoured`). The seal test's
new N5 part runs before its end check, so it passed in build 2 as well as in the four green runs.

## Not verified

- Whether the 2026-11-14 town flake is gone: it came once in several runs; three green runs cannot show it.
- The real tick rate of this laptop's test server was not measured here (the 70,000 a second is
  `GateGameTests`' note).

## JUDGMENT-CALL

- **The shared tick bound is 40,000,000, also for package 37's tests.** Kept at 4,000,000, the tick bound would come
  before the 120-second clock on an idle server (about 57 s at 70,000 ticks a second), against the brief's "never
  reached first". Raising it changes only how a stuck test fails (by the clock, after 120 s). Rejected: a second,
  larger constant for the town tests only (two bounds for one rule). Undoing it is one number.
- **`guarded` not reused in the town tests**: it is tied to the getting-around `Host`; the town tests' `inTown` and
  `keeping` already release on every way out of a step, and the shared `waitFor` covers the waits.
- **Point 2 checks every place a logo stood in, not only `hub.logos()` at the end**, because each of the three tests
  ends with its town taken down, which would make the end check empty.
- **N1 skips the smoothed-edge step too when nothing would be dropped**, so the many-coloured path is certain (with
  over a hundred groups the step could, in theory, remove all but a few).
