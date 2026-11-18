# Package 54: review fix 2

## Done

- Merged `origin/main` through `7417c19a` before editing (merge commit `8f6935eb`). This follow-up stays on
  `pkg/54-town-one-line` and updates PR #108.
- Implementation commits: `219b0485` (keeper and 48-row table), `ec0a7225` (client timing assertion),
  `345ba61d` (client-test shutdown repair).
- **Cause:** a pending replacement retained only `MOVED` or `RENEWED`. A renewal could therefore complete at a
  different place while still saying it was renewed. Cancellation discarded that marker even when the old logo
  had already come down, losing the removal announcement.
- **`TownKeeper`:** one replacement record retains the app, starting operation, original place and successful
  removal. Retries preserve it. Completion compares the actual place with the original: the same place means
  `RENEWED`; another place means `MOVED`, including a renewal whose category or obstruction changed its destination.
  A replacement is never counted as a fresh build. A refused removal leaves the old logo standing and clears the
  attempt; ordinary removal handles any subsequent cancellation. Cancelling after removal emits one `DOWN` line
  before discarding the replacement, including when the app record itself disappeared.
- **Keeper coverage:** a table of 48 keeper cases crosses renewal/move, original/different/obstructed destination,
  completion/cancellation/return after processed cancellation/return before a complete retry, and removal succeeded/
  removal still waiting. Every row repeats pending and terminal passes. It checks exactly one ordinary terminal line
  per operation, the expected kind and place, WAY lines and preservation of the obstruction. It covers all three
  cancellation reasons (My apps, uninstalled, absent app record) and uses its own environment, fixture and chunk tickets.
- **Return semantics:** a processed cancellation ends the old operation with one take-down; a later return is a fresh
  build. An app returning before a complete retry continues the same replacement, including across an incomplete
  catalogue pass. If removal never succeeded and the requested move is withdrawn, the original logo stays silently.
- **Client timing:** the first-start assertion now checks delivery from completion (0–5 server ticks) and measures
  the 200-tick deadline from the first actual build, retaining the earlier loading and expiry scenarios.
- **Test shutdown repair:** the second full client attempt exposed an existing Fabric barrier deadlock in the
  mounted-rejoin test, before package 54 ran. `IntegratedServer.halt` blocks on an initial server task before Fabric's
  later disconnect busy-wait hook can advance its test barrier. A client-test-only mixin submits that same task and
  invokes Fabric's existing task pump until completion, then joins it so failures remain visible. Server-thread and
  non-test calls retain the original execution. No assertion, case or screenshot ordering changed.
- No production saved-data format, deadline policy or staging change in this follow-up.

## Verified

- First full `mod/dev/build.sh --rerun-tasks`: `BUILD SUCCESSFUL in 2m 37s`, exit 0; all 17 tasks executed.
  All **106 required server game tests passed**, including all **48 replacement-table rows** and the previous
  keeper regressions. JUnit XML: **285 tests, 0 failures, 0 errors, 6 existing Windows-only skips** (279 passed).
- First full `mod/dev/client-test.sh`: `BUILD SUCCESSFUL in 12m 23s`, exit 0. The script reported
  `Client tests ended with exit code 0 after 12 min 25 s`, NVIDIA RTX 4060, headless. Controlled first start:
  **9 at tick 3**, **40 at tick 103**, sole complete announcement at **tick 104**. New home (Flat): **24 at
  tick 2**, **40 at tick 102**, exactly one full line. Staging built zero logos. Controlled expiry: **9 at tick 2**,
  partial announcement at **tick 202**, **31 later builds at tick 302** reported as a change. All three scenarios
  watched another 220 ticks for duplicates.
- Inspected the first run's three screenshots: [first start](screenshots/0092_54-first-start.png),
  [New home](screenshots/0093_54-new-home-flat.png), [expiry and later change](screenshots/0094_54-first-build-expired.png).
