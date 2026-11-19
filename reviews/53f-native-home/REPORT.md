# 53f report: the laptop home drawn natively

Branch `pkg/53f-native-home`, based on 53c's branch (PR #114); the lead rebases it onto main after #114 merges.
Built by Claude Opus agents in two steps on 2026-11-19. Step A built the model, the painter, the test channel and the
checks against injected state. Step B built input, motion, icons, memory and the clean-up. This text replaces step A's
handoff; the lead moves it to `REPORT.md`. Step B's hosted checks-only run 44426761677 failed on GitHub's runner (no
bwrap, no pycairo; fixed in review fix round 1). Round 1's hosted run: **44432045490** (started on `af0b16c4`, not waited for; an earlier start, 44431977176, ran on `3b0b4c2f` after a push that had failed and is superseded).

## Review fix round 1 (REVIEW-1, `briefs/53f-review-fix-1.md`)

Built by a Claude Opus agent on 2026-11-19. Each fix and the test that shows it; every new test was also run against
the reviewed program (`ff28bf01`) and failed there.

1. **The icon decoder runs in bubblewrap** (finding 1). `decoder_command` follows the helper's icon worker:
   `--unshare-all --die-with-parent --new-session --cap-drop ALL --clearenv`, read-only `/usr/lib64` (and `/usr/lib`
   where the interpreter's library lives there, as on Debian), the interpreter, a private `/dev` and an empty `/tmp`;
   no `/proc`, no `/run`, no home. The PNG comes on a memory file as stdin. `run_sandboxed` reads the reply under a cap
   of 8 + 512 × 512 × 4 bytes (`MAX_DECODED`) and a deadline, and kills the process group after. Without
   `/usr/bin/bwrap` nothing runs and the row keeps its plain square. Tests (`test_aresos_laptop_home.IconTest`): a
   probe through the same command cannot connect to a helper socket, open a file in a runtime folder or open
   `/proc/<parent>/environ` (run plainly, the probe reaches all three); `/` holds only `usr`, `lib64`, `dev`, `tmp`;
   a child writing one byte past the cap is refused; a missing bwrap starts no process. The image check now decodes
   through bubblewrap, or, where the container allows no user namespace, checks that the home refuses.
2. **Clicks and hover only where something is painted** (finding 2). `hit_test` rejects points outside the stage.
   The finder's list and line and the hotbar are `chrome` hits that take a click and open nothing; rows still open.
   A house takes clicks on its logo, its mat, its sign's painted plate and, while framed, its frame; a cut end's
   mask (by day up to `EDGE/2`) or wall (night, 18 px) hides the rest. The street sign's box is its measured text
   (plus the day plate's 24 px): the model asks `Painter.measure` (the painter's own Pango settings; an estimate in
   the model's tests), and the day plate is painted from that box. Tests (`HitTest`, and `WindowTest.check_signs`
   with the program's real fonts): the finder header, its padding, a 2304 × 1080 window's margin and the side of a
   short group or house sign open nothing; the day plate's painted edges are where its box ends.
3. **One icon worker** (finding 3). `IconWorker`: one thread; each draw replaces its queue with the rows shown now
   (at most five); a result for a row no longer shown is dropped; a failure is not retried until the catalogue
   changes, which also drops pictures of icons that left. Tests (`IconWorkerTest`): ten result changes start one
   worker and decode only the last five rows; an obsolete result is dropped; a failure waits for a new catalogue.
4. **Logo caches pruned** (finding 4): every paint drops logo pictures of houses that left and slots unpinned. The
   memory check: `laptop_home_memory.py --used` and the opt-in
   `MemoryGuardTest.test_rest_after_typing_sliding_and_finder_results_stays_within_two_percent` type ten queries
   (finder rows with icons among them), slide a street by hand, clear the query and sample again 15 s after a
   redraw. Without more, the second sample was 2.9 to 3.9 % above the first, and the reviewed program grew the same
   (3.5 %): glibc kept the heap's freed space. The home now calls `malloc_trim(0)` once, 2 s after the last redraw
   of a burst (`SETTLE_MS`; no timer at rest beyond the clock's). With it: 1.3 % and 1.5 %.
5. **Finder text** (finding 5). `natural` sorts as `localeCompare('en', {numeric: true})` for ties: base letters
   first, accents next, lower case before upper, runs of decimal digits (Unicode Nd) by value, spaces and
   punctuation before digits before letters; `²` weighs as a 2 and never reaches `int()`. A row's name and kind
   shrink in proportion when they do not fit (53c's flex line, `row_columns`), each ellipsized. Tests
   (`FinderTextTest`): `2²` searched with `2`; accented, cased and numeric ties; the shares; and painted rows with a
   64-character kind and a long name leave the icon column and the row's outside untouched.
6. **Checks that can fail** (finding 8): the grid check requires both plot sides; the idle colour is compared with
   53c's own `day-home.png` and `night-home.png` at the same point (the `idle` paint break fails it:
   `(25, 130, 143)` against 53c's `(76, 112, 116)`); the rest check counts the program's tick callbacks (none in
   13 s); a real labwc pointer click on `test-game-1` makes the stand-in helper receive `test-game-1`; focus and
   reconnect run as two tests, on the layer surface and in the fallback window.
7. **The harness hides the host's `/run`** (finding 9): a tmpfs on `/run` before labwc starts, then only the
   fixture's own folders bound back. The fixture reports an empty `/run`, a reachable private display and stand-in
   socket, in both surface modes.

**Also fixed:** step B's hosted run failed because `WindowTest` had no skip (its decorator sat on `MotionTest`,
which needs nothing) and the icon tests needed pycairo and bwrap. Now `needs(...)` in `laptop_home_headless.py` skips
a test whose stack is missing; with `LAPTOP_HOME_REQUIRE_HEADLESS=1` (AresOS, where all is present) it fails
instead. A run with bwrap, labwc and pycairo hidden gives 16 skips, no errors. One bug of this round, caught by the
memory script: the new hit loop's names shadowed `build_scene`'s `width` and `height`, so `scene['size']` was wrong;
the margin test now checks `size` too.

**Memory remeasure** (set-up S, 15 s after one redraw, `laptop_home_memory.py --runs 3 --used`, before the trim):
median **64,993 KiB** (64,867 to 65,286), Pss_Anon 30,532, two window pictures, heap 12,184 KiB; after use
66,873 to 67,852. With the trim (two runs): 65,154 and 64,929 at rest, 66,030 and 65,892 after use. **The
64,000 KiB guard fails today, for the reviewed program too:** `ff28bf01`, measured in the same session, gave 64,844
KiB (step B measured 62,358 with that code). The rise is the laptop's state, not this round's code; the lead decides
whether to re-pin the guard. Runs: `.work/mem/fix-1.jsonl`.

## Review fix round 2 (REVIEW-2, `briefs/53f-review-fix-2.md`)

Built by a Claude Opus agent on 2026-11-19. Each fix and the test that shows it. Every new test was also run against
the reviewed program (`301e7084`), loaded into the same test module, and failed there.

1. **The finder never raises on a name** (finding 5, blocking). `natural` passed `character.casefold()` to
   `unicodedata.digit` as one character. `ß` folds to `ss`, so searching `Straße` raised `TypeError`.
   - Now each folded character is weighed alone, after NFD. A combining mark that folding produces joins the
     accents: `İ` sorts as `i` with a dot above.
   - Each folded letter keeps its character's case, now read with `lower()` (so `ß` counts as lower case). Ties come
     out as ICU orders them: Strasse, Straße, STRASSE.
   - Number runs weigh as (significant digits, digits) instead of `int()`, which refuses runs past 4,300 digits.
   - Tests (`FinderTextTest`):
     - searches with `Straße`, `ß`, `ﬁ`, `İ`, `²`, `٣` and `Ⅻ`: each finds its own name, the same way twice;
     - the Strasse order, `ﬁ` against `fi`, and a run of 5,000 digits;
     - a property test over the BMP's 49,708 letters and numbers: a one-character name (beside six names built from
       it), searched by itself, raises nothing, keeps its order between two calls and finds the name. On
       `301e7084` it stops at U+00DF.
   - A one-off sweep of all 1,114,112 code points (surrogates included) through `natural` and `search`: nothing
     raised.
2. **A click opens a house only on what is painted** (finding 2). `logo_shapes` yields the logo's painted parts in
   painting order: each block's face, plus its top and side where no block covers them.
   - The painter fills exactly these shapes. Six scenes (day and night, with and without a query) paint
     byte-identical pictures to `301e7084`'s painter.
   - `painted` tests a point against the same shapes, so a click on an empty cell or a transparent corner of the logo
     picture opens nothing.
   - A framed house's frame takes clicks only on its ring, not its inside. `frame_band` gives the ring: by day from
     the 2 px shadow to the inner line, by night the 2 px border.
   - Tests (`HitTest`), by day and night, framed and not:
     - the transparent lower-right corner of the logo picture opens nothing, and nor does the inside of the frame
       beside the logo;
     - the ring and the door open the house.
   - A pixel test covers one house per logo outline (square, disc, diamond, octagon) and the framed one. Every pixel
     the painter fills completely is a hit, and every clear pixel is not. For the frame, the test checks the pixels
     that the ring's edge does not cross.
   - The cut-end test now clicks a painted block. Its old point was on a logo's empty corner cell.
3. **No stale icon results** (finding 3). The home updated the worker only while there were rows or a queue. So a
   cleared finder left the last rows "shown", and an icon still being decoded was kept.
   - `load_icons` now passes the rows on every draw, also when there are none.
   - A failure is remembered only for the catalogue generation it was tried with. One that comes back after a refresh
     is not remembered and, while its row is shown, is queued again.
   - Tests (`IconWorkerTest`):
     - through the home's own `load_icons` and `icon_ready`, an icon that is decoding when the finder is cleared is
       dropped, and decoded anew when the name is typed again;
     - a failure from before a refresh never blocks a retry, whether its row is still shown or shown later.
4. **Nothing ticks at rest** (finding 4). `redraw` arms the 2 s trim only for reasons other than `clock` and `star`
   (`IDLE_REDRAWS`).
   - Test (`WindowTest.check_rest`, day and night): the channel counts each time the trim timer is armed.
     - The input before the rest check has armed it.
     - The test then asks for one clock redraw through the same path, because the minute may not fall in the
       window.
     - Over 13 s at rest nothing arms the trim, and no trim timer is waiting at the end.
   - On `301e7084`: armed once by day and 4 times by night.
5. **The opt-in memory tests fail by name** (finding 8). `laptop_home_memory.missing()` names what a measurement
   lacks: the headless stack, fontconfig, the layer library or the study's fonts.
   - `MemoryGuardTest.setUp` fails with that list.
   - A measurement that cannot run (fonts not matched, a device visible, the wrong surface) fails with its reason.
   - With `LAPTOP_HOME_TEST_LAYER_DIR=/nonexistent`: two failures naming gtk4-layer-shell. Before, these were errors.

**One bug of this round:** fix 4's first commit (`1962dc6c`) read `reason` in `redraw`, whose parameter was named
`_reason`. The headless window tests caught it as channel timeouts. Fixed in `057df6ea` before the runs below.

**Round 2's runs** (headless as above, `LAPTOP_HOME_REQUIRE_HEADLESS=1`, `LAPTOP_HOME_TEST_LAYER_DIR` set to the
verified extraction):
- `discover -p 'test_aresos_laptop_home_native.py'`: 37 tests, OK (2 skipped: the opt-in memory tests), 55 s,
  after the last code change. Second run: 37 tests, OK (2 skipped), 55 s.
- `discover -p 'test_aresos_laptop_home.py'`: 16 tests, OK.
- The same module with `LAPTOP_HOME_MEMORY_GUARD=1 -k MemoryGuardTest`: 2 tests, OK, 81 s. These are the 2 % check
  after use (the trim still runs after a burst) and the median of three under 68,000 KiB.
- Against `301e7084`, these new tests failed:
  - `FinderTextTest`'s two (`TypeError`; U+00DF);
  - `HitTest`'s logo test (the corners and the frame's inside open the house);
  - `IconWorkerTest`'s two;
  - `WindowTest` day and night (armed once and 4 times at rest).
