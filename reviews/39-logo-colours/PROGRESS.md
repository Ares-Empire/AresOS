# 39: Logos in their icon's main colours: progress

Step 1 is done (builder: a Claude agent on Fable 5.2, 2026-11-14). Step 2 is left; it is listed at the end.

## Done in step 1

- **The "before" pictures,** by the old rules (converter 1): `screenshots/0076_logos-before-row-1.png` and
  `0077_logos-before-row-2.png`, ten drawn icons as logos, five a picture, from 32 blocks. Private: the real three
  in one row from 24 blocks (path under "The real three").
- **A client game test,** `LogoColoursClientGameTest`, last in the list: it builds the ten icons of
  `src/testShared/.../zone/LogoIcons.java` in a row on a grass field at noon and takes the two pictures. The unit
  tests use the same ten drawings. With `ARESOS_LOGO_LOOK=<folder>` it also builds `chrome.png`, `discord.png` and
  `lunar-client.png` from that folder and writes their picture to `<folder>/screenshots`, outside the repo.
- **The new rules** in `zone/GatePicture.java` (`CONVERTER = 2`) and the palette choice in `zone/GatePalette.java`.
- **Unit tests:** `GatePictureColoursTest` (new, 12 tests), `GatePaletteTest` and `GatePictureTest` (brought to the
  new rules).
- **The "after" pictures** of the same ten (`0076_logos-after-row-1.png`, `0077_logos-after-row-2.png`) and, private,
  of the real three.
- `mod/dev/build.sh` passes; pushed.

How package 36's private run fed the real icons to the fake helper (asked in the step's task): `TownPicturesClientGameTest`
reads the environment variable `ARESOS_TOWN_LOOK`, a folder outside the repo holding `chrome.png`, `discord.png` and
`lunar-client.png`. Its `entry(...)` then gives the fake helper's entries `browser`, `discord` and `lunar-client` that
file's path as their `icon` instead of the drawn one, takes only the arrival view and the view east, and writes them to
`<folder>/screenshots`. This package's test does the same with its own variable and builds the three logos directly,
side by side, so they can be compared at one glance.

## The rules as built

Steps 1 to 3, 5 and 6 of HUB.md 3.6 are as they were (cut at 12%, the plate test with its numbers, a cell solid from
half covered, tidy, door), with one change in the plate step: the square around the figure is centred on the figure to
the half pixel of the 96-pixel copy, where it was rounded to a whole pixel. A figure that is the same left and right
(a face with two eyes) now gives cells that are the same left and right.

Step 4, the colours, is new:

1. **Samples.** The square that becomes the picture is looked at as 8 x 8 samples a cell (96 x 96 for 12 cells), each
   the average of its area. On a plate every sample is laid on the plate's colour.
2. **Main colours.** The samples' colours are counted in steps of 8 per channel and taken from the most common down
   (equally common ones in the order of their colour value, so the same icon always gives the same result). A colour
   within **0.10** (plain Oklab distance) of an earlier group belongs to it; any other starts a group. Three rounds
   move each group to the average of its colours and each colour to its nearest group. Groups whose averages are
   within **0.07** of each other are merged, the nearest two first (two shades of one white). Then two kinds of
   group are dropped: one that covers under **1%** of the picture (about a cell and a half), and one that lies
   between two larger groups (at most **0.06** beside the straight line between them) and covers at most **half** of
   what the smaller of the two covers: that is the colour of a smoothed edge. What is left are the main colours:
   2 for Discord and Lunar Client, 5 for Chrome. **How many:** as many as the icon has, up to **6**. An icon with
   more is many-coloured or photo-like and keeps version 1's rule: each cell the block nearest to its own average.
3. **One block per main colour,** largest first: its nearest block. When an earlier main colour already has that
   block and the two colours are more than **0.15** apart, it takes its next nearest. Main colours with the same
   block count as one colour from here on.
