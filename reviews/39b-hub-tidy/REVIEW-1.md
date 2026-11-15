`3089333f4922975d8b09f36ddc0682d2ee464b4d` was reviewed read-only. I only read files and ran `git log`, `git diff` and `git show` in the worktree. I built nothing and ran no tests or programs. The code is the same as `dd2ce9d2`, the commit the builder's three final runs tested: only the report was added after it.

# Review 1: package 39b, "Hub tidy" (PR #65)

| Point | State | Reason |
|---|---|---|
| 1. The waits | OK | Every chunk wait in `TownGameTests` and `GateGameTests` is now a `ChunkWaits.waitFor`. Each one ends after 120 s, or after 40,000,000 of its own ticks if the server runs faster than about 333,000 ticks a second, and releases its own tickets. The framework limits sit above the sum of each test's waits. Package 37's code is moved unchanged apart from the tick bound. The clean-ups on timeout match the failure paths the tests already had. Leaving `FlatHomeGameTests` at 6,000 ticks is right for this package, but it stays open (S1). |
| 2. The fixtures | OK | `allListed` is sound for what it sees, and it found a real gap: Mail at N1L0 in the seal test. I traced that by hand and it is correct. It does not see places a pass only inspects, and in the first test it only restates the test's own list (NIT 1, NIT 2). Making `LIGHT_MELTS` public changes nothing in the game: it is a compile-time constant of 4. The `Fixture` check runs before anything changes. |
| 3. The converter, N1 | OK | The code is unchanged whenever the largest colour group covers at least 1%. When it covers less, the old code always threw, and the logo got a plain front. Only those icons change, and the picture hash renews their logos, so `CONVERTER` does not need raising (NIT 3). The output stays deterministic and bounded. The 104-colour icon has every group at 0.955% or 0.966%. |
| 4. The docs | OPEN (SHOULD) | N2, N3 and HUB.md's N1 sentence match the code. N4's two exceptions are correct, but "with two exceptions" leaves out a third: a logo whose take-down something of his refuses (S2). |
| 5. Tests | OK | By my reading, each of the three unit tests fails without its rule. The seal test's N5 part pins both the freeze and the converter clause of `changed()`. Nothing forces or releases chunks it does not own. |

## 1. The waits

- **Coverage.**
  - Every `thenWaitUntil` in the server tests is a `waitFor` (grep):
    - Town: `TownGameTests.java:171, :438, :440, :679, :862`;
    - Gate: `GateGameTests.java:257, :641`;
    - Getting around: the existing ones.
  - No other server test class holds chunks. `FlatHomeGameTests` waits through its test player.
- **Bounds.**
  - **Clock and tick bound.** At the 70,000 ticks a second recorded in `GateGameTests`, 40,000,000 ticks take about 570 s, so the 120 s clock comes first up to about 333,000 ticks a second.
  - **Framework limits** (all fit in an `int`):

    | Class | Limit | Waits per test |
    |---|---|---|
    | Town | 80,001,000 | the keeping test 2, the others 1 |
    | Gate | 40,001,000 | 1 each |
    | Getting around | 160,001,000 | the TOWN test 4, NO_TOWN 3 |

  - **When it ends.** On a server that keeps ticking, a wait that never completes ends after 120 s. A server that stops ticking runs no test code, as before; `ChunkWaits.java:31-35` says so.
- **Nothing grows with the limit.** None of the three classes calls `onEachTick`, `runAtTickTime` or `succeedWhen`, the only framework calls whose cost grows with `maxTicks`. `onEachTick` is used only in SlashNames (limits 600 and 300) and FlatHome (20,440), and neither changed.
- **Clean-ups on timeout.**
  - **`inTown` and every first wait.** Nothing has changed when they time out. The wait releases exactly the set the test held.
  - **The far-place wait** (`:440-443`) runs `clearZones`, then `letGo(fake, level, Set.of())`: the old hub record goes back and the far chunks are released. After that, the `finally` in `waitFor` releases `near`. This is exactly the failure path of `keeping` (`clearZones` + `letGo(near)`), with no double release and nothing left held. Like every failed run, it leaves its logo blocks and his planks on its own new ground.
  - **The gate site** releases the same `chunks()` that `Site.hold` took.
  - **The border test** removes its radius-0 ticket in the clean-up, as its own `finally` does.
- **Package 37.**
  - `chunks`, `hold`, `loaded` and `waitFor` are package 37's code byte for byte: radius-2 DRAGON tickets, a box from either corner, the same messages. The town's old `chunks` differed only when `from > to`, and no town box has that.
  - Passing runs are unchanged. A stuck wait now fails at 120 s by the clock, where before it failed by ticks after about 57 s on an idle server.
  - The forced-timeout check passes `LOAD_TICKS` only as the bound it must not reach (`GettingAroundGameTests.java:577`).
