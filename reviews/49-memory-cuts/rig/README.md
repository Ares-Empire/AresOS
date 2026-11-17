# Package 49 measurement rig

Development aids only. Nothing ships in the image. Copied from package 41; package 41 is unchanged.
The `pkg41` names in the frame recorder, fake apps and glide pack deliberately preserve that workload.

Run from the worktree:

```bash
reviews/49-memory-cuts/rig/retry.sh reviews/49-memory-cuts/rig/run.sh example COVER=300
```

`run.sh` uses `mod/dev/env.sh` to find Java 25, enforce the 6 GiB floor and owner-game guard, and wait on the
shared client lock **before** preparing the world/options or compiling the small recorder. `measure.sh` is its
implementation; do not invoke it directly. The lock is inherited by the run and released between runs. The
retry wrapper waits five minutes after exit 75, with at most six retries. Other failures stop immediately.
No `--force`, daemon stop, owner display, product OS command or disk mount is used.

The default is package 41's v1: heap 1024/256 MiB, G1 free ratios 30/10, scope MemoryHigh 2560M, render 8,
simulation 5, 1920×1080@144. The development client runs inside its own headless labwc and Xwayland with
NVIDIA offload and null audio. All game scope names start `pkg49-game-`. Cgroup actions compare the supplied
PID's exact current scope, its systemd ControlGroup and membership before any write. Cleanup thaws before
stopping only this run's scopes. Launcher logs remain local under `.work/pkg49/rigs/`.
The refreshed rig also clears `ARESOS_DESKTOP_LIFECYCLE`: package 46's gated lifecycle client must not connect
to the owner's real supervisor socket. The game still uses this rig's private app helper.

In addition to package 41's settings:

| Setting | Meaning |
|---|---|
| `ENV=MALLOC_ARENA_MAX=2` | Comma-separated assignments passed only to the game's scope with systemd `--setenv`. Only allocator variables are accepted. |
| `MODS=/absolute/file.jar` | Comma-separated local jars appended to `fabric.addMods`. |
| `PROBE=1` | Each live snapshot: capture memory/smaps first, trim, memory, full GC, memory, second trim, memory, heap info. Diagnostic runs are intentionally perturbed. |
| `COVER_ACTION=gc-trim` | One GC and glibc trim at 30 seconds covered. |
| `RECLAIM=300M` or `600M` | GC+trim at 30 seconds, then one `memory.reclaim` write with `swappiness=max`. EAGAIN is retained as partial, never silently reported as complete. |
| `FREEZE=1` | Requires reclaim. Freeze only the game scope after reclaim; snapshots skip jcmd until thaw. |
| `LONG=20` | After standing/flight, remain visible and idle, with minute snapshots for 20 minutes. Use `FLIGHT=none` for step 0. |
| `NMT=0` | Omit tracking and require the JVM to confirm it is disabled at every live snapshot. Other instrumentation remains. |
| `CREATE_FLOW=automatic` | Current product flat first start. Observe the actual `HomePlan.create` entry instead of sending obsolete title-screen clicks. |
| `CREATE_FLOW=menu` | Nether setup: start a fresh copy of the flat base and use Esc → New home → Nether → Create → confirmation. Require one observed Nether plan and the final ready message. |

Every snapshot records scope swap, global zram mm_stat, host load/free memory and selected executable counts,
minflt/majflt and smaps classes. `sample.py` records cheap memory/fault/load samples every two seconds. Global
zram changes can include other builders: use scope swap for attribution; zram bytes alone cannot identify this
process's compressed physical cost. Anonymous VMAs are explicitly unattributed: smaps cannot prove which
allocator owns them. The Java heap range, glibc brk heap, jemalloc library maps and NVIDIA maps are separated.

Cover timing uses a fixed deadline from the cover mark, not a minute plus snapshot overhead. A return-request mark precedes thaw.
The ten-second `wake_start` mark follows the cover process closing; activation and input follow it. The first
interval is clipped to that mark, so a five-minute frozen interval is not counted as a five-minute wake stall.
`return_to_first_frame_ms` includes thaw and window-close overhead; `wake_first_frame_ms` starts at cover close.
These are recorder frame starts, not display presentation timestamps. Frames count gaps >17 and >33 ms exactly.
The diagnostic `s0-probe` used one tiny relative movement and stayed at vanilla's 30 fps inactivity cap after
cover close. Its raw wake data is retained, but comparisons use active input (`WAKE_INPUT=active-v2`, then `active-v3`): a control-key
transition plus repeated camera turns through the wake window (`wake.py`), like the active standing workload.
Version 3 retains the same key/camera workload but holds its FIFO writer open, with a one-second bounded
retry at startup. This fixes the reader-reopening race found in the first FerriteCore trial. A dead reader
still fails promptly instead of holding the shared lock forever.

