# 53f progress (step A done; step B next)

Branch `pkg/53f-native-home`. Step A was built by a Claude Opus agent on 2026-11-19. This file is the handoff
for step B. Step B replaces it with the final report in the AGENTS.md format.

## Done in step A

- **The program** (`os/config/usr/libexec/aresos-laptop-home`, one file as before). The helper connection, kept
  town, battery, surfaces, token and `LD_PRELOAD` handling are unchanged. The web view is replaced by:
  - `load_gui()`: before importing `gi` it sets `GDK_DISABLE=gl,vulkan` and `GSK_RENDERER=cairo` with
    `setdefault`, so an explicit outside choice still wins. It imports Gtk, Gdk, Pango, PangoCairo, cairo and the
    optional layer library. No WebKit is imported any more.
  - **The model** (pure Python, no `gi`). `build_scene(inputs)` turns explicit inputs into where every street,
    terrace, plot, house, door, mat, frame, sign, end sign, hotbar slot and line of text goes, plus the hit regions.
    The inputs are: look, size, home, programs, running, online, query, selected, `best_cleared`, offsets,
    `by_hand`, hover, opening, error, clock, battery and stars. 53c's rules are pure functions: `place_index`,
    `town_grid`, `snap`, `street_range`, `follow`, `hidden`, `score`, `search` and `hint_text`.
  - **`Town`**: 53c's `home.js` state without GTK. It covers `apply`, `search`, `refresh` (follow), `key`,
    `click`, `pan` (onPan's move of the frame), `step` (arrows), `open` (600 ms opening, five-second failure line),
    `blur` and `twinkle`. Timers, the opener and redraws are passed in as callables.
  - **`Painter`**: 53c's CSS and `logo.js` in Cairo and Pango, with plain text only (`set_text`, never markup).
    It keeps one surface per house logo, and one per hotbar logo (48 × 48, nine at most). The stacking is the
    page's: ground; clock, battery and streets in document order; pad, hotbar and hint; the night fades (z 5);
    the end signs (z 6); the typing line (z 40). The idle filters are the CSS filter formulas applied to each
    flat colour. Box shadows are separable erf masks, cached by size. The day view mask is a group masked by a
    linear gradient, clipped to the street (about 1.5 MiB, temporary). There are no full-screen caches.
  - **`LaptopHome`**: a `GtkDrawingArea` on the layer surface or the fallback window. All redraws go through
    `redraw(reason)`. The clock ticks once a minute; at night one star changes every 4 s, only while mapped.
    Focus loss calls `town.blur()`, as the page's blur did.
  - **The startup gate**: the window is presented on the first helper state (`helper` in a publish) or 500 ms
    after activate. Opening needs `peer` and `shown`, and the town needs `online`, which only the complete paged
    reads set.
- **The test channel** (`os/tests/laptop_home_headless.py`, only in the harness). The interface is below.
- **53e's harness changes** brought over: `/dev` masked with bubblewrap before labwc, private XDG data and cache
  folders and `TMPDIR`, `layer_state()`, the program path, and 53e's prototype as `prototype=True`
  (`laptop_home_native.py`, unchanged). New: `--unshare-net`, because labwc's Xwayland tried to bind the host's
  abstract `@/tmp/.X11-unix/X1`. `headless_available()` no longer asks for WebKit.
- **Tests** (`os/tests/test_aresos_laptop_home_native.py`, 14 tests):
  - `GeometryTest` (model only): the study's grid and terraces for three towns; REVIEW-3 finding 6 (plot counts
    per street and side, the terraces at each street's foot); places by day and night with a hole; Night street's
    road; slide targets, a hand slide, a framed house beside a cut end, the end counts, 53c's slid grid
    (offset 196, the 673–757 and 1261–1345 columns); a hand slide moving the frame to a visible match.
  - `FinderTest` (model only): ranking (short, name, generic, keyword), Backspace, Escape, arrows, Enter,
    1–9, clicks on a house, a slot and a finder row, the failure line and its 5 s timer, blur, offline.
  - `WindowTest` (headless, day and night): the first draw lights the running houses; `GskCairoRenderer`; the
    program's own renderer variables; no GPU driver mapped. The paint checks on the 1920 × 1080 offscreen picture:
    terraces at 53c's sampled values; an idle, a lit and a dimmed house; the gold door and its day frame; the
    frame around the best hit; an empty slab and the turf between plots; the fade at `EDGE/2` and past `EDGE` by
    day, and the 120 px wall fade at night; an end sign. Also 13 s at rest, the reconnect, the saved town without
    battery, and the full kept town lit on first draw while the catalogue is held back (53c's
    delayed-catalogue regression).
  - `SurfaceTest`: real focus reports and their replay after hello (virtual pointer); the token and
    `LD_PRELOAD`, vendor pins, app ID, layer or fullscreen window, renderer, no driver or WebKit mapped; the old
    bridge's open results; the kept town coming up with opening off.
- **Removed** (the web view is gone, so these can no longer run): `test_aresos_laptop_home_page.py`,
  `test_aresos_laptop_home_webkit.py` and the bridge fixture `os/tests/laptop-home-page/`. Their kept checks are
  ported, as listed above. The generated fixture town moved to `laptop_home_helper.py`.
- **Pictures** (`reviews/53f-native-home/pictures/`, 53c's names): `{day,night}-{home,forty-five,opened,helper-away}`.
  They come from the channel's offscreen picture of the running program, with the clock fixed at
  2026-11-19 09:41. The typing pictures belong to step B.

## Verified in step A

Every run was headless, with `DISPLAY`, `WAYLAND_DISPLAY` and `WAYLAND_SOCKET` removed and
`LAPTOP_HOME_TEST_LAYER_DIR=<worktree>/.work/layer-test/extracted/usr/lib64`. That is Fedora 44's
`gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm`, as 53e used it; `rpm -K` printed `digests signatures OK`.

| Command | Result |
|---|---|
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_native.py'` (with `LAPTOP_HOME_TEST_PICTURES=1`) | 14 tests, OK, 40 s |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 11 tests, OK |
| The day or night test with `LAPTOP_HOME_TEST_BROKEN=<part>`, once per part | Each fails at its own check, see below |
| `cd os/tests && python3 laptop_home_memory.py --runs 5`, then the same with `--prototype` | See the memory section |

**Each paint check caught a broken painter:**

| Broken part | Look | The check that failed |
|---|---|---|
| `background` | day | terraces: `[(13,13,16), (43,40,50), (13,13,16), (13,13,16)] != [turf, paving, turf, bank edge]` |
| `plots` | day | empty plot slab: `(138,178,84) != (185,199,162)` |
| `idle` (no idle filter) | day | idle house: `(25,130,143)`, expected `(77,112,116)` |
| `gold_door` | day | gold door, row 1: `(5,5,6)`, expected `(253,226,158)` |
| `frame` | day | frame |
| `view_mask` (painted without the fade) | day | fade at `EDGE/2`: `(38,38,40) != (138,178,84)` |
| `street_ends` | day | end sign plate: 127 > 26 |
| `fades` | night | night fade: `(24,24,28) != (13,13,16)` |

**Rest:** over 13 s, nothing redraws except the clock (at most 2) and, at night, the star (3 or 4). The frame
clock painted no more frames than that. The day and night runs both passed.

## The pictures against 53c's

I looked at all eight pictures, each beside 53c's picture of the same name. Layout, colours and text match:
street positions, plots, roads and joints, houses and their logos, plates, signs, end signs with `‹ 2` and `2 ›`,
the night fades, the lit door and mat, the hotbar, the typing line and the hint. The differences, and why:

- **Clock and date:** a fixed 09:41, Thursday 19 November (injected for repeatable pictures). 53c used the live
  clock.
- **Text rasterising:** Pango with no hinting and grey antialiasing, against WebKit's text. Glyph edges and
  sub-pixel positions can differ by up to a pixel. Pango splits letter spacing on both sides of a glyph, which
  shifts the spaced uppercase labels (dates, group names, the hint) by a fraction of a pixel.
- **Blurred shadows** (the hotbar's drop shadow, the night door and mat glows, the running slot's mark) use an
  exact Gaussian for a rectangle that ignores corner radii. At the hotbar's 12 px corners the shadow is a little
  fuller.
- **The charging bolt** `ϟ` comes from Pango's font fallback, so its shape can differ slightly from WebKit's.

## Memory, first measurement (A.8)

Set-up S: the shipped entry point under the harness, the real background layer (checked each run), the verified
`GskCairoRenderer`, `/dev` masked before labwc, fonts matched by `fc-match`, 45 houses and 47 programs. Each of
five fresh runs was sampled 15 s after the first complete draw. 53e's prototype ran as the control in the same
session. The per-run data is in `memory-step-a.jsonl` (home paths written as `/home/owner`).

| Process (set-up S) | Median PSS | Spread | Pss_Anon median |
|---|---:|---:|---:|
| 53e's WebKit home, final shipped settings (53e's report) | 418.1 MiB | 417.1–419.5 | — |
| **53f native home, step A** | **55,678 KiB (54.4 MiB)** | 55,454–73,210 KiB | 29,420 KiB |
| 53e's native prototype (control, this session) | 48,625 KiB (47.5 MiB) | 48,363–48,723 KiB | 23,600 KiB |
| 53e's native prototype (53e's report) | 46.6 MiB | 45.8–46.6 | — |

