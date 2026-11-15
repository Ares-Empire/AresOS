# 41, review fixes 1: the report's text, and two more runs

Review 1 (`reviews/41-home-memory/REVIEW-1.md`, fresh Claude Opus 5.5 reviewer) found the numbers right and the
recommended values sound, with CHANGES-NEEDED for the reasoning around them. This step fixes the report and adds the
two runs the study left out. The recommended values change only if the new runs ask for it.

**Builder:** one fresh Claude agent on Opus 5.5 (text fixes and two runs with the existing rig).

## Text (REPORT.md)

Apply REVIEW-1's findings 1 to 10 as their "Fix" lines say:
1. Render distance: 5 for up to 29 apps in a group, 6 from 30; at render 4 only S3R3 and S4R3 are out of view; the
   61-program list needs 7. Correct it everywhere (the table, "What the town needs", JUDGMENT-CALL 2, the skipped
   list). Check the arithmetic yourself with `rig/town-reach.py` against HUB.md 3.3's fill order before writing it.
2. PLAN-GAP 2: periodic GC fired (c2: 9, c3: 10 while covered) and gave nothing back because each Remark found the
   heap about 48 % free, under `MaxHeapFreeRatio=70`.
3. Page cache: the product's scope will also carry the file pages the game reads first after a boot; 2560M still
   holds (worst case about 1.75 GiB anonymous, clean cache reclaimed first). Into the `MEMORY_HIGH` row and Known
   limits; the laptop check reads `memory.stat` anon and `memory.events` high, not `MemoryPeak` alone; the rig's
   `app.slice`/`--collect` against the product's `aresos.slice`.
4. The Nether home and first world creation: measured now (below); the report says what they showed.
5. Noise: drop the GPU explanation, the spread after the flight is about 90 MiB, and "1024 saves nothing" becomes "not
   measurable here, confounded with run order"; keep that the flags' saving survives (c4, v1 below every default run,
   v2 last and still higher).
6. Frames with the flags: "no worse", not "smoother".
7. to 10.: "GC pauses" with the split by kind and the pause total; G1 never shrinks below `-Xms`; the longest-pause
   column says "after joining" (or covers the whole run); today covered is about 1.42 GiB; native 250 / 313; a1 and
   a2's covered rows follow a flight marked not valid.
11. The raw `frames.txt` stay local (too big for the repo): say so in Method.

## Two runs at the recommended settings

Both at `HEAP=1024 MIN_HEAP=256 GC=-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 MEMHIGH=2560M`, render 8,
simulation 5, 1920 x 1080, with the GC log, NMT, the sampler and the frame recorder as in every run.

1. **First world creation (flat home):** from a game folder with no `AresHub`, the title screen's AresOS button,
   Home: Flat, until "The town is built: 40 logos". Record the heap's peak and committed, the longest GC pause and any
   over 50 ms, RSS and scope peak during creation and town building, and frame hitches while the town builds. Then
   settle and measure as `MODE=measure` does if the rig allows it from that state; otherwise creation alone.
2. **The Nether home:** create one through the same screen with Home: Nether (default seed), then settle 2 min,
   stand 60 s, fly 60 s at full speed over ground not loaded before (adapt the route to the Nether: the rig's flat-road
   flight does not fit; say what you flew), and 5 min covered. The same numbers as v1.

Pass: no `OutOfMemoryError`, no GC pause over 50 ms after joining, scope below `MEMORY_HIGH` with no `high` events,
frames no worse than the flat runs. If a run fails, say what a value that passes would be and measure it.

Add both runs to the tables (mark creation rows clearly), and to "Combinations run".

## Rules

As `briefs/41-home-memory.md`: worktree `~/AresOS-41-home-memory`, branch `pkg/41-home-memory`, push with
`git push origin pkg/41-home-memory`, never merge, never `--no-verify`. `free -g` at least 6 GiB available and the
client-test lock before each run; headless compositor only, never `wayland-0`; stop only your own processes by PID or
the rig's own scopes. Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Nothing under `os/` or `mod/src`
changes; rig changes stay in `reviews/41-home-memory/`. Never edit `rig/run.sh` while a run uses it. Public repo: no
personal data, no names of his programs, no pictures of a real screen. Don't edit REVIEW-1.md. Write the report into
`REPORT.md` directly. Commit and push after each part that works; commits end with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No `gh` commands.
