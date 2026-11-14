# 39b: Hub tidy (test waits, test fixtures, converter docs)

Follow-up of packages 36, 36b and 39. It collects what their reviews and builds left: the board's #257 (a town test that times out waiting for its chunks), #252 (36b's review NITs 2 and 3) and #258 (39's review NITs). It changes no rule of the town or the converter, and nothing he sees except one safe fallback (point 3).

**Builder:** one Claude agent on Opus 5.5, one step: every item below is stated, and none is a design question. **Review:** a fresh Claude reviewer on Opus 5.5.

## 1. The town's tests wait like package 37's (#257)

- On 2026-11-14 `TownGameTests`' seal test (`the_town_trusts_its_records_only_while_the_world_was_saved_with_them`) failed once at "The town's chunks are not loaded yet on tick 400002", before its body ran. The same code then passed. `TownGameTests.LOAD_TICKS` is 400,000; the test server runs through ticks without pause while tests wait, so that can be a few seconds when the laptop is busy.
- Give `TownGameTests`' waits what package 37 gave `GettingAroundGameTests` (its review fixes 1 and 2): a tick bound large enough never to be reached first, a wall-clock bound (120 seconds) checked by the test's own steps, the tickets released however a wait ends, and the framework's own limit above both. Read `GettingAroundGameTests`' `waitFor` and `guarded` and reuse them rather than copying them, if that stays simple.
- Check every other server test class that waits for chunks with a fixed tick count, and treat it the same way. List them in the report.

## 2. 36b's review NITs 2 and 3 (#252)

- `withinTown` (`TownGameTests`) relies on hand-kept lists of places and on `LOOKS = 4` copied from `GateBuilder`. At the end of each town test that uses it, check that every place in `hub.logos()` was on its list. Take `LOOKS` from one constant that `GateBuilder` also uses, or check in a unit test that the two agree.
- `SlashNamesGameTests.Fixture` creates a host without the `!TownKeeper.complete()` check that `GettingAroundGameTests.Host` has. Add the same check.

## 3. 39's review NITs (#258, `reviews/39-logo-colours/REVIEW-1.md`)

- **N1:** when the 1% filter (`GatePicture.java` around line 373) removes every colour group, keep the groups and take the many-coloured path, instead of throwing and falling back to a plain front. Add a unit test with such an icon (noise of many near-equal colours).
- **N2:** HUB.md 3.6 states the colour distance as a squared value but compares square roots. Write "the square root of …" so the numbers fit.
- **N3:** "a speck smaller than a cell is left out" (HUB.md 2.x and 3.6, `mod/README.md`): write what the code does: a speck is not drawn as a line; it shows only where it covers most of a cell.
- **N4:** HUB.md 2.5 and `mod/README.md` say a logo drawn by older rules is "drawn again where it stands, in one pass". Add the two exceptions: a logo whose place is not loaded is renewed when he comes near, and a logo with a block of his in it moves one place on (as with `hub rebuild`; his block stays).
- **N5:** unit tests that fail without the centring of the enlarged square to the half pixel and without the 1% drop. A server test that a logo of converter 1 in a frozen town is renewed after `/aresos hub trust` (the report says so; nothing tests it).

## Verification

- `mod/dev/build.sh` three times on the final code, all passing; say if any run fails, with its line.
- `mod/dev/client-test.sh` only if a client test changes.
- The report (`reviews/39b-hub-tidy/PROGRESS.md`, renamed by the orchestrator): per item what changed, which tests fail without it (say which claims are from reading), what ran.

## Rules

- Worktree `~/AresOS-39b-hub-tidy`, branch `pkg/39b-hub-tidy`, from main `3d96d78e`. Push with `git push origin pkg/39b-hub-tidy`. Never merge, never push to main, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` (and `mod/dev/client-test.sh` if needed). Never `./gradlew`, never `--force`. Before `build.sh`, check that `free -g` shows at least 6 GiB available.
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- `gh` only for `gh pr create` at the end.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
