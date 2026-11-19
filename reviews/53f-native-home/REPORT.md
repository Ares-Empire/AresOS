# 53f report: the laptop home drawn natively

Branch `pkg/53f-native-home`, based on 53c's branch (PR #114); the lead rebases it onto main after #114 merges.
Built by Claude Opus agents in two steps on 2026-11-19. Step A built the model, the painter, the test channel and the
checks against injected state. Step B built input, motion, icons, memory and the clean-up. This text replaces step A's
handoff; the lead moves it to `REPORT.md`. Hosted checks-only run: **44426761677** (started on `246441f4`, not waited for).

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
  - `decode_png` runs a short-lived `python3 -I -S -c` child. Its environment holds only `PATH` and `LC_ALL`, it
    has no descriptor but its pipes and no helper socket, and it gets the bytes on stdin, never the path.
  - The decoder is PNG only and non-interlaced: grey, RGB, palette (with `tRNS`), grey with alpha and RGBA, at 1
    to 16 bits, with the CRC checked and the inflated size bounded. It returns at most 512 × 512 RGBA.
  - `icon_surface` fits the result into a 48 × 48 picture, drawn at 24 × 24 (object-fit: contain). Cairo
    premultiplies it through an A8 mask.
  - Decoding runs on a worker thread, one child at a time. On any failure the row keeps its plain square. At most
    20 icons are kept.
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

Every run was headless: a private labwc, `/dev` masked and the network unshared before it started, and its own
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
