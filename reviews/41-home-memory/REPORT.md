# Package 41: how much memory the home screen needs (report)

Brief: `briefs/41-home-memory.md`. Branch `pkg/41-home-memory` from main `79f0ad53`. Builder: one Claude agent on
Opus 5.5 (measurement against a clear plan). No product code and nothing under `os/` changed; everything added is a
development aid under `reviews/41-home-memory/`.

## Summary

The home screen uses about **1.2 to 1.5 GiB** of memory (RSS) at his screen size, and almost all of it is fixed cost:
the Java heap holds only about **300 MiB** of live data, the JVM itself about 350 MiB, native graphics and chunk
buffers about 200 to 330 MiB, mapped program files about 200 MiB. Today's 3 GiB heap allowance is never used: at
every ceiling from 3072 down to 768 MiB, G1 committed at most about 620 MiB.

- **Render and simulation distance hardly change memory** in the flat home. Render 6 uses the same RAM as 8; only 4
  saves about 50 to 130 MiB, and 4 leaves two logos of a 40-app town out of view. Simulation 2 equals 5.
- **A 1024 MiB heap ceiling** passes every test of the brief (no `OutOfMemoryError`, longest GC pause after joining
  14 ms, the same frame times as 3072). Whether it also lowers daily memory is not measurable here (confounded with
  run order); it halves what the game may ever take.
- **G1's periodic collection gives nothing back** while a maximized app covers the world: it runs every 30 s, but each
  time about half the heap is free, and G1 only shrinks the heap when more than 70 % of it is free. A lower free ratio (`-XX:MaxHeapFreeRatio=30
  -XX:MinHeapFreeRatio=10` with `-Xms256m`) keeps the heap at about 390 MiB and saves **about 50 to 95 MiB** at every
  moment, covered too, for more GC work while flying over new ground.

## Recommendation

