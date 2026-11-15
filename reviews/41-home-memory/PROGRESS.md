# Package 41: how much memory the home screen needs (progress)

Brief: `briefs/41-home-memory.md`. Branch `pkg/41-home-memory` from main `79f0ad53`. Builder: one Claude agent on
Opus 5.5 (measurement against a clear plan). No product code and nothing under `os/` changes.

## Status

- Done: the rig (`rig/`), the frame recorder (`frames/`), the base world with a town of 40 test logos
  (`.work/pkg41/AresHub-base`, untracked), set 1 of the distance runs (`runs/a*`), the flight check.
- Running: set 2 of the distance runs (`runs/d*`, corrected flight) and the heap ceilings 2048 / 1536 / 1024 / 768 at
  render 8, simulation 5 (`runs/h*`).
- Left, in order: `-Xms` and periodic-GC runs with 5 minutes covered at the chosen ceiling (`runs/c*`); one run of
  the whole recommendation with the recommended `MEMORY_HIGH` (`runs/v*`); the report in this file; the PR.

## Findings so far

- The heap is not where the memory goes. At heap 3072 G1 never committed more than about 600 MiB: the `-Xms512m`
  floor plus a little. The live heap after GC is about 320 MiB at render 8, 300 at 6, 270 at 4.
- Render and simulation distance barely move memory in the flat home: settled RSS 1338 to 1369 MiB across render
  8 / 6 / 4 and simulation 5 / 2 (set 1), within the run-to-run noise. GPU memory 306 to 316 MiB in every run.
- Covered for 5 minutes with G1's defaults, RSS does not go down (1453 MiB at render 8, 1394 at 6).
- Frame rate is the game's default cap of 120 in every window; worst frames 9 to 25 ms; no GC pause over 20 ms.
- What the town needs (`rig/town-reach.py`): with 28 of 40 apps in System & Tools (rows 0 to 4) render 6 is the
  least that has every logo loaded and drawn from home; his laptop's full list (42 in System & Tools, rows 0 to 5)
  needs 7 to 8. Render 4 is below what the town needs.

## What the code doesn't show

- **Never edit `rig/run.sh` while a run uses it:** bash reads a script as it goes; an edit broke the first A1 (kept
  as `.work/pkg41/rigs/pilot-a1`, not in the table).
- **Vanilla's inactivity limit:** with no input for 60 s the game draws 30 frames a second (10 after 10 minutes);
  the pilot's standing window showed exactly 30.0. The standing window therefore looks around slowly.
- **Key taps must last two ticks:** a 40 ms tap can fall between two game ticks. Set 1's double jump only sometimes
  started flying (A2 flew, the check run did not), so set 1's flight windows are not valid; set 2 holds each press
  and gap for 100 ms and lands first. `rig/check-flight.sh` with F3: 21 blocks up, 21.6 blocks a second, and 1263
  counts of relative motion for a half turn (1200 gave 171 degrees).
- On foot, a drifting run can walk into a doorway and open a test app, whose window then takes the keys. No measured
  run opened one (their helper logs list no start); the flight runs above the logos.
- The GC log prints uptime before timenanos whatever order `-Xlog` names them in.
- A `pgrep -f` wait whose own command line contains the pattern waits for itself.
