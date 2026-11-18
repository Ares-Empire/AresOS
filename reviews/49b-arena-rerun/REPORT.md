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

Pending measurements. Rig repair and no-game validation are recorded in
[rig/README.md](rig/README.md) and [verification/](verification/).

## Verified

Before the pass-line commit: 14 inherited rig tests passed. Three real-user-scope
stand-in failures passed with bounded non-zero exits, all owned processes/scopes
gone and the lock free. Exact output: [unit-tests.txt](verification/unit-tests.txt),
[lifecycle-tests.txt](verification/lifecycle-tests.txt), [lifecycle.json](verification/lifecycle.json).
`bash -n reviews/49b-arena-rerun/rig/*.sh` exited 0 without output.

## Not verified

Measurements, full client qualification, verdict and shipping recommendation are
pending. Normal play on the owner's visible desktop is outside this rig.

## JUDGMENT-CALL

Pending the committed rules' verdict. No product setting ships in this package.

## PLAN-GAP

None at plan freeze. The frozen pass line above remains unchanged.

The second full build/client qualification deadlocked in the unmodified
`NetherHomeClientGameTest.testMountedRejoin` during `TestSingleplayerContext.close`.
Two [thread dumps](verification/client-2-deadlock.txt) show the render thread
waiting in `IntegratedServer.halt` / `executeBlocking`, while server and test
threads wait at Fabric phase barriers. Its log stopped advancing at 09:18:30
local. Only this invocation was cancelled through `client-test.sh`'s owned-scope
cleanup, which exited 143 after 10 min 40 s; all its scopes stopped and screenshots
were backed up/restored. The first full qualification passed. This is not two
passing qualifications and cannot be reported green. Changing the product test or
Fabric dependency is outside this brief's allowed files. Independent measurement
work continues, with this verification gap retained for review; a later passing
rerun alone would not fix the observed deadlock.

## Open questions

Pending the measurements.
