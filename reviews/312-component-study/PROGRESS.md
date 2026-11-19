# 312 progress

Brief: `briefs/312-component-study.md`. One fresh agent per step. The last step deletes this file and puts its last
state into the pull request's description.

## Done: step 1, foundations and the indicator (2026-11-19, Claude Fable 5.2)

**Public sections finished** in `docs/design/COMPONENTS.md`:
- 1, the theme layer (function and look, the look pack, where the look lives per renderer, what it costs);
- 2, version A's colours and font (builds on Ares-Block's construction, changes its colours; Jersey 10 measured);
- 3, the grid and the scales, with A's first sprites;
- 4.1, the brightness and volume indicator, complete in both looks;
- 5, version B's runtime contract;
- first entries in 6 (findings for step 4), 7 (two questions) and 8 (the checks answered so far).

**Public pictures** in `docs/design/components/` (204 KB in all; the folder's limit is about 3 MB):
`A-01-palette`, `A-02-font`, `A-03-sprites`, `A-04-indicator-states`, `A-05-indicator-scales`, `A-06-indicator-top`,
`A-07-indicator-bottom`, `A-08-indicator-over-app`, and 16 sprites at one pixel per GUI unit in `sprites/`.

**Private mockups finished** (`~/.local/state/aresos-dev/312-look-b/`, with `B-INDEX.md`): `B-01` indicator states,
`B-02` the slider form, `B-03` A and B side by side, `B-04` top centre on the drawn scene, `B-05` over an app, `B-06`
scales. `work/parts.png` there is a working sheet of game sprites, not a mockup.

**The public and private check.** Before the push of this step I ran `git status` and `git diff --cached --stat` and
confirmed: every staged PNG is under `docs/design/components/` and was written by `tools/draw_a.py`, which opens no
game file; no staged file's SHA-256 equals a file in the private folder; nothing staged came from the game jar, an
extracted file or the private folder. Every later step repeats this before each push and says so here.

## Left, in order

2. **The window frame** (section 4.2): buttons and frame states in A and B, minimize and restore, what labwc can draw
   and what programs draw themselves. Step 1 left a first pass of A's push buttons (`button*.png`); step 2 owns them
   and may redraw them. labwc's title-bar buttons are separate sprites (one image per button and state, no
   nine-slice, no pressed state).
3. **Layouts and switching** (4.3, 4.4): window layouts with the covering rule's cases, and app switching.
4. **The overview, the password window and the decision** (4.5, 4.6, 6, 7, 8): then delete this file.

## How to draw

The drawing kit is `reviews/312-component-study/tools/`:
- `look.py`: version A's palette, sprites and font handling (`LookA`), the indicator's layout (`indicator()`), and the
  backdrops (a drawn noon scene, a drawn app). A piece is one function that takes a look and asks it for every part.
- `draw_a.py`: writes A's sprites and pictures into `docs/design/components/`.
- `draw_b.py`: version B's look (`LookB`: the game's sprites and its letter sheets) and B's pictures. It writes only
  to the private folder and has no option to write anywhere else. It also rewrites `B-INDEX.md`, so add new rows to
  its `INDEX` text.

Both need Jersey 10, which is not in the repo. Download `Jersey10-Regular.ttf` from Google Fonts' `ofl/jersey10`
(`github.com/google/fonts`) into a new folder outside the checkout; the scripts check its SHA-256
(`db9cbd09…1c3e82`).

    python3 -I reviews/312-component-study/tools/draw_a.py --font <folder>/Jersey10-Regular.ttf
    python3 -I reviews/312-component-study/tools/draw_b.py --font <folder>/Jersey10-Regular.ttf

Python leaves a `__pycache__` folder beside the scripts; it is ignored by git.

**For a new piece:** add its made-up states and one layout function to `look.py`, add any new part as a method to
both `LookA` and `LookB`, and draw it from both scripts. That keeps the study's own proof that one layout serves two
looks.

## What the files don't show

- **Why the bar is 143 units wide:** "Laptop screen" and "100%" have to fit on one line above it. The first try (123)
  made them touch.
- **Jersey 10's grid** was found by measuring: 1400 units per em, squares of 75 units. `look.py` draws it at 56 px,
  where a square is exactly 3 pixels, and keeps every third pixel. `docs/design/WINDOWS.md` still says 21 pt is "its
  exact double size"; that is one and a half times, and its note about half pixels follows from it. WINDOWS.md was
  not edited (it is not one of this package's outputs): the package that next touches it should correct the line.
- **Nothing was run** against labwc, Qt, PipeWire or the backlight. Section 4.1's "Not verified" list and section 5's
  two Prism paths are for the build packages to confirm.
- **B's icons are a weak point:** the game has no sun, loudspeaker or microphone picture at icon size (its sun is a
  32 × 32 sky texture on black), so `B-01` uses a lantern, a bell, the barrier sign and the social screen's
  chat-bubble buttons. `B-02` (the game's slider with the text inside) avoids icons altogether.
- **B's font in the mockups** follows the game's own table (`font/include/default.json`): a letter's width is its
  rightmost inked column plus one, a space is 4, the shadow is the colour at a quarter.
- **Tried and dropped:** Pixelify Sans as a second font (never on whole pixels from 8 to 48 px in the same test).

## For the lead to confirm (not questions for the owner)

- The GUI scale his game actually runs at (decides whether overlays want 3x or 4x).
- That labwc looks for a theme in `~/.local/share/themes/` before `/usr/share/themes/` (B's frame relies on it).
- That labwc puts a layer surface without a named output on the pointer's screen.
- Prism's two paths for the client jar and the asset objects, on the first real `AresDesktop` instance.
- Whether the session has a bus that can start a program on demand (the indicator's start).

## Questions for the owner so far (section 7; the lead posts them, step 4 makes the final list)

1. Where should the brightness and volume plate appear: at the top centre (`A-06`, over an app `A-08`) or low above
   the hotbar (`A-07`)? Recommended: top centre.
2. How big: small, medium or large (`A-05`, `B-06`)? Recommended: medium (3x).