The median is under the 61,440 KiB limit.

**The finding that matters for step B:** the 73,210 KiB run was the one where the clock ticked inside the rest
window, the only one with a draw at rest (`draws_at_rest` 1). After that one redraw the process holds a second
8,100 KiB `memfd:gdk-wayland` buffer, and its heap grew from 12,080 to 21,472 KiB. The other four runs drew once
and held one buffer. The prototype never redraws, so it holds one buffer too. A real home redraws every minute
for the clock, so **its steady state is about 71.5 MiB, over the limit**. Fifteen seconds after the first draw is
the best case, not the resting state. Step B should measure after at least one redraw, for example by waiting
past a minute boundary or by asking the channel for one redraw before the 15 s. Then it should bring that number
under 60 MiB without redesigning the painter. Candidates, unmeasured:
- `malloc_trim(0)` after a draw;
- keeping the cairo render node small: a redraw replays a recording of every operation, and GTK keeps the
  previous node for diffing;
- drawing the clock (and the night star) as their own small widgets, so a tick does not re-record the whole town;
- understanding whether GTK's Wayland Cairo context can keep a single buffer at rest.

## Left for step B, in order

1. **Input (B.1).** Wire the controllers to the existing `Town` handlers:
   - `GtkEventControllerKey` with a `GtkIMMulticontext` (commit → one `town.key(char)` per character; Escape,
     BackSpace, Return, arrows and the digits by keyval; ignore Ctrl, Alt and Super; pass `repeat`);
   - `GtkGestureClick` → `town.click(x, y)` (window coordinates; `hit_test` applies the fit);
   - `GtkEventControllerMotion` → `town.set_hover(...)`, with the hover strings `house:<id>`, `slot:<i>`,
     `row:<id>` (built from `hit_test`; for `end:` and `sign:` hover add drawing first, 53c has an end-sign hover
     border);
   - focus loss already calls `town.blur()`; test it through real focus.
   
   Drive one key and one click through labwc's virtual keyboard and pointer (`Headless.virtual_click`).
