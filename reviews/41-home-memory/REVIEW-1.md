Verdict: CHANGES-NEEDED

# Package 41: review 1 (fresh reviewer, Claude Opus 5.5)

Reviewed: branch `pkg/41-home-memory` at `560cd2e3` (PR #75): `REPORT.md`, `rig/`, `frames/` and all 19 `runs/`,
against the brief, `os/config/usr/libexec/aresos-desktop` and HUB.md 2, 3.1 to 3.3 and 5. Read-only: no game, Gradle,
labwc or rig was started.

The measurements are sound and the four recommended values hold up. One number in the reasoning for the
render distance is wrong (finding 1). Under this review's rules that makes the report blocking, but fixing it is a
text change and the recommended value stays 8. The other findings correct explanations that the data contradict,
and add limits the lead should know about before the release.

## Findings

1. **blocking: the 40-app town needs render 5, not 6, by the report's own rule** (`REPORT.md` lines 31, 68 to 72,
   214, 282).
   HUB.md 3.3 fills a group's places by row, then by `k`, then L before R. With 28 apps in System & Tools that is
   rows 0 to 3 (20 places) plus row 4 with k 0 to 3 on both sides (8 places). Row 4's k = 4 places stay empty. The
   `ChunkTrackingView.isWithinDistance` rule is right: I checked it against the 26.2 jar with `javap`. Applied to each
   place on the south road (the town-reach.py arithmetic, place by place), it gives these distances:
   - Every place of rows 0 to 4 with k ≤ 3 needs at most render 5. S3R3 and S4R3 need 5; every other place in those
     rows needs 4 or less.
   - Only S4R4 needs 6. That place is not used until System & Tools has 30 apps; S4L4, the 29th, needs 5.

   So at the rig's 40-app mix, render 5 draws and loads the whole town, not 6. At render 4, only the two logos S3R3
   and S4R3 are out of view, not "rows 3 and 4". The 61-program list (42 in System & Tools, rows 0 to 5 full) needs
   exactly 7 on the south road ("7 to 8" is loose).

   **Fix:**
   - Say 5 for up to 29 apps in one group, and 6 from 30.
   - At render 4, only S3R3 and S4R3 are missing.
   - The full list needs 7.

   The recommendation stays 8: render 6 saves no RAM, and the 61-program list needs 7. Optionally add that the
   circle rule describes the drawn chunks. The server may load further through ticket propagation, so these are
   upper bounds for "loaded".

2. **should-fix: the reason given for periodic GC returning nothing contradicts the GC logs** (`REPORT.md` lines
   289 and 290, PLAN-GAP 2).
   The text says young collections run "every 15 s or so anyway", so periodic GC never fires. The logs show
   otherwise:
   - c2 logged 9 and c3 logged 10 `G1 Periodic Collection` pauses while covered. Each one started a concurrent cycle
     with a Remark.
   - c1 paused only 6 times in its 5 covered minutes, 4 of them young collections, about one a minute rather than
     every 15 s.

   The real reason is the second half of the sentence. At every Remark the heap was about 48 % free (c2:
   `Pause Remark 319M->319M(610M)`). That is under the default `MaxHeapFreeRatio=70`, so G1 uncommitted nothing. The
   13 to 14 s gap holds only for the small heap of c4 and v1. That is why no periodic collection fired in c4, and why
   adding periodic GC to the flags gains nothing.

   **Fix:** reword PLAN-GAP 2 along those lines. The recommendation ("not `G1PeriodicGCInterval`") stands.

3. **should-fix: the scope numbers leave out page cache that the product's scope will carry** (`REPORT.md` lines
   30, 114 to 118, 267 and 268).
   In the rig, the game's scope held almost no file pages: `memory.stat` file was 7 to 38 MiB. `RssFile` (143 to
   147 MiB) and `RssShmem` (54 to 56) were charged to cgroups that read them earlier (Gradle and earlier runs). On his
   laptop after a boot, the JVM is the first reader of the client jar, the libraries, the assets and the world files.
   Those pages are charged to `aresos-game-<id>.scope`, so its `memory.current` and `MemoryPeak` will read higher than
   this table's "Scope peak", up to about RSS plus read cache.

   2560M still holds:
   - The worst-case anonymous memory is about 1024 MiB of heap plus about 0.7 GiB of the rest. Scope anon minus heap
     committed reached 661 to 717 MiB after the flight. That totals about 1.75 GiB.
   - Clean page cache is reclaimed first under `MemoryHigh`.

   The report should still say this.

   **Fix:**
   - Add it to the `MEMORY_HIGH` row and to Known limits.
   - Make the "Not verified" check on his laptop read `memory.stat` anon and `memory.events` high, not
     `MemoryPeak` alone. Otherwise a higher peak will look like a regression.
   - Minor: the rig's scope ran in `app.slice` with `--collect`; the product's runs in `aresos.slice` without it.
     Neither slice has limits, so the numbers are unaffected, but the report should say so.

