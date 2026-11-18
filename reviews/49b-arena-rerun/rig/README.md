# Package 49b measurement rig

Copied from package 49 into this package; historical evidence is unchanged. The frame recorder and fake-app/glide workloads retain their `pkg41` names. No product code or settings ship.

`run.sh <name> [KEY=value ...]` acquires the shared client-test lock, applies the owner-game and 6 GiB guards, and uses `mod/dev/env.sh`'s independent supervisor and NVIDIA CUDA holder. Both control and candidate run with that holder (package 47); package 49 did not. A scoped controller launches its own headless labwc/Xwayland and game scope. Every exit stops only those scopes before the outer supervisor releases its holder and lock. Runtime outputs live in `.work/pkg49b/`; public summaries are in this package's `runs/`.

The v1 defaults are heap 1024/256 MiB, G1 free ratios 30/10, MemoryHigh 2560M, distances 8/5, 1920×1080@144, cap 120 fps, NMT summary. `ENV=MALLOC_ARENA_MAX=2` sets only the game JVM environment through the wrapper. `COVER=300` retains the untreated cover/wake workload. Probe, reclaim, freeze and GC/trim cover actions are refused in this package. No direct writes under `/sys`, `/proc` or `/etc` occur.

`input.py` bounds every FIFO open and atomic write to one second, including standing, flight, chat, screenshots, UI and wake input. `health.py` uses pidfds to watch the rig launcher, compositor and reader, including during sleeps. A loss signals the controller's EXIT cleanup. The reader also treats Wayland EOF as failure. Long sleeps use interruptible child waits; a health failure also interrupts only the controller's direct children in its own cgroup, so a foreground UI/jcmd command cannot defer cleanup. Normal intentional shutdown stops the health watcher first.

Validation without a game:

```
bash -n reviews/49b-arena-rerun/rig/*.sh
python3 reviews/49b-arena-rerun/rig/test_rig.py
python3 reviews/49b-arena-rerun/rig/test_lifecycle.py
```

The lifecycle test uses real disposable user scopes, a local test lock and FIFO/process stand-ins. It kills the reader before standing input, during the flight sleep, and the compositor while a foreground command blocks; requires bounded failure, all peer pidfds exited, no scope left and actual nonblocking lock reacquisition. It sources the production `lifecycle.sh`. It never starts a game or opens a display.

Measurements must follow the separately committed pass line and schedule in `REPORT.md`. Retry exit 75 after five minutes, at most six retries. Leave thirty seconds between runs for other lock holders. Retain and identify every failed or externally contaminated attempt. `analyze.py` preserves package 49's frame definitions: gaps between recorder frame starts, counted by the gap's ending timestamp; exact >17/>33 ms counts, with rounded display maxima. Global zram is host context, not attributed game memory. Raw logs/worlds/jars stay ignored; published files redact local paths.