- **FlatHome.** The builder's reason holds: `onEachTick` registers one callback for every tick up to `maxTicks`. The test holds no ticket, and its own checks end before its limit (6,000 + 2,400 + 12,000 < 20,440). See S1 for what is still open.

## 2. The fixtures

- **The seal test's N1L0.** I traced the trusted pass:
  1. `blocked()` treats N0R0 as free, because the town's own Discord logo stands there (`TownKeeper.java:634`).
  2. Mail is planned at N0R0. Discord's logo comes down.
  3. Mail's build is refused, because his diamond is in the space.
  4. N0R0 goes into `refused`, and the next round puts Mail at N1L0.

  So 36b's note was wrong and the new list is complete. `withinTown` confirms that N1L0 lies inside the held box.
- **What `Fake.pass` records.** It records places from every record the test itself stores: frozen, refused, other rules, read back from files. Town tests are alone in their batch, and the game's own keeper is idle in the server run, so no other test's record can leak in.
- **`LOOKS`.** `GateBuilder.LIGHT_MELTS` is the largest reach of `prepare` and `checkRemoval`: the solid blocks and the doormat reach 2, the lights 4. Making it `public` does not change the bytecode of any game path.
- **`SlashNamesGameTests.Fixture`.** The check comes first in the constructor. A throw there leaves try-with-resources nothing to close, and it cannot fire in the server run.

## 3. The converter, N1

- **Only icons that threw change.**
  - With the largest group under 1%, every group is under 1%. The old code emptied `mains`, `nearestMain` returned 0 for each covered sample, and `blocks[main[i]]` (`GatePicture.java:257`) threw.
  - Whenever `steps` is non-empty, at least one sample is covered, so this always threw. The `steps.isEmpty()` path returns before the new branch.
  - `GateBuilder.icon` caught the exception, so the logo got a plain front.
  - A town logo with that plain front has the plain front's hash. `changed()` (`TownKeeper.java:671`) renews it once through the hash. Hand-built gates keep their blocks.
- **Deterministic:** the code uses a `TreeMap`, stable sorts and strict comparisons, and the new branch compares one double.
- **Bounded:** the code always samples 96 × 96, whatever the icon's size. Groups are seeded more than 0.10 apart, so there are at most about 100 to 200. More than 100 groups means the many-coloured path for certain. That path costs about 9,216 × groups distance checks plus one small array per cell. The O(g³) merge loop ran before too.
- **The test icon.**
  - It has no plate: the rim is noise, so at most one colour lies within 0.05 of the rim's median.
  - It gets one sample per pixel, and every pair of colours is more than 0.10 apart, checked with the same `oklab`. So the icon gives 104 groups that the rounds do not move and that `NEARLY` never merges.
  - Each colour covers 88 or 89 of 9,216 samples, under `enough` = 92.16.
  - All weights are equal, so the smoothed-edge step could never fire here. The test pins the fallback, not the skipped step. That is fine: the skip is a stated judgment call.

## 5. Tests that fail without their rule (from reading)

- **Centring.** Converter 1 used `Math.round(...)`, as `3d96d78e` shows. `round(30.5)` is 31, which puts the middle at 48.5, not 48, so the test fails. Floor or truncation fail too.
- **1% drop.** Without `removeIf`, yellow (64 samples, 0.69%) stays as a third main colour. It is not taken for a smoothed edge, because it does not lie between red and blue. The list assertion fails, and cell (1, 6) would be yellow wool.
- **N1.** Without the fallback, `mainColours` returns an empty list, and 104 ≠ 0.
- **Seal test, N5 part.**
  - While frozen, `keep` returns `Pass.NOTHING` before anything else (`TownKeeper.java:370-374`).
  - After trust, the converter is the logo's only difference. The picture hash, name and short name are those the trusted pass recorded and the save at `:1130` wrote. So the exact one-line check pins the converter clause. Without the freeze the first check fails; without the clause the second fails.
  - It all runs in one tick, so no autosave falls in between.
  - The later steps (backup, moved away, empty) still hold, because the save at `:1149` seals the two-logo town again.

## Findings

**S1 (SHOULD): the no-mob test still has a tick-counted ground wait.**
- Where:
  - `FlatHomeGameTests.java:71-77` (`LOAD_LIMIT` 6,000), `:385` and `:428-436`;
  - `reviews/39b-hub-tidy/REPORT.md:43-45`.
