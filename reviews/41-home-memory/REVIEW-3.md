Verdict: SAFE

# Package 41: review 3 (fresh reviewer, Claude Opus 5.5)

Reviewed: branch `pkg/41-home-memory` at `d9e2acac` (PR #75), the fixes `f2dc1c8e..d9e2acac` against REVIEW-2 and
`briefs/41-review-fixes-2.md`. I checked them against the local raw data in `.work/pkg41/rigs/` (`frames.txt`, `gc.txt`,
`marks.txt`, `samples.csv`, `game.txt`) and the committed snapshots. Read-only: no game, Gradle, labwc or rig was
started. `analyze.py` and `table.py` (new, and the old ones from `f2dc1c8e`) were rerun into a scratch folder only.

Review 2's five main findings and four nits are closed. The new `window()` is right at every edge and counts no gap
twice across adjacent windows. Every number in the creation-freeze table recomputes from the raw frames. One number
in the `MEMORY_HIGH` margin is still a little low: the most memory measured beside the heap is 869 MiB, not 839. That
leaves 2560M about 0.65 GiB of room instead of 0.7, which is within the report's stated noise and changes no value.

## Findings

1. **should-fix: the most memory measured beside the heap is 869 MiB (n2), not 839**
   (`REPORT.md` line 43, `MEMORY_HIGH` row; lines 59 to 61, "What he will notice"; lines 456 to 459, Known limits).
   The 839 comes from the snapshots. The 2 s sampler shows more:
   - After n2's cover closed and the world was drawn again, n2's scope anon rose from 1565 to 1595 MiB. That was
     6.7 s after `covered_end` and stayed until the run's end at +16.4 s. The committed heap stayed at 726 MiB
     (`GC(110)` at +7.0 s: `685M->381M(726M)`).
   - So 1595 - 726 = **869 MiB** beside the heap. At the same moment the scope held 1636 MiB and RSS was 1793. The
     table shows 1605 and 1763 for n2 because its peaks are taken at the last snapshot (covered 5 min).
   - n3 also reached 743 at `stand_end` by the sampler, against 736 in its snapshot.
   - No other run moved by more than 2 MiB after its last snapshot. At the same point after the cover closed, n1 rose
     5 MiB (619 to 624), v1 2 and f1 3.
   - The runs at the recommended settings never passed 732 (n4) on either the snapshots or the sampler.

   So the measured worst case is 1024 + 869 = 1893 MiB, about 1.85 GiB, and 2560M sits 667 MiB (about 0.65 GiB) above
   it, not 697.

   Also, "scope anon minus the committed heap" is a lower bound for the memory beside the heap. Committed heap pages
   that were never touched are not resident, so the real value can be a little higher. The report already says the
   rest is not capped and could be higher in a flight that looks ahead.

   Not blocking:
   - It is 30 MiB, inside the report's own ~150 MiB native spread between runs.
   - It changes no value and nothing the lead must do.

   **Fix:**
   - In the three places, use 869 MiB (n2, the 2 s sampler after the cover closed), about 1.85 GiB, and about 0.65 GiB
     (667 MiB) of room.
   - Optionally add to "How to read them" that the tables' peaks are as of the last snapshot. n2 went on to 1636 MiB
     scope and 1793 RSS in its last 10 s.

2. **nit: "not from GC" is stronger than the evidence** (`REPORT.md` line 33 "not from GC"; line 54 "(not garbage
   collection)"). Lines 219 to 222 rightly list G1's near-continuous marking (6 concurrent cycles in n0's freeze) as
   not excluded. The evidence rules out GC *pauses* and heap growth, not concurrent GC work.
   **Fix:** "not from GC pauses" in the summary, and "not garbage-collection pauses" in "What he will notice".

3. **nit: "about 1.2 GiB standing" in the Nether leaves out n4** (`REPORT.md` line 64). At the recommended settings
   n0 and n1 stood at 1235 and 1230 MiB, but n4 stood at 1394 (1.36 GiB).
   **Fix:** "about 1.2 to 1.4 GiB standing".

4. **nit: "in every default run" means the flat-home default runs** (`REPORT.md` lines 475 and 476).
   - 470 to 623 MiB committed and 194 to 299 MiB native (settled) are right for the 16 flat-home runs with G1's
     default free ratios.
   - The Nether default runs lie outside both ranges: n2 at 528 to 726 committed and 309 native, n3 at 574 and 366.

   The direction only gets stronger.
   **Fix:** "every flat-home default run".

5. **nit: which p99 is "about 1 ms higher"** (`REPORT.md` lines 286 and 287).
   - n1's 10.81 ms is 1.15 ms above n2's 9.66.
   - It is about 2.3 ms above the flat flights' ~8.5.
   - n2 itself sits 1.2 ms above the flat flights, which is the glide's own cost.

   **Fix:** "about 1 ms above n2's (which is itself about 1 ms above the flat flights', from the glide)".

6. **nit: small wording at the window edges and in n0's text.**
   - `rig/analyze.py` lines 62 to 64 and `REPORT.md` line 330 say "the one in progress at its end counts in the next
     window". That is true only where a window starts at that end: `create` into `town` and `first_30s`. Between
     `stand_end` and `flight_start` (6.5 s apart) such a gap counts in no window. Add "if one starts there".
   - Line 331, "starts 2 to 10 ms before the rig's mark". The measured values:
     - f1 3.5 ms, n3 9.7 ms and n4 10.3 ms before the mark.
     - In n0 the frame in progress at the mark had started 14.8 ms before and lasted only 16.7 ms. The frame that
       handled the click started 1.9 ms *after* the mark.

     Say "about 3 to 10 ms before the mark, or just after it (n0)".
   - Lines 214 and 215, "the one 'Evacuation Failure: Pinned' came 6.9 s after the click". n0's log has two more,
     23 s before the click. Say "the only one after the click".

## Review 2's findings

| # | Closed? | Where, and what I checked |
|---|---|---|
| 1 | yes | `window()` now prepends the last frame before `start` (`analyze.py` lines 65 and 66), so a window counts every gap that *ends* inside `[start, end)`. Recomputed from `frames.txt` (below): f1 2143.4, n0 5693.2, n4 3748.4, n3 3673.1 ms, base world 1981.3 ms. The table and text (lines 31 to 34, 191 to 225, 243 to 264) match. "What he will notice" (lines 52 to 55) and Known limits (lines 491 to 494) carry the plain version. The optional `-Xlog:safepoint` runs are listed under Not verified. |
| 2 | yes, with finding 1 | 717 is gone. The row now says only the heap is capped and gives 839 (n2), 732 (n4), 736 (n3) and 717 (flat, m1), all right per snapshot. The sampler finds 869 (finding 1). |
| 3 | yes | Method lines 386 to 395, Known limits lines 482 to 490, Not verified lines 525 and 526: the camera faced south on both legs, so the glide is an upper case for the server and not for drawing. The `MEMORY_HIGH` row points at it. |
| 4 | yes | Summary lines 27 to 30, lines 271 to 280, Known limits lines 469 to 478. The values check out: 121 of 340 MiB is heap (726 - 605) and 197 is native (452 - 255). The heap part is 83 settled and 121 to 200 after the glide. n0 and n4 stood 159 apart (1235 and 1394), native 229 and 388. f1 and v1 were 107 apart after the flight, native 144 and 365. Run order is stated, and so is the direction in all three pairs (445, 456 and 448 against 528 and 574). |
| 5 | yes | Line 51: 14.7 ms (n1). The 16.4 ms while loading is c4's `gc_before_join` (16.35). |
| 6 | yes | Lines 253 to 256: 172 MiB of file pages already 20.3 s before the click (sampler), and f1 started half an hour after v2 ended (11:53 against about 11:22). |
| 7 | yes | Lines 451 to 453: `memory.stat` file at most 38 MiB except f1's 200 to 202, `RssFile` 143 to 156, `RssShmem` 54 to 66, all exact from the 25 runs' snapshots. |
| 8 | yes | n4 is in the pass table (10.85 ms, 1200 MiB, 0, 511, 0 (10.3)). Its 629 MiB is at +0.26 s after `done`, n3's 628 at +0.27 s, and n0's 650 at -1.18 s, during its quit after `stand_end`. `table.py` marks "settled 30 s" from `SETTLE`. |
| 9 | yes, with nit 5 | Lines 283 to 287: 346 / 142 = 2.4 ms per pause, and 142 of 7155 frames is 2.0 %. No frame over 33 ms in either run. |

## What I checked and found right

- **The rebuilt summaries.**
  - The new `analyze.py` rerun on all 25 local rig folders gives summaries byte-identical to the committed ones.
  - I compared the old analyzer (`f2dc1c8e`) with the new one field by field on the same raw data. Each window gained
    exactly one gap. `concurrent_cycles` halved. Otherwise the changes are:
    - the creation and first-30-s columns;
    - d2's flying p99 (8.52 to 8.51);
    - the covered `over_*` counts (+1 each; covered fps stays 10.0 in every run);
    - the `whole_run` maxima of a4 (86.5 to 130.6), n2 (101.0 to 121.3), n0 and n3. That is the frame across the
      joining mark, and no table or sentence uses `whole_run`.
  - The old committed summaries of the first 19 runs differ from the old analyzer's output only by added fields
    (`BASE`, `FLIGHT`, `HOMEKIND`, `MODE` and the per-window memory maxima), as "Verified" says.
- **The tables.** `table.py` on the rebuilt summaries prints exactly what is committed, and every row appears verbatim
  in the report. Against the old script on the old summaries, the only differences are:
  - d2's p99;
  - n4's "settled 30 s" label;
  - the four creation rows.

  Together with the hand-written n4 pass-table row, that is what "Verified" claims.
- **`window()` at its edges.**
  - A gap belongs to the window its ending frame starts in. `create` ends at `joined`, where `town`, `first_30s` and
    `whole_run` start, so the gap across joining counts in the later windows only, never in both.
  - The nested windows (`town` inside `first_30s` inside `whole_run`) overlap by design, as before.
  - A frame exactly at `start` counts as inside, and its gap from the previous frame ends at `start`. That is
    consistent.
  - All `frames.txt` are in time order, and no run lost frames.
  - A window lying wholly inside one gap would get no frame statistics. That doesn't happen in any run.
  - The fps now divides by a span that starts a few ms early. It is not reported anywhere.
- **The creation freeze, recomputed.**

  | Run | Freeze | Frame start vs. mark | Server "Time elapsed" | GC in the freeze | Committed heap |
  |---|---|---|---|---|---|
  | f1 | 2143.4 ms | 3.5 ms before | 1502 ms | 19 pauses, 46.8 ms, at most 4.5; 3 cycles | 309 |
  | n0 | 5693.2 ms | 1.9 ms after | 6113 ms | 30 pauses, 85.8 ms, at most 10.0; 6 cycles; no humongous or Full GC | 308 throughout |
  | n4 | 3748.4 ms | 10.3 ms before | 4341 ms | 16 pauses, 60.2 ms, at most 10.1; 3 cycles | - |
  | n3 | 3673.1 ms | 9.7 ms before | 4315 ms | 7 pauses, 35.7 ms, at most 11.5; 1 cycle | - |
  | base world | 1981.3 ms | - | 1432 ms | 6 pauses, 22.0 ms | - |

  - **The base world.** Its 1981.3 ms is the longest frame before joining. It ends 1.0 s before joining, as f1's
    does, and the next longest is 295 ms.
  - **Spawn search.** "Selecting global world spawn" to the first save took 3 s in n0, 1 s in n4 and 2 s in n3.
  - **Cores at the click.** 2.6, 4.3 and 3.9 cores in the 2 s sample around the click. The next sample is 8.5, 8.5 and
    7.6, so n0's low use is in the first 2 s only, as the report words it.
  - **Frames at joining.**
    - The loading screen's last frame: f1 201.5 ms and n4 233.3 ms (inside `create`).
    - The frame across the joining mark: n0 206.4 ms and n3 244.3 ms (in `first_30s`).
    - The base world's: 125.5 ms.
  - **The first 30 s, without the frame at joining.**
    - Frames over 17 ms: 11, 10 and 11. Over 50 ms: 2, 1 and 1. Worst: 67.5, 50.9 and 56.0 ms.
    - The base world: 109.6 ms worst, 3 frames over 33 ms.
    - f1: 136.4 ms at the town's appearance, GC at most 5.11 ms in `create` and 12.47 ms in `town`. Before joining it
      was 14.32 ms.
- **`concurrent_cycles`.**
  - Each cycle has one opening line (`Concurrent Mark Cycle`) and one closing line with its duration. The regex sends
    the duration into `rest`, so `not rest` keeps only the opening line.
  - An independent count after joining matches all 25 runs (for example v1 53, c4 51, n1 47, h3 14 opened / 15
    closed).
  - In the flight c4 and v1 run 33 and 34 cycles against 7 or 8 in the default runs, so "about four times as many"
    stands.
  - Neither the old nor the new report ever quoted the counts, so no ratio or claim rested on them.
- **The other changed numbers.**
  - **Scope peaks.** In the Nether: 1071, 1200 and 1262 at the recommended settings, 1330 and 1605 at today's. In the
    flat home: 1136 to 1304.
  - **Default runs, settled.** The flat-home default runs' committed heap is 470 (c3) to 623, and their native memory
    194 (c2) to 299 (a4). c4 and v1: 288 and 271.
  - **Memory beside the heap (snapshots).** n2 839 (838 after the glide), n3 736, n4 732, and m1 717 in the flat home.
    Almost all of the rise is native memory outside NMT (n2 309 to 489).
  - **The heap claims.** The committed heap stayed at most 605 while measuring at the recommended settings, and the
    longest pause after joining with the flags is 14.71 ms (n1). The no-flags maximum is 21.33 (d3).
  - **The noise ranges.** The first 19 runs spread about 50 MiB settled and 90 after the flight.
- **Honesty.**
  - **The creation freeze** is in the summary, "What he will notice", the body, Known limits and Not verified. Each
    says that every creation freezes at today's settings too, that n0's 5.7 s was a one-off of unknown cause, and that
    one slow run in two can neither rule the settings in nor out.
  - **The glide** is called an upper case for the server only.
  - **The Nether savings** are given as single pairs, with only the heap part pinned on the flags.
  - **"What he will notice"** is plain and true apart from nits 2 and 3 and finding 1's number.
- **Hygiene.**
  - The diff touches only `REPORT.md`, `rig/analyze.py`, `rig/table.py` and 25 `summary.json`. No file is added,
    deleted or binary.
  - The 822 added lines contain no path under a home folder, no player name, no personal data, no picture and no
    Mojang file. The only `@` is the glide's `tp @s`.
- **The recommendation.** `HEAP_MB` 1024, `MIN_HEAP_MB` 256, the two free-ratio flags, `MEMORY_HIGH` 2560M and render
  8 / simulation 5 all still follow from the data.
  - The live heap stays at most about 410 MiB in the Nether.
  - The worst measured anonymous memory is about 1.85 GiB against 2.5 GiB.
  - No run had an `OutOfMemoryError`, a Full GC, a `high` event or swap at these settings.

## Summary

The review 2 fixes are right. The `window()` change counts the gap in progress at a window's start, so the creation
freeze now shows: f1 2143, n0 5693, n4 3748, n3 3673 ms, and 1981 ms for the base world made by hand. Adjacent windows
still count no gap twice. The only other table change is d2's flying p99 by 0.01 ms, and the `whole_run` maxima that
moved are not used anywhere. The `concurrent_cycles` fix halves counts that the report never used. The new
`MEMORY_HIGH`, noise and Nether-pair numbers all recompute. The report now says plainly that only the heap is capped,
that every creation freezes the create screen for about 2 s (flat) or 4 s (Nether) as today, that n0's 5.7 s is
unexplained, and that the glide is an upper case for the server only. One margin number is 30 MiB low: n2 reached
869 MiB beside the heap after its cover closed, so the worst case is about 1.85 GiB and 2560M has about 0.65 GiB of
room. That is within the stated noise and changes no value. Five wording nits remain. The recommendation can go to
the OS lead as is, preferably with finding 1's three numbers corrected.
