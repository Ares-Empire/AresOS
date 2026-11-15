# 36b: The town's tests own their town

Follow-up of package 36 (the town builds itself). Tests only, unless the cause is in the mod's own code; no change to what he sees.

**Builder:** one Claude agent on Opus 5.5, one step: finding the cause of a test failure and making the tests independent is debugging with a clear goal. **Review:** a fresh Claude reviewer on Opus 5.5.

## Why

On 2026-11-14 package 36's server test `TownGameTests.theTownKeepsInStepWithHisApps` failed once on the laptop at "A newcomer: []" (`TownGameTests.java`, around line 468: after `fake.change("keep-spotify", …)`, `fake.pass(server)` said nothing and built no logo). It passed on the same code right after. It ran before package 37's tests in that build, so it was not caused by them (board #249).

A failure that comes and goes in the server tests will also fail hosted `Mod` runs at random, and every mod package waits on those.

**The orchestrator's guess** (check it, don't assume it): `TownKeeper` registers its own tick (`ServerTickEvents.END_SERVER_TICK`), and it runs on the shared test server once any test has made `TownKeeper.complete` true (`MyAppsGame` calls `TownKeeper.listed()`). The test's own fake keeper and the production keeper may share state, through the per-server `TownKeeper.keeper(server)` (pictures, `said`, refused places, pending work) or through the server's one `HubData`. Then a production pass can act on the test's town between the test's steps. The test batches' order decides whether that happens.

## What to do

1. **Find the cause.**
   - Read `TownKeeper` (the tick, `keeper(server)`, `step`, `complete`, `listed`), the fake keeper in `TownGameTests` (`pass`), and every test that sets the program list complete (`MyAppsGame`, the `GettingAround` tests, package 34's My apps tests).
   - Make the failure happen on purpose if you can, for example by running a test that makes the list complete before the town tests.
   - Say in the report what caused it, with the evidence, or that you could not show it and why you believe what you fixed.
2. **Make the town's tests independent.** No production pass of the town may run on the test server while a test drives the town through its own keeper, and no state may leak between the test's keeper and the production keeper or between tests.
   - Prefer a fix in the tests: their own keeper instance, the production tick held off while a test owns the town, or `complete` restored after the tests that set it.
   - A change to production code is allowed only where the tests cannot reach the state otherwise. It must not change what the game does outside tests; say exactly what it is.
   - Check the same for package 37's `GettingAroundGameTests` (it reads `TownKeeper.complete()`) and package 34's My apps tests.
3. **Show it holds.** Run `mod/dev/build.sh` three times on the final code, all passing. If you found a way to make the failure happen on purpose, show it fails before the fix and passes after.

## Rules

- Worktree `~/AresOS-36b-town-tests`, branch `pkg/36b-town-test-isolation`, from main `b07b86a7`. Push with `git push origin pkg/36b-town-test-isolation`. Never merge, never push to main, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` (and `mod/dev/client-test.sh` only if you change something a client test covers). Never `./gradlew`, never `--force`. Another builder (package 39) may use Gradle: before `build.sh`, check that `free -g` shows at least 6 GiB available, otherwise wait.
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Use `gh` only for `gh pr create` at the end. The report text goes in `reviews/36b-town-test-isolation/PROGRESS.md` (Claude builders cannot create `REPORT.md`) and, shortly, in the pull request's description.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
