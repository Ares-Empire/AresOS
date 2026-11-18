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