4. **Which colour a cell gets.** Every sample belongs to its nearest main colour, so a sample on a smoothed edge
   takes one side. A cell takes the colour that covers most of it. Exception, **thin parts:** a part of one colour
   is thin where it is narrower than a cell (no 8 x 8 square of samples fits into it) and more than **3** samples
   away from any place where one fits (so the rim of a wide part is not thin). A cell that has a thin part of
   another colour over at least **10%** of it may show that colour. From the cell with the least of it up, a cell
   is dropped again while the cells of that colour around it stay connected without it, so a line lying across two
   rows of cells is shown in one row, one cell wide. At last a single cell goes that neither continues a line nor
   joins two parts of its colour (a speck, or the tip of a wide part). Of two thin colours in one cell the one that
   covers more wins.
5. **The palette, plain blocks first.** The 60 blocks stay in the table. Plain are the dyed 48 and three of the
   twelve: snow block, blue ice, smooth sandstone. The nearest block is found as before (Oklab, lightness counted
   half). If it is a patterned one, the plain block nearest to **that block's own colour** is built in its place,
   when it is within **0.06** of it:

   | Patterned block | Built in its place | Distance |
   |---|---|---|
   | red mushroom block | red wool | 0.050 |
   | emerald block | lime wool | 0.054 |
   | lapis block | blue concrete | 0.043 |
   | honeycomb block | yellow concrete | 0.046 |
   | polished diorite | white concrete | 0.029 |
   | iron block | white concrete | 0.015 |
   | smooth stone | white concrete | 0.011 |
   | prismarine bricks | stays (cyan wool is 0.068 away) | |
   | amethyst block | stays (purple wool is 0.080 away) | |

**What the rules give up:**
- A thin line is shown a whole cell wide, however thin it is, and a sharp corner of a thin line can be cut
  diagonally. A thin part shorter than two cells that sticks out of a wide part is not shown (a pointed tip, a
  single star).
- A small detail whose colour lies between two larger colours (a grey mark on a black and white icon) is taken for
  a smoothed edge and painted in the nearer of the two.
- A gradient becomes bands: the drawn coral-to-violet tile has four.
- A strong red is built in red wool, which is darker than the icon's red; a bright green in lime wool, which is
  yellower than the emerald block was. No plain block is nearer.

**First cost numbers** (scratch measurement on the laptop while another test ran; step 2 measures properly): the ten
drawn icons scaled to 128 pixels take 7 ms each on average (17 ms the slowest; version 1: 2.5 ms), scaled to 1024
pixels 25 ms (37 ms the slowest; version 1: 15 ms). Forty icons of 1024 pixels: about one second on the picture
thread.

## The real three, in words

The pictures are private: `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg39-real/screenshots/`
(`0078_real-three-before.png`, `0078_real-three-after.png`).

**Before** (the old rules, `0078_real-three-before.png`: the three side by side from 24 blocks, at noon):
- **Chrome:** round, red on top, green left, yellow right, a blue middle. The red is red mushroom block, with white
  spots all over it. The ring around the blue is a mix of grey framed blocks (polished diorite, smooth stone), a
  pinkish cell, two sand-coloured ones and two bricked sea-green ones: it reads grey and rough, not as a white ring.
- **Discord:** a dark blue front with a pale face. The face is edged in light blue (blue ice), with two violet
  amethyst cells at its upper corners and grey framed cells along its sides and between the eyes. Frayed.
- **Lunar Client:** a black front with a ring of four or five greys and a white-grey patch low in the middle. No
  line is one colour; the moon cannot be made out.

**After** (the new rules, `0078_real-three-after.png`: same spot, same light):
- **Chrome:** the same shape in five plain blocks: red wool, yellow wool, lime concrete, a middle of 4 x 4 light
  blue concrete, and around it a closed ring of snow block, one block wide. No spots, no grey. The red is darker
  than Chrome's red: red wool is the reddest plain block there is.
- **Discord:** two blocks, blue wool and white wool. The face has a clean outline with its two ears on top and
  its two legs below, and two eyes, each one cell wide and two tall, the same left and right. No fringe.
