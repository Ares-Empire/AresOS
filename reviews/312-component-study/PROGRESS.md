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

**Public pictures:** `A-01-palette`, `A-02-font`, `A-03-sprites`, `A-04-indicator-states`, `A-05-indicator-scales`,
`A-06-indicator-top`, `A-07-indicator-bottom`, `A-08-indicator-over-app`, and 16 sprites in `sprites/`.

**Private mockups** (`~/.local/state/aresos-dev/312-look-b/`, with `B-INDEX.md`): `B-01` indicator states, `B-02` the
slider form, `B-03` A and B side by side, `B-04` top centre on the drawn scene, `B-05` over an app, `B-06` scales.

## Done: step 2, the window frame (2026-11-20, Claude Opus 5.5)

The lead (`mac-capacity`) moved this step from Fable to Opus because the Claude week is over pace. Main was merged
into the branch first (clean).

**Public sections finished or changed** in `docs/design/COMPONENTS.md`:
- 4.2, the window frame and its buttons, complete in A, B and C: what each part does, the buttons in every state
  (no pressed state in labwc), active and inactive, Windows and our own (right-click on maximize opens the layout
  menu; the world's hotbar holds minimized windows, proposed for a later package; no roll-up on scrolling over the
  bar), minimize and restore, what labwc can draw (checked in its 0.9.6 manual pages), what programs draw themselves
  and which looks reach them, B and C in words, what the frame needs from the look setting (one theme name, the same
  geometry in every look, a live switch through `labwc --reconfigure`), A's `themerc` and the `rc.xml` mouse block,
  what it is built from, the build's tests, decisions and what is not verified.
- 1: the "no setting" line and cost 4 follow Patrik's decision after step 1.
- 2: one new colour, `red-800` (the lip of a red button).
- 3: the frame's sprites in the sprite table.
- 5: what B and C read for the frame; labwc's home-folder-first rule is now checked in its manual.
- 6, 7 (question 3, and a note on the game's letters in titles for step 4), 8 (four rows extended).

**Public pictures** (`docs/design/components/`, 412 KB in all): `A-09-frame-buttons`, `A-10-frame-windows`,
`A-11-frame-maximized-menu`; `A-01-palette` redrawn with `red-800`; sprites `button-close-hover`, `gold-block`,
`gold-block-hover`, and labwc's 36 images in `sprites/frame/` (named as labwc wants them, at 1 pixel per unit).

**Private mockups finished:** `B-07` B's title-bar images, `B-08` C's, `B-09` B on the scene, `B-10` C on the scene,
`B-11` one title bar in A, B, B with the game's letters, and C, `B-12` B maximized with the menu. Rows are in
`B-INDEX.md`. `work/frame-parts.png` there is a working sheet of game sprites, not a mockup.

**The public and private check, step 2.** Before the push I ran `git status` and `git diff --cached --stat` and
confirmed: every staged PNG is under `docs/design/components/` and was written by `tools/draw_a.py`, which opens no
game file; no staged file's SHA-256 equals a file in the private folder; nothing staged came from the game jar, an
extracted file or the private folder.

## Done: step 3, layouts and switching (2026-11-20, Claude Opus 5.5)

`mac-capacity` moved steps 2 to 4 to Opus (the Claude week is over pace). Mid-step the lead relayed the owner's
answer to board T432, "Yes, follow the look": 4.2 now states it as decided (Ares-Crown is replaced once the frame is
built), and section 7's question 3 is marked answered. The brief is the lead's to update.

**Public sections finished or changed** in `docs/design/COMPONENTS.md`:
- 4.3, window layouts and split screen: the nine places (halves, quarters, two thirds and a third, the middle, its
  own size), the layout menu's rows and "Share the screen with" (our own Snap Assist, a labwc pipe menu), the
  Super+arrow keys with a guard that keeps them off the world, dragging and the preview, what labwc 0.9.6 can and
  cannot do (checked in its manual pages, `rc.xml.all`, `labwc --help` and the list of interfaces in its program),
  the covering rule (the geometry is the shell's own record, filled by labwc's `If` answers at the end of each layout
  binding; which windows go down on a return to the world; a layout comes back whole), the known limits, the build's
  tests, the `rc.xml`, `menu.xml` and `themerc` lines, the two packages it splits into, decisions and what is not
  verified.
- 4.4, app switching: labwc's switcher, its contents and order, the world as "Home", how minimized windows come back
  (four ways), keys, focus, screens, how far the look follows A, B and C, the `themerc` and `rc.xml` lines, tests,
  decisions.
- 4.2: T432 decided; pointers to 4.3 and 4.4 instead of "step 3". 3: the pictograms in the sprite table. 5: what B
  reads for step 3 (nothing new). 6, 7 (question 3 answered; step 3 adds no question), 8 (three rows extended).

**Public pictures** (`docs/design/components/`, 524 KB in all): new `A-12-layouts`, `A-13-half-and-world`,
`A-14-switcher`, and 11 pictograms in `sprites/layout/`; `A-11` redrawn with the final menu and its open list.
`A-09` was redrawn too, from unchanged code: the committed one predated step 2's last caption fix (its column
captions overlapped).