4. **should-fix: the Nether home and first world creation are not measured, but the settings apply to them too**
   (Known limits, lines 227 to 248).
   `HEAP_MB`, `MIN_HEAP_MB`, the flags and `MEMORY_HIGH` are global in the supervisor. The create screen still offers
   "Home: Flat / Nether" (`mod/src/client/java/dev/aresos/client/HomeCreateScreen.java`). Generating and meshing real
   Nether terrain is heavier, on the heap and in native memory, than the flat world. Creating a world and the first
   town build were not measured at 1024 with the flags either: the base world was made once in `setup`.

   **Fix:**
   - Name this in Known limits and in the `HEAP_MB` row.
   - Either run one Nether-home measurement (a d1-style flight at 1024/256 with the flags) before the release, or
     have the lead accept that risk on purpose.

5. **should-fix: the noise explanation is contradicted by the data, and "1024 saves nothing" is not established**
   (lines 123 to 126, 17, 287 and 288).
   - The GPU explanation does not hold. The report says the driver's host-side share adds about 50 MiB to RSS. But
     c1 had 424 MiB on the GPU and 1384 MiB RSS after the flight, while h3 (306 MiB GPU) had 1393 and c2 (306) had
     1390. c3 (424) had 1456. c4, a run with the flags, is used as a comparator in that sentence. With G1's defaults
     at render 8, RSS after the flight ranges from 1384 to 1476 MiB, a spread of about 90 MiB, not 50.
   - "Saves nothing" is not shown either way. On average, the runs at a heap ceiling of 1536 or more (a1, d1, h1,
     h2) sit about 60 MiB above the default runs at 1024 or less (h3, h4, c1, c2, c3):
     - settled: 1316 to 1343 against 1257 to 1290 MiB, with no overlap;
     - after the flight: 1451 to 1481 against 1384 to 1456 MiB.

     But the higher runs all ran earlier (09:10 to 10:09 against 10:14 onwards), and 3072 uses 2 MiB G1 regions where
     the others use 1 MiB. So the 1024 ceiling may also save about 50 MiB, or this may be drift.
   - The flags' saving survives both checks. c4 and v1 are below every default run. v2 ran last (11:17) with the
     defaults and still settled at 1290 MiB while being throttled, so the saving is not drift.

   **Fix:**
   - Drop the GPU explanation.
   - Give the spread after the flight as about 90 MiB.
   - Replace "saves nothing in daily use" and "the heap ceiling does not move daily memory" with "not measurable
     here, confounded with run order".

6. **should-fix: the frame claims overstate a difference that is noise** (line 29 "frames a little smoother"; lines
   37 and 38 "the only runs without a single frame over 17 ms").
   One frame over 17 ms against none, out of about 7,200 frames in a window, is noise:
   - The flights of c3, d2, d4 and h3 also had none over 17 ms.
   - h3's and d2's standing windows each had one.
   - The worst frames with the flags (11.2 to 13.6 ms) lie inside the default runs' range (8.6 to 25.4).

   **Fix:** say "no worse", as JUDGMENT-CALL 1 already does ("at least as smooth").

7. **nit: the pause counts are labelled "young collections"** (lines 29, 274 to 279).
   The flight counts 165, 174, 116 and about 38 include Remark and Cleanup pauses. Split by kind:

   | Runs | Young pauses | Remark and Cleanup pauses (each) |
   |---|---|---|
   | v1 / c4 | 106 / 99 | 34 / 33 |
   | m1 | 70 | 23 |
   | d1 and c1 | 22 | 8 |

   The extra CPU comes from about four times as many concurrent cycles. Total pause time was 324 to 331 ms per
   flight minute with the flags, against about 140 ms with the defaults.

   **Fix:** call the counts "GC pauses" and add the concurrent cycles and the pause total.

8. **nit: the MIN_HEAP_MB 512 claim is G1's rule, not a measurement** (line 28: "at 512 they could not take it below
   512"). No run combined the flags with `-Xms512m`. The statement is G1's rule that the heap never shrinks below
   `-Xms`.

   **Fix:** say "G1 never shrinks below `-Xms`".

