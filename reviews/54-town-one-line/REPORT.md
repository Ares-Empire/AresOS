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