**Private mockups finished:** `B-12` redrawn with the final menu; new `B-13` half and world with the preview, `B-14`
Alt+Tab, `B-15` the layout menu and Alt+Tab in A and B side by side (the sheet to choose from). C has no picture of
its own here: the game has no control for a menu, a preview or a switcher, so C uses B. Rows are in `B-INDEX.md`.

**The public and private check, step 3.** Before the push I ran `git status` and `git diff --cached --stat` and
confirmed: the 21 staged files are `COMPONENTS.md`, `PROGRESS.md`, the three kit scripts, and 16 PNGs, all under
`docs/design/components/` and all written by `tools/draw_a.py`, which opens no game file (its only inputs are flat
colours, the letter maps in `look.py` and Jersey 10); no staged file's SHA-256 equals any file in the private folder
(0 matches); no staged path names the game, its jar, its assets or the private folder; nothing staged came from the
game jar, an extracted file or the private folder.

## Left, in order

4. **The overview, the password window and the decision** (4.5, 4.6, 6, 7, 8): then delete this file and put its
   last state into the pull request's description. Step 4 also designs the look setting itself (where it lives, how
   he changes it); 4.2 says what the frame needs from it, 4.3 adds the layout pictograms (icons the sync step writes
   for B and C). The overview should say how it relates to Alt+Tab (4.4) and to a layout's group (4.3).

## How to draw

The drawing kit is `reviews/312-component-study/tools/`:
- `look.py`: version A's palette, sprites and font handling (`LookA`); the indicator's layout (`indicator()`); the
  frame's layout (`window_frame()`, `window_menu()`, the shared geometry `TITLE_H`, `CELL_W`, `BORDER`, labwc's
  button and state names, and our 8 × 8 pictograms `GLYPHS`); the backdrops and the frame's sheets and scenes.
- `draw_a.py`: writes A's sprites and pictures into `docs/design/components/`.
- `draw_b.py`: version B's look (`LookB`: the game's sprites and its letter sheets), version C's (`LookC`, which
  changes only the title-bar buttons), and their pictures. It writes only to the private folder and has no option to
  write anywhere else. It also rewrites `B-INDEX.md`, so add new rows to its `INDEX` text.

Both need Jersey 10, which is not in the repo. Download `Jersey10-Regular.ttf` from Google Fonts' `ofl/jersey10`
(`github.com/google/fonts`) into a new folder outside the checkout; the scripts check its SHA-256
(`db9cbd09…1c3e82`).

    python3 -I reviews/312-component-study/tools/draw_a.py --font <folder>/Jersey10-Regular.ttf
    python3 -I reviews/312-component-study/tools/draw_b.py --font <folder>/Jersey10-Regular.ttf

Python leaves a `__pycache__` folder beside the scripts; it is ignored by git.

**For a new piece:** add its made-up states and one layout function to `look.py`, add any new part as a method to
both `LookA` and `LookB`, and draw it from both scripts. For the frame the parts are `frame_colours()`,
`menu_colours()`, `title()`, `title_width()` and `title_button()`; step 3 added `layout_icon()`,
`switcher_colours()` and `snap_colours()`. Step 3's layout functions are `window_menu()` (now with pictograms and
submenu rows), `layout_menu_open()`, `half_scene()`, `layouts_sheet()`, `switcher_panel()` and `switcher_scene()`;
the places are `REGIONS`, the menu `LAYOUT_MENU`.

## What the files don't show

- **Why the bar is 20 units and the title starts 5 units down:** Jersey 10's ascent and descent are 1125 and 375 of
  its 1400 units, so at 28 pt its line is exactly 40 px, the bar at 2x, and its capitals start 5 units below the top.
- **B's frame colours** are values typed into `draw_b.py` (the chest grey 198, the slot grey 139, the label grey 64,
  white and black); the menu's colours are read from the game's tooltip sprites at run time.
- **C's signs are small:** the game's font draws `□` and `×` five units wide. Restore is two `□` drawn one unit apart
  each way, because the font has no restore sign.
- **labwc's default mouse bindings apply today:** AresOS's `rc.xml` has no `<mouse>` block. It has keybinds and no
  `<keyboard><default />`, so labwc's own default keys (W-Return and the rest) are not loaded, but its default mouse
  bindings are, including the roll-up on scrolling over a title bar. The frame's mouse block must start with
  `<default />` to keep the rest.
