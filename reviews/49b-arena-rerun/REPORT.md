# Package 49b: the arena cap, measured again

## Pass line — fixed before any game run

This section is committed before the first game run. The verdict will use this
committed line. Any later change to it is a PLAN-GAP and cannot change the rule
used to judge these measurements.

- **Safety (package 41):** no OOM, no `memory.events high`, and no GC pause over
  50 ms after joining. Check every completed control and candidate run.
- **Memory:** median of the six paired settled-RSS savings (control minus
  candidate) is at least **100 MiB**.
- **Flat flight:** summed over the six flat pairs, candidate flight gaps >17 ms
  number at most the control sum **plus 2**. No candidate flight gap exceeds
  **33 ms**.
- **First creation:** summed over the two creation pairs, candidate gaps >33 ms
  in the first 30 seconds after joining number at most the control sum **plus 1**.
- **Nether glide:** candidate flight gaps >17 ms number at most the paired
  control count **plus 2**; no candidate flight gap exceeds **33 ms**.
- **QUALIFIED** requires every rule above. Otherwise **NOT QUALIFIED**, identifying
  each failed rule and its margin. Report all spreads and whether package 49's
  19.948 ms flight event recurs (an event in that range or another >17 ms event;
  exact numerical equality is not required).

Counts use unrounded gaps between recorder frame starts, exactly >17 and >33 ms.
The first-creation window starts at the rig's observed join mark, as in package 49.
These are frame-start gaps, not presentation timestamps. No trial is dropped for
its result. A run overlapping another builder's Gradle build or game is retained,
marked and repeated; only the replacement qualifies for its planned slot.

## Fixed run plan and conditions

A is unmodified v1. B is v1 with `MALLOC_ARENA_MAX=2` in the **game JVM environment
only**. Both use heap 1024/256 MiB, G1 free ratios 30/10, MemoryHigh 2560M,
distances 8/5, NMT summary, 1920×1080@144, cap 120 fps, 120 seconds settling,
60-second standing/flight windows and a 300-second untreated cover followed by
the existing ten-second wake workload. No reclaim, freezing or forced GC/trim.

1. Six flat pairs, orders **AB, BA, BA, AB, AB, BA** (control first in pairs 1,
   4 and 5), each using a fresh copy of the same new disposable flat fixture.
2. Two first-creation pairs, **AB, BA**, with no AresHub and the real automatic
   flat creation path. Each JVM creates its own seed-0 forty-app home.
3. One Nether-glide pair, **AB**, each using a fresh copy of the same new
   seed-49 fixture with the existing 1200-tick teleport-route data pack.

This is 18 measurement runs. Fixture construction is recorded separately as
utility work, never included in paired results. No historical world or untracked
file is taken from another worktree. The repaired rig is validated and committed
before this pass-line commit. Full build/client qualification will run twice
through `mod/dev/client-test.sh`, retaining screenshots locally and restoring
rewritten historical screenshots.

Every run holds the shared client-test lock and enforces 6 GiB available and the
owner-game guard; all display/input is private and headless. Thirty seconds
between runs lets other lock holders enter. Exit 75 waits five minutes, at most
six retries per run. Other failures stop the schedule for diagnosis.

Main moved and was merged before repair: `fd9cb695` adds package 47's NVIDIA
holder. This rig explicitly uses its supervisor and holder, keeping the GPU awake
for controls and candidates through shutdown. Package 49 lacked that holder;
compare only within package 49b pairs. Load, free memory, selected process counts
and continuous interference observations accompany each run.

## Done