- Second full `mod/dev/build.sh --rerun-tasks`, after the test-only shutdown repair: `BUILD SUCCESSFUL in
  2m 34s`, exit 0; **17/17 tasks executed**. Again **106 required server tests passed**, including all **48 table
  rows**; JUnit XML again recorded **285 tests, 0 failures, 0 errors, 6 Windows-only skips** (279 passed).
  `sha256sum -c .work/pkg54/fix2/build-1-jar.sha256` printed `mod/build/libs/aresos-0.1.0.jar: OK`.
- Hosted checks on `ec0a7225`: [Mod](https://github.com/Ares-Empire/AresOS/actions/runs/44292390965) and
  [Repo privacy](https://github.com/Ares-Empire/AresOS/actions/runs/44292390997) both completed with `success`.
  These preceded the client-test-only shutdown repair; both local full builds above passed.
- First full client run with the shutdown repair (`mod/dev/client-test.sh`, attempt 3):
  `BUILD SUCCESSFUL in 12m 24s`, exit 0; script reported `exit code 0 after 12 min 25 s`, NVIDIA, headless.
  Both mounted-rejoin cases and the missing-home-data regression passed. First start again built **9 at tick 3**,
  completed **40 at tick 103**, announced at **tick 104**; New home completed at **tick 102** with one full line.
  Expiry again announced nine at **tick 202** and reported the remaining 31 after building at **tick 302**.
  Inspected all three screenshots again. This is the first complete passing run with the final test-harness code.
- Second full client run with the unchanged shutdown repair (`mod/dev/client-test.sh`, attempt 4):
  `BUILD SUCCESSFUL in 12m 21s`, exit 0; script reported `exit code 0 after 12 min 22 s`, again headless on NVIDIA.
  Both mounted-rejoin cases passed again. Controlled first start again built **9 at tick 3**, completed **40 at
  tick 103**, and delivered its one full line at **tick 104**. New home again built **24 at tick 2**, completed **40
  at tick 102**, and said one full line. Expiry again said nine at **tick 202**, then 31 later builds at **tick 302**
  as a change. The 220-tick duplicate observation windows passed in every scenario. Both complete final client
  suites passed on the same production jar and unchanged implementation/test sources.
- Inspected all three final screenshots again. Restored **57** other tracked review files and removed **25**
  newly numbered PNGs outside package 54 after the final run; only this package's three pictures remain changed.
- Hosted checks including the test-only shutdown repair on `345ba61d`:
  [Mod](https://github.com/Ares-Empire/AresOS/actions/runs/44300568276) and
  [Repo privacy](https://github.com/Ares-Empire/AresOS/actions/runs/44300568328) both completed with `success`.
- Final `sha256sum -c .work/pkg54/fix2/build-1-jar.sha256` again printed `mod/build/libs/aresos-0.1.0.jar: OK`.
  Production jar: `e66257e0d977b4334ea6eeab4b305520d02835247d00f59163890e053be21647`.
- Closing artifact check (`rg --files --hidden --no-ignore .work`, then file sizes): **no file over 500 MB** remains
  in `.work/`. No large download or extracted image was made. The scripts completed their scope cleanup, and the
  final process check found **zero Java processes referring to this worktree**. No Gradle daemon-control command was used.
- `git diff --check` passed. `bash .work/pkg54/repo-privacy.sh` printed
  `No file holds a home path with a real user name.`, exit 0.

### Interrupted verification attempts

- The second-build waiting shell exited 143 before any Gradle invocation (no build log was created). It was
  rescheduled sequentially; it is not passing build evidence.
- Second full `mod/dev/client-test.sh`: stopped only this script with TERM, exit 143, after its progress halted
  during `NetherHomeClientGameTest.testMountedRejoin`. `jcmd 1119145 Thread.print` captured the render thread
  blocked in `IntegratedServer.halt -> executeBlocking`, while the server and test thread waited at Fabric's phaser.
  The script printed `Client tests ended with exit code 143 after 10 min 28 s`. This attempt did not reach package 54
  and is not passing evidence. Its scopes were cleaned up by the script. The repair changes the shutdown mechanism,
  with every assertion retained.
- An intermediate screenshot cleanup stopped at a nested screenshot directory. The completed run's package 54
  images were already preserved; other packages' tracked files had been restored. Final cleanup handles all generated
  PNGs, including nested screenshot and seed folders.

## Not verified

- The home-switch tests still use `HomeSwitch.closeFromTestTasksForTests` to cross Fabric's close-world barrier.
  The real creation, provisioning, save, rename, reopen and town scheduler paths run.
- The owner's real desktop, real catalogue and subjective waiting experience require the owner in the game.

## JUDGMENT-CALL

- None beyond the explicit replacement and cancellation rules in review fix 2. The existing 200-tick deadline
  and staging hold remain as authorized by review fix 1.

## PLAN-GAP

- The full-suite repeat exposed an existing shutdown race in Fabric's client test harness. The required repeat
  cannot count a hung run as passing; the test-only repair above closes the missing barrier pump before rerunning.

## Rules met

- Both full builds used `mod/dev/build.sh --rerun-tasks` after the required
  `/usr/bin/flock -n ~/.cache/aresos-dev/client-test.lock true` preflight; busy preflights waited with one-minute
  checks. Each build held that lock for its duration. The client scripts took the same lock themselves, so the
  queued repeat could not overlap the active run. No exit 75 or `--force` was needed.
- Two full builds and two full client runs with the repaired shutdown passed. The earlier hung run is recorded
  above and is not counted as passing. Tests and assertions were retained.
- All work remains on `pkg/54-town-one-line` and PR #108. No new PR, PR merge, push to main, `--no-verify`, or
  Gradle `--stop`. Each new commit has the brief's required model trailer.

## Open questions

- None.

---

The following reports retain the earlier implementation's evidence; they do not verify review fix 2.

# Package 54: review fix 1

Implementation commit: `6992a29d`.

## Done

- Merged `origin/main` through `fd9cb695` before editing (merge commit `d711bdaa`).
- **Cause confirmed:** the old keeper's `cameDown` set belonged to one pass. A category change could take down a
  standing logo with the wanted IDs unchanged, defer its destination, then count its replacement as a new build.
  Since no `MOVED` line existed in the removal pass, first-build collection continued and could count 41 for 40 apps.
- **`TownKeeper` / `TownLines`:** signal a real move or renewal when it begins, before attempting removal. That signal
  ends first-build collection even without a completed change line. Keep `MOVED` / `RENEWED` per app across rounds
  and later passes until the replacement is built; discard entries for apps no longer wanted. Commands retain their
  existing messages. No saved-data or world-format change.
- **First-build deadline:** 200 server ticks (about 10 seconds), starting with the first pass that actually builds.
  Say the complete total immediately when all original work is ready; otherwise expiry says what has been built,
  and later passes use the existing ordinary-change messages. Empty attempts before any logo is built do not start
  the clock. `WAY` lines and rebuild's own line retain their rules.
- **Regressions:** a keeper test with 40 unchanged IDs builds 32, changes one app's catalogue category from Network
  to Game, defers its new place, and expects the 32-logo first line followed by one change line for eight builds and
  one move. It also delays a renewal after removal and checks that it remains a renewal. The test has its own batch
  and owns all chunk tickets it releases. Its fixture resets its own isolated ground and text displays before a run
  and removes its logos at teardown, so a kept test world or an interrupted run cannot obstruct the next run.
- **Controlled client loading:** the first-start case delays southern places until tick 100, checks an early partial
  build and exactly one full line by tick 200, and retains the real New home (Flat) scenario. An additional New home
  keeps some places unavailable past the deadline, checks the partial line 200 ticks after building started, then
  releases them and checks the later change line. A test-only mixin can delay loading checks; it never makes an
  actually unloaded place appear loaded. Original screenshot order is preserved; the expiry picture is appended.

## Verified

- Initial keeper-corrected `mod/dev/build.sh` (before the fixture cleanup below): `BUILD SUCCESSFUL in 3m 43s`,
  exit 0. All **105 required server game tests passed**. JUnit XML: **285 tests, 0 failures, 0 errors, 6 skipped**
  (279 passed); the skips are the existing
  Windows-only catalogue cases. All **13** `TownFirstBuildTest` cases passed.
- First full `mod/dev/client-test.sh`: `BUILD SUCCESSFUL in 12m 25s`, exit 0; script reported `Client tests ended
  with exit code 0 after 12 min 27 s`, NVIDIA RTX 4060, headless. The controlled first start built **9 at tick 3**,
  completed **40 at tick 103**, and received its sole complete line at **tick 104**, before tick 200. Ordinary New
  home completed at **tick 102** with exactly one 40-logo line and staging built nothing. The expiry case built
  **9 at tick 2**, received the partial nine-logo line at **tick 202**, then built the remaining **31 at tick 302**
  and said one ordinary change line. Each arrival remained under observation for another 220 ticks.
- Inspected all three screenshots from this run: [first start](screenshots/0092_54-first-start.png),
  [New home](screenshots/0093_54-new-home-flat.png), and [expiry then later change](screenshots/0094_54-first-build-expired.png).
  The first two show one complete 40-logo announcement; the last shows the nine-logo first line and the later
  31-logo change line.
- After the initial fixture cleanup (before separating its location), full `mod/dev/build.sh --rerun-tasks`:
  `BUILD SUCCESSFUL in 2m 25s`, exit 0,
  **17/17 tasks executed**. All **105 required server tests passed**; JUnit XML again recorded **285 tests,
  0 failures, 0 errors, 6 skipped**. `sha256sum -c .work/pkg54/review-fix-jar-1.sha256` printed
  `mod/build/libs/aresos-0.1.0.jar: OK`: production bytes match the build used by the first successful client run.
- After fixture separation to the unused location, full `mod/dev/build.sh --rerun-tasks`: `BUILD SUCCESSFUL in
  2m 34s`, exit 0, **17/17 tasks executed**. All **105 required server tests passed**; JUnit XML again recorded
  **285 tests, 0 failures, 0 errors, 6 skipped**. The production jar hash check again printed `OK`.
- Repeated the same full `mod/dev/build.sh --rerun-tasks` on the unchanged final source and kept world:
  `BUILD SUCCESSFUL in 2m 28s`, exit 0, **17/17 tasks executed**. Again **105 required server tests passed**;
  JUnit XML again recorded **285 tests, 0 failures, 0 errors, 6 skipped**, including all 13 first-build unit cases.
  `sha256sum -c .work/pkg54/review-fix-jar-1.sha256` again printed `mod/build/libs/aresos-0.1.0.jar: OK`.
  The reproducible production jar is `cfa0492b870e43f6e2063016e3ce5edf3dca2771f081275eee1c306c5bc6d8b3`.
- Second full `mod/dev/client-test.sh`: `BUILD SUCCESSFUL in 12m 22s`, exit 0; script reported `Client tests ended
  with exit code 0 after 12 min 24 s`, again headless on NVIDIA. First start again built **9 at tick 3**, completed
  **40 at tick 103**, and received its one full line at **tick 104**. New home built **24 at tick 2**, completed
  **40 at tick 102**, and said one complete line. Staging built no logos. Expiry again announced **9 at tick 202**
  after building began at **tick 2**, then built **31 at tick 302** and said one ordinary change line. All three
  scenarios again watched another 220 ticks with exactly the expected messages. The client code and production
  jar are unchanged between the two successful client runs; the intervening corrections were server-fixture setup.
- Inspected all three final screenshots again. Restored the other packages' tracked pictures and removed their
  newly numbered pictures after both client runs; only this package's three pictures remain changed or added.
- `git diff --check` and `git diff --cached --check` passed. `bash .work/pkg54/repo-privacy.sh` (the workflow's
  exact shell block, with its scratch output redirected into this worktree) printed
  `No file holds a home path with a real user name.`, exit 0.
- Closing artifact check, using `rg --files --hidden --no-ignore .work` and file sizes: **no file over 500 MB**
  remains in `.work/`. It contains diagnostic logs, small verification scratch files and screenshots. No large
  download or extracted image was made. The scripts finished their scope cleanup successfully; the final process
  check found no Java process referring to this worktree. No `--force` or Gradle daemon-control command was used.

### Interrupted and failing attempts in this follow-up

- Initial `mod/dev/build.sh`: mistakenly started after the required preflight lock check returned 1. Stopped only
  this build script promptly with TERM (exit 143); its scope cleanup left no worktree Java process. It had reached
  server startup. This was an orchestration error and is not passing evidence; it briefly overlapped the held lock.
  Subsequent builds check the lock, wait in one-minute intervals when busy, and hold it for the duration of the build.
- Next `mod/dev/build.sh`, after the lock cleared: `BUILD FAILED in 1m 5s`, exit 1. The unchanged existing rebuild
  regression expected `5 logos built again, 1 moved`, but the initial replacement tracking said six renewals.
  Corrected the keeper: a replacement refused by an actual obstruction must move on and keeps `MOVED`; a renewal
  merely waiting for loading retains `RENEWED`. No assertion was weakened.
- First repeated `mod/dev/build.sh --rerun-tasks`: `BUILD FAILED in 1m 23s`, exit 1. The new regression's first
  partial build saw saved-world fixture blocks as obstructions and moved apps away from their saved places.
  Inspection also found that its initial 23,000-block offset was already used by a navigation fixture. Moved it to
  the unused 35,000-block offset and fixed setup/teardown to reset only its isolated, ticketed ground and clean up
  its logos. The first 32-logo assertion stays intact. Production and client test code did not change for this
  fixture correction.

## Not verified

- The owner's real desktop, real app catalogue and how the ten-second bound feels in normal use. All client checks
  use development saves and the scripts' isolated headless compositor.
- As in the original run, the home-switch test uses `HomeSwitch.closeFromTestTasksForTests` to cross Fabric's
  close-world barrier. The real create, provision, save, rename, reopen and town scheduler paths still run.

## JUDGMENT-CALL

- No new owner decision. The lead's decision in `briefs/54-review-fix-1.md` explicitly replaces the original
  "first start must not get slower" rule with a maximum of 200 ticks from the first actual build. The earlier
  600-tick choice recorded in the historical report below is superseded. This remains a constant and per-server
  state; changing it later needs no migration.

## PLAN-GAP

- No new gap beyond the two findings addressed by this follow-up. The original staging-world cause and its hold
  remain unchanged.

## Rules met

- The current first-start rule is **one complete line as soon as ready, with a 200-tick bound from the first build**,
  replacing the original brief's "no slower" line as authorized on 2026-11-18.
- Builds used the required `/usr/bin/flock -n ~/.cache/aresos-dev/client-test.lock true` preflight. Busy locks were
  checked in one-minute intervals; the build also held that lock throughout its run. The interrupted initial
  preflight mistake is recorded above. Two final full builds and two full client suites passed.
- Work stays on `pkg/54-town-one-line` and PR #108. No merge of the PR, push to main, new PR or `--no-verify`.

## Open questions

- None.

---

The following is the original implementation report and its historical verification, before REVIEW-1.
Its 600-tick policy and original test counts are superseded by the follow-up above.

# Package 54: the town arrives in one line after New home

## Done

- **Cause, reproduced before changing the rule:** `TownKeeper.keep` decided `first` from whether any logo stood
  before **that pass**. A build refused with `GateBuilder.NotLoaded` set `pending`; the next scheduled pass, 100
  ticks later, saw standing logos and spoke as a change. `GateBuilder.loaded` checks both chunks and their entities:
  an unloaded place is deliberately deferred so the build can check entities in its way. The exact first-pass
  count depends on loading, rather than being fixed at 32.
- **An additional cause in New home:** the hidden staging world could run the town before `HomeSwitch` closed
  it. Its partial logos were saved, but its `TownKeeper` (and any first-build state) ended with that server. The
  reopened home then started with an existing, partial town. This is more than the brief's guess about farther
  chunks after opening. In the reproduction the staging server built **24** logos at tick 2; the reopened server
  started with those 24 at tick 1 and built the other **16** at tick 102. The first start also reproduced the general
  race: **18** at tick 3, then **22** at tick 103. Every missing place observed at the partial build refused with
  `NotLoaded`. The observation does not distinguish chunk generation from entity loading.
- **`HomeSwitch` / `TownKeeper`:** mark the staging folder before its server starts. Its town does no work;
  provisioning still builds the flat hub. Release the hold after that server closes, on the promotion and recovery
  paths. The town starts in the actual reopened home, with its keeper and announcements intact. No save-format change.
- **`TownLines.FirstBuild` / `TownKeeper`:** collect only the first build's `BUILT` lines across passes, then say one
  total as soon as its places and pictures are ready. Bound the collection at **600 server ticks** (about 30 seconds);
  the server tick checks expiry even while a picture is still being read. A complete first pass speaks immediately,
  with no new delay or extra pass. `WAY` lines speak immediately and individually. Completion, expiry, a changed
  wanted-app list, an ordinary change, or a move/swap ends the collection; rebuild keeps its own single line.
- **Tests:** 12 unit cases cover immediate first builds, two passes, empty retries, `WAY` in both passes, the bound
  with and without a following pass, changes during and after the first build, rebuild, move/swap and an existing
  town. The server keeping test now checks the deferred first total and its flush when a genuinely new app arrives.
  `TownArrivalClientGameTest`, appended to the suite, uses the rig's same proportions: 6 Internet, 3 Games,
  3 Work & Media, 28 System & Tools. It drives first start and New home (Flat) with a connected fake helper,
  observes the scheduler without forcing chunks, checks that staging builds no logos, checks 40 standing logos and
  exactly one complete first-build line each time, and waits two more retry intervals to catch late duplicate lines.
- **Verification setup:** shorten the unit temporary root from `build/tmp/unit-tests` to `build/tmp/t`. The existing
  lifecycle gate test's longest socket path could reach 108 bytes in this worktree, which Linux refuses. The shorter
  root reduces that to 99 bytes; the test and its assertions are unchanged, and its temporary files stay in the repo.
- `git fetch origin` at the start found `origin/main` already an ancestor of this branch (ahead 1, behind 0);
  there was nothing to merge.

## Verified

- Final-source `mod/dev/build.sh`: `BUILD SUCCESSFUL in 2m 18s`, exit 0. All 104 required server game tests passed.
  JUnit XML: **284 tests, 0 failures, 0 errors, 6 skipped** (278 passed). The six skips are the existing Windows-only
  catalogue tests on Linux. All 12 `TownFirstBuildTest` cases passed.
- First full `mod/dev/client-test.sh`: `BUILD SUCCESSFUL in 11m 56s`, exit 0; script: `Client tests ended with
  exit code 0 after 11 min 58 s`, NVIDIA RTX 4060 in its own headless compositor. Existing town, rebuild, navigation,
  swaps, home-switch recovery and save-during-switch client checks passed as well as the new test. Its observations:
  - first start: 40 logos at tick **3**, with the complete line in that pass;
  - staging: **0** logos;
  - reopened New home: **24** at tick **2**, **40** at tick **102**, with exactly one `The town is built: 40 logos.
    /apps lists them.` line, and no `The town changed` line;
  - the test then watched another **220 ticks** on each arrival, without duplicate town lines.
- Screenshots, inspected after the run: [first start](screenshots/0092_54-first-start.png) and
  [New home (Flat)](screenshots/0093_54-new-home-flat.png). Both show the one complete town line in the chat.
- Repeated full `mod/dev/build.sh --rerun-tasks`: `BUILD SUCCESSFUL in 2m 14s`, exit 0, **17/17 tasks executed**.
  Again all 104 server tests passed; JUnit XML again recorded **284 tests, 0 failures, 0 errors, 6 skipped**.
- Second full `mod/dev/client-test.sh`: `BUILD SUCCESSFUL in 11m 54s`, exit 0; script: `Client tests ended with
  exit code 0 after 11 min 56 s`, again on the NVIDIA GPU headlessly. The same observations held: first start's
  40-logo line in tick **3**, staging **0**, reopened New home **24** in tick **2** then **40** in tick **102**,
  exactly one complete first-build line on each arrival, no town-changed line and no late duplicates.
- The full client suite ran twice to meet `AGENTS.md`'s repeat requirement. No `--force`, Gradle daemon-control
  command, or busy retry was needed. The scripts cleaned up their own scopes; no Java process referring to this
  worktree remained afterwards.
- Restored all other packages' tracked pictures and removed the new numbered pictures the suite left there.
  Only package 54's two screenshots are included. `git diff --check` passed.
- `bash .work/pkg54/repo-privacy.sh`: the exact `Repo privacy` workflow shell block, with only its scratch output
  redirected into this worktree, printed `No file holds a home path with a real user name.`, exit 0.
- Closing artifact check: no file over **500 MB** remains in `.work/`. It holds diagnostic logs, the earlier
  diagnostic screenshots and small PR/verification scratch files; no large download or extracted image.

### Diagnostic runs, before the fix

- `mod/dev/client-test.sh -Dfabric.client.gametest.testClass=dev.aresos.test.TownArrivalClientGameTest`: the installed
  Fabric runner does not implement that class filter, so it started the full suite. Stopped only this script with
  TERM, exit 143. This is not a passing run.
- `mod/dev/client-test.sh`, temporarily registering only the new client test for diagnosis: `BUILD FAILED in 38s`,
  exit 1. The assertion caught first start saying `The town is built: 18 logos. /apps lists them.` followed by
  `The town changed: 22 logos built. /apps lists where your apps stand.`
- The same focused command, with both paths observed before asserting: `BUILD FAILED in 58s`, exit 1. First start
  again said 18 then 22. New home said `The town is built: 24 logos. /apps lists them.` in staging, then
  `The town changed: 16 logos built. /apps lists where your apps stand.` after reopening. The full entrypoint list
  was restored afterwards. These failures establish the cause; they are not counted as full-suite evidence.
- First `mod/dev/build.sh` attempt: all 104 server tests passed, then `BUILD FAILED in 1m 55s`: `compileTestJava` failed because a unit-test
  edit made during the build referenced `expire` after the main classes had already compiled without that helper.
  Reran with the source held unchanged.
- Second `mod/dev/build.sh`: all 104 server tests and all 12 new unit tests passed; `284 tests completed, 1 failed,
  6 skipped`, `BUILD FAILED in 2m 30s`. The failure was `LifecycleClientTest.theGateAloneOpensTheChannel`:
  `java.net.SocketException: Unix domain path too long`. Fixed the temporary-root length as described above.

## Not verified

- The owner's real session and app catalogue, and how the bounded wait feels there. All game runs used the
  development client's own saves and the headless test compositor; no owner's desktop, game folder or try-out was used.
- The game itself closing staging from its tick: the client test uses the existing
  `HomeSwitch.closeFromTestTasksForTests` adapter to avoid the Fabric framework's close-world barrier deadlock.
  It still drives the real create, provision, save, rename, reopen and town scheduler paths. No separate manual rig
  was run for this package.

## JUDGMENT-CALL

- Chose the brief's **wait for completion with a bound** option, at 600 ticks. A single-pass first build still speaks
  in its original pass; only a partial first build's total waits. The alternative of editing an already displayed
  chat message would need message identity and client/network behavior beyond this rule. The bound is one constant;
  the collection is per server and changes no saved data, so changing the policy later requires no migration.
- Hold the town in staging rather than carrying first-build chat state between two servers or saving it on disk.
  Staging is hidden and exists to provision the hub; its logos become visible only in the actual home. This avoids
  a loading-dependent partial town being silently carried into the new keeper. Reversing it is a small code change.

## PLAN-GAP

- The brief's loading guess missed the town running in staging. An accumulator in one keeper alone would lose its
  pending first total when that server stopped. The staging hold is needed as well as the rule fix.
- The existing unit temporary root did not leave enough Unix socket path space for this worktree's name.

## Open questions

- None that block this package. The owner can judge the partial-build wait during their normal try-out.