9. **nit: the longest-pause column covers only the time after joining** (table column "Longest GC pause in the run";
   line 37).
   `table.py` takes `gc_after_join`. While loading, the runs with the flags reached 16.35 ms (c4), 14.81 ms (v1) and
   14.15 ms (m1), so "with the flags the longest was 13.7 ms" holds only after joining.

   **Fix:** rename the column to "after joining", or report the whole run.

10. **nit: small number slips.**
    - Line 40, "about 1.35 [GiB] while an app covers it" for today: a1 (today's 3072/512) was at 1453 MiB covered,
      about 1.42 GiB. 1.35 GiB is the 1024-heap runs with G1's defaults (c1, c2). The report understates the gain.
    - Line 134: d1's RssAnon minus NMT is 250 MiB settled and 313 MiB after the flight, not "about 260 (330)".
    - a1's and a2's covered rows follow a flight that the report marks not valid. Say so before calling them good.

11. **nit: the raw frame logs are not committed.**
    `frames.txt` stays in `.work/pkg41/rigs/`, so the frame columns can be checked only against `summary.json`. I
    recomputed them from the local `.work` copies and they match.

    **Fix:** commit them compressed (about 0.4 MB per run), or say in Method that they stay local.

## What I checked and found right

- **Numbers.** An independent script recomputed every run from the raw files. All 19 rows of both tables match
  exactly:
  - from the snapshots: RSS, PSS, heap used and committed, NMT, GPU, VmHWM and scope peak;
  - from `frames.txt`: frames per second, average, p99, worst and frames over 17 ms;
  - from `samples.csv`: CPU;
  - from `gc.txt`: the GC pause count and longest pause in the flight, and the longest after joining;
  - the covered RSS series, the committed heap and the scope and GPU readings at 5 minutes.

  The live heap after mixed collections was 249 to 363 MiB. The highest committed heap was 623 MiB (c3). h4 reached
  607 MiB committed in the flight.
- **Windows and clock.** The marks (`time.monotonic_ns`), the frame recorder (`System.nanoTime`) and the `-Xlog`
  `tn` decoration all read CLOCK_MONOTONIC. `flight_start` is set after the climb and `flight_end` after the 60 s of
  sprint-flying, so the flight window is the flight. Pauses are put into a window by their start time. The recorder's
  ring (64 K entries) cannot overflow at 120 frames a second, and `lost` is 0 in every run.
- **The rig measured what it says.**
  - The game command lines in `java.txt` (checked for v1, c2, c4 and h4) carry exactly one `-Xms`/`-Xmx`, the GC
    flags and NMT.
  - `GC.heap_info` reserved equals `-Xmx` in all 19 runs, and the first pause shows 258 or 514 MiB as `-Xms` says.
  - Every run had its own `pkg41-game-*.scope`, with `memory.high` at 5G, 2560M or 1100M as its settings say.
  - The output was 1920 x 1080 at 144 Hz in all 19 runs (randr.txt).
  - One variable changes per step: d1 → h1 to h4, d2 ↔ d4, and c1 → c2 → c3 → c4. c4 → v1 changes two, but c4
    fired no periodic collection and v1 had no `high` event, so the change is harmless.
- **The supervisor.**
  - `MEMORY_HIGH` applies only to `aresos-game-<id>.scope`. `game_scope()` puts it before Java in the wrapper, and
    `systemd-run --scope` then runs Java in that scope.
  - Prism runs in its own `aresos-desktop-<id>.scope`, which has no memory limit.
  - On Linux the mod starts no processes of its own: `ProcessLaunch` is used only by `WindowsAppLauncher`. Nothing
    else shares the game's budget.
  - The "Today" column is right: 3072, 512, `5G`, 8, 5, and no JVM flags in `instance_config`.
- **Headroom.** With a 1024 MiB heap and `MEMORY_HIGH=2560M`, the worst case is about 1.75 GiB of anonymous memory.
  That stays well under the limit even with some page cache (see finding 3). v2 shows what too low a value costs.
- **Town geometry.**
  - town-reach.py follows HUB.md 3.1 and 3.2: the outward and right vectors per group, a0 = 20 + 14 r, the L and R
    columns, and floor division for negative chunk coordinates.
  - The 26.2 bytecode confirms the drawn-chunk rule.
  - The per-group table (full rows) is right. Only the step from 28 apps to rows is wrong (finding 1).
- **Repo hygiene.**
  - The diff touches only `briefs/41-home-memory.md` and `reviews/41-home-memory/`. Nothing under `os/` or `mod/`
    changed.
  - No binaries are committed (`frames/build/` is not tracked) and there are no pictures.
  - The test apps are named "Test <word> <n>". The only paths are `/var/home/ares`. I found no hostname, no names of
    his installed programs and no personal data.
