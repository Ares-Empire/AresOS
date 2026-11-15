# 39: Logos in their icon's main colours: report

Built in two steps by two Claude agents on Fable 5.2 (2026-11-14). This file holds the full report; a Claude builder
cannot create `REPORT.md`, so the orchestrator renames it.

The owner compared his three real logos before and after step 1 and chose the new rules ("Yes, after is better",
2026-11-14). Step 2 tuned them and did not go back.

## What he sees

A logo is built from its icon's few main colours, one kind of block for each, plain blocks first.
- **Chrome:** red, yellow and green in plain wool and concrete, a blue middle, and around it a closed white ring one
  block wide. No white spots on the red, no grey ring.
- **Discord:** two blocks, blue and white. The face has a clean outline and two equal eyes. No fringe.
- **Lunar Client:** two blocks, black and white: the house as a white outline one block wide, and in it the moon as
  a crescent. It was four or five greys.
- In a world that already has a town, every logo is drawn again where it stands on the first visit, and the chat says
  so: one line a logo up to five ("The logo of Chrome was renewed."), one line for all with more ("The town changed:
  40 logos renewed. /apps lists where your apps stand.").

**Try this:** on the AresOS laptop run `mod/dev/run-hub.sh` and open the AresOS flat home. From the pad Chrome and
Discord stand in front of you (north); turn right for Lunar Client (east). In a world whose town was built before
this package, the chat first says the three "was renewed" lines. Walk up to Chrome: its red is red wool, darker than
the icon's red (see judgment call 2-1 and the private picture that shows the other choice).

## The rules

`docs/design/HUB.md` 3.6 has them exactly, with the numbers; 2.3 and the corrections at its top say what changed.
In short (`zone/GatePicture.java`, `CONVERTER = 2`; `zone/GatePalette.java`):

Steps 1 to 3, 5 and 6 of 3.6 are as they were (cut at 12%, the plate test, a cell solid from half covered, tidy,
door), with one change: the square around an enlarged figure is centred on the figure to the half pixel.

Step 4, the colours, is new:
1. **Samples.** 8 x 8 samples a cell (96 x 96), each the average of its area; on a plate laid on the plate's colour.
2. **Main colours.** Colours in steps of 8 per channel, most common first; one within **0.10** (plain Oklab) of an
   earlier group joins it; three rounds of averaging; groups within **0.07** merge; dropped are groups under **1%**
   of the picture and groups between two larger ones (at most **0.06** off the line between them, at most **half**
   of the smaller one's share: a smoothed edge). 2 for Discord and Lunar Client, 5 for Chrome.
3. **Up to 6 main colours: one block each,** largest first, its nearest block; a second colour more than **0.15**
   away never shares a block. A sample belongs to its nearest main colour; a cell takes the colour that covers most
   of it.
4. **Thin parts.** Thin is what is narrower than a cell and more than **3** samples from a wide part. A thin part
   under a cell wide and high is a speck and is left out (step 2). A cell with a thin part of another colour over
   **10%** of it may show it; cells are dropped again while the line stays connected, so a line is one cell wide;
   a single cell that neither continues a line nor joins two parts goes.
5. **More than 6 main colours** (a photo, many hues): each cell keeps a colour of its own, the block nearest to the
   average of the main colour that covers most of it (step 2; before, the average of the whole cell).
6. **Plain blocks first.** Nearest block as before (Oklab, lightness counted half). Where a patterned block is the
   nearest, the plain block nearest to that block's colour is built when it is within **0.06**: red wool for red
   mushroom block (0.050), lime wool for emerald (0.054), blue concrete for lapis (0.043), yellow concrete for
   honeycomb (0.046), white concrete for polished diorite (0.029), iron (0.015) and smooth stone (0.011).
   Prismarine bricks and amethyst stay: no plain block is near them.

**What the rules give up:** a thin line is a whole cell wide however thin it is; a sharp corner of a thin line can be
cut diagonally; a small detail whose colour lies between two larger colours is taken for a smoothed edge; a gradient
becomes bands (the drawn coral-to-violet tile has four); a row of dots each under a cell wide is not shown; a strong
red is red wool, darker than the icon's red; a bright green is lime wool, yellower than the emerald block.

## What step 2 tuned, and why

Looked at: the private picture of the real three, the two repo rows, and scratch sheets of 21 icons (the real three,
the ten drawn ones and eight more drawn for this: five, six, seven and eight flat colours, four greens, a green
disc, a crescent, a line with a star) rendered with the game's own textures at the pad's scale. Tuned only what
those showed to be wrong:

1. **Lunar Client's moon had a tick.** A star lay on the cell above the tip of the moon's right horn, and the two
   cells held each other up as a "line": a white post beside the moon. Now a thin part under a cell wide and high
   is a speck and is left out. The moon is a crescent; the house is unchanged.
2. **Flat icons with seven or eight colours had the old fringe.** Above six main colours each cell took the average
   of all that fell into it, so six flat stripes on a dark tile came out as twelve blocks, five of them between two
   stripes. Now the cell takes the average of the main colour that covers most of it: seven blocks. The drawn photo
   went from 12 blocks to 9 (no prismarine bricks any more); "Many colours" is unchanged.
3. **The cost fell a little** (each sample's main colour is found with the Oklab values worked out once).

Looked at and left as it is, each with its reason under "Judgment calls": Chrome's red (2-1), the limit of six
(2-3), bright greens (2-4), Lunar's left wall (2-5).

## The real three, in words

The pictures are private, in `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg39-real/screenshots/`:
`0078_real-three-before.png` (the old rules), `0085_real-three-after.png` (the final rules, same spot and light),
`town-arrival-after.png` and `town-east-after.png` (the town from the pad with the three, final rules),
`chrome-red-wool-or-mushroom.png` (Chrome twice, side by side: red mushroom block and red wool),
`reds-textures-close.png` (Chrome's red as red wool, redstone block, red mushroom block and red concrete powder) and
`greens-lime-wool-or-emerald.png`. Step 1's "after" is in `pkg39-real/step1/`.

**Before** (old rules): Chrome's red is red mushroom block with white spots all over; its ring is a mix of grey
framed blocks, a pinkish cell and two sea-green bricked ones. Discord's face is edged in light blue with two violet
cells and grey framed ones. Lunar Client is a ring of four or five greys with a pale patch; the moon cannot be made
out.

**After** (final rules):
- **Chrome:** five plain blocks: red wool, yellow wool, lime concrete, a middle of 4 x 4 light blue concrete and a
  closed ring of snow block, one block wide. The red is a deep red, darker than Chrome's.
- **Discord:** blue wool and white wool. Two ears, two legs, two eyes one cell wide and two tall, the same left and
  right.
- **Lunar Client:** black wool and snow block. The house: a flat roof top four cells wide, two sloping steps on each
  side, walls one block wide down to a white bar on each side of the door. In it the moon: a crescent four cells
  tall on the left that widens to five cells along the bottom, open to the upper right. No stars. It reads as a moon
  in a house. The left wall steps in by one cell at its top and bottom (it lies on a cell edge).
- **From the pad** (`town-arrival-after.png`): Chrome left and Discord right of the north road, both clear at once.
  East (`town-east-after.png`): Lunar Client; the game shades a logo that faces east or west darker than one facing
  north or south, so its white reads light grey there.

The ten drawn icons (in the repo, `0083_…` and `0084_…`, before and after): the thin arch and ring are white lines
one block wide; the pale bubble has no edge blocks; the wheel's ring is one block; the heart is red wool; the photo
is calmer than in step 1 (two blues of sky, a pale band, two greens, the lake); the rest as in step 1.

## The first visit, the frozen town, hand-built gates (the brief's point 4)

- **Checked through the keeper** (`TownGameTests`, in package 36's own town): five standing logos recorded with
  converter 1 are renewed where they stand in one pass and said one by one; six are said in one line ("The town
  changed: 6 logos renewed. /apps lists where your apps stand."); every record then holds converter 2 and its place;
  a second visit says nothing. Forty: `TownLinesTest` (one line, "40 logos renewed").
- **A frozen town draws nothing:** its logo recorded with converter 1 stays as it is, record and blocks, and the
  pass says nothing (the same test that checks the freeze). After `/aresos hub trust` the next pass renews it.
- **Hand-built gates are not redrawn.** A gate built with `/aresos logo` has no converter in its record
  (`zones.dat`), and nothing in the mod compares it. It keeps its blocks until he removes it and builds it again;
  then it is drawn by these rules.

## Cost

The converter runs in `GateBuilder.icon`, which the town calls through `PictureReader` on the "AresOS pictures"
thread, never on the server thread (package 36; unchanged).

Measured on the laptop with nothing else building (load 0.7), JDK 25, the converter's own source compiled outside
Gradle: 13 icons (the real three and the ten drawn ones), each scaled to the size, five warm-up runs, then the median
of nine; twice, with the same result.

| Icon size | Mean an icon | Slowest | Step 1's rules, same measurement | Forty icons |
|---|---|---|---|---|
| 128 pixels | 4.9 ms | 8 ms | 7.9 ms | 0.2 s |
| 256 pixels (what the helper gives for the real three) | 6.7 ms | 8 ms | 10.7 ms | 0.3 s |
| 1024 pixels | 41 ms | 48 ms | 46 ms | 1.7 s |

At 1024 pixels nearly all of the time is reading the million pixels four times (cut, plate test, cells, samples),
not the new rules.

## Pictures in the repo

`reviews/39-logo-colours/screenshots/`: `0083_logos-before-row-1.png`, `0084_logos-before-row-2.png` (the old rules,
taken in step 1) and `0083_logos-after-row-1.png`, `0084_logos-after-row-2.png` (the final rules). Package 37's
client test now runs before this one, so the numbers moved from 0076 and 0077; the two "before" files were renamed
to the new numbers so each pair sorts together (their content is step 1's). **Package 37's seven pictures are
committed anew** under their own numbers (0076 to 0082): the converter changes what they show. The envelope, the
globe and the speech bubble lose their grey, sea-green and violet edge blocks; the chat lines and the places in them
are the same. I looked at each beside its old one. The pictures of packages 33 to 36 were put back as they are and
still show converter 1's logos, as those packages were reviewed.

## What ran (step 2)

| What | State | Result |
|---|---|---|
| `mod/dev/build.sh` | `8283c37b`, main merged, before any change | exit 0, `BUILD SUCCESSFUL in 2m 5s`, "All 98 required tests passed :)", 220 unit tests passed, 6 skipped. The merge broke nothing |
| `mod/dev/client-test.sh` with `ARESOS_LOGO_LOOK` and `ARESOS_TOWN_LOOK` (tuning run) | the tuned rules, plus a temporary, never committed fourth private logo (Chrome with the mushroom block) | exit 0, `BUILD SUCCESSFUL in 8m 53s`, "Client tests ended with exit code 0 after 8 min 54 s", 15 "client checks passed" lines. Source of the private town views and the red comparison |
| `mod/dev/build.sh` | the tuned code (as committed in `6882cb24` to `ad652bd0`) | **exit 1**, `BUILD FAILED in 2m 7s`, "1 required tests failed": `town_game_tests_the_town_trusts_its_records_only_while_the_world_was_saved_with_them`, "The town's chunks are not loaded yet on tick 400002". That is the wait before the test's body: 400,000 ticks went by in 8 seconds before its chunks had loaded. See "Not verified" |
| `mod/dev/build.sh` again | the same code | exit 0, `BUILD SUCCESSFUL in 2m 20s`, "All 98 required tests passed :)", 223 unit tests passed, 6 skipped (the Windows ones), none failed |
| `mod/dev/client-test.sh` with `ARESOS_LOGO_LOOK`, first | the final code (`4d22cbd9`) | exit 0, `BUILD SUCCESSFUL in 9m 48s`, "Client tests ended with exit code 0 after 9 min 49 s", 16 "client checks passed" lines, "39 pictures taken (after)" |
| `mod/dev/client-test.sh` with `ARESOS_LOGO_LOOK`, second | the same | exit 0, `BUILD SUCCESSFUL in 9m 46s`, "Client tests ended with exit code 0 after 9 min 46 s", 16 lines. This package's three pictures (two in the repo, one private) have the same pixels as in the first run |
| Scratch, outside the repo and outside Gradle | the converter's source compiled with `javac` | the sheets the tuning was judged from, the survey of the game's block textures, the cost numbers. Not evidence for the build |

After the build passed, `origin/main` was merged once more (`4d22cbd9`): its one new commit changes `HANDOFF.md`
only, so the mod's files are those the build tested. Both final client runs ran on that commit's mod code. After each
client run the other packages' tracked pictures were put back and their renumbered copies removed. Every picture of
this package was looked at.

## Not verified

- **The failed build once.** Package 36b's seal test timed out waiting for its chunks in one of three builds, before
  its body ran; the next build of the same code passed. This package changes that test's body (one line that makes
  the frozen logo an older one, one more condition), not its wait. I did not look for the cause.
- No world saved by the older mod was opened in the game. The renewal is tested with records set to converter 1
  whose blocks converter 2 built; that an old logo's other blocks (a mushroom block) come down is package 36's
  tested path (a renewal takes down what the record holds).
- Forty logos renewed in a real world: not run. Six through the keeper, forty in the lines' unit test.
- The 24 icons package 33 tested with were not run again (they are not in the repo). HUB.md 2.3 now says its count
  of loose cells is version 1's.
- The cost was measured outside the game.
- The private town views come from the tuning run. Its converter is the final one; only the client test had the
  temporary logo.
- All client runs drew on the Intel GPU.

## Judgment calls

Step 1:
- **1-1: seven of the twelve added blocks are no longer built** (red mushroom, emerald, lapis, honeycomb, polished
  diorite, iron, smooth stone); a plain block stands in. Snow block, blue ice and smooth sandstone count as plain.
  Rejected: counting a patterned block as "farther away" (a strong red came out orange) and a distance that forgives
  a duller block (reds came out pink terracotta). Changing it later: one number and a list, and a new converter
  number.
- **1-2: a thin line gets a whole cell,** one cell wide and connected. Rejected: the colour that covers most of the
  cell (lines vanish) and a fixed share (lines break or double).
- **1-3: an icon with more than six main colours keeps a colour of its own in each cell** (see 2-2 and 2-3).
- **1-4: the enlarged square is centred exactly.** Discord's eyes came out different without it.
- **1-5: a colour between two larger ones is an edge, not a detail.** Without it Lunar Client kept a light grey as a
  third colour.
- **1-6: `GatePicture.ofBlocks`,** a public way to make a picture from given cells, for the game tests that still
  build and remove a mushroom block. Nothing in the mod calls it.
- **1-7: the "before" pictures were taken twice** (the first thin-lines drawing had its ring in the doorway).

Step 2:
- **2-1: Chrome's red stays red wool. This is the one thing asked for that I did not do.** Minecraft 26.2 has no
  plain block of a brighter red. I measured every block texture in the game's own jar near Chrome's red (`e0382c`):
  red mushroom block 0.053 away (plain Oklab), redstone block 0.115, red concrete powder 0.113, red wool 0.137, red
  concrete 0.180. The mushroom block is the only one clearly brighter, and its white spots show from the pad (the
  private picture `chrome-red-wool-or-mushroom.png` shows both from 22 blocks); the brief asks for "a plain red
  block, not a spotted one". The redstone block is as dark as the wool, has a frame on every block and powers
  redstone next to it. Red concrete powder falls. **For the owner, from that picture:** deep plain red (as built) or
  bright red with white dots. Choosing the mushroom block later costs an exception for that one block in
  `GatePalette`, a changed unit test and converter 3; the logos then renew by themselves.
- **2-2: a speck is no line, and a many-coloured icon's cell takes one side** (the two tunings above). Given up: a
  row of dots, each under a cell wide, was joined into a line before and is now left out.
- **2-3: the limit stays six.** Tried 8 and 12 on the drawn icons: "Many colours" loses hues (orange goes into red,
  pink into red, because neighbouring hues are one main colour), and the thin dark gaps between seven stripes become
  whole black rows. With 2-2 the two rules now differ less where an icon has six or seven colours, which was the
  worry.
- **2-4: bright greens stay lime wool.** With the emerald block kept (a stand-in distance of 0.052) a bright green
  is the right blue-green, and every block shows its frame: a grid over the logo
  (`greens-lime-wool-or-emerald.png`). Plain first, as for the red.
- **2-5: no rule for Lunar Client's left wall or the moon's inner curve.** The wall lies on a cell edge and steps by
  one cell; the inner curve is "what covers most of the cell". I tried centring the enlarged square past the icon's
  edge: it moved no cell in any of the 19 icons I had then, so it was taken back.
- **2-6: the cost is left as it is.** Reading the pixels into an array once would bring a 1024-pixel icon from 41 ms
  to about a third; at the 256 pixels the helper gives it would save a millisecond. Not worth changing working code
  for.
- **2-7: `CONVERTER` stays 2.** Step 1's rules were never merged, so no world holds a logo of theirs.
- **2-8: the "before" pictures were renamed** to the new numbers (see "Pictures in the repo").
- **2-9: two more drawn icons in `LogoIcons`** (a line with a star, seven stripes), for the unit tests only; `all()`
  and the ten of the pictures are unchanged.
- **2-10: README says the unit and server game tests run on GitHub,** not all tests: the `Mod` workflow runs
  `build`, which has no client game tests.
- **2-11: the renewal check extends package 36's own town test** instead of building a second town; forty logos are
  checked in the lines' unit test, six through the keeper.

## Files

- `mod/src/main/java/dev/aresos/zone/GatePicture.java`, `GatePalette.java`: the rules.
- `mod/src/test/java/dev/aresos/zone/GatePictureColoursTest.java` (14 tests), `GatePaletteTest.java`,
  `GatePictureTest.java`; `mod/src/test/java/dev/aresos/hub/TownLinesTest.java`.
- `mod/src/testShared/java/dev/aresos/zone/LogoIcons.java`: the drawn icons.
- `mod/src/gametest/java/dev/aresos/test/LogoColoursClientGameTest.java` (the pictures; `ARESOS_LOGO_LOOK` for the
  private look), `TownGameTests.java` (the first visit, the frozen town), `GateGameTests.java`.
- `mod/src/main/java/dev/aresos/hub/TownKeeper.java`: wording only (package 37's review 3).
- `docs/design/HUB.md` (2.3, 3.6, corrections), `mod/README.md`, `README.md`.
