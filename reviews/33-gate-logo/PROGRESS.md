# 33 gate logo: builder handoff (delete in the last commit before the PR is ready)

Read `briefs/33-gate-logo.md` first. This file holds only what the code and the brief don't show.

## Coordinator's rules, 2026-11-13

- Work in steps. After each step: commit, update this file, push. After roughly 80 tool calls, or at a natural break, end the turn with one line on what is left; a fresh builder continues from here.
- The owner answered the height question: **12**. `SIZE` stays one number, and the tests for 10, 14 and 16 stay.
- Do not edit `mod/dev/`. Before finishing: `git fetch origin`; if PR #44 (package 29) is in `main`, merge `origin/main` and take main's `mod/dev/` on any conflict there. (Still open at 18:00 on 2026-11-13.)

## Done

- Palette, picture rules, plan, build, record, removal, commands, neighbour check, group colours (all in `mod/src/main/java/dev/aresos/zone/`).
- Unit tests (`GatePaletteTest`, `GatePictureTest`) and server game tests (`GateGameTests`, 9 tests). `mod/dev/build.sh` passed four times on 2026-11-13: 47 game tests, all unit tests.
- Client game test `GateLogoClientGameTest` with nine screenshots under `reviews/33-gate-logo/screenshots/` (0033 to 0041). Two full `mod/dev/client-test.sh` runs, both exit 0: 7 min 15 s (before the sign's dark plate and before the test moved to the end of the list) and 7 min 34 s on the final code, with the real-icon look switched on. The gate test itself takes about 27 s. I looked at all nine pictures against `reviews/hub-design-v1/gate.png`: shape, door, black niche back, doormat colours, the enlarged sun on its plate, the round pinwheel, the plain front, the mirrored back, the sign on its dark plate and the lit fronts at night are as designed.
- `mod/dev/build.sh` passed five times, the last on the final code: 47 game tests, all unit tests.
- The three real icons, looked at in scratch (contact sheets `…/scratchpad/pkg33/look/sheet-12.png` and `sheet-sizes.png`; nothing committed). In words, for the report:
  - **Chrome at 12:** clearly Chrome: a round build, red on top, green left, yellow right, a blue disc with a light ring in the middle. The red is red mushroom block, whose cap texture has white spots; from 20 blocks the red reads as red with a few light dots.
  - **Discord at 12:** a dark blue (lapis) front with a big light face, two blue eyes and a light blue edge: recognisable by the face, as the design says.
  - **Lunar Client at 12:** a black front with a grey ring and a white crescent shape. The weakest of the three: readable as "the moon logo" if you know it. A few of its dark grey cells came out olive green (green terracotta): with lightness counted half, a dark grey with almost no colour can land on a dull green block.
  - **10, 14, 16:** at 10 Chrome still reads, Discord's eyes run together and Lunar is a grey smudge. At 14 and 16 all three are clearer, Lunar most of all (at 16 the moon is plain). 12 is the smallest size at which all three can be told apart from other apps; this agrees with HUB.md 2.3 and does not change my view of 12.
  - PLAN-GAP to add: near-grey colours can pick a dull coloured block (Lunar's olive cells). Proposal, not built: when a cell's colour has almost no chroma, match it among the neutral blocks only. And: the red mushroom block's white spots.
- `mod/README.md`: the gate, the doormat, `logo remove`.

## Left, in order

1. **One more full `mod/dev/client-test.sh` pass on the final code** (it must pass twice; one pass on the final code is done). After a run: from the repo root `git checkout -- reviews/` and `git clean -fdq -- reviews/04-nether-home reviews/07-real-apps reviews/08-walk-in-logos reviews/09-mode-inventories`; the gate's pictures should come out byte-identical or be committed again.
2. **`reviews/33-gate-logo/REPORT.md`:** the draft is at the end of this file; add the "Verified" section from "Done" above and the real-icon words. The Write tool refused to create a file named REPORT.md from a subagent ("return findings as text"); the coordinator has to create it or say how.
3. `git fetch origin`; merge `origin/main` if PR #44 is in (still open at 18:35 on 2026-11-13); delete this file; push; `gh pr create` against `main`.

## Things a fresh builder must know

- **Wall and floor must stay exactly as today.** `LogoPixels.convert`, `LogoPixels.nearest` (plain RGB) and the 48 numbers in `LogoPixels.PALETTE` feed them and a frozen layout test. The gate has its own match and table.
- **Never force or release chunks in a server game test.** The framework forces the chunks of each test structure and releases them when that test ends; `setChunkForced(…, false)` in one test took the chunks of four neighbouring tests away before they had started, and the run never ended (no timeout applies to a test that has not started; the log filled with progress lines). `GateGameTests.Site` holds its chunks with a ticket of its own instead. If a run prints the progress bar thousands of times a second, stop it and look for this.
- **The game-test server ticks as fast as it can** (about 70,000 ticks a second when idle), so a wait for anything from disk needs a large `maxTicks`.
- **Commands cannot run in server game tests:** `DesktopWorld.isHost` needs a singleplayer owner. They are tested in the client test.
- **Screenshot names start with a running number** over the whole client suite. A test added in the middle of the list renames every later package's pictures, so `GateLogoClientGameTest` is last in `fabric.mod.json`.
- **The sign:** made from NBT because a display's setters are private; `Display.hurtServer` is final and returns false and it has no hit box.
- **Doormat colour:** `AppDefinition` has no categories yet; `GateGroup` holds the gate's own copy of the four group concretes and knows only the three starters.
- **Real-icon look:** `ARESOS_GATE_LOOK=<folder>` with `<folder>/icons/<name>.png`; pictures go to `<folder>/screenshots/`. The three icons are in `…/scratchpad/pkg33/look/icons/` (Chrome from `/usr/share/icons/hicolor/256x256/apps/`, Discord's SVG rendered with `magick`, Lunar Client from `~/.local/share/icons/hicolor/512x512/apps/`).

## Dead ends

- Forcing the site's chunks in the server tests (see above).

## Draft of REPORT.md

### Try this

In an AresOS world, stand on open flat ground, look where the logo should stand and type `/aresos logo browser` (or any app ID; Tab lists them). A gate appears six blocks ahead, facing you, with the app's name above it. Walk along its front: nothing happens. Walk into the doorway: the app opens. Close the app: you stand where you built it, looking at the door. `/aresos logo remove here` (or `/aresos logo remove browser` from anywhere near) takes it down and puts the grass under the doormat back. Before removing, press G, swap one of its blocks for something of yours, press G again: that block stays.

### Done

- **`zone/GatePalette`:** the 60 blocks with colours measured from the game's own textures, and the nearest block in Oklab with lightness counted half. The wall keeps its own table and its RGB match.
- **`zone/GatePicture`, `zone/GateNumbers`:** HUB.md 3.6 as pure functions. `SIZE` (12), `DEPTH` (3) and every other number of the gate are in `GateNumbers`.
- **`zone/GatePlan`:** plain data from a picture, an origin block, a facing and names: every block, the niche (the trigger zone), the exit point, the sign, the two light blocks, the doormat, and the spaces that must be free. No player and no world in it. `originInFrontOf` turns "where he stands" into an origin for the command.
- **`zone/GateBuilder`:** builds a plan (all refusals before the first block), records what it placed, removes a gate block by block where the block is still the recorded one. The sign is a text display made from NBT.
- **`zone/AppZone`:** an optional `gate` field: every placed block as `{pos, block}`, the ground the doormat replaced, the sign's entity ID. Zones without it are walls, floors and hand-made zones, as before.
- **`zone/Neighbors`:** the neighbour check, moved out of `LogoBuilder` and shared by all three forms.
- **`zone/GateGroup`:** the gate's own copy of the four group concretes; it knows the three starter IDs, every other app gets light grey.
- **`zone/ZoneCommands`:** `/aresos logo <app>` builds the gate; `wall` and `floor` as before; `/aresos logo remove <app | here>`; `/aresos zone remove` leaves gates alone; `/aresos zone list` marks gates.
- **`mod/build.gradle`:** the development task `measureBlockColours` and the screenshot folder for the client test.
- **Tests:** `GatePaletteTest`, `GatePictureTest`, `GateGameTests`, `GateLogoClientGameTest`; two zones files written before this package in `mod/src/test/resources/zones/`.

**The palette, measured.** Each colour is the plain mean of the block's side texture per sRGB channel, rounded. Of the wall's 48 numbers, 16 are the same and 32 differ by one step in one or more channels (the old numbers look cut off instead of rounded); the largest difference is pink terracotta's red, `a0` then, `a2` measured. Too small to see, so the wall's table is left alone. All twelve new blocks are full blocks that do not fall, burn, tick, hold data or give a redstone signal in 26.2 (`GateGameTests.paletteBlocksAreFullAndStill` checks all 60). Nine are plain blocks. Three have a class of their own and stay: a red mushroom block hides the faces that touch another mushroom block, amethyst chimes when hit, blue ice is slippery to walk on.

### JUDGMENT-CALL

1. `/aresos zone remove` leaves a gate's zone alone and points to `/aresos logo remove`. Rejected: removing the zone and leaving 420 unprotected blocks and a sign nothing can remove any more.
2. The plate test counts a pixel from half opacity, not from the 12% of the cut. With 12% Lunar Client's glow counts as figure and the icon is not enlarged, against HUB.md 2.3; with half, the design's 24 icons give exactly the four it names.
3. The doormat is laid only on natural ground: all eight floor blocks and the ring around them must be one kind of grass, dirt, stone or the like. Any other floor may be his paving, and the gate is built without a doormat (the command says so).
4. A place that is not loaded is refused, for building and for removing, instead of loading it. Package 36 must build where he is or retry when he comes near.
5. A light block's neighbours are checked four cells around (ice melts at block light 11), the logo's two cells as before.
6. The command's gate stands with its doorway's centre line on the block edge nearest to him; the exit point is the middle of the block he stood in, on that line.
7. `/aresos logo remove here` means anywhere between the gate and its exit point, not only inside the doorway.
8. The wall and floor forms now use the shared neighbour check, which also accepts natural ground and the mod's own logo blocks next to a logo. Before, a wall next to a grass block was refused.
9. The sign's plate is three quarters black (`GateNumbers.SIGN_BACKGROUND`), as in the design's drawing, instead of the game's quarter-black default, on which the white name was hard to read against the sky. HUB.md 3.2 gives no number.

### PLAN-GAP

1. Grass under a gate turns to dirt after a while, as under any solid block. A removal puts back the ground under the doormat, not this. HUB.md 3.3 calls a place buildable when its floor is "the untouched grass block or a block the mod placed"; package 36 should accept dirt there, or the gate should record the floor it stands on.
2. Three of the twelve new blocks are not "plain" blocks in the game's sense (red mushroom block, amethyst block, blue ice); none does anything a logo would notice, so all twelve stay.
3. Categories are not in `AppDefinition`, so only the three starters get a group colour. The plan takes the doormat block as text, so package 36 can pass the right one.
4. From behind, nearer than about 50 blocks, the gate's own top edge hides the lower part of the sign: it floats over the front layer, 2.5 blocks from the back. Over the middle layer it would show sooner.
5. Shared one-line files: one class name in `mod/src/gametest/resources/fabric.mod.json` and one line in `mod/build.gradle`. Packages 32 and 34 touch the same lines; expect a small merge conflict, and keep this test last (screenshot numbers).
6. The client suite's ten-minute limit: this package adds about half a minute to a suite that takes a little over seven minutes here.
7. Server game tests must never release forced chunks (see above). Worth a line in `AGENTS.md`.

### Not verified

- A gate in a world with weather, mobs and a day cycle over a long time.
- The doormat colours for apps other than the three starters.

### Open questions

- Should a gate remember the floor it stands on, so a removal can put grass back?
- The sign's second line (the short name in gold) is built and has a field in the plan; it stays empty until package 35.