`analyze.py` publishes small evidence and redacts worktree/home paths. Raw game logs, jars, worlds, frames and
launcher/helper credentials remain in ignored `.work/`. Public data includes heap/probe outputs, snapshots,
NMT, GC, frame statistics, scope actions and host context. Start time measures the dev JVM to join and includes
mod-loader/world work; it is not Prism's product launch time.

The original base used the earlier title-screen creation flow. On the refreshed source create flat with
`MODE=create CREATE_FLOW=automatic FLIGHT=none QUIT=1`; each first-creation comparison starts with no AresHub.
The Nether setup uses `MODE=create CREATE_FLOW=menu HOMEKIND=nether FLIGHT=none QUIT=1` from the flat base,
then saves its actual Nether world before `prepare-glide.py`. That setup includes a warm flat/menu switch,
so its startup is not a cold Nether launch. Both Nether measurement JVMs load fresh identical Nether copies.
`WORLD=keep` and `MODE=hold` exist for rig diagnosis only.

The refreshed recorder requires package 48's `HomePlan` and records creation at its real entry without changing
the plan. Optional GUI observations let `ui.py` click a unique active button at its actual bounds through the
private input FIFO; they never call a button's action directly. `creation.py` rejects a wrong or duplicate home
kind. Raw GUI history stays local because encoded labels could contain paths on an error screen. Only the plain
creation kind/timestamp is published. Replay earlier measurements with their recorded source/rig revision.
`QUIT=1` requires the launcher to report a clean game exit before copying the saved world; a vanished PID
or a quit timeout fails the measurement instead of producing a reusable base.

Checks without a game:

```bash
python3 -m unittest discover -s reviews/49-memory-cuts/rig -p 'test_rig.py' -v
for script in reviews/49-memory-cuts/rig/*.sh reviews/49-memory-cuts/frames/build.sh; do bash -n "$script"; done
```

`batch.py` provides the ordered `step0`, `factors`, `covered` and `winners <settings.json>` schedules. The factor
stage waits for `.work/pkg49/factors-ready`: create that marker only after auditing the step-0 summaries and rig
controls. The winner settings file contains `{"settings": ["KEY=value", "..."]}`; choose it from the evidence.
Each factor has a fresh baseline, in A/B order in round 1 and B/A in round 2. Every completed run releases the
shared game lock; the batch also waits 30 seconds. Interrupted/failed runs are never silently overwritten.

`GC=` replaces the extra JVM-argument string. Keep the v1 free-ratio arguments when overriding it, as `batch.py`
and each recorded settings file do. Heap figures in the comparison table use post-G1 minima in the settled
standing window, not join-time collections before the world is fully populated.

The winner schedule includes a current v1 Nether glide before the winner's glide, from identical fresh base
copies. This is one additional control: package 41's earlier code revision cannot by itself establish that
Nether frames are unchanged. Inspect both glide tick totals as well as the frame and memory numbers.

Main moved during the original matrix, including product mod changes. Finish that matrix on its original
tree, merge main, and repeat the full client qualification before the winner stage. That stage now pairs
each of the three flat winner runs with a fresh v1 control (A/B, B/A, A/B), and adds a current v1 first
creation. Source grouping in the audit keeps the earlier factor controls separate from the merged tree.
These four controls bring the planned experiment count to 54, including both setup runs and the additional
Nether control. Failed attempts and retired pairs are separate evidence, not extra repetitions in a mean.
The winner schedule checks both automatic flat creations and the menu-driven Nether setup before the three
flat pairs, so the changed creation flow is exercised early.

After the runs, `table.py` generates the paired, covered and individual-run tables from public summaries.
`audit.py` records each run's memory/GC/recorder guards, source mod-tree identity, action durations, observed
flat-control frame ranges and the winner's same-base Nether comparison. It does not turn experimental GC
failures into passes or introduce a frame tolerance. The zram table uses the kernel's first three `mm_stat`
fields (original bytes, compressed bytes, total allocated memory including overhead), summed over devices;
all three remain global observations rather than a per-game physical-memory measurement.

The first freeze attempt exited during return (game status 137, followed by a broken virtual-input pipe).
It is retained under `failures/`, with partial measurements and no qualified wake window. The unchanged
second attempt adds `observe-return.py <pid> <owned-scope> <rig>`: read-only scope counters and process state
at 20 ms intervals for three seconds after the return mark. This diagnostic checks exact scope membership
and PID start time, and neither attaches to the JVM nor changes freezer state. It is not part of winner runs.
