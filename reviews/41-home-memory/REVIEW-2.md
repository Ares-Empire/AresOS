Verdict: CHANGES-NEEDED

# Package 41: review 2 (fresh reviewer, Claude Opus 5.5)

Reviewed: branch `pkg/41-home-memory` at `c58a553e` (PR #75), the fixes `9ee8cbf6..c58a553e` against REVIEW-1 and
`briefs/41-review-fixes-1.md`, and the six new runs from their raw files: the committed `runs/<name>/` and the local
`.work/pkg41/rigs/<name>/` (`frames.txt`, `game.txt`, the rig's pictures). Read-only: no game, Gradle, labwc or rig was
started.

All four recommended values still hold, and review 1's findings are closed. Two numbers in the new reasoning are
wrong, though:
- **The creation table misses the freeze at the Create click.** Every creation froze the picture, at today's settings
  too, so n0's 5.7 s freeze did come back.
- **The `MEMORY_HIGH` row's "at most 717 MiB"** is exceeded by the new runs.

Neither changes a recommended value; both change what the lead is told. Three more points correct how the Nether runs
are read.

## Findings

1. **blocking: the creation windows leave out the freeze at the Create click, so "it did not come back" is wrong**
   (`REPORT.md` lines 182 to 185, 205 and 206, 212 to 218; `rig/analyze.py` line 62).
   `window()` counts only the gaps between frames that *start* inside the window. The frame that handles the click
   starts 2 to 10 ms before the `create_start` mark, so its gap is counted only when it happens to start after the
   mark. That happened in n0 and nowhere else. From `frames.txt`, the gap in progress at the click:

   | Run | Settings | Freeze at the click | Report's worst frame "Create to joining" | Server "Time elapsed" | GC in the freeze |
   |---|---|---|---|---|---|
   | f1, flat | recommended | **2143 ms** | 201.5 | 1502 ms | 19 pauses, 47 ms; heap 309 MiB |
   | setup-world, flat (by hand) | today's | **1981 ms** | - | 1432 ms | - |
   | n0, Nether | recommended | **5693 ms** | 5693.2 | 6113 ms | 30 pauses, 86 ms, at most 10.0; 6 concurrent cycles; heap 308 MiB throughout |
   | n4, Nether | recommended | **3748 ms** | 233.3 | 4341 ms | 16 pauses, 60 ms; 3 cycles; heap 488 → 339 to 354 MiB |
   | n3, Nether | today's | **3673 ms** | 63.2 | 4315 ms | 7 pauses, 36 ms; 1 cycle; heap 514 MiB |

   The same window edge drops the frame at joining from both `create` and `first_30s`: n0 206 ms, n3 244 ms. n4's
   233 ms at joining fell inside `create`.

   - **What the freeze is.** In all five creations the picture stops at the click. It comes back when the server has
     picked the spawn and saved once, just before "Loading N chunks for player spawn". It covers the data-pack load,
     the server start, "Selecting global world spawn" and the first saves. It is the game's own creation flow, with
     the same length at both settings: flat 2.1 s against 2.0 s, Nether n4 3.7 s against n3 3.7 s.
   - **Not GC, as the report says, and now shown properly.**
     - The pauses during n0's freeze total 86 ms of 5.7 s.
     - The heap never resized during it (308 MiB), so nothing stalled on heap expansion.
     - There was no humongous-allocation GC, to-space exhaustion or Full GC inside it. The one "Evacuation Failure:
       Pinned" came 6.9 s after the click.
     - n0's extra 2 s sits in the server's spawn search: "Selecting global world spawn" took about 3 s against 1 to
       2 s in n3 and n4. The first 2 s after the click used only 2.6 cores, against 4.3 (n4) and 3.9 (n3). So n0 was
       waiting on something rather than computing.
   - **What is not excluded.**
     - Safepoints other than GC are not logged: there is no `-Xlog:safepoint`.
     - The flags keep G1 marking almost continuously while a world is created: 6 cycles in n0's 5.7 s, against 1 in
       n3's 3.7 s. But n4 had the same rate and was as fast as n3.

     So nothing points at the settings, but one slow run in two can't rule them out.
   - **What the lead should be told.** Creating a home freezes the create screen for about 2 s (flat) or about 4 s
     (Nether) after the Create click, the same as today. Once in two Nether creations at the new settings it took
     5.7 s. The extra time was in the server's spawn search, not in GC pauses, and the cause was not found. It is a
     one-time wait at creation, not a stall in daily use. Measured against the brief's pass line, the Nether
     creation is worse than the flat one at either setting: that is the Nether's own cost.

   **Fix:**
   - In `window()`, also count the gap in progress at the window's start: include the last frame that starts before
     `start`. Rerun `analyze.py` and `table.py` on the local rig folders; no game is needed.
   - Correct the creation table and the f1 and n0/n3/n4 text: "The loading screen's slowest frame was 202 ms" and
     "It did not come back".
   - Add the creation freeze to "What he will notice" and Known limits, worded as above.
   - Optional, if the lead wants n0 settled: two more Nether creations per setting with `-Xlog:safepoint`. They are
     cheap: 4 minutes each with `SETTLE=30 SHOTS=0`.

2. **blocking: "the rest" reached more than 717 MiB in the new runs** (`REPORT.md` line 36, lines 47 to 49,
   lines 387 and 388).
   The `MEMORY_HIGH` reasoning says scope anon minus the committed heap "reached at most 717 MiB after a flight", so
   the worst case is about 1.75 GiB. The new runs' own snapshots go higher:
   - n2: 838 after the glide and 839 covered;
   - n3: 736 standing;
   - n4: 732 standing, at the recommended settings.

   Almost all of the increase is native memory outside the JVM's tracking (`RssAnon` minus NMT): n2 452 to 489 MiB,
   n4 336 to 388 MiB.

   2560M still holds. 1024 + 839 MiB is about 1.82 GiB, which leaves about 0.7 GiB for page cache and growth. But
   the number is wrong, and so is the wording in "What he will notice": "its own memory stops at about 1.75 GiB".
   Only the heap is capped; native memory is not.

   **Fix:**
   - Use the highest measured rest: about 840 MiB (n2), so the worst case is about 1.85 GiB.
   - Say "should stay under about 1.85 GiB (the heap is capped at 1 GiB, the rest is not)".
   - Keep the conclusion that 2560M holds.

3. **should-fix: the glide looked backwards on its northbound legs, so it is an upper case only for the server**
   (`REPORT.md` lines 322 to 326, 405 to 407).
   The rig's own glide check shows this: `.work/pkg41/rigs/pilot-nether-spectator/shots/g-leg1.png` and
   `g-leg2.png`, F3 on, the same sequence as `check-flight.sh … glide`.
   - **Leg 1:** Z -258.3, so he was moving north, but "Facing: south (0.0 / 20.0)".
   - **Leg 2:** Z +334.8, moving south, still "Facing: south (0.0 / 20.0)", although the rig's 1263-count half turn
     ran between the two pictures.

   The Nether home faces south (yaw 0). The glide copies the flat route's legs, north first, while the flat home
   faces north. A `tp` every tick most likely keeps resetting the camera to the server's rotation, so the mouse turns
   did nothing. So legs 1 and 3, 30 of the 60 s, glided with the camera looking backwards.

   The server's load is unaffected: it generates and sends chunks wherever he faces. That part is an upper case, as
   the report says. The client compiles only the chunk sections in view, though. New ground behind the camera was not
   meshed until leg 2 looked at it. So the meshing side (native buffers, GPU memory, the compile threads) is not shown
   to be an upper case. "The camera turns with him as in the flat flight" is not what happened.

   This does not touch the heap recommendation: meshes live in native memory, and the client's chunk storage is the
   same whichever way he looks. It does touch the native margin in finding 2.

   **Fix:** correct the Method text and the Known limit. Then either:
   - say that the client-side half is not an upper case, and accept that limit; or
   - give the pack's teleports an explicit rotation (`tp @s ^ ^ ^1.08 180 20` on the northbound legs, `0 20` on the
     southbound one), drop the mouse turns for `FLIGHT=glide`, and repeat n1 and n2 (about 10 minutes each).

4. **should-fix: the Nether savings and the noise bands rest on single runs, inside a larger native spread than
   stated** (`REPORT.md` lines 26 and 27, 52 to 54, 222 to 226, 399 to 401).
   Native memory outside the JVM's tracking varies a lot between runs at the *same* settings:
   - n0 and n4, the same Nether creation at the recommended settings, stood at **1235 and 1394 MiB**, 159 MiB apart.
     Their heaps were the same (456 and 448 committed); the native part was 229 against 388.
   - f1 and v1, flat home at the recommended settings: 1197 against 1304 after the flight. Native 144 against 365.
   - n2 against n1 (today's against recommended, the same glide): of the 340 MiB after the glide, the committed heap
     explains 121 (726 against 605) and native memory about 200 (452 against 255).

   So the Nether saving that can be pinned on the flags is the heap's: about 80 MiB settled and 120 to 200 MiB after
   new ground. "About 190 MiB settled and 340 to 420 after loading new ground" is one pair of runs inside a spread of
   about 150 MiB. The direction holds in all three Nether pairs (n1/n2, n0/n3, n4/n3).

   **f1's low native memory does not undermine the recommendation.** The flat-home case for the flags rests on the
   committed heap, which is G1's deterministic sizing: c4 and v1 sit at 385 to 394 MiB against 512 to 623 in every
   default run. Their native part (271 to 288 settled) lies inside the default runs' 197 to 303. And for
   `MEMORY_HIGH` only the highest native value matters (finding 2), never f1's low one. f1 only shows that the
   "50 MiB settled, 90 MiB after the flight" noise in Known limits is too narrow.

   **Fix:**
   - State the Nether saving as the heap part, with the RSS figures as one pair.
   - Widen the noise statement to about 150 MiB between runs of the same settings, from native memory outside
     NMT, citing n0/n4 and f1/v1.
   - The comparisons are also in run order, n2 after n1 and n3 after n0; say so as in "The spread between runs".

5. **nit: "with the flags the longest after joining was 13.7 ms"** (`REPORT.md` line 44). n1 had 14.7 ms after
   joining. **Fix:** 14.7 ms (n1).

6. **nit: f1's 200 MiB of file pages are not "the world files the game had just written"** (lines 209 and 210).
   The flat base world is 8.3 MiB on disk (`.work/pkg41/AresHub-base`), and f1 already had 200 MiB of file pages when
   it settled, before the flight. The point still holds: f1 was the first reader of something no earlier run had kept
   in cache. **Fix:** "file pages it was the first to read (or write)", without naming the world.

7. **nit: the page-cache limit's ranges predate the new runs** (lines 382 to 384). "`memory.stat` file at most
   38 MiB", "`RssFile` 143 to 149" and "`RssShmem` 54 to 58" are exceeded: f1's scope held 200 to 202 MiB of file
   pages, `RssFile` reached 156 and `RssShmem` 66 (f1, n0, n3). **Fix:** "except f1", and widen the ranges.

8. **nit: small gaps in the pass table and the summary** (lines 25, 190 to 196, 129 and 130).
   - n4, a run at the recommended settings, is missing from the pass table. It passes: 10.85 ms after joining, scope
     1200 MiB, no `high` event, 0 frames over 17 ms standing.
   - n4's heap reached 629 MiB committed and n3's 628, both 0.3 s after `done`, while the rig stopped the game. The
     summary's "605 (650 while n0 saved and quit)" leaves n4 out.
   - n4's "RSS settled" in the main table is after 30 s, not 2 minutes, and its row does not say so.

9. **nit: the glide's frames are "no worse" for hitches, but not for p99** (lines 228 to 230). n1's p99 was 10.8 ms,
   against n2's 9.7 ms and about 8.5 in every flat flight. That fits its 142 GC pauses against 60: about 2 % of the
   frames carry a pause of 2 to 4 ms. There were no frames over 33 ms in either run. **Fix:** say "no more hitches;
   p99 about 1 ms higher from the extra GC pauses".

## Review 1's findings

| # | Closed? | Where, and what I checked |
|---|---|---|
| 1 | yes | Lines 14, 37, 71 to 98 and 446 to 448. An independent recomputation from HUB.md 3.1 to 3.3 matches `town-reach.py` road by road: the L columns at `-(FIRST + PITCH k + 11) + u`, the fill order by row, then `k`, then L before R, floor division into chunks, and the `isWithinDistance` rule. North needs 6 from 27 apps (N4L3), west from 28 (W4R3), east from 29 (E4L4), south from 30 (S4R4). Most apps per group at render 4 to 7: 18/18/19/19, 26/28/29/27, 38/40/41/39 and 40/52/53/41. At 28 apps on the south road only S3R3 and S4R3 need 5. The full list (42) needs 7 (S5R5). The other groups (9, 5, 5) need at most 4. The builder's per-road difference from review 1's wording is right: review 1 counted the south road only. |
| 2 | yes | Lines 19 to 22 and 456 to 461. The GC logs show `G1 Periodic Collection` 9 times in c2 and 10 in c3 over the whole run, 8 and 9 inside the covered window, exactly 30.0 s apart. They are steps of concurrent cycles (Concurrent Start, then Prepare Mixed, then Mixed), as the report now says. Review 1's "each started a cycle" was loose. c2's last Remark: `319M->319M(610M)`, 48 % free. Young gaps while covered: c4 19.8 to 24.3 s and v1 20.9 to 25.1 s, so no periodic collection could fire. c1's gaps were 87 to 97 s. The builder's wording is right. |
| 3 | yes, with nits 6 and 7 | `MEMORY_HIGH` row, Known limits and Not verified. The supervisor runs the game in `aresos.slice` without `--collect` (`aresos-desktop` lines 721 and 740), as stated. |
| 4 | yes, with findings 1 to 4 | Six runs added. |
| 5 | yes | Lines 161 to 170 and 452 to 455. The GPU explanation is dropped, the spread is 1384 to 1476 MiB (a1's invalid flight is rightly left out), and "confounded with run order" replaces "saves nothing". |
| 6 | yes | Line 35 says "no worse"; JUDGMENT-CALL 1's "at least as smooth" is acceptable. |
| 7 | yes | 99 + 33 + 33 = 165 and 106 + 34 + 34 = 174; the pause totals are 331 and 324 ms; m1 has 70 young pauses. |
| 8 | yes | Line 34. |
| 9 | yes | The column is "after joining"; line 44 adds the loading figure (nit 5 aside). |
| 10 | yes | 1.42 GiB (a1), native 250 / 313 (d1), and the note on a1's and a2's covered rows. |
| 11 | yes | Method, lines 272 to 274. |

## What I checked and found right

- **Every number of the six new runs** in both main tables, the covered table, the creation table (except the
  worst-frame column, finding 1) and the pass table, recomputed by an independent script from the snapshots,
  `gc.txt`, `samples.csv` and the local `frames.txt`:
  - RSS, PSS, heap, NMT, GPU, `VmHWM` and scope peaks;
  - stand and flight frames and CPU;
  - GC pauses in the flight, with their longest and total (n1 142 / 8.42 / 346 ms, n2 60 / 9.0 / 198 ms);
  - the longest pause after joining;
  - the covered series;
  - for creation: heap before GC and committed, RSS and scope most, and the town build (3.0 s, 136.4 ms, 7/2/1).

  All match.
- **The pass line holds for every run at the recommended settings (f1, n0, n1, n4).**
  - No `OutOfMemoryError` in any game or Gradle log.
  - No Full GC, no `high` event and no swap.
  - `memory.high` is 2684354560 (2560M), or 5G for n2 and n3.
  - The longest GC pause after joining is 14.7 ms.
  - Hitches are no worse than in the flat runs (finding 9 aside), apart from the creation freeze, which is the same
    at today's settings (finding 1).
- **The glide ran as described.**
  - n1 and n2 logged "pkg41 glide ticks: 1200", with no "Can't keep up".
  - The pilot's F3 pictures show Y 64.2, Z -258 after leg 1 and +335 after leg 2: 20 ticks a second at 1.08 blocks,
    so full sprint-flying speed.
  - It loads new ground from z of about -287 to +361, as stated.
- **The glide stays in the rig.**
  - The pack and `prepare-glide.py` live only under `reviews/41-home-memory/rig/`. The pack's three functions and its
    `pack.mcmeta` are the rig's own; no vanilla file is copied.
  - `prepare-glide.py` writes only into the save it is given, and refuses unless exactly one `allowCommands` byte tag
    exists.
  - `run.sh` takes `BASE` only as a folder name in `.work/pkg41`.
  - The branch changes nothing outside `briefs/41-*` and `reviews/41-home-memory/`.
  - `mod/run/` is ignored by git, and its current `AresHub` (n4's) has no data pack.
- **Repo hygiene of the new files.**
  - Only text, JSON and CSV; no pictures and no binaries.
  - The only paths are `/var/home/ares/...`, plus uid 1001 in cgroup paths.
  - Test apps are "Test <word> <n>", and the output is `HEADLESS-1`.
  - No hostname, no names of his programs and no personal data.
  - The player names (`PlayerNNN`) and the pictures with the laptop's CPU and GPU stay in `.work/`, untracked.
- **The recommendation follows.**
  - The live heap in the Nether stayed under about 425 MiB after mixed collections (n2; n1 at most 412), so 1024
    leaves about 2.4 times that.
  - The committed heap never passed 650 MiB, and that only while saving at quit.
  - The free-ratio flags' saving rests on the flat-home heap sizing, which the new runs repeat (f1 442 to 499
    committed, n1 445 to 605, against 528 to 726 for n2).
  - Render 8 and simulation 5 are unaffected.

## Summary

Review 1's eleven findings are closed, and the two places where the builder departs from review 1's wording are
right: the render distance depends on the road, and periodic GC fired every 30 s while covered. Every new run's number
recomputes from its raw files, except one column. The creation windows start a few milliseconds after the frame that
handles the Create click, so they miss the freeze that every creation has. That freeze lasts about 2 s for the flat
home and about 3.7 s for the Nether, at today's settings too. So n0's 5.7 s did come back, in a shorter form, in n3 and
n4. It is not GC and probably not the settings, but the lead should hear it plainly. The `MEMORY_HIGH` margin also
rests on a figure, 717 MiB, that the new runs exceed (up to 839), though 2560M still holds. The Nether glide looked
backwards for half its route and the Nether savings are single pairs inside a 150 MiB native spread. Both need
honest wording, not new values. All of this is text plus a two-line fix to `analyze.py`. The recommended values
(1024, 256, the two free-ratio flags, 2560M, 8 / 5) stand.