| Setting (`aresos-desktop`) | Today | Recommended | Why |
|---|---|---|---|
| `HEAP_MB` | 3072 | **1024** | The live heap after GC is 250 to 375 MiB in every run; G1 never committed more than about 620 MiB. 1024 passed the brief's floor test (no `OutOfMemoryError`, no GC pause over 50 ms in the flight, longest 14.3 ms after joining; frame times as at 3072). The 768 probe passed too but ran its heap at 607 of 768 MiB in the flight, so 1024 is the lowest listed ceiling with real margin (about 3x the live heap) for a bigger town and long sessions. |
| `MIN_HEAP_MB` | 512 | **256** | With G1's defaults `-Xms` changes nothing measurable (c3: the heap grew to 623 MiB anyway). With the free-ratio flags below it is the floor the heap can shrink to: G1 never shrinks the heap below `-Xms` (G1's rule; no run combined the flags with `-Xms512m`). |
| JVM flags | none | **`-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`** | Keeps the committed heap near the live data (about 390 MiB instead of 510 to 620): RSS about 50 MiB lower settled (c4, v1: 1223, 1194 against 1257 to 1290 in every default run at 1024 or less: c1 to c3, h3, h4), about 95 lower after the flight (1291, 1304 against 1384 to 1456 in the same runs) and about 85 lower covered (1271, 1282 against c2's 1362). Cost: about four times as many GC pauses while flying at full speed over new ground (165 and 174 instead of about 38: 99 and 106 young pauses plus 33 and 34 each of Remark and Cleanup, from about four times as many concurrent cycles; pauses still short, longest under 10 ms, together 331 and 324 ms in that minute instead of about 140; 99 and 104 % of a core instead of about 80 %); standing (36 to 37 %) and covered (7 to 8 %) CPU unchanged, and frames no worse (their worst frames, 11.2 to 13.6 ms, lie inside the default runs' 8.6 to 25.4). **Not** `G1PeriodicGCInterval`: it measured no gain (c2 against c1, c4). See JUDGMENT-CALL 1 and the m1 run. |
| `MEMORY_HIGH` | `5G` | **`2560M`** | The game's own scope peaked at 1136 to 1304 MiB in every run with room (`memory.peak`, anon plus a little cache). With a 1024 MiB heap its anonymous memory can reasonably reach the full heap plus about 0.7 GiB of the rest (scope anon minus the committed heap reached at most 717 MiB after a flight), about 1.75 GiB; 2560M sits above that, so it only acts on something abnormal (a native leak). In the product the scope also carries page cache the rig's did not: after a boot the game is the first to read its jars, libraries, assets and world, so `aresos-game-<id>.scope` will read higher than this table's scope peak (up to about RSS plus what it read); clean cache is the first thing reclaimed under `MemoryHigh`, so 2560M still holds (Known limits). v1 ran with it: no `high` event, scope peak 1136 MiB. v2 (1100M, below the game's need) shows the cost of too low a value: 322 throttle events, 165 MiB of the game pushed into swap, worst frames up to 32 ms. |
| `RENDER_DISTANCE` | 8 | **8** (unchanged) | No RAM to gain: render 6 used the same memory as 8 (after the flight 1462 against 1476 MiB, within the spread). 5 is the least that has the rig's 40-app town (28 in System & Tools) drawn and loaded from home, 6 from 30 apps in that group, and his laptop's full list (42 in System & Tools) needs 7. 4 would save about 50 to 130 MiB but leaves two logos of the biggest road (S3R3, S4R3) out of view from home. Render 6 would only save GPU memory (306 instead of up to 434 MiB of the RTX 4060's 8 GiB) and some CPU (74 against 80 % of a core flying). |
| `SIMULATION_DISTANCE` | 5 | **5** (unchanged) | 2 measured the same memory and CPU as 5 at render 6 (d4 against d2). Nothing in the town ticks. |

## What he will notice

- **In the world: nothing.** Same view distance (the terrain fades out 115 to 128 blocks away, as today), the same
  120 frames a second, no stutter: no GC pause over about 21 ms after joining in any run; with the flags the longest after
  joining was 13.7 ms (16.4 ms while the world loaded), and their frames were no worse than with G1's defaults.
- **In memory:** the home screen takes about 1.2 GiB while he stands at home and about 1.3 GiB after flying around,
  instead of about 1.3 and 1.45 GiB today; about 1.25 GiB instead of about 1.42 (a1) while an app covers it. The bigger
  change is the ceiling: today the game may grow to a 3 GiB heap plus about 1 GiB more before anything holds it back
  (and `MemoryHigh` at 5G); with the recommendation its own memory stops at about 1.75 GiB, and systemd starts holding
  it back at 2.5 GiB.
- **Battery, maybe:** flying fast over ground the world has not loaded before costs a fifth to a quarter of a core
  more with the flags (more garbage collections). Standing, walking the town and covered cost the same.

## What the town needs

Worked out with `rig/town-reach.py` from HUB.md 3.1 and 3.2 (where every logo block stands) and the game's own rules,
read from the 26.2 jars:

- **Which chunks are drawn:** `ChunkTrackingView.isWithinDistance`: a chunk dx, dz chunks from the player's is in view
  when `max(0, |dx| - 1)² + max(0, |dz| - 1)² < distance²`.
- **Where the fog is:** `FogRenderer`: terrain fades from `16 d - clamp(1.6 d, 4, 64)` to `16 d` blocks: render 8
  fades from 115 to 128 blocks, 6 from 86 to 96, 4 from 58 to 64.
- **What the mod needs loaded:** `swap`, `move`, `/go`'s spot check and the town's building pass want a logo's chunks
  loaded with their entities (`hasChunk`, `areEntitiesLoaded`), which the integrated server does out to the render
  distance (a drawn chunk is always loaded). Simulation distance only decides which loaded chunks tick. The circle
  rule describes the drawn chunks; the server may load further through its chunk tickets, so for "loaded" the
  distances below are upper bounds.

| Rows a group uses | Logos per group | Farthest logo corner from home | Render distance that has every logo drawn (and loaded) from home |
|---|---|---|---|
| 0 | 2 | 27 blocks | 2 |
| 0 to 1 | 6 | 46 blocks | 3 |
| 0 to 2 | 12 | 66 blocks | 4 |
| 0 to 3 | 20 | 86 blocks | 5 |
| 0 to 4 | 30 | 105 blocks | 6 |
| 0 to 5 | 42 | 125 blocks | 8 (7 for the east and south roads) |

A group fills its places by row, then by `k`, then L before R (HUB.md 3.3), so a row is used before it is full, and
the distance a town needs follows from its biggest group's count (`rig/town-reach.py`, place by place):

| Render distance | Most apps a group holds with every logo drawn from home: north, east, south, west |
|---|---|
| 4 | 18, 18, 19, 19 |
| 5 | 26, 28, 29, 27 |
| 6 | 38, 40, 41, 39 |
| 7 | 40, 52, 53, 41 |
| 8 | 54, 68, 69, 55 |

The roads differ because blocks on the negative side of home round down into the next chunk out (north from 27 apps,
west from 28 and east from 29 need 6). At 40 apps in his laptop's proportions, System & Tools holds 28: rows 0 to 3
and row 4 up to `k` = 3 on both sides (S4L4 and S4R4 stay empty). Render 5 has that whole town drawn and loaded from
home; on the south road it holds up to 29 apps, and S4R4, the 30th, needs 6. At 4 only two logos are out of view,
S3R3 and S4R3 (`swap` and `move` there would say "Stand at home and try again" even at home). From home he sees only
the front row anyway (the rows behind are hidden by it, HUB.md 2.2); along a road every next row is well inside even
render 4. His laptop's full list (61 programs, 42 of them System & Tools, HUB.md 5) fills rows 0 to 5 of the south
road and needs render 7 (S5R5, the 42nd); its other groups (9, 5 and 5 apps) need at most 4.

## Measurements

### Every run

| Run | Render / sim | -Xmx / -Xms | GC flags | RSS settled | PSS settled | Heap used / committed (settled) | NMT settled | RSS after flight | Peak RSS | Scope peak | GPU settled / after flight | Standing: fps, avg, p99, worst ms, CPU | Flying: fps, avg, p99, worst ms, CPU | GC pauses in flight, longest | Longest GC pause after joining |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a1-rd8-sd5-h3072 | 8 / 5 | 3072 / 512 | default | 1343 | 1227 | 298 / 518 | 871 | not valid | 1481 | 1304 | 306 / - | 120, 8.34, 8.46, 22.6 | not valid | not valid | 19.44 ms |
| a2-rd6-sd5-h3072 | 6 / 5 | 3072 / 512 | default | 1306 | 1189 | 319 / 516 | 867 | not valid | 1399 | 1219 | 316 / - | 120, 8.33, 8.46, 11.6 | not valid | not valid | 16.51 ms |
| a3-rd4-sd5-h3072 | 4 / 5 | 3072 / 512 | default | 1338 | 1221 | 349 / 512 | 864 | not valid | 1444 | 1259 | 316 / - | 120, 8.33, 8.46, 8.6 | not valid | not valid | 14.67 ms |
| a4-rd6-sd2-h3072 | 6 / 2 | 3072 / 512 | default | 1369 | 1254 | 391 / 518 | 870 | not valid | 1431 | 1252 | 306 / - | 120, 8.34, 8.47, 23.2 | not valid | not valid | 15.98 ms |
| d1-rd8-sd5-h3072 | 8 / 5 | 3072 / 512 | default | 1332 | 1215 | 392 / 524 | 878 | 1476 | 1476 | 1299 | 306 / 424 | 120, 8.33, 8.47, 9.4, 36 % | 120, 8.34, 8.49, 20.4, 80 % | 38, 19.37 ms | 19.37 ms |
| d2-rd6-sd5-h3072 | 6 / 5 | 3072 / 512 | default | 1358 | 1243 | 435 / 514 | 870 | 1462 | 1462 | 1284 | 306 / 306 | 120, 8.34, 8.45, 23.4, 34 % | 120, 8.34, 8.52, 13.0, 74 % | 34, 8.8 ms | 17.79 ms |
| d3-rd4-sd5-h3072 | 4 / 5 | 3072 / 512 | default | 1284 | 1173 | 481 / 512 | 869 | 1342 | 1342 | 1164 | 308 / 308 | 120, 8.33, 8.5, 8.8, 26 % | 120, 8.34, 8.52, 25.4, 55 % | 25, 21.33 ms | 21.33 ms |
| d4-rd6-sd2-h3072 | 6 / 2 | 3072 / 512 | default | 1331 | 1216 | 424 / 514 | 869 | 1436 | 1436 | 1258 | 306 / 306 | 120, 8.34, 8.47, 23.8, 35 % | 120, 8.34, 8.5, 13.1, 76 % | 34, 7.36 ms | 16.3 ms |
| h1-rd8-sd5-h2048 | 8 / 5 | 2048 / 512 | default | 1316 | 1204 | 301 / 517 | 870 | 1475 | 1475 | 1296 | 306 / 434 | 120, 8.33, 8.47, 10.5, 36 % | 120, 8.34, 8.5, 18.6, 78 % | 36, 17.75 ms | 17.75 ms |
| h2-rd8-sd5-h1536 | 8 / 5 | 1536 / 512 | default | 1334 | 1217 | 464 / 512 | 866 | 1451 | 1451 | 1273 | 306 / 424 | 120, 8.33, 8.46, 11.7, 36 % | 120, 8.34, 8.5, 19.0, 79 % | 37, 14.52 ms | 14.52 ms |
| h3-rd8-sd5-h1024 | 8 / 5 | 1024 / 512 | default | 1257 | 1143 | 368 / 512 | 860 | 1393 | 1393 | 1211 | 306 / 306 | 120, 8.34, 8.46, 22.6, 35 % | 120, 8.34, 8.49, 12.2, 81 % | 39, 6.75 ms | 14.25 ms |
| h4-rd8-sd5-h768 | 8 / 5 | 768 / 512 | default | 1290 | 1173 | 416 / 518 | 873 | 1409 | 1409 | 1232 | 316 / 316 | 120, 8.33, 8.46, 10.9, 34 % | 120, 8.34, 8.52, 20.6, 77 % | 35, 17.59 ms | 17.59 ms |
| c1-h1024-xms512-default | 8 / 5 | 1024 / 512 | default | 1268 | 1152 | 326 / 512 | 862 | 1384 | 1384 | 1207 | 316 / 424 | 120, 8.33, 8.45, 12.3, 36 % | 120, 8.34, 8.49, 18.4, 80 % | 38, 14.31 ms | 14.31 ms |
| c2-h1024-xms512-periodic | 8 / 5 | 1024 / 512 | -XX:G1PeriodicGCInterval=30000 | 1262 | 1147 | 319 / 515 | 868 | 1390 | 1390 | 1214 | 306 / 306 | 120, 8.34, 8.45, 12.0, 36 % | 120, 8.34, 8.49, 22.2, 79 % | 40, 16.9 ms | 16.9 ms |
| c3-h1024-xms256-periodic | 8 / 5 | 1024 / 256 | -XX:G1PeriodicGCInterval=30000 | 1269 | 1156 | 313 / 470 | 819 | 1456 | 1457 | 1284 | 306 / 424 | 120, 8.34, 8.49, 18.7, 37 % | 120, 8.34, 8.49, 14.4, 82 % | 37, 8.45 ms | 15.91 ms |
| c4-h1024-xms256-periodic-free30 | 8 / 5 | 1024 / 256 | -XX:G1PeriodicGCInterval=30000,-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 | 1223 | 1107 | 302 / 392 | 731 | 1291 | 1299 | 1144 | 316 / 316 | 120, 8.33, 8.46, 12.0, 36 % | 120, 8.34, 8.52, 13.6, 99 % | 165, 9.57 ms | 13.65 ms |
| m1-h1024-xms256-free40 | 8 / 5 | 1024 / 256 | -XX:MaxHeapFreeRatio=40,-XX:MinHeapFreeRatio=20 | 1198 | 1083 | 319 / 360 | 695 | 1359 | 1359 | 1197 | 306 / 434 | 120, 8.33, 8.46, 12.3, 38 % | 120, 8.34, 8.51, 13.5, 95 % | 116, 5.89 ms | 10.87 ms |
| v1-recommended | 8 / 5 | 1024 / 256 | -XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 | 1194 | 1082 | 329 / 385 | 725 | 1304 | 1304 | 1136 | 306 / 306 | 120, 8.33, 8.46, 11.2, 37 % | 120, 8.34, 8.53, 13.0, 104 % | 174, 4.77 ms | 13.25 ms |
| v2-memoryhigh-too-low | 8 / 5 | 1024 / 512 | default | 1290 | 1175 | 323 / 514 | 863 | 1276 | 1290 | 1103 | 316 / 424 | 120, 8.34, 8.47, 31.7, 36 % | 120, 8.34, 8.49, 24.6, 79 % | 36, 18.86 ms | 18.86 ms |

### Covered by a maximized app for 5 minutes (RSS in MiB)

| Run | -Xmx / -Xms | GC flags | RSS when covered | 1 min | 2 min | 3 min | 4 min | 5 min | Heap committed at 0 / 5 min | Scope at 5 min | GPU at 5 min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a1-rd8-sd5-h3072 | 3072 / 512 | default | 1481 | 1453 | 1453 | 1453 | 1453 | 1453 | 598 / 598 | 1274 | 295 |
| a2-rd6-sd5-h3072 | 3072 / 512 | default | 1399 | 1371 | 1393 | 1393 | 1394 | 1394 | 554 / 554 | 1213 | 295 |
| c1-h1024-xms512-default | 1024 / 512 | default | 1384 | 1355 | 1355 | 1355 | 1355 | 1355 | 612 / 612 | 1174 | 422 |
| c2-h1024-xms512-periodic | 1024 / 512 | -XX:G1PeriodicGCInterval=30000 | 1390 | 1362 | 1362 | 1362 | 1362 | 1362 | 610 / 610 | 1184 | 295 |
| c3-h1024-xms256-periodic | 1024 / 256 | -XX:G1PeriodicGCInterval=30000 | 1457 | 1431 | 1431 | 1431 | 1431 | 1431 | 623 / 623 | 1249 | 422 |
| c4-h1024-xms256-periodic-free30 | 1024 / 256 | -XX:G1PeriodicGCInterval=30000,-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 | 1299 | 1271 | 1271 | 1271 | 1271 | 1271 | 393 / 393 | 1115 | 295 |
| v1-recommended | 1024 / 256 | -XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 | 1304 | 1275 | 1282 | 1282 | 1282 | 1282 | 394 / 394 | 1108 | 295 |

**`MemoryHigh` below the game's need (v2, 1100M, G1 defaults):** the scope was held at 1099 MiB from the start; by the end of the flight systemd had counted 322 `high` events and the kernel had moved 165 MiB of the game into swap. The frame rate held (120); the worst frame, 31.7 ms standing, was the worst of all runs, and each window had two frames over 17 ms (other runs: 0 to 2). Mild at this level, because the laptop had swap to spare; set lower, or with less swap free, the game would stall on its own swapped-out memory.

How to read them: every run at 1920 x 1080, 144 Hz, render / simulation as listed, G1. Memory in MiB. RSS settled:
2 minutes after joining, no input. RSS after flight: right after the 60 s flight. Peak RSS: `VmHWM`. Scope peak: the
game's own systemd scope (`memory.peak`), which is what `MemoryHigh` acts on; it is lower than RSS because the
program files it maps were read into the page cache before this scope existed and stay charged to whoever read them
first. GPU: the game process's memory on the RTX 4060 (`nvidia-smi`). Frame columns: frames a second, average,
99th percentile and worst frame time in ms, and the game's CPU in % of one core. Set 1 (`a*`) flew only sometimes
(a key tap shorter than a game tick, see "What the code doesn't show"), so its flight columns are marked not valid;
its settled and standing numbers are good and repeat set 2's settings. a1's and a2's covered rows follow such a flight,
which may have loaded less new ground than a valid one: read them as today's covered level, not to the MiB. The raw
frame logs stay local (see Method).

**The spread between runs** of the same setting: settled RSS 1332 and 1343 MiB at render 8 / heap 3072 (d1, a1),
1306 and 1358 at render 6 (a2, d2), 1284 and 1338 at render 4: about 50 MiB. After the flight the runs at render 8
with G1's defaults (d1, h1 to h4, c1 to c3) lie between 1384 and 1476 MiB, a spread of about 90 MiB, and the game's
GPU memory does not explain it (c1: 424 MiB on the GPU and 1384 RSS; h3 and c2: 306 and 1393, 1390). Within that
spread the runs with a heap ceiling of 1536 or more (a1, d1, h1, h2) sit about 60 MiB above the default runs at 1024
or less (h3, h4, c1 to c3): settled 1316 to 1343 against 1257 to 1290 MiB, after the flight 1451 to 1476 against
1384 to 1456. But they all ran first (09:10 to 10:09 against 10:14 on), and 3072 gives G1 2 MiB regions where the
others use 1 MiB, so whether the lower ceiling saves about 50 MiB too is not measurable here: it is confounded with
run order. The flags' saving is not: c4 and v1 sit below every default run, and v2 ran last (11:17) with the
defaults and still settled at 1290 MiB.

### Where the memory goes (d1: today's settings, settled, 1332 MiB RSS)

| Part | MiB | Changes with |
|---|---|---|
| Java heap, committed | 524 (live data after GC: 270 to 375) | `-Xms`, G1's sizing; the recommended flags take it to about 390 |
| JVM itself (NMT without the heap): metaspace 119, code cache 72, G1's own structures 71, class space 26, symbols 23, shared classes 14, NMT 11, threads 7 | 354 | fixed (the game and its mods' code) |
| Native memory outside the JVM's tracking (the NVIDIA driver, LWJGL's buffers for chunk meshes) | 250 (313 after the flight) | render distance a little, the GPU driver |
| Mapped program files and shared memory (`RssFile`, `RssShmem`) | 146 + 56 | fixed |