- Pictures: not regenerated. The painter's output is unchanged (above).

## Known limits

- REVIEW-1 finding 6: Tab and a focused sign's Enter or Space no longer reach the end and group signs (53c's
  focusable buttons); the keyboard has the finder, the arrows and 1 to 9.
- REVIEW-1 finding 7: night glides paint at about 65 ms a frame in software (two full-stage gradients per frame);
  the day look, at about 15 ms, is the default.

## Done

**The program** (`os/config/usr/libexec/aresos-laptop-home`, one file in three sections):
- **The layout model** (pure Python, step A). `build_scene(inputs)` holds 53c's rules (`place_index`, `town_grid`,
  `snap`, `street_range`, `follow`, `hidden`, `score`, `search`, `hint_text`). `Town` holds 53c's `home.js` state.
  - Step B added the glide: each street has a resting `offset` (the ends, the frame and the target use it) and a
    drawn `shift` (houses, signs, plots and the night road use it). The companions can read `shift` every frame.
  - Also: the puff's particles, the caret's blink state, `hover_key()`, the end-sign hover, and CSS `ease-out`
    (`ease_out`, the cubic-bezier(0, 0, 0.58, 1) curve).
- **Motion** (B.2):
  - `Town.glide` starts a 0.3 s ease-out glide from where a street is drawn whenever its resting offset changes.
  - `Town.open` starts 53c's 0.6 s puff: nine 5 px squares from the door, rising and fading.
  - `LaptopHome.start_motion` adds a frame-clock tick callback that removes itself when every glide and puff is
    done.
  - The caret blinks five times in 1.1 s steps after each keystroke, on timers (ten redraws), then stays.
  - Nothing ticks at rest.