- Scenario: the same kind of wait as #257.
  - Under load the ground took about 800 ticks (the `CONTROL_LIMIT` note), and 6,000 is about seven times that.
  - But #257 shows ticks can run at 50,000 a second while chunk work is starved. Then the test fails with "Fixture: the ground around home did not load within 6000 ticks", a failure that comes and goes.
- Why not a FIX:
  - The diff only changes a comment.
  - The test holds no ticket: `restore` removes its player on every failure of its own.
  - Its own checks end before its framework limit.
- **The report's first suggested restructure does not work.** If the ground wait becomes a sequence step and is followed by `onEachTick`, `onEachTick` still registers a callback for every tick from then up to a limit of 40,000,000 or more.
- What would work: replace `onEachTick` and then raise the limit, in one of two ways:
  - make the ground wait, the control and the quiet ten minutes sequence steps (`thenWaitUntil`, throwing `GameTestAssertException` until each is done);
  - or use a runnable that registers itself again with `runAtTickTime(tick + 1)`.
- Put it on the board for the hub topic.

**S2 (SHOULD): "with two exceptions" leaves out a third.**
- Where:
  - docs: `docs/design/HUB.md:44`, `:243`, `mod/README.md:741-746`;
  - code: `TownKeeper.java:466-476`.
- Scenario:
  1. His torch stands on Chrome's doormat, the keeping test's own case (`TownGameTests.java:587-596`).
  2. On the first visit with converter 2, `changed()` is true, but `Town.remove` is refused, and not because the place is unloaded.
  3. The pass says once "The logo of Chrome stays as it was: … The town tries again later."
  4. The logo keeps converter 1's blocks until he takes the torch away.
- HUB.md says every logo is drawn again in one pass, apart from the other two. The code's own `rebuild` javadoc (`TownKeeper.java:354`) states this case for `hub rebuild`.
- Also, "a block of his in it" is narrower than the code. Anything of his in the logo's place refuses the rebuild and moves the logo on: the layer in front, the sign's space above, or the way in.
- Why not a FIX:
  - Both exceptions are the brief's own N4 text, taken from 39's review, and what they say is true.
  - The game says the third case in chat when it happens.
  - HUB.md 2.5 already says elsewhere (`:53`) that a logo with his torch on its doormat cannot come down.
- Fix: add one clause in the three places: "and a logo that something of his rests on (a torch on its doormat) stays as it was until he takes that away, said once". Optionally, change "a block of his in it" to "something of his in its place".

**NIT 1: the first town test's `allListed` only restates its own list.**
- Where: `TownGameTests.java:327`.
- `logo`, `signed` and `reused` are all built at `place` (N0R0), so the set can never hold another place.
- Scenario: a later edit adds a build or check at W0R0 in that test. It goes unnoticed unless the same edit also adds W0R0 to that line.
- It is no weaker than the brief's check, since `hub.logos()` is empty at the end. Hardening: send `Town.build` and `Town.check` in this test through one helper that records the place.

**NIT 2: `allListed` sees where logos stand, not where a pass looks.**
- Where:
  - `TownGameTests.java:406-414`;
  - `TownKeeper.java:632-645`: `blocked()` calls `Town.check`;
  - `TownKeeper.java:486-499`: a refused build.
- Scenario:
  1. A later step puts his block in an unlisted place P, so an app goes on past it.
  2. The pass inspected P's surroundings, but no logo stood there, so `stood` misses it.
  3. In a run where P's chunk is not loaded, `blocked()` reads `NotLoaded` as free. The app is planned at P and its build waits: 36b's failure mode again, about 1 run in 16.
  4. `allListed` still passes.
- Today every inspected place is on the lists (the seal test's N0R0 is listed).
- Hardening: also count the places named in "… is blocked by something of yours" lines and in refused builds.

**NIT 3: the `CONVERTER` javadoc now reads as if N1 should have raised it.**
- Where: `GatePicture.java:16-21`.
- "Raise it with every change that can draw a different picture": N1 can (a plain front becomes many-coloured), and rightly does not raise it.
- Fix: one sentence there. A change whose new pictures appear only for logos the picture hash renews anyway (N1: icons that used to throw) does not raise it. The next converter change then neither copies nor "corrects" this.

**NIT 4: one sentence in HUB.md 2.3 now has two colons.**
- Where: `docs/design/HUB.md:188`.
- It reads "…is not drawn as a line: it shows only where it covers most of a cell (…; section 3.6): none of the 24 test icons…".
- Split it after the parenthesis.

VERDICT: SAFE with documented known limits