- **Lunar Client:** two blocks, black wool and snow block. A white arch, one block wide and whole from foot to
  foot; inside it the moon as a thick white crescent open to the upper right; under it one white bar where the
  icon has three thin water lines. The stars are gone (single specks are dropped). It is a clear white drawing on
  black now. Someone who knows the logo sees the moon in its house; whether it is recognisable without its sign is
  the owner's to judge from the picture.

The ten drawn icons, before and after (in the repo): the thin arch and ring were four greys and are now white wool
lines, one block wide and connected; the pale bubble lost its amethyst, blue ice and grey edge; the wheel's ring is
one block (white wool) where it was six; the heart is red wool without spots; the sun on its tile lost five edge
blocks; the gradient has four bands where it had seven blocks, two of them patterned. The tree and the magnifying
glass are unchanged. "Many colours" and "Photo" keep their cells' own colours, now in plain blocks (photo keeps a few
prismarine bricks).

## What I would still tune, and what step 2 needs

Not done, in the order I would look at it:
1. **Lunar Client's moon.** It is drawn by "what covers most of the cell", and at 12 cells its inner curve is two
   cells of black. Try whether the picture gets rounder with a little change of the thin-part numbers; I would not
   add a rule for this one icon.
2. **Chrome's red is dark.** The palette has no plain bright red. A brighter one needs a block that is not in the
   palette (I know none that is plain, full and inert) or the mushroom block back for strong reds, which the
   owner's remark about its spots rules out. For the owner to see in the picture.
3. **Bright greens share lime wool.** In "Many colours" four green patches of different hue are one band (before:
   lime wool and emerald block). Keeping the emerald block would mean a stand-in distance of 0.052 instead of 0.06,
   a hair above the mushroom block's 0.050: too fine a line to tune on without the owner.
4. **The limit of six main colours is close to real icons.** The drawn photo has 7. An icon with 6 or 7 changes
   rule when its picture changes a little. Look at a few more many-coloured drawn icons.
5. The wheel's ring is a cell thicker at its lower corners than at its upper ones (the ring's middle is not on a
   cell edge). Harmless at this size.
6. The row pictures show the edge of a sixth logo. Framing them better means taking "before" again from commit
   `84fc8801`; I would leave it.