- **Input** (B.1):
  - Keys: a key controller with **GTK's simple input method** (`Gtk.IMContextSimple`), so dead keys and compose
    work. Its `commit` gives `town.key` one character at a time. Escape, Backspace, Enter (also keypad and ISO) and
    the arrows (also keypad) come by key name. Nothing is taken while Ctrl, Alt, Super or Meta is held. A
    capture-phase controller tracks held keys, so a repeated press of a held key counts as a repeat, as the page's
    `event.repeat` did.
  - Pointer: `GestureClick` → `town.click`. Motion → hover from the last drawn hit regions, with the `pointer`
    cursor over anything clickable. Leaving the window clears the hover.
  - Focus loss clears the line, as before, and moves the input method's focus.
- **Finder icons** (B.3):
  - `read_icon` keeps 53c's checks on the opened file: an absolute path, a regular file and not a symlink
    (`O_NOFOLLOW`), at most 1 MiB, a PNG header and an IHDR of at most 512 × 512.
  - `decode_png` runs a short-lived `python3 -I -S -c` child in bubblewrap (review fix 1). It gets the bytes on
    stdin, never the path.
  - The decoder is PNG only and non-interlaced: grey, RGB, palette (with `tRNS`), grey with alpha and RGBA, at 1
    to 16 bits, with the CRC checked and the inflated size bounded. It returns at most 512 × 512 RGBA.
  - `icon_surface` fits the result into a 48 × 48 picture, drawn at 24 × 24 (object-fit: contain). Cairo
    premultiplies it through an A8 mask.
  - Decoding runs on one worker thread for the rows shown (review fix 3). On any failure the row keeps its plain
    square. At most 20 icons are kept.
