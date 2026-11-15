# Package 41: how much memory the home screen needs (progress)

Brief: `briefs/41-home-memory.md`. Branch `pkg/41-home-memory` from main `79f0ad53`. Builder: one Claude agent on
Opus 5.5 (measurement against a clear plan). No product code and nothing under `os/` changes.

## Status

- Done: the rig (`rig/`), the frame recorder (`frames/`), the base world with a town of 40 test logos.
- Left, in order: the runs below, then the table, the recommendation and the method in this file, then the PR.

## Plan of runs

Every run: the development client in a headless labwc at 1920 x 1080, 144 Hz (his screens), the image's `rc.xml`,
the worktree's helper seeing only 40 test apps of the rig's own, a fresh copy of the same base world, the game in a
scope of its own with `MemoryHigh` (as the supervisor starts it), 2 minutes to settle, then a snapshot, 60 s standing
at home, 60 s flying at full speed along the roads, a snapshot after each.

1. Distances at today's heap (3072 MiB, G1 as the JVM picks it): render 8 / simulation 5 (today, with 5 minutes
   covered), 6 / 5 (with 5 minutes covered), 4 / 5, and simulation 2 at the chosen render distance.
2. Heap ceilings 2048, 1536, 1024 at the chosen distances, each with 5 minutes covered (G1 default).
3. G1 with `-XX:G1PeriodicGCInterval` at the chosen heap, 5 minutes covered.
4. One run of the whole recommendation, with the recommended `MEMORY_HIGH` on the game's scope.

Combinations skipped and why are recorded with the results.
