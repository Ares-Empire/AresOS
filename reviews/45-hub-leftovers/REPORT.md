# Package 45: two leftovers from 39b's review

## Done

- `mod/src/gametest/java/dev/aresos/test/FlatHomeGameTests.java`: the no-mob test schedules only its next tick instead of pre-registering a callback for every tick. Every scheduled callback has a distinct key because the framework removes the current `Runnable` after it returns. Ground loading now uses `System.nanoTime()` and the shared `ChunkWaits.WAIT_NANOS` (120 seconds); its framework ceiling is `ChunkWaits.LOAD_TICKS + CONTROL_LIMIT + TEN_MINUTES + 40` (40,014,440 ticks). The spawning-positive control, its 2,400-tick allowance after loading, all 12,000 quiet ticks, cumulative mob-addition assertions, final fixture checks and cleanup remain.
- `docs/design/HUB.md`: the summary and section 2.5 now include the third converter-renewal exception: something resting on a logo, such as a torch on its doormat, keeps it unchanged until removed, with one chat line. Obstructions are described as something in its place, including the front layer, sign space and way in.
- `mod/README.md`: the renewal paragraph states the same three cases. Confirmed against `TownKeeper`'s renewal pass and `rebuild` contract, `GateBuilder.prepare` and `checkRemoval`, and `Neighbors.checkRemoval`. No application code changed.

## Verified

All local Minecraft runs used the development scripts, one at a time. The client ran headlessly on NVIDIA. No OS test modules, system-update commands or disk mounts ran on the laptop. No `--force`, daemon-stop command or real desktop window was used.

### Local commands and results

| Run | Command | Result |
|---|---|---|
| Baseline | `mod/dev/build.sh --console=plain` | Exit 0; `BUILD SUCCESSFUL in 2m 27s`; 104 server tests; 236 unit tests, 0 failures/errors, 6 existing Windows-only skips. `/usr/bin/time -p`: 147.69 s. |
| Initial negative check | `mod/dev/build.sh --console=plain`, with the player deliberately left away from home | Stopped only this run's game-test JVM by PID (TERM); exit 143 from the JVM, build exit 1; `BUILD FAILED in 4m 37s` (277.94 s). Exposed that re-registering the same `Runnable` loses the next tick. Fixed by scheduling a distinct wrapper each time; the final checks below cover that fix. |
| Negative check on final code | `mod/dev/build.sh --console=plain`, again temporarily omitting the player's home teleport and chunk-map move | Expected exit 1; exactly one server test failed, with `Fixture: the ground around home did not load within 120000 ms (644985 ticks)`. This is its own clock deadline, far beyond the old 6,000 ticks and below the framework ceiling. `BUILD FAILED in 3m 18s` (199.07 s). The other 103 tests passed. The wrapper restored the source in `finally`; neither broken fixture was committed. |
| Full run 1 | `mod/dev/client-test.sh --keep-screenshots .work/45-hub-leftovers/client-1 build --console=plain --rerun-tasks` | Exit 0; `BUILD SUCCESSFUL in 12m 10s`; all 104 server tests passed; 236 unit tests, 0 failures/errors, 6 existing Windows-only skips; all 21 client entrypoints completed. Total wall time 733.38 s including the headless probes/cleanup. |
| Full run 2 | `mod/dev/client-test.sh --keep-screenshots .work/45-hub-leftovers/client-2 build --console=plain --rerun-tasks` | Exit 0; `BUILD SUCCESSFUL in 12m 18s`; all 104 server tests passed; 236 unit tests, 0 failures/errors, the same 6 skips; all 21 client entrypoints completed. Total wall time 741.98 s including probes/cleanup. |

Timings above were collected with `/usr/bin/time -p -o .work/45-hub-leftovers/<run>.time`; stdout/stderr went to the matching `.log`.

### No-mob test timing

The game log timestamps are local CET and have one-second precision, so these are approximate wall times on a shared laptop, not a benchmark. Before: environment start 11:00:21, control at 11:00:22 (96 ticks), quiet interval finished 11:00:25: about 4 seconds total, 3 for the quiet interval. After, full run 1: environment start 11:23:04, control at 11:23:10 (723 ticks), quiet interval finished 11:23:11: about 7 seconds total, 1 for the quiet interval. Ground loading varies independently of tick speed. Both quiet intervals still represent exactly ten minutes of game time. Full run 2: environment start 11:35:25, control at 11:35:26 (358 ticks), quiet interval also finished at 11:35:26: about 1 second total and under 1 second for the quiet interval. Both final runs printed `32 server no-mob check: 12000 ticks, 0 mob additions`. No resource refusal (exit 75) occurred, so no retry was needed.

### Hosted checks

Before dispatch, `git fetch origin main` followed by `git merge origin/main` printed `Already up to date.`; the branch already contained main `ee2d576b`. Implementation/docs commit: `5bc5c341`. Before the final report push, fetched again and merged main `e1694830` as `2c2f2e18`; only `HANDOFF.md` and two review documents came in. No executable code or test changed after the local runs or the hosted OS run.

- PR: https://github.com/Ares-Empire/AresOS/pull/99
- `gh workflow run 'OS image' --ref pkg/45-hub-leftovers -f checks_only=true`, then `gh run watch 44062599775 --exit-status --interval 60`: exit 0, [run passed](https://github.com/Ares-Empire/AresOS/actions/runs/44062599775). Regression job: 31m 52s; printed `Ran 1673 tests in 1870.686s` and `OK (skipped=4)`. The four existing skips are cover tests: three need headless labwc, grim and GTK 4 (explicitly not the hosted runner), one needs GTK 4 through gi. Syntax checks, hosted system-manager query (437 unit files, 478 unit names), release-input resolution and upstream-signature verification passed. The model selector chose the normal bounded slice because no full-model dependency changed; no image/VM/publish job ran.
- Mod build and reproducibility: https://github.com/Ares-Empire/AresOS/actions/runs/44062576510 — passed on `5bc5c341`.
- Repo privacy: https://github.com/Ares-Empire/AresOS/actions/runs/44062576390 — passed on `5bc5c341`.

### Screenshots and workspace

Inspected and saved [run 1](screenshots/run-1-arrival.png) and [run 2](screenshots/run-2-arrival.png): the flat home, north road and group label render normally. All 86 PNGs from each full run remain in `.work/45-hub-leftovers/client-1` and `client-2`. Restored 51 changed tracked PNGs and removed 25 preserved untracked PNGs from older review folders; no test list or screenshot number changed.

`git diff --check` passed. Final inventory: **no file over 500 MB remains in `.work/`**; no large download was made. The development scripts stopped their own scopes, including their single-use Gradle processes; no shared daemon was stopped.

## Not verified

The owner's real session and shader pack were not opened. This package adds no gameplay or visual behavior requiring a new human check. The hosted run did not execute the four existing cover tests named above; this package changes none of that code.

## JUDGMENT-CALL

None. The self-scheduling approach and shared clock/tick bounds are the brief's stated options; the control and quiet interval are unchanged.

## PLAN-GAP

The brief has no gap. The verification guidance says the hosted suite skips nothing, but the current suite intentionally skips four cover tests without its display/GTK dependencies; the exact result is recorded above. No test or workflow was changed. A fresh callback identity is necessary for the proposed self-scheduling approach because of the framework's callback map; it is handled in the implementation.

## Open questions

None.