- **Memory settings** (B.4, each measured on its own, below):
  - `Allocator` fixes glibc's mmap threshold at 128 KiB.
  - The program puts `None` in `sys.modules['ssl']` before importing asyncio (no OpenSSL), and makes the
    connection prefix with `os.urandom(8).hex()` instead of `secrets`.
  - `load_gui` sets `GIO_USE_VFS=local` with `setdefault`.
- **Removed** (B.5): `PAGE_ROOT`, `SCHEME`, `MIME` and `Resources`; the `urllib` and `ExitStack` imports; the page
  folder `os/config/usr/share/aresos/laptop-home/` (HTML, CSS, JS, `BRIDGE.md`). Its deletion landed in commit
  `9c562c9e`, whose message does not mention it.

**The image check** (`os/ci/image-checks.sh`): the WebKitGTK import is replaced. The check loads the program's own
`load_gui()` as `ares` (as the cover's check does), checks `GDK_DISABLE`/`GSK_RENDERER`, and decodes a 1 × 1 PNG
through the child.

**Tests:**
- `test_aresos_laptop_home_native.py` (19 tests, 1 opt-in):
  - New `MotionTest`, against a hand-driven clock and timers:
    - the glide by day and night: drawn at home until the first frame; mid-glide the house, its box, its sign, the
      street sign and the plots (by day) or the road (by night) move together, while the resting offset, the
      target and the ends stay; a cleared line glides home;
    - the puff rises, fades and stops;
    - the caret goes off and on five times, then stays;
    - the hover keys and the end-sign border.
  - `WindowTest.play` (day and night) now drives **real input through labwc**: a virtual pointer click, then a
    virtual keyboard with a German xkb keymap:
    - a dead circumflex and `a` give `â` through the input method;
    - Escape clears the line;
    - `tool` and Return open `test-tool-1` through the stand-in helper;
    - the new `check_typing` types `tool19`, waits for the glide (it checks that `motion` frames were drawn), takes
      the `typing` picture with a paint check on the framed house, and Escape glides the street home.
    
    Step A's later checks (cut ends, rest, reconnect) run after this real input.
  - `FinderTest` picks the 600 ms opening timer by its delay, since the caret's 550 ms timers now wait beside it.
  - New `MemoryGuardTest` (opt-in, `LAPTOP_HOME_MEMORY_GUARD=1`): three fresh runs, median at most 61,440 KiB after
    a redraw.
- `test_aresos_laptop_home.py`: `ResourcesTest` is replaced by `IconTest`:
  - 53c's limits on `read_icon`;
  - the child's bare environment, closed descriptors, `-I -S`, and no path in its arguments;
  - corrupt, truncated, non-PNG and oversized inputs are refused;
  - the filters, a palette with transparency, 16-bit grey;
  - `icon_surface`'s fit and premultiplication.
  
  The page-containment test is deleted, as the brief says.

**The harness** (`laptop_home_headless.py`):
- `virtual_input(layout='de')` adds labwc's virtual keyboard with an xkb keymap (sent with `SCM_RIGHTS`) beside the
  pointer. `virtual_click` uses it.
- The program's process no longer imports the stand-in helper's module.

**The memory script** (`laptop_home_memory.py`):
- It samples 15 s after one redraw that it asks for through the channel; `--first-draw` keeps step A's method.
- It reports the window buffers, the heap and memory by mapping.
- The prototype (`laptop_home_native.py`) redraws once by itself when asked, so the control is measured the same
  way.

**The design** (`docs/design/LAPTOP-HOME.md`):
- Section 4 is rewritten for the native program: why, the owner's choice on board #375, the rules, and the memory
  table.
- Section 7: the companions bring their own web view, only while switched on, and read `shift` for their world.
- Section 8: the web page is now the rejected option.
- Section 2.4 and section 9 no longer name the engine for the home.

## Verified

Every run was headless: a private labwc, `/dev` and (since round 1) `/run` masked and the network unshared before it
started, and its own
`HOME`, `XDG_*` folders, session bus and stand-in helper. `DISPLAY`, `WAYLAND_DISPLAY` and `WAYLAND_SOCKET` were
removed. `LAPTOP_HOME_TEST_LAYER_DIR` pointed to the verified Fedora 44 `gtk4-layer-shell` extraction, as in step A.

| Command | Result |
|---|---|
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 13 tests, OK |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_native.py'` (with `LAPTOP_HOME_TEST_PICTURES=1`) | 19 tests, OK (1 skipped: the opt-in guard), 43 s, in full after the last code change; the night test once more before it, OK |
| `cd os/tests && python3 -m unittest test_aresos_laptop_home_native.GeometryTest …FinderTest …MotionTest` | 11 tests, OK |
| `LAPTOP_HOME_MEMORY_GUARD=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_native.py' -k MemoryGuardTest` | **FAILED**: the median is above 61,440 KiB (see PLAN-GAP 1) |
| `cd os/tests && python3 laptop_home_memory.py --runs 5`, the same with `--prototype`, and `--runs 3 --first-draw` | The table below; the runs are in `memory-step-b.jsonl` |
| The image check's Python, run locally against the worktree's program with `env -i HOME=/tmp PATH=/usr/bin` | `LAPTOP_HOME_GTK 4 22 cairo 1.28.0`; the decoder assertion held. `bash -n os/ci/image-checks.sh`: OK |
| Hosted: `gh workflow run "OS image" --ref pkg/53f-native-home -f checks_only=true` | Run **44426761677**, started, not watched |

**Step A's paint breaks** (commit `a58b608a`; `LAPTOP_HOME_TEST_BROKEN=<part>`, each check failed):

| Broken part | Look | The check that failed |
|---|---|---|
| `background` | day | terraces: `[(13,13,16), (43,40,50), (13,13,16), (13,13,16)]` against turf, paving, turf, bank edge |
| `plots` | day | empty plot slab: `(138,178,84) != (185,199,162)` |
| `idle` (no idle filter) | day | idle house: `(25,130,143)`, expected `(77,112,116)`; round 1, against 53c's picture: `(76,112,116)` |
| `gold_door` | day | gold door, row 1: `(5,5,6)`, expected `(253,226,158)` |
| `frame` | day | frame |
| `view_mask` (no fade) | day | fade at `EDGE/2`: `(38,38,40) != (138,178,84)` |
| `street_ends` | day | end sign plate: 127 > 26 |
| `fades` | night | night fade: `(24,24,28) != (13,13,16)` |

**Round 1's runs** (headless as above, `LAPTOP_HOME_REQUIRE_HEADLESS=1`):
`discover -p 'test_aresos_laptop_home.py'`: 16 tests, OK. `discover -p 'test_aresos_laptop_home_native.py'`: 31
tests, OK (2 skipped: the opt-in memory tests), 47 s, after the last code change. Pictures: unchanged apart from
the night stars' random twinkle.

**The debugging that set a design choice:** with `Gtk.IMMulticontext`, a dead circumflex and then `a` gave a bare
`a` under labwc. GTK picked its Wayland text-input method, and that composes nothing while no input-method program
runs. The same keys with `GTK_IM_MODULE=gtk-im-context-simple` gave `â`. Hence `Gtk.IMContextSimple` (JUDGMENT-CALL 1).

**Pictures**, all looked at:
- **New in step B:** `day-typing.png` and `night-typing.png`, each beside 53c's `day-typing.png`. They match in
  layout, colour and text: the long street glided so that Test Tool 19 stands framed at the left edge, the rest
  dimmed, `0 ›` at the right end, `/tool19` and "Enter opens Test Tool 19" on the line.
  - Differences: the clock is fixed at 09:41.
  - The caret is drawn (the picture asks for it; 53c's caught a blink's off phase).
  - North shows 9 houses where 53c's shows 8: 53c took its picture in the town with `test-web-1` removed, ours is
    taken before that step.
- **One bug a picture caught:** a street's first glide was drawn at its target before the first frame, then jumped
  back. Fixed (`Town.glide` sets the drawn offset when it starts), and the model test now checks it.
- Step A's eight pictures were unchanged by step B's code, apart from `night-helper-away.png`, whose random star
  twinkle differs per run. Step A's comparison with 53c's pictures still holds.

**Memory, set-up S** (five fresh runs each, sampled at rest 15 s after one redraw; the prototype in the same session):

| Process (set-up S) | Sampled | Median PSS | Spread | Pss_Anon median | Window buffers |
|---|---|---:|---:|---:|---:|
| 53e's WebKit home, final shipped settings (53e's report) | at rest | 418.1 MiB | 417.1–419.5 MiB | — | — |
| 53f step A (step A's report) | 15 s after the first draw | 55,678 KiB (54.4 MiB) | 55,454–73,210 KiB | 29,420 KiB | 1 (2 in one run) |
| 53f step A's code (this session, 3 runs) | 15 s after one redraw | 73,003 KiB (71.3 MiB) | 72,530–73,271 KiB | 38,808 KiB | 2 |
| **53f final** | **15 s after one redraw** | **62,358 KiB (60.9 MiB)** | **62,310–62,488 KiB** | 27,804 KiB | 2 |
| 53f final (3 runs) | 15 s after the first draw | 53,462 KiB (52.2 MiB) | 53,453–53,486 KiB | 27,560 KiB | 1 |
| 53e's native prototype (control, same redraw) | 15 s after one redraw | 64,075 KiB (62.6 MiB) | 63,778–64,179 KiB | 31,144 KiB | 2 |
| 53e's native prototype (53e's report) | first draw | 46.6 MiB | 45.8–46.6 MiB | — | 1 |