What step 2 needs (the brief's list; none of it is started):
- Tune from the pictures (above). `CONVERTER` is 2 already; this branch is not merged anywhere, so tuning needs no
  3.
- The renewal test: a server game test through `TownKeeper` that a town logo recorded with converter 1 is drawn
  again with these rules; and the chat check of the brief's point 4: what a world with five and with forty logos
  says on its first visit (`TownLines`: one "The logo of ... was renewed." per logo, one summary line above its
  limit), that a frozen town draws nothing, and the sentence that hand-built gates are not redrawn.
- The cost, measured properly, at 128 and 1024 pixels (first numbers above).
- The repo "after" pictures on the final code, each looked at. The two here are step 1's state.
- `docs/design/HUB.md` 3.6 with the rules and numbers above. Section 2.3 also needs a look: it calls the twelve
  "full, plain blocks", names the red mushroom block as the answer to Chrome's red and says that averaging removes
  thin bits. `mod/README.md` if it describes the converter or the palette.
- The full report with a "try this" note; `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice on the final
  code; merge `origin/main`; push; `gh pr create`; delete this file.
- Do not change `LogoIcons`' drawings without saying so: the two "before" pictures show these ten.

## Decisions

- **JUDGMENT-CALL 1-1: seven of the twelve added blocks are no longer built.** Red mushroom, emerald, lapis,
  honeycomb, polished diorite, iron and smooth stone give way to a plain stand-in (table above); amethyst and
  prismarine bricks stay, because no plain block is near their colour. Snow block, blue ice and smooth sandstone
  count as plain: in the "before" pictures they read as one flat colour from the pad, the other nine show spots,
  frames or facets. Rejected: counting a patterned block as "farther away" from the wanted colour (a strong red
  then came out orange concrete, the fault HUB.md 2.3 added the mushroom block against); and a distance that
  forgives a duller block of the right hue (reds came out pink terracotta). Cost of changing later: the table's one
  number (0.06) and the list of plain blocks; logos are then drawn again by a new converter number.
- **JUDGMENT-CALL 1-2: a thin line gets a whole cell.** A line that covers a tenth of a cell is shown as that
  cell, one cell wide and connected, so Lunar Client's lines are lines. Rejected: the colour that covers most of the
  cell (lines vanish), and a fixed share such as a quarter (lines break where they lie across two cells, and get two
  cells wide where they do not).
- **JUDGMENT-CALL 1-3: an icon with more than six main colours keeps version 1's rule** (each cell its own
  average), as the brief allows ("keep the old result for that kind"). Of the drawn ten that is "Many colours" and
  "Photo". Rejected: forcing them into six colours, which merges hues the old rule kept apart.
- **JUDGMENT-CALL 1-4: the enlarged square is centred exactly** (the brief says the enlarging stays unless the
  pictures show a reason). The reason: Discord's two eyes came out different, one cell against an L of three,
  because the square sat half a copy pixel off centre.
- **JUDGMENT-CALL 1-5: a colour between two larger ones is an edge, not a detail** (see "What the rules give up").
  Without it Lunar Client kept a light grey as a third main colour and its lines were half snow, half white
  concrete.
- **JUDGMENT-CALL 1-6: `GatePicture.ofBlocks`,** a small public way to make a picture from given cells. The server
  game tests built red mushroom, amethyst and blue ice from a three-stripe icon; the converter no longer gives the
  mushroom block, and a gate drawn by version 1 may still hold it, so the fixture now gives its cells directly and
  the tests keep building and removing a mushroom block. Nothing in the mod calls it.
- **JUDGMENT-CALL 1-7: the "before" pictures were taken twice.** The first thin-lines drawing had its ring where
  the doorway is; no rule could have shown it whole. It was redrawn (an arch beside the door, a ring above it) and
  both pictures were taken again by the old rules before the rules changed (commits `a0fcf641`, `84fc8801`).

## What ran

| What | State | Result |
|---|---|---|
| `mod/dev/client-test.sh` with `ARESOS_LOGO_LOOK` (before, first take) | old rules, `a0fcf641` | exit 0, `BUILD SUCCESSFUL in 9m 31s`, "Client tests ended with exit code 0 after 9 min 32 s", 15 "client checks passed" lines, "39 pictures taken (before)" |
| the same (before, second take: the pictures in the repo) | old rules, the redrawn thin-lines icon, `84fc8801` | exit 0, `BUILD SUCCESSFUL in 9m 26s` (9 min 27 s), 15 lines, "39 pictures taken (before)". The new rules were copied into the worktree while this run's game was already running from its compiled classes; the pictures show the old rules (spots, greys) |
| `mod/dev/build.sh` | the new rules, `b754f614` | exit 0, `BUILD SUCCESSFUL in 1m 52s`: 218 unit tests passed, 6 skipped (the Windows ones), none failed; "All 94 required tests passed :)" for the server game tests |
| `mod/dev/client-test.sh` with `ARESOS_LOGO_LOOK` (after) | `b754f614` | exit 0, `BUILD SUCCESSFUL in 9m 21s` (9 min 22 s), 15 lines, "39 pictures taken (after)" |
| Scratch, outside the repo and outside Gradle | the converter's plain Java files, compiled with `javac` in the scratchpad | the rules were tried there on the thirteen icons as flat colour sheets, the three unit test classes were pre-checked (27 passed, with a stand-in for JUnit), and the first cost numbers were taken. Not evidence for the build; the rows above are |

All three client runs drew on the Intel GPU ("Headless rendering on nvidia does not work here"). After each one the
other packages' tracked pictures were put back and their renumbered untracked ones removed. Every picture of this
package was looked at: the four in the repo and the two private ones.

**Not verified:** one client run on the new rules, not two (step 2 runs two on the final code). No town with logos
recorded by converter 1 was opened with these rules; package 36's server tests for a changed converter passed in
`build.sh`. HUB.md still describes version 1.
