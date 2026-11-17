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
| `NMT=0` | Disable native memory tracking. Other instrumentation remains. |

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

`analyze.py` publishes small evidence and redacts worktree/home paths. Raw game logs, jars, worlds, frames and
launcher/helper credentials remain in ignored `.work/`. Public data includes heap/probe outputs, snapshots,
NMT, GC, frame statistics, scope actions and host context. Start time measures the dev JVM to join and includes
mod-loader/world work; it is not Prism's product launch time.

Create the disposable flat base once with `MODE=create FLIGHT=none QUIT=1`, then copy that run's `world` into
`.work/pkg49/AresHub-base`. Every comparison gets a fresh copy. Create a Nether base similarly, then run
`prepare-glide.py` on its local copy. `WORLD=keep` and `MODE=hold` exist for rig diagnosis only.

Checks without a game:

```bash
python3 -m unittest discover -s reviews/49-memory-cuts/rig -p 'test_rig.py' -v
for script in reviews/49-memory-cuts/rig/*.sh reviews/49-memory-cuts/frames/build.sh; do bash -n "$script"; done
```