**The candidates, one at a time** (3 runs each, after one redraw; each row is measured on top of the kept rows above it):

| Candidate | Median PSS | Change | Kept |
|---|---:|---:|---|
| Step A's code | 73,003 KiB | | |
| Fixed mmap threshold (`mallopt(M_MMAP_THRESHOLD, 128 KiB)`): the heap went from 21,480 to 12,328 KiB | 64,035 KiB | −8,968 | yes |
| `malloc_trim(0)` 1 s after each draw | 63,759 KiB | −276 (heap −56) | no: within noise, and a timer per frame |
| No OpenSSL in the process (`sys.modules['ssl'] = None`, `secrets` → `os.urandom`) | 63,274 KiB | −761 | yes |
| The stand-in's module out of the measured process (the harness, not the program) | 62,632 KiB | −642 | yes (a measurement fix) |
| One malloc arena (`M_ARENA_MAX` 1) | 62,520 KiB | −112 | no: within noise |
| GIO's local file system (`GIO_USE_VFS=local`) | 62,078 KiB | −554 | yes |
| Step B's input, motion and icons on top (5 runs, the final row) | 62,358 KiB | +280 | |

**Why the fixed threshold matters.** GSK's Cairo renderer replays the drawing area's recording into a full-window
temporary picture (8 MiB) every frame. glibc serves the first one with mmap. When that one is freed, glibc raises its
mmap threshold to the picture's size, so from the second frame on the temporary comes from the heap, which keeps the
space. That was step A's "heap growth". The control has it too: its heap is 14,904 KiB after a redraw.