**Verdict: NOT QUALIFIED. Retain v1; linux-aresos should not add the arena cap.**
The first-creation rule failed: the two candidates recorded **5** gaps over 33 ms,
the controls **2**, and the committed allowance was **3**. That is **2 gaps over
the allowance**. Every other committed rule passed. This verdict uses the original
[pass-line commit `2ddcb93f`](https://github.com/Ares-Empire/AresOS/commit/2ddcb93f);
its text and the fixed plan above are unchanged.

| Committed rule | Observed result | Verdict |
|---|---|---|
| Safety, all 18 measurements | No OOM or `high` events; maximum post-join GC **18.698 ms**, including covered phases | PASS |
| Median paired settled saving ≥100 MiB | **242 MiB**, range **152–318**; 142 MiB above the minimum | PASS |
| Six flat pairs: candidate flight >17 ms ≤control sum +2 | Candidate **0**, control **2**, allowance **4** | PASS |
| No flat candidate flight gap >33 ms | Candidate maximum **13.550 ms** | PASS |
| Two creations: candidate first-30-second >33 ms ≤control sum +1 | Candidate **5**, control **2**, allowance **3**: **exceeds by 2** | **FAIL** |
| Nether >17 ms ≤control +2 | Candidate **0**, control **2**, allowance **4** | PASS |
| No Nether candidate flight gap >33 ms | Candidate maximum **16.272 ms** | PASS |

[Machine-readable verdict](verification/verdict.json), [all run/pair tables](TABLES.md),
[measurement audit](verification/measurement-audit.json), and [accepted slots](accepted.json)
retain the individual observations. There are **18 completed measurements and two
separate fixture utilities**, in the prescribed order, with no contaminated or
failed measurement attempt removed or replaced. All 20 individual rig invocations
exited 0. The final scheduler bookkeeping interruption is recorded below.

### What was built

- `rig/` copies package 49's rig into this package. `input.py` bounds every FIFO
  open/write to one second; standing, flight, chat, UI, wake, screenshot positioning
  and the optional flight-check utility use it. `health.py` watches owned launcher,
  reader and compositor pidfds. It interrupts the controller and its direct children
  in the controller's cgroup, so a foreground command cannot defer cleanup.
  `lifecycle.sh` stops only this run's game/rig scopes; the outer package-47
  supervisor releases its NVIDIA holder and shared lock after controller cleanup.
- The initial repair and three no-game failure cases were committed at `94f0e416`,
  before the pass line. Further pre-measurement hardening covered foreground-command
  interruption and the optional flight-check utility. Every paired measurement used
  the runtime/recorder sources frozen at `32bcdb55`; [source hashes](verification/runtime-sources.json)
  confirm they stayed unchanged throughout. Later edits are evaluation/publication code.
- `frames/` preserves the existing frame-start recorder and passive creation/UI
  observations. The workload retains the `pkg41` names. GUI observations only locate
  buttons for private compositor input; they never invoke product actions directly.
- `schedule.py` implements the fixed AB/BA order, 30-second unlocked gaps, five-minute
  exit-75 retries (at most six retries), continuous host sampling, and retained
  interference/failure records. `verdict.py` independently recounts exact frame gaps
  and GC durations; `audit.py` checks settings, sources, ordering, complete required
  frame windows, host observations and unchanged fixture hashes. `finalize.py` can
  recover only the final manifest from already completed attempts.
- Public data contain small snapshots, GC/heap/NMT records, samples, settings,
  actual JVM environment/flags, source/jar identities, decisive frame timestamps,
  and screenshots. Raw launcher/helper/game logs, worlds and jars stay in ignored
  `.work/pkg49b/`. Nothing under `mod/src` or `os/` changes; package 49's record
  stays unchanged. No settings or mod ship here.

### Memory and spread

All values below are MiB, with medians and observed ranges over six flat pairs.
The saving column is the median of **paired differences**, not the difference
between the two independent medians. These ranges are not confidence intervals.

| Phase | v1 RSS median (range) | Arena RSS median (range) | Paired saving median (range) |
|---|---:|---:|---:|
| Settled, visible | 1287.5 (1211–1366) | 1052.5 (1013–1091) | **242 (152–318)** |
| After flight | 1363.5 (1301–1436) | 1071 (1032–1099) | **304 (202–350)** |
| Covered for five minutes | 1338 (1273–1408) | 1043 (1004–1075) | **307 (198–348)** |

The two first creations saved 190/201 MiB settled, 230/390 after flight, and
238/365 covered. The Nether pair saved 212/330/330 MiB at the same three snapshots.
Heap commitment, PSS, scope memory and anonymous/file mapping classes remain in
individual summaries; RSS savings are not an exact measurement of the whole
session's incremental physical memory. All runs kept NMT enabled, as specified.

### Frames, startup and the old 19.948 ms event

The six flat candidate flight maxima were 10.837–13.550 ms, with **zero** gaps
above 17 ms. The two control outliers were 25.682 and 25.069 ms. Thus package 49's
**flat** candidate outlier was not reproduced in these six candidate trials.
One creation candidate flight did contain a **17.827 ms** gap; the second creation
candidate peaked at 14.092 ms. No candidate flight in any of the nine workloads
exceeded 33 ms. [Outlier timestamps/durations](verification/frame-outliers.json)
and every run's `decisive-frames.json` preserve these events; no cleaner repetition
replaces them. The measurements do not establish the cause of the old event.

First-30-second creation counts (>33 ms) were **control/candidate 1/2 and 1/3**.
Their maxima were 90.845/79.174 and 108.832/142.159 ms. This startup count failure
is independent of the passing flat flight rule. Both Nether JVMs completed the
full **1200-tick** route; control/candidate flight maxima were 20.738/16.272 ms,
with >17 ms counts 2/0 and >33 ms counts 0/0.

Flat game-PID-detection-to-join medians were **9.89 s v1 / 9.38 s arena**, ranges
9.13–11.14 / 8.63–10.14. Creation joins were 9.14/10.48 s and 10.28/9.84 s
(control/candidate). This excludes Gradle/Prism startup and has roughly one-second
PID-detection granularity; it is not a cold product boot measurement. The creation
frame window starts at the inherited observed join mark, exactly as frozen above.

For flat ten-second wakes, control/candidate worst-frame ranges were
**33.539–57.958 / 33.484–71.509 ms**. Counts >17 ms ranged 11–12 / 11–13;
counts >33 ms were 11–12 for both. Return-request-to-first-frame ranged
**57.61–101.32 / 43.80–115.29 ms**. Every flat run had zero added wake major faults
and zero scope swap at five minutes. These are untreated cover/activation windows;
there was no reclaim, freeze or forced GC. Their full spread remains visible.

### Conditions and source

The observed platform was the i5-13500H/16 GB laptop, RTX 4060, NVIDIA 615.78.08,
Temurin 25.0.5+8 and glibc 2.43 ([platform record](verification/platform.json)).
The private headless labwc/Xwayland used 1920×1080@144, NVIDIA GLX, null audio,
120 fps cap, distances 8/5, heap 1024/256 MiB, G1 free ratios 30/10 and game-scope
MemoryHigh 2560M. Every actual candidate JVM had `MALLOC_ARENA_MAX=2`; controls
had it unset. Other allocator variables were unset and JVM flags matched.
[Loaded-mod lists](verification/loaded-mods.json) are identical across all 18:
Fabric Loader 0.19.5, Fabric API 0.161.0+26.2, Minecraft 26.2, and the frame recorder;
no FerriteCore or allocator-system variant was added.

Main `fd9cb695` was merged before repair. This rig explicitly uses package 47's
independent supervisor/CUDA holder through `mod/dev/env.sh`, keeping NVIDIA awake
for both controls and candidates through shutdown. Package 49 lacked that holder.
Both new seed-0 flat and seed-49 Nether fixtures were constructed in this worktree;
no untracked input was taken from another worktree. Their [hashes](fixture-hashes.json)
were unchanged after all measurements. **Only this package's pairs are compared**;
package 49's controls and savings are not pooled with them.

All measurements used product tree `09a77ad94e74f4c5c8e51c71a418d23048792cb3`, with
identical helper/labwc blobs and runtime sources. Every launch passed the shared
owner-game/memory guards; the minimum recorded pre-launch available memory was
**8621 MiB**. During games, sampled available memory reached 5912 MiB and load-1
reached 4.374. Every run retains load/free memory and selected executable counts
in two-second host observations. No other Gradle build/game was detected during
an accepted measurement at that sampling resolution. Lock waits let other
builders through between runs; they are outside measured windows. The [command
ledger](verification/run-commands.txt) retains every invocation, wait and exit.
No guard was forced and no busy-refusal retry was needed.

Frames are gaps between recorder frame starts, not presentation timestamps.
Counts use unrounded gaps and the inherited end-of-gap boundary rule. Nominal
`WINDOW=60` retains the existing route/cadence; actual standing windows are about
57.6 s and flight windows about 60.1 s, with exact markers published. The Nether
route is the inherited level teleport glide through terrain; occluded views are
possible, so it is not a worst-case human flight/rendering test. Global zram
statistics include other processes and cannot attribute compressed physical cost
exactly to this JVM.

## Verified

- `bash -n reviews/49b-arena-rerun/rig/*.sh`: exit 0, no output.
  `python3 reviews/49b-arena-rerun/rig/test_rig.py`: **14 tests, OK**; `python3 reviews/49b-arena-rerun/rig/test_input.py`:
  **2 tests, OK**. These include dead/full FIFO bounds and refusal of a regular-file
  input target. [Unit output](verification/unit-tests.txt), [input output](verification/input-tests.txt).
- `python3 reviews/49b-arena-rerun/rig/test_lifecycle.py`: standing reader loss,
  mid-flight reader loss, and compositor loss while a foreground command blocks
  all printed **PASS, exit 1, processes/scopes gone, lock free**, in 0.114–0.164 s
  in the retained final validation. Real disposable user scopes and a local lock,
  no game or CUDA. [Output](verification/lifecycle-tests.txt), [measurements](verification/lifecycle.json).
- `reviews/49b-arena-rerun/rig/retry.sh mod/dev/client-test.sh --gpu nvidia
  --keep-screenshots .work/pkg49b/client-1 build`: **BUILD SUCCESSFUL in 14m 14s**,
  exit 0, NVIDIA renderer. It passed 104 required server tests; JUnit contains
  272 cases, zero failures/errors, six Windows-only skips. [Extract](verification/client-1.txt).
- The same command with `client-2` **did not pass**. It deadlocked in mounted rejoin;
  two thread dumps were saved, then only this owned invocation was cancelled through
  its cleanup. Exit **143 after 10 min 40 s**. [Extract](verification/client-2.txt),
  [thread dumps](verification/client-2-deadlock.txt), [observation/action](verification/client-2-deadlock.json).
  This is not two passing full qualifications and is not reported green.
- `reviews/49b-arena-rerun/rig/retry.sh mod/dev/build.sh`: **BUILD SUCCESSFUL in
  2m 47s**, exit 0; all 104 required server tests passed. `:test` was UP-TO-DATE,
  reusing the prior JUnit results; those 272 unit cases did not execute again.
  [Output](verification/build-2.txt), [JUnit totals](verification/unit-results.json).
  Test-generated historical pictures were backed up under `.work/pkg49b/client-1`
  and `client-2`, then [restored/removed](verification/screenshot-restoration.json).
- `gh workflow run "Mod" --ref pkg/49b-arena-rerun` and
  `gh run watch 44283000984 --exit-status --interval 60`: **passed** at `32bcdb55`.
  [Hosted run](https://github.com/Ares-Empire/AresOS/actions/runs/44283000984) built
  two clean checkouts in 1m 19s / 1m 13s, each passing 104 required server tests.
  Both jars hashed `e88194c52e956e5c098477d02cc5debc7ce3b3d4c234c05ca676235152f45b48`.
  [Extract](verification/hosted-mod.txt), [identity/jobs](verification/hosted-mod.json).
  It covers the same product tree as every measurement, not the rig-only input code.
- `python3 reviews/49b-arena-rerun/rig/schedule.py`: all **18 measurement and two
  utility** rig invocations completed with exit 0, with the prescribed ordering and
  unlocked gaps. The outer scheduler command later reported 143 during final
  bookkeeping; no measured child was interrupted. `python3 reviews/49b-arena-rerun/rig/finalize.py`
  reconstructed only the final accepted-slot manifest and rechecked fixture hashes:
  **18 completed slots; no game launched or replaced**.
  [Finalization record](verification/scheduler-finalization.json).
- `python3 reviews/49b-arena-rerun/rig/verdict.py` independently recounted the retained flight/creation
  timestamps and exact GC durations: **NOT QUALIFIED**, creation limit exceeded by 2.
  `python3 reviews/49b-arena-rerun/rig/audit.py` printed **18 accepted measurements; frozen
  line/order/settings/source/frames/fixtures audited; all attempts retained**.
  There are zero lost frame records, and the raw recordings cover every required
  window. Absolute worktree/home paths are redacted in published captures.

Inspected pictures: [flat south road](screenshots/home-south.png),
[above the town](screenshots/above-south.png), and the actual
[Nether/seed-49 choice](screenshots/nether-choice.png). These are private dev-client
pictures with generated test logos. No owner display/input was used.

The [closing storage inventory](verification/closing-storage.json) found **no
regular file over 500 MiB** in `.work/` (about **143 MiB** total at that check).
There were no ISO/image downloads or extractions. [Closing process checks](verification/closing-processes.json)
found no owned game/rig/controller scopes or exact rig-script processes. Guarded
builds used single-use daemons; **no daemon-stop command was run**.

Final local syntax, JSON, whitespace and the exact Repo privacy workflow body
passed ([record](verification/final-local-checks.json)). The privacy check printed
“No file holds a home path with a real user name.” The PR's hosted privacy result
is pending publication; no hosted privacy pass is asserted yet.

## Not verified

- **Two passing full build/client qualifications.** The second attempt's deadlock
  remains unresolved; hosted build/server passes do not replace that client check.
- Human play in the owner's real session, real app focus/return, audio/multiple
  displays, and production Prism/boot time. This used a dev client, null audio and
  a private compositor; the game-only RSS is not the complete desktop's memory cost.
- The cause of startup/flight outliers, a universal physical-memory floor, other
  runtimes/backends or long-term session retention. This package ran the requested
  matrix, with NMT on throughout; it did not add an NMT-off or LONG trial.

## JUDGMENT-CALL

**Keep the current product settings.** The cap's memory benefit was reproduced,
but the committed creation count rule rejects this set. No game-wrapper default,
supervisor allowlist addition, image environment setting, JVM-argument change,
cover action or extra mod is qualified to ship from this package. Nothing under
`os/` or `mod/src` was changed. A different adoption decision needs a new brief
or owner decision; this report does not revise the committed pass line.

## PLAN-GAP

- The unchanged full client suite can deadlock in
  `NetherHomeClientGameTest.testMountedRejoin` during `TestSingleplayerContext.close`.
  Two thread dumps show the render thread waiting in `IntegratedServer.halt` /
  `executeBlocking`, while server and test threads wait at Fabric phase barriers.
  The log stopped advancing at 09:18:30 local. Its owned invocation was cancelled,
  its scopes stopped, and screenshots were backed up/restored. Fixing the product
  test or Fabric dependency is outside this brief's allowed files. No test or
  assertion was weakened, skipped or deleted; a later clean rerun alone would not
  resolve the observed deadlock.
- After the final rig invocation exited 0, the scheduler command reported exit 143
  and did not write its final manifest/COMPLETE line. The sender/cause is unknown.
  All 18 individual success logs and published attempt records were already saved.
  Finalization rebuilt the manifest from them, audited both unchanged fixtures and
  launched no new game. This is not claimed as one uninterrupted successful batch.
- **No pass-line change occurred.** The failed startup result is judged against
  `2ddcb93f`, not a later tolerance or a different window definition.

## Open questions

- What causes the full client-test shutdown/phase-barrier deadlock, and what
  separately scoped fix can make the required two full qualifications reliable?
- What causes the candidates' extra creation gaps? The memory result and clean
  flat flights do not identify that cause or waive the failed startup rule.