2. **Motion (B.2).**
   - `Town.refresh` now sets `offsets` straight to each street's `target`. Add a current offset that glides
     there over 0.3 s ease-out on a `add_tick_callback` that is removed when every street rests. The scene
     already takes `offsets` as the current position and returns `target`.
   - The other motion is the 0.6 s purple puff, the caret's five blinks (1.1 s steps), the 0.12 s and 0.15 s
     transitions (slot hover lift, house filter and opacity, finder line), and the hotbar hover lift (drawn,
     without motion).
   - Then rerun step A's checks through real input, add 53c's intermediate-frame check (house, roof and road
     moving with the offset mid-glide), and take the `typing` pictures after typing `tool19`.
   - Night repaint costs about 59 ms against 6.6 ms by day, measured offscreen: two full-screen radial
     gradients. Make the glide affordable at night without a full-screen cache.
3. **Finder icons (B.3).** `LaptopHome.icons` already holds the helper's icon paths (set in `publish`). The
   painter draws the 24 × 24 placeholder in each row; draw the decoded icon there. The decoder child and the
   limit tests are as in the brief. `Resources.read`'s icon branch holds 53c's opened-descriptor checks.
4. **Memory (B.4).** `os/tests/laptop_home_memory.py` (53e's method; `--prototype` is the control). Add the
   opt-in guard (median of three at most 61,440 KiB) and the post-redraw sample above.
5. **Remove the web engine (B.5).**
   - Still there: `PAGE_ROOT`, `SCHEME`, `MIME` and `Resources` in the program (for `ResourcesTest` and the icon
     checks); `os/config/usr/share/aresos/laptop-home/`; and `image-checks.sh` lines 678–685, which import WebKit.
   - The page tests and the WebKit tests are already removed (above).
6. **The design (B.6)**, the CI run, and the report in this file.

## The native test channel (for step B)

`Headless(path, socket, look='day'|'night', size='1920x1080', font_dir=..., battery=True, clock=ISO or None,
broken=None, prototype=False)`. Requests go through `Headless.request(op, **fields)`. Each is a JSON file
answered on the GTK thread, and they run one at a time.

| Request | Answer |
|---|---|
| `model` (or `.model()`) | The scene dict without `logos`: `streets[].houses[]`, `slots`, `finder`, `hits`, `framed`, `matches`, `online`, `grid`, `fit` |
| `.until(predicate)` | Polls `model` until `predicate(scene)` holds |
| `set`, `state={...}`, optional `refresh=True` | Sets `Town` fields (`query`, `selected`, `hover`, `opening`, `error`, `offsets`, `by_hand`, `best_cleared`, `stars`) and redraws with the reason `test` |
| `picture`, `state={...}` (or `.picture(**state)`) | Injects the state, then the painter draws `build_scene` at 1920 × 1080 into a `cairo.ImageSurface`. Returns the PNG path. |
| `key`, `key='Escape'` (or `.key(...)`, `.type(text)`) | `town.key(...)`: DOM key names, one character per printable key |
| `click`, `x`, `y` | `town.click(x, y)` in window coordinates; returns the hit |
| `blur` | `town.blur()` |
| `bridge-open`, `id` | `LaptopHome.open_app`; the helper's result, as the old `aresosHome.open` |
| `counters` | `{draws, frames, reasons: {state, clock, star, test}, first: {houses, lit, online, hint}}`. `frames` counts the frame clock's `after-paint`; `first` is the first draw |
| `renderer` | The window's GSK renderer type name |
| `window`, `other-window`, `close-other-window` | As 53c's `@window` and the focus test's helpers |

`parent.json` holds `pid`, `before` and `after` (token and `LD_PRELOAD`), `pins`, `drm_hidden`, `app_id`,
`display`, `environment` (the program's `GDK_DISABLE` and `GSK_RENDERER`) and `layer`. `LAPTOP_HOME_TEST_BROKEN`
(a name from `BREAKS`) switches off one painter part for the break runs. `LAPTOP_HOME_TEST_PICTURES=1` copies
the named pictures into `pictures/`.

## What the code doesn't show

- **PLAN-GAP: "maps no libEGL, libGLX, libvulkan".** Fedora's GTK 4 links `libvulkan.so.1` (the loader) and
  `libepoxy`, which brings glvnd's `libEGL.so.1` and `libGLX.so.0` dispatchers into every GTK 4 process (53e's
  prototype too). They load no driver by themselves. The tests check for drivers instead: `libEGL_*`,
  `libGLX_*`, `libvulkan_*`, gallium, LLVM, anything NVIDIA and `/dri/`. None were mapped.
- **Decision: one file.** The model and the painter are sections of the program, because libexec has no
  convention for shared Python modules and the image installs single files. The model section imports
  nothing from `gi`, and its tests run without a display.
- **Decision: the paint checks run in the real program**, through the channel, not in the test process. Pango in
  the test process would use the owner's own fontconfig cache and fonts.
- **Decision: approximate hit regions for the signs.** Night street sign 200 × 38, day 200 × 51; a house's
  sign column is `pitch − 6` wide and 54 high above its logo. Day plates are measured only by the painter.
  Step B should check clicks on a plate's edge.
- **Decision: `best_cleared`.** This input reproduces 53c's `best = null` after a hand slide that leaves no
  match in view.
- **Fonts:** the painter sets hint metrics off, no hinting and grey antialiasing on every layout, so the window
  and the offscreen picture render text the same way.
- **`.work/` holds** `layer-test/` (the verified RPM and its extraction, under 1 MiB) and small scratch pictures.
  Nothing is over 500 MB.
- **Not verified:** the Intel chip (set-up I, deferred), the owner's session, and real input (step B).