**Ten largest mappings** of the median final run (PSS, KiB): `[heap]` 11,436; `memfd:gdk-wayland` 8,100;
`memfd:gdk-wayland` 8,100; `libgtk-4.so` (text) 4,612; anonymous 3,464; anonymous 3,052; `libgtk-4.so` (data)
2,536; anonymous 1,008; anonymous 1,008; anonymous 992. The Python object arenas are the 1 MiB anonymous ones.

**The GPU check** (accepted by the lead in step A, kept): GTK 4 links glvnd's `libEGL`/`libGLX` dispatchers and the
Vulkan loader into every GTK 4 process, the prototype too, and they load no driver by themselves. The checks look
for real drivers instead: vendor EGL, GLX and Vulkan libraries (`libEGL_*`, `libGLX_*`, `libvulkan_*`), gallium,
LLVM, anything NVIDIA's and `/dri/`. None was mapped in any run, and every memory sample asserts the same.

## Not verified

- **Set-up I (the Intel chip)** is deferred to the laptop trial. It is where the one-buffer number should show
  (PLAN-GAP 1).
- **His session:**
  - his real keyboard and mouse (the tests use labwc's virtual devices);
  - an input-method program (ibus or fcitx), if he runs one: see JUDGMENT-CALL 1;
  - his compose file;
  - key repeat (GTK repeats held keys itself; the tests press and release).
- **Accessibility:** the harness sets `GTK_A11Y=none`. With AT-SPI on in his session, memory may be a little higher.
- The hosted run's result. It was started and not watched, as the brief says.

## JUDGMENT-CALL

1. **GTK's simple input method, not the multicontext.**
   - Chosen: `Gtk.IMContextSimple`. Dead keys and compose work on his German layout whatever runs in the session.
   - Rejected: `Gtk.IMMulticontext`. On labwc it picked the Wayland text-input method, which composed nothing
     without an input-method program (seen above).
   - Cost: an input-method program (Japanese or Chinese input through ibus or fcitx) cannot type into the finder.
   - Changing it later: one line, plus a check that dead keys still work in his session.
2. **The 0.12 s and 0.15 s hover and match transitions are instant.** These are 53c's fades of a house's idle
   filter and dim opacity, the slot's hover lift and border, the finder line's background, and the day plate's
   background. The glide, the puff and the caret blinks are ported.
   - Rejected: cross-fades. They need a second logo picture per changing house while the fade runs, and a frame
     per tick for 45 houses at once while typing. Their memory and processor cost were not worth 0.15 s here.
   - Changing it later: a fade amount per house in the model and a second blit in the painter.
3. **Three process-wide settings for memory**, each measured above:
   - no TLS anywhere in the home's process;
   - only GIO's local file system (the home opens no remote files);
   - a fixed malloc mmap threshold.
   
   Each is one line with a comment, and an outside environment still wins for the GIO one.

## PLAN-GAP

1. **The limit is not met after a redraw in set-up S: the floor is 62,358 KiB (60.9 MiB), 918 KiB over 61,440.**
   The look is kept, and the opt-in guard fails, as it should.
   - Where it goes: two 8,100 KiB window buffers (26 %), `libgtk-4.so` about 7.1 MiB, the heap 11.4 MiB, and Python
     and GTK's anonymous memory.
   - Why two buffers: GTK's Wayland Cairo context keeps one released buffer for reuse. It needs a second buffer
     from the second frame on because set-up S's compositor draws with pixman, which keeps the shown buffer as its
     texture and so does not release it until the next one arrives.
   - The bare prototype is over the limit too after one redraw (64,075 KiB). The limit as worded (after a redraw,
     in set-up S) is below what any GTK 4 window of this size reaches there.
   
   What would get there, in order of cost:
   - **Measure in set-up I.** A compositor that draws on the graphics chip uploads each shared-memory picture and
     releases it at once, so GTK reuses one buffer. That state measured 52.2 MiB here (the first-draw row).
   - **About 1.4 MiB of the program's own:** the 45 house logo pictures (90 × 90 × 4 bytes each, in the heap).
     They could be drawn from 12 × 12 cell pictures scaled up without smoothing, plus a shared overlay for the
     block hints. That is a painter change the brief ruled out for this step.
   - A GTK change that drops the spare buffer at rest.
2. **The brief's "maps no libEGL, libGLX, libvulkan"** cannot hold for any GTK 4 process (step A's finding,
   accepted). The checks look for real drivers, as listed above.
