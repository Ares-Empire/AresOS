# 41, review fixes 2: the creation freeze, the margin, the glide's view

Review 2 (`reviews/41-home-memory/REVIEW-2.md`, fresh Claude Opus 5.5 reviewer) closed all of review 1 and found the
new runs' numbers right except one column, with CHANGES-NEEDED for the reasoning. No recommended value changes.

**Builder:** one fresh Claude agent on Opus 5.5 (an analysis fix and text, no new game runs).

1. **The creation freeze (blocking).** `rig/analyze.py` `window()` counts only frames that start inside a window, so
   the frame already running at the Create click is missed. Count the gap in progress at a window's start (and say in
   Method how windows are cut). Rerun `analyze.py` and `table.py` on the local run data (`.work/pkg41/rigs/`), check
   the creation table now shows about 2.1 s (f1), 5.7 s (n0), 3.7 s (n4) and 3.7 s (n3), and add the base world made
   at today's settings (about 2.0 s) if its data is there. Rewrite the text: every world creation freezes the picture at
   the click, at today's settings too (about 2 s flat, about 4 s Nether); it is not GC (the evidence REVIEW-2 gives);
   n0 took 5.7 s once at the new settings for a reason not found, and one slow run in two cannot rule the settings in
   or out. Put the plain version into "What he will notice" and Known limits: a one-time wait on the create screen, as
   today, not a daily stall.
2. **The MEMORY_HIGH margin (blocking).** Memory outside the heap reached 732 (n4), 736 (n3) and 838 to 839 MiB (n2),
   not at most 717: recompute the worst case from all runs (about 1.82 GiB) and say only the heap is capped, so "its
   own memory stops at about 1.75 GiB" goes. 2560M still holds; say by how much.
3. **The glide looked backwards for half its route.** Correct the text: the glide is an upper case for the server's
   loading and generating, not for drawing (the game meshes ground in view, and the camera faced south on both legs).
   No rerun.
4. **Single runs and noise.** The Nether savings rest on single pairs (n1 against n2; n0 and n4 stood 159 MiB apart,
   all native): say so, give how much of n2's excess is heap (about 121 of 340 MiB), and widen the stated noise to
   about 150 MiB where native memory varies. Keep that the flat-home case for the flags rests on the committed heap.
5. **Nits:** longest pause after joining with the flags is 14.7 ms (n1); f1's 200 MiB of file pages cannot be its
   world (8.3 MiB on disk): say what it more likely is or that it is unexplained; refresh the page-cache ranges in
   Known limits from the new runs; add n4 to the pass table with its 629 MiB heap peak at the rig's stop and mark its
   30 s settle; n1's p99 is about 1 ms above n2's from the extra GC pauses, with no frame over 33 ms in either.

Check every number you write against the run data. Rules as in `briefs/41-review-fixes-1.md`, and no game runs in
this step: nothing starts Minecraft, Gradle, labwc or the rig. Don't edit REVIEW-1.md or REVIEW-2.md.