- **Considered and dropped for A's buttons:** Ares-Block's sunken slots. Raised buttons were chosen so that the frame
  and the push buttons speak one language, and so that an inactive window can show its buttons flat.
- **B's white focus line** (the game's sign for focus) is weak over the bright sky (`B-09`). It was kept because it is
  the game's own; the bar's colour carries the focus there.
- **The hotbar's mark for a minimized app is not drawn:** it belongs to the mod's hotbar, whose look is the game's.
- **Jersey 10's 21 pt in WINDOWS.md** is still uncorrected (step 1's note); 4.2 gives the line to the frame package.
- **Nothing was run** against labwc, Qt, PipeWire or the backlight. Sections 4.1 to 4.4's "Not verified" lists and
  section 5's two Prism paths are for the build packages to confirm.
- **Step 3, ways to learn a window's place that were considered and dropped:** a picker program of our own that
  presses a hidden key through labwc's virtual keyboard so that labwc places the window (a virtual keyboard sends its
  own key map to the focused program, which could disturb the game); tiny see-through probe surfaces under the
  windows (whether they count as hidden depends on each program declaring its opaque area); the world learning from
  the compositor that it is hidden (not knowable without running it); a `ForEach` count of filled places on every
  binding (it names no window, and the reports would arrive in no fixed order).
- **Why keys use `SnapToRegion`** and not labwc's `SnapToEdge` with `combine`: a named region makes each key's result
  and the report exact; edge snapping still serves dragging, and the report reads `tiled` for it.
- **Alt+Tab's tiles are scaled smoothly** (`switcher_panel()` uses bilinear scaling), the one place the kit does not
  scale by whole steps: labwc scales live window pictures. Where labwc puts the icon and the title on a tile is
  approximate; colours and sizes are exact. "Home" as the world's title is a proposal (a later mod change).
- **In `A-14` the editor is drawn active** behind the previewed terminal: during Alt+Tab the focus has not moved yet.
- **The pictograms have one state:** labwc shows a menu icon unchanged on the chosen row, so there is no gold-300
  variant, although the chosen row's text turns gold.
- From step 1: why the indicator's bar is 143 units wide (its two labels must fit above it); Jersey 10's grid of 1400
  units per em and squares of 75 units, drawn at 56 px and sampled every third pixel; B's indicator icons are stand-ins
  (lantern, bell, barrier, chat bubbles) because the game has no sun, speaker or microphone at icon size; B's letter
  widths follow `font/include/default.json`; Pixelify Sans was tried and dropped.

## For the lead to confirm (not questions for the owner)

- The GUI scale his game actually runs at (decides whether overlays want 3x or 4x).
- That labwc puts a layer surface without a named output on the pointer's screen.
- Prism's two paths for the client jar and the asset objects, on the first real `AresDesktop` instance.
- Whether the session has a bus that can start a program on demand (the indicator's start).
- The frame's later `rc.xml` mouse block, the new `menu.xml` and the theme name `AresOS` go to `linux-aresos` first.
- Checked in step 2, no longer open: labwc looks for a theme in `~/.local/share/themes/` before `/usr/share/themes/`
  (labwc-theme(5), "THEME").
- From step 3, for `linux-aresos` with the later `rc.xml`: the world's window rule gains `fixedPosition="yes"` (today
  labwc's default Super+drag can move the maximized world), and the start-up cover and the shutdown's black screen
  gain `skipWindowSwitcher="yes"`. These are small and could go in before the layout packages.
- From step 3, for 23c: whether Super held through a mouse drag and then released opens the search (labwc's
  `onRelease` waits only for other keys). Today's default Super+drag already raises it.
- From step 3: covering by layouts needs a new 1.x request from the mod, `world_clicked` (4.3), and splits the layout
  work into two packages (layouts first, covering second). Both are recorded as technical calls, not owner questions.

## Questions for the owner so far (section 7; the lead posts them, step 4 makes the final list)

1. Where should the brightness and volume plate appear: at the top centre (`A-06`, over an app `A-08`) or low above
   the hotbar (`A-07`)? Recommended: top centre.
2. How big: small, medium or large (`A-05`, `B-06`)? Recommended: medium (3x).
3. Should windows wear the Minecraft-look frame too, following the look setting, instead of today's black-and-gold
   Ares-Crown (`A-10`, `B-09`, `B-10`)? Recommended: yes. **Answered** on board T432, 2026-11-20: "Yes, follow the
   look".

Step 3 adds no question: its calls are technical and recorded in 4.3 and 4.4. For the A-or-B choice, step 3's sheet
is `B-15` (menu and Alt+Tab side by side), and `B-13` shows B on a whole screen.