3. **The brief's step B.4 sample "15 s after the first complete draw"** is GTK's best case: one buffer and no
   frame-temporary growth. The lead's correction (after a redraw) is what step B measured. The first-draw number
   is kept beside it.

## Open questions

- (Round 2, outside the brief.) The finder matches with `lower()`, as 53c's page did with `toLowerCase()`.
  So `strasse` does not find `Straße`, and `straße` does not find `Strasse`. Matching with `casefold()` would find
  both. That changes what the owner's German typing finds, so it is the lead's call.

- Should the limit be judged in set-up I on the laptop (the one-buffer state), or should set-up S's limit change to
  "after a redraw, two window buffers included"? This decides whether PLAN-GAP 1 needs the logo change.
- Does he run an input-method program in his session? If yes, JUDGMENT-CALL 1 needs his word.

## `.work/`

`layer-test/` (the verified RPM and its extraction, under 1 MiB) and `mem/` (the measurement JSON, under 1 MiB).
Nothing is over 500 MB.

## The lead's decisions (2026-11-19)

- **The 60 MiB limit is judged in set-up I** (the real compositor on the Intel chip, one window picture: 52.2 MiB
  measured here with one picture), at the laptop trial. In set-up S the guard pins today's two-picture number:
  `MemoryGuardTest.LIMIT_KIB = 64000` (step B measured 62,358 KiB). PLAN-GAP 1 is closed by this; the logo-cell
  change (about 1.4 MiB) is not needed.
- **JUDGMENT-CALLs 1 to 3 are accepted** as technical: GTK's simple input method (the owner types German with dead
  keys and runs no input-method program), instant hover and match changes instead of 53c's 0.12 s and 0.15 s fades,
  and the three process-wide memory settings.
- The page folder's deletion landed in commit 9c562c9e, whose message does not say so.