## Method

**The rig** (`rig/`, every file a development aid; like package 40's rig it calls Gradle itself, `gradlew --no-daemon
runClient`, inside a scope of its own). One run is `rig/run.sh <name> KEY=value ...`:

- **The screen:** a headless labwc 0.9.6 (`WLR_BACKENDS=headless`, its own Wayland socket and Xwayland, never
  `wayland-0` or `:0`) with the image's `rc.xml`, its output set to 1920 x 1080 at 144 Hz with `wlr-randr` (his
  screens). The game is the session's maximized, frameless, always-on-bottom desktop window, rendering on the
  RTX 4060 with the same offload variables as `mod/dev/client-test.sh` and the supervisor (its log: `Using graphics
  backend OpenGL ... NVIDIA 615.78.08`).
- **The town:** the worktree's helper, unchanged, started through `rig/helper41.py`, which points its discovery at the
  rig's own folder only, so the town holds 40 test apps written by `rig/make-apps.py` (generated 128 x 128 pictures,
  names "Test Web 1" and so on) and none of the laptop's programs. The mix is the laptop's own proportions (HUB.md 5:
  9 / 5 / 5 / 42 of 61) scaled to 40: 6 Internet, 3 Games, 3 Work & Media, 28 System & Tools, so the south road has
  rows 0 to 4 and its farthest logos stand about 100 blocks from home.
- **The world:** made once through the title screen's AresOS button (Home: Flat), the town built ("The town is
  built: 40 logos"), saved, and kept as `.work/pkg41/AresHub-base` (untracked). Every run starts from a fresh copy,
  so every flight generates the same new ground.
- **The game's JVM and scope:** the JVM settings reach the development client through a Gradle init script
  (`rig/jvm41.gradle`, `-I`), never a product file: `-Xms<MIN_HEAP>m -Xmx<HEAP>m`, the GC flags under test,
  `-XX:NativeMemoryTracking=summary`, `-Xlog:gc:file=...:tn,u` and the frame recorder. The game starts through
  `rig/java-wrapper.sh`, installed as `bin/java` of a folder that otherwise links to the JDK (so Gradle takes it for
  the JDK), which runs it in a systemd user scope of its own with `MemoryHigh`, as the supervisor's `game_scope()`
  does; that scope's `memory.current`, `memory.peak` and `memory.events` are what `MEMORY_HIGH` acts on. Prism's
  instance gives the same heap settings (`MinMemAlloc`, `MaxMemAlloc`) and no GC flags, so G1 with the JVM's
  defaults is today's product.
- **Frame times:** `frames/`, a 3 KB Fabric mod added with `-Dfabric.addMods` (never part of the mod): a mixin at the
  head of `Minecraft.runTick`, which runs once per frame, writes `System.nanoTime()` into a fixed 512 KB ring that a
  daemon thread writes out every 250 ms. Frame time is the gap between two frame starts. GC pauses come from the GC
  log with the same clock (`timenanos`), so each pause falls into its window. The raw frame logs (`frames.txt`, about
  0.4 MB a run) stay local in `.work/pkg41/rigs/<name>/` with the game's and Gradle's logs, too big for the repo; the
  frame columns can be checked against each run's `summary.json`.
- **Memory:** `rig/snap.py` per snapshot: RSS (`VmRSS`, `VmHWM`), PSS (`smaps_rollup`), the heap
  (`jcmd GC.heap_info`), native memory (`jcmd VM.native_memory summary`), the scope's current and peak use and its
  `high` events, and the GPU memory of the game's process (`nvidia-smi -q -x`). `rig/sample.py` records RSS, the
  scope's use and the game's CPU time every 2 s. `rig/analyze.py` turns a run into `runs/<name>/summary.json`;
  `rig/table.py` prints the tables above.

**One run** (`MODE=measure`): copy the base world, set `renderDistance` and `simulationDistance` (and
`tutorialStep:none`) in `mod/run/options.txt`, take the client-test lock, start, wait for "joined the game", then:

1. settle 120 s without input; snapshot `settled`;
2. **standing at home**, 60 s: H (on the pad facing north), then a slow 30-degree turn right and back every 3 s.
   Without input for 60 s vanilla draws only 30 frames a second (10 after 10 minutes; his default too), which would
   hide the frame times: the pilot run's standing window showed exactly 30.0. Snapshot `stand`;
3. **flying**, 60 s: H, Shift (land), a double jump, 2.5 s up (21 blocks above the ground, over the 12-block logos and
   their signs), then sprint-flying north along the Internet road for 15 s, a half turn, 30 s south over home and down
   the System & Tools road, a half turn, 15 s north. Every key press and gap lasts 100 ms (two game ticks). About
   1300 blocks: the town passed three times and new ground generated up to about 320 blocks out on both sides.
   `rig/check-flight.sh` checked it with F3 in a held rig: after the second leg X 105, Y 85, Z 314, i.e. 21 blocks up
   at 21.6 blocks a second; a half turn is 1263 counts of relative pointer motion (set 1 used 1200, which turned
   171 degrees). Snapshot `flight`; a picture right after (`shots/after-flight.png` in the rig folder) shows him in
   the same spot above the town in all 15 runs from set 2 on;
4. with `COVER=300`: a `foot` window of the rig's own, maximized through foreign-toplevel (package 40's `rig/tl.py`):
   the helper reports the world covered and the mod pauses it at 10 frames a second ("Saving and pausing game" in its
   log); a snapshot at once and every minute for 5 minutes;
5. two pictures, then the game's scope and the rig are stopped and `rig/analyze.py` writes the summary.

Before every run `mod/dev/env.sh`'s check passed (6 GiB available, no Lunar Client) and the run held
`~/.cache/aresos-dev/client-test.lock`; one game at a time, and `run.sh` refuses to start next to another run of the
rig. Stopped were only this rig's own scopes (`pkg41-rig-*`, `pkg41-game-*`) and processes.

**To repeat:** `frames/build.sh`; `rig/run.sh setup MODE=hold` (title screen: AresOS, Create AresOS world, wait for
"The town is built: 40 logos", H, then close the game window with `reviews/40-real-home/rig/tl.py <rig folder> close
aresos-desktop`); copy `mod/run/saves/AresHub` to `.work/pkg41/AresHub-base`; then each run as its `settings.txt`
lists, for example `rig/run.sh v1-recommended HEAP=1024 MIN_HEAP=256
GC=-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 MEMHIGH=2560M COVER=300`; then `rig/table.py`.

## Combinations run, and the ones skipped

The brief's grid: render 8 / 6 / 4 with simulation 5 / 2; heap ceilings 3072 / 2048 / 1536 / 1024 at the chosen
distances; G1 against G1 with periodic uncommit, 5 minutes covered; 1920 x 1080. Run (19 measured runs):

- **Distances at heap 3072**, twice (set 1 `a*`, set 2 `d*`): render 8, 6, 4 with simulation 5, and simulation 2 at
  render 6. **Skipped:** simulation 2 at render 8 and at render 4. At render 6, simulation 2 against 5 made no
  difference in memory (settled 1331 against 1358 MiB, after the flight 1436 against 1462) or CPU (76 against 74 % of
  a core flying); simulation distance only decides which loaded chunks tick, and little ticks in the flat home.
- **Heap ceilings at render 8, simulation 5** (`h*`, and d1 for 3072): 2048, 1536, 1024, plus **768** as a probe
  below the brief's list to see how much margin 1024 has. Render 8 because distances do not decide memory and his own
  program list needs 7.
- **GC with 5 minutes covered at the chosen ceiling 1024** (`c*`): G1's defaults (c1) against
  `-XX:G1PeriodicGCInterval=30000` (c2), both at `-Xms512m`; then `-Xms256m` with periodic GC (c3); then, because
  neither gave anything back, `-Xms256m` with periodic GC and `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10` (c4).
  A1 and A2 add the covered default at today's ceiling 3072.
- **The recommendation as a whole** (v1: 1024 / 256, the two free-ratio flags without periodic GC, `MemoryHigh`
  2560M, 5 minutes covered); **a middle free ratio** (m1: 40 / 20) to see whether less GC work keeps most of the
  gain; and **`MemoryHigh` below the game's need** (v2: 1100M) to show what too low a value costs.
- **Window size:** every run at 1920 x 1080 (his screens), 144 Hz. **Skipped:** a run at package 40's 1280 x 720:
  its 1370 MiB at render 8 lies within this study's spread for the same setting at 1920 x 1080 (1332 to 1343 MiB
  settled), and the game's GPU memory (306 MiB) was the same in every run before a flight, so the window size is not
  where memory goes.

## Known limits

- **Headless, not his screen.** The rig's labwc draws to a virtual 1920 x 1080 output at 144 Hz on the RTX 4060; his
  session shows the world on a real panel, maybe on an external monitor. Window size, refresh and the GPU are the
  same; scan-out, the outer desktop and a second screen are not.
- **The development client, not Prism's instance.** Loom's `runClient` loads Minecraft, Fabric API and the mod from
  the build folders with the development launcher and adds its own JVM arguments (`-XX:StackShadowPages=32`,
  `--enable-native-access`, every Fabric API module on the class path). Prism starts the same game, loader, Fabric API
  and mod from jars with `-Xms`/`-Xmx` and no GC flags. Class metadata, code cache and mapped files differ a little;
  the heap, the chunks, the town and the graphics work are the same. Absolute numbers may differ by a few tens of
  MiB; the comparisons between settings hold.
- **Page cache in the game's scope.** In the rig the game's scope held almost no file pages (`memory.stat` file at
  most 38 MiB): its jars, libraries and assets had been read by Gradle and earlier runs, whose cgroups keep the
  charge (`RssFile` 143 to 149 MiB, `RssShmem` 54 to 58). On his laptop after a boot the game is the first reader of
  the client jar, the libraries, the assets and the world, so `aresos-game-<id>.scope` carries those pages and its
  `memory.current` and `MemoryPeak` read higher than this report's scope peak, up to about RSS plus what it read.
  `MEMORY_HIGH` must leave room for the anonymous memory, at most about 1.75 GiB with a 1024 MiB heap (1024 plus the
  at most 717 MiB of the rest measured after a flight); clean cache is reclaimed first under `MemoryHigh`, so 2560M
  holds. The rig's scope also ran in `app.slice` with `--collect`, the product's in `aresos.slice` without it;
  neither slice has limits, so the numbers are the same.
- **The frame recorder** adds a 512 KB array and one daemon thread, the same in every run.
- **A test town, not his.** 40 test apps with plain generated pictures in his laptop's group proportions. His own
  pictures do not change the memory (a logo is blocks), but a town of all 61 of his programs would reach row 5.
- **One flat world, short runs.** Each run is 5 to 10 minutes in a fresh copy of the same world. Hours of use, a
  world he has built in, other dimensions and many apps open over the world are not measured. The heap's live data
  (about 300 MiB here) is the number to watch there; the recommended ceiling leaves about three times that.
- **Single runs per setting,** with set 1 and set 2 as repeats of the distance settings for their settled and standing
  parts, and c4 / v1 as repeats of the free-ratio flags. Differences under about 50 MiB settled and about 90 MiB
  after the flight are noise, and the runs' order is mixed in (see "The spread between runs").
- **The frame rate is capped** by the game's default (120 frames a second, `maxFps:120`, vsync on) in every window, so
  the frame numbers show hitches (the worst frame), not how much faster a setting could draw.
- **CPU** is the game process's own time from `/proc`, sampled every 2 s, from set 2 on.

## Done

- `rig/`: the measurement rig (start, inner, helper wrapper, test apps, Gradle init script, java wrapper, virtual
  input with relative motion, snapshot, sampler, analysis, tables, flight check, town reach).
- `frames/`: the frame recorder mod and its build script.
- `runs/<name>/`: every run's summary, settings, marks, GC log, snapshots (`snap-*.json`, `nmt-*.txt`), samples.
- This report.

## Verified

- All runs listed in the tables, with the commands in each `settings.txt`. The flight with F3 (`check-flight.sh`).
  The cover pausing the world: "Saving and pausing game" in the game log and 10.0 frames a second in every covered
  window. No measured run opened a test app (their helper logs list no start). No `OutOfMemoryError`, no Full GC, and
  the town never frozen in any run.

## Not verified

- On his own screen with Prism's instance and his own programs: the next release's numbers on his laptop would
  confirm them: `ps -o rss` of the game, and in its scope (`/sys/fs/cgroup/user.slice/user-<uid>.slice/user@<uid>.service/aresos.slice/aresos-game-<id>.scope/`)
  `memory.stat`'s `anon` and `memory.events`' `high`. Not `MemoryPeak` alone: it also counts the page cache the game
  read first after a boot, so it will read higher than this report's scope peak without anything being wrong.
- Hours-long sessions and a heavily built world.

## JUDGMENT-CALL

1. **The free-ratio flags.** I recommend `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10` with `MIN_HEAP_MB=256`:
   about 50 to 95 MiB less at every moment and frames at least as smooth, for about four times as many GC pauses
   (and concurrent cycles) while flying fast over new ground (99 and 104 % of a core instead of about 80 % for that
   minute). Rejected: G1's defaults (`HEAP_MB=1024`, `MIN_HEAP_MB=512`, no flags), whose saving in daily use is not
   measurable here (confounded with run order). A gentler middle (m1: `MaxHeapFreeRatio=40`, `MinHeapFreeRatio=20`)
   kept most of the gain (1198 MiB settled, heap 360 to 434 MiB) with 116 GC pauses in the flight (70 young) instead
   of about 170 and 95 % of a core; it ran once and without
   the covered phase, so I recommend the pair validated twice (c4, v1), with 40 / 20 as the choice if the flight's CPU
   matters more than about 40 MiB. Changing it later: the flags are two instance keys in `aresos-desktop` (PLAN-GAP
   3), and the same keys take them out again.
2. **Render distance stays 8.** Memory does not ask for less, and his full program list needs 7 (a 40-app town 5).
   Rejected: 6 (saves GPU memory and a little CPU, not RAM, and holds at most 41 apps in System & Tools) and 4 (two
   logos of a 40-app town out of view from home).

## PLAN-GAP

- The brief's expected lever, the heap ceiling, has no measurable effect on daily memory here: G1 sizes the heap from
  the live data and `-Xms`, not from `-Xmx`, and the about 60 MiB that the runs at 1536 or more sat above those at
  1024 or less is confounded with run order (and 3072's bigger regions). The ceiling bounds the worst case; the daily
  number moves measurably with G1's free ratios.
- `G1PeriodicGCInterval` (the brief's "periodic uncommit") does not return memory here. It does fire: every 30 s
  while covered, 8 times in c2's and 9 in c3's five covered minutes (9 and 10 in the whole run), each a step of a
  concurrent cycle that ends in a Remark. But at every Remark about 48 % of the heap was free (c2: `Pause Remark
  319M->319M(610M)`), under the default `MaxHeapFreeRatio=70`, so G1 gave nothing back. With the free-ratio flags the
  heap is small enough that a young collection comes every 20 to 25 s even while covered, so the 30 s periodic
  collection never fired in c4; adding it to the flags gains nothing.
- The brief asks for JVM flags, but the supervisor's `instance_config` writes none today: the flags need two more
  instance keys there (Prism's `OverrideJavaArgs=true` and `JvmArgs=...`; check the key names against the pinned
  Prism), a change for `linux-aresos` with its own test.

## Open questions

- None that block. Whether to take the flags (JUDGMENT-CALL 1) is the lead's call.

## What the code doesn't show

- **Never edit `rig/run.sh` while a run uses it:** bash reads a script as it goes; an edit broke the first A1 (kept
  as `.work/pkg41/rigs/pilot-a1`, not in the tables).
- **Key taps must last two ticks:** a 40 ms tap can fall between two game ticks. Set 1's double jump only sometimes
  started flying, so set 1's flights are not valid; set 2 holds each press and gap for 100 ms and lands first.
- A drifting run on foot can walk into a doorway and open a test app, whose window then takes the keys (it happened
  in the first flight check, never in a measured run).
- He is still flying when a flight ends, and H puts him on the pad hovering: a double jump then ends flying
  instead of starting it. Land first (Shift); landing ends flying. (The rig also hands the keyboard back to the
  world with `tl.py activate aresos-desktop` after the cover closes.)
- The GC log prints uptime before timenanos, whatever order `-Xlog` names them in.
- A `pgrep -f` wait whose own command line contains the pattern waits for itself.
- `G1PeriodicGCInterval`, `MaxHeapFreeRatio` and `MinHeapFreeRatio` are manageable flags: `jcmd <pid> VM.set_flag`
  changes them in a running game, which makes trying values on his laptop cheap.
