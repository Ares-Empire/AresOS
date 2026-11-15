# 41: How much memory the home screen needs (a measurement study)

The owner (2026-11-15): "I think we do need to optimize memory usage of the homescreen because if as a default it just uses lots that is suboptimal for a homescreen."

Today package 23's supervisor gives the home screen's Java a heap of up to 3072 MiB (`HEAP_MB`, minimum 512) and a systemd `MemoryHigh` (`os/config/usr/libexec/aresos-desktop`), with render distance 8 and simulation distance 5 (`RENDER_DISTANCE`, `SIMULATION_DISTANCE`). Package 40 measured about 1370 MiB resident in a headless labwc at 1280 x 720 and render distance 8. `linux-aresos` (the OS lead) sets the numbers for the next release (planned 19 to 21 November) and asked for them.

This package measures and recommends. It changes no product code. If a mod change would clearly save memory, describe it with its expected gain; it becomes a package of its own.

**Builder:** one Claude agent on Opus 5.5: measurement against a clear plan. **Review:** a fresh Claude reviewer on Opus 5.5 checks the method and the numbers.

## Measure

Measure in a headless compositor with the development client, as package 40's rig does (`reviews/40-real-home/rig/`, `mod/dev/client-test.sh` for the GPU and environment). Use the flat home with a town of about 40 apps: the rig's helper with a registry of test entries of your own, never the owner's programs.

Per setting, after the world has settled (2 minutes):
- resident memory of the Java process (RSS and PSS), the heap in use and committed (`jcmd <pid> GC.heap_info` or JFR), and native memory (`-XX:NativeMemoryTracking=summary`, `jcmd VM.native_memory`);
- GPU memory (`nvidia-smi --query-compute-apps`, or the process's share);
- frame time: average and worst of 60 s, standing at home and while flying down a road at full speed with the town loading;
- GC pauses (`-Xlog:gc`): count and longest.

Settings:
1. Render distance 8, 6 and 4, with simulation distance 5 and 2. Check what the town needs to be seen from home and from a road (HUB.md: the logos stand up to about 100 blocks out at 40 apps). Below what the town needs is not an option.
2. Heap ceilings: 3072, 2048, 1536 and 1024 MiB at the chosen distances. The floor is the lowest ceiling with no `OutOfMemoryError`, no GC pause over 50 ms in the flight, and no worse frame time than at 3072.
3. GC: the JVM's default (G1) against G1 with periodic uncommit (`-XX:G1PeriodicGCInterval`), so memory goes back to the system while he works in other apps. Measure RSS after 5 minutes covered by a maximized app (package 40 pauses the world then).
4. The window size: 1920 x 1080, his screens' size.

## Report

`reviews/41-home-memory/PROGRESS.md`: the orchestrator commits it as `REPORT.md`. It contains:
- the table of every measurement;
- the recommendation for `HEAP_MB`, `MIN_HEAP_MB`, `MEMORY_HIGH`, render and simulation distance, and any JVM flags, each with why;
- what the owner will notice (for example, how far he sees the town);
- the method: commands, durations and the rig, so a reviewer can repeat it;
- known limits (headless rather than his screen, the development client rather than Prism).

## Rules

- Worktree `~/AresOS-41-home-memory`, branch `pkg/41-home-memory`, from main `79f0ad53`. Push with `git push origin pkg/41-home-memory`. Never merge, never push to main, never `--no-verify`.
- Before any game run, `free -g` shows at least 6 GiB available. One game client at a time on the laptop: take `~/.cache/aresos-dev/client-test.lock` for your runs. Never `./gradlew` outside the scripts' way of starting it, never `--force`.
- Headless compositors only; never `WAYLAND_DISPLAY=wayland-0`. Stop only processes you started, by PID.
- Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client.
- Change nothing under `os/` and no product code under `mod/src`. Measurement scripts go into `reviews/41-home-memory/`, each labelled as a development aid.
- The repo is public: no personal data, no names of his installed programs, no screenshots of his screen.
- `gh` only for `gh pr create` at the end (title "Package 41: how much memory the home screen needs", body ending with the two attribution lines the orchestrator gives).
- Commit and push after each part that works. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
