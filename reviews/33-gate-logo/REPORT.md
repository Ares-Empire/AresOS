# 33: The gate logo: report

Built by Claude Fable 5.2 agents in three sittings (a usage limit and the step rule cut the work); this file was put together by the orchestrator from the builders' handoff notes, because the builders' tool refused to create it.

## Try this

In an AresOS world, stand on open flat ground, look where the logo should stand and type `/aresos logo browser` (or any app ID; Tab lists them). A gate appears six blocks ahead, facing you, with the app's name above it. Walk along its front: nothing happens. Walk into the doorway: the app opens. Close the app: you stand on the snapped exit point in front of the door, looking at it. `/aresos logo remove here` (or `/aresos logo remove browser` from anywhere near) takes it down and puts the grass under the doormat back. Before removing, press G, swap one of its blocks for something of yours, press G again: that block stays.

## Done

- **`zone/GatePalette`:** the 60 blocks with colours measured from the game's own textures, and the nearest block in Oklab with lightness counted half. The wall keeps its own table and its RGB match.
- **`zone/GatePicture`, `zone/GateNumbers`:** HUB.md 3.6 as pure functions. `SIZE` (12), `DEPTH` (3) and every other number of the gate are in `GateNumbers`.
- **`zone/GatePlan`:** plain data from a picture, an origin block, a facing and names: every block, the niche (the trigger zone), the exit point, the sign, the two light blocks, the doormat, and the spaces that must be free. No player and no world in it. `originInFrontOf` turns "where he stands" into an origin for the command.
- **`zone/GateBuilder`:** builds a plan (all refusals before the first block), records what it placed, removes a gate block by block where the block is still the recorded one. The sign is a text display made from NBT. Two new zone entries in the same tick open nothing; touching a previously entered zone while entering one new zone can still open the new one.
- **`zone/AppZone`:** an optional `gate` field: every placed block as `{pos, block}`, the ground the doormat replaced, the grass under the whole footprint, and the sign's entity ID. Zones without it are walls, floors and hand-made zones, as before.
- **`zone/Neighbors`:** the neighbour check, moved out of `LogoBuilder` and shared by all three forms.
- **`zone/GateGroup`:** the gate's own copy of the four group concretes; it knows the three starter IDs, every other app gets light grey.
- **`zone/ZoneCommands`:** `/aresos logo <app>` builds the gate; `wall` and `floor` as before; `/aresos logo remove <app | here>`; `/aresos zone remove` leaves gates alone; `/aresos zone list` marks gates.
- **`mod/build.gradle`:** the development task `measureBlockColours` and the screenshot folder for the client test.
- **Tests:** `GatePaletteTest`, `GatePictureTest`, `GateGameTests`, `GateLogoClientGameTest`; two zones files written before this package in `mod/src/test/resources/zones/`.

**The palette, measured.** Each colour is the plain mean of the block's side texture per sRGB channel, rounded. Of the wall's 48 numbers, 16 are the same and 32 differ by one step in one or more channels (the old numbers look cut off instead of rounded); the largest difference is pink terracotta's red, `a0` then, `a2` measured. Too small to see, so the wall's table is left alone. All twelve new blocks are full blocks that do not fall, burn, tick, hold data or give a redstone signal in 26.2 (`GateGameTests.paletteBlocksAreFullAndStill` checks all 60). Nine are plain blocks. Three have a class of their own and stay: a red mushroom block hides the faces that touch another mushroom block, amethyst chimes when hit, blue ice is slippery to walk on. Mushroom neighbours are safe only at recorded mod-owned positions; external mushroom blocks now cause refusal (review fix 3).

## Verified

- `mod/dev/build.sh` passed five times, the last on the final code: all unit tests (`GatePaletteTest`, `GatePictureTest` among them) and 47 server game tests, nine of them `GateGameTests`: the worked examples of HUB.md 3.2, sizes 10, 12, 14 and 16 in all four facings, build, record and remove leaving the world as it was, a changed block surviving the removal, 15 refusals that change no block, and zones files written before this package.
- `mod/dev/client-test.sh` (headless, RTX 4060): two full runs with exit 0, 7 min 15 s and 7 min 34 s; the second is on the final code. A third pass on the final code was run by the orchestrator before the review (see the pull request). `GateLogoClientGameTest` takes about 27 s and is last in the list: four gates built by command and a refusal on an occupied place; walking past opens nothing; walking in opens the app once through the fake launcher and the return lands on the exit point; Live-mode protection; `zone remove` leaves gates; `logo remove here` and by name, also after a rejoin; a wall's blocks stay.
- Nine screenshots under `reviews/33-gate-logo/screenshots/` (0033 to 0041), all looked at against `reviews/hub-design-v1/gate.png`: shape, door, black niche back, doormat colours, the enlarged sun on its plate, the round pinwheel, the plain front, the mirrored back, the sign on its dark plate and the lit fronts at night are as designed.

## The three real icons at 12 blocks (looked at in scratch, never committed)

- **Chrome:** clearly Chrome: a round build, red on top, green left, yellow right, a blue disc with a light ring in the middle. The red is red mushroom block, whose cap texture has white spots; from 20 blocks the red reads as red with a few light dots.
- **Discord:** a dark blue (lapis) front with a big light face, two blue eyes and a light blue edge: recognisable by the face, as the design says.
- **Lunar Client:** a black front with a grey ring and a white crescent shape. The weakest of the three: readable as "the moon logo" if you know it. A few of its dark grey cells came out olive green (green terracotta).
- **10, 14, 16:** at 10 Chrome still reads, Discord's eyes run together and Lunar is a grey smudge. At 14 and 16 all three are clearer, Lunar most of all. 12 is the smallest size at which all three can be told apart from other apps; this agrees with HUB.md 2.3. The owner chose 12 on 2026-11-13 (board #207).

## JUDGMENT-CALL

1. `/aresos zone remove` leaves a gate's zone alone and points to `/aresos logo remove`. Rejected: removing the zone and leaving 420 unprotected blocks and a sign nothing can remove any more.
2. The plate test counts a pixel from half opacity, not from the 12% of the cut. With 12% Lunar Client's glow counts as figure and the icon is not enlarged, against HUB.md 2.3; with half, the design's 24 icons give exactly the four it names.
3. Corrected by review fix 4: all eight doormat floor blocks and their complete ring must be grass block or dirt. Stone and other floors get no doormat. Grass or dirt placed by the owner is indistinguishable from generated ground; removal restores the recorded block kind.
4. A place that is not loaded is refused, for building and for removing, instead of loading it. Package 36 must build where he is or retry when he comes near.
5. A light block's neighbours are checked four cells around (ice melts at block light 11), the logo's two cells as before.
6. The command's gate stands with its doorway's centre line on the block edge nearest to him; the exit point is the middle of the block he stood in, on that line.
7. `/aresos logo remove here` means anywhere between the gate and its exit point, not only inside the doorway.
8. The wall and floor forms use the shared neighbour check, accepting inert full blocks and plain ground. Reactive palette neighbours require recorded gate ownership, with a matching block ID; being a palette block alone does not establish ownership. Mycelium and nylium are refused because their decay is not recorded.
9. The sign's plate is three quarters black (`GateNumbers.SIGN_BACKGROUND`), as in the design's drawing, instead of the game's quarter-black default, on which the white name was hard to read against the sky. HUB.md 3.2 gives no number.

## PLAN-GAP

1. Resolved by review fix 5: the gate records grass under its complete footprint and restores it when it is dirt at removal. Other replacements stay. HUB.md 3.3 can retain its untouched-grass rule.
2. Three of the twelve new blocks are not "plain" blocks in the game's sense (red mushroom block, amethyst block, blue ice). Mushroom neighbour changes matter: review fix 3 refuses external mushroom blocks. Amethyst sound and blue ice rendering/slipperiness do not change neighbouring states.
3. Categories are not in `AppDefinition`, so only the three starters get a group colour. The plan takes the doormat block as text, so package 36 can pass the right one.
4. From behind, nearer than about 50 blocks, the gate's own top edge hides the lower part of the sign: it floats over the front layer, 2.5 blocks from the back. Over the middle layer it would show sooner.
5. Shared one-line files: one class name in `mod/src/gametest/resources/fabric.mod.json` and one line in `mod/build.gradle`. Packages 32 and 34 touch the same lines; expect a small merge conflict, and keep this test last (screenshot numbers).
6. The client suite's ten-minute limit: this package adds about half a minute to a suite that takes a little over seven minutes here.
7. Server game tests must release only tickets they own, never the framework's or another test's tickets. These tests use and release their own DRAGON tickets.
8. Near-grey colours can pick a dull coloured block: Lunar Client gets a few olive cells at 12, because with lightness counted half a dark grey with almost no colour can land on a dull green block. Proposal, not built: when a cell's colour has almost no chroma, match it among the neutral blocks only.
9. The red mushroom block has white spots, so Chrome's red is dotted from close up.

## Not verified

- A gate in a world with weather, mobs and a day cycle over a long time.
- The doormat colours for apps other than the three starters.

## Open questions

- Resolved: new gates record their grass floor and conditionally restore it on removal. Gates built before this fix have no grass record.
- The sign's second line (the short name in gold) is built and has a field in the plan; it stays empty until package 35.


## Review fixes 1

Built by Codex, gpt-6.1-sol, for `briefs/33-review-fixes-1.md` on the same branch and PR #49. The numbered fixes were committed separately with a model trailer. No converter, palette colour or presentation rule was tuned.

### Done, by finding

1. **Removal safety:** compute the actual mutation set first, then use the shared `Neighbors.check` preflight before any block, entity or record is changed. Dependent blocks, hanging entities (including item frames, paintings and leash knots) and entities standing on a changed block cause refusal. The error names the first obstacle and its coordinates; the entire gate record and sign remain. Regressions attach a torch, replace a supported pixel with sand, and attach an item frame, and compare snapshots and saved records after each refusal. Stable edited glass remains accepted and preserved.
2. **Edited lights:** remove a recorded light only at level 15 and without waterlogging. A waterlogged light retains its water, and a level-7 light remains unchanged; both count as kept blocks in the regression. A kept light does not lose support when adjacent blocks are removed.
3. **Ownership:** the neighbour check resolves ownership from saved gate coordinates and matching block IDs, rather than accepting a palette kind everywhere. An external mushroom immediately behind a planned mushroom pixel refuses the build without changing its face state. The palette test inspects all sixty registered blocks' classes and inherited neighbour callbacks; in 26.2 only `red_mushroom_block:updateShape` overrides the checked callbacks. `javap -p` confirms amethyst adds projectile sound and blue ice adds rendering behaviour. Plain full ground remains accepted. There is no hub ledger in this package; package 36's independent records must supply its ownership when integrated.
4. **Doormat:** only grass block or dirt under all eight cells and the complete one-block ring, including the rear row, qualify. Tests cover grass, dirt, stone, paving and a changed rear row. Each replaced block's original kind is retained for removal.
5. **Grass floor:** the optional `gate.grass` field records grass under the full size-by-depth footprint. Removal restores only recorded positions currently containing dirt; other edits remain. Older records without this field load with an empty list. The regression round-trips the record, calls vanilla grass random ticks under the gate, requires dirt before removal, and compares the final world with the original snapshot while retaining a diamond-block edit. The main restoration regression now compares before and after directly, without repairs in between; explosion protection remains covered by a separate test with its original assertions. Existing side-by-side grass assertions now require grass, rather than also accepting dirt. Mycelium and nylium are refused because this package has no restoration record for their decay.
6. **Unloaded chunks:** before any block reads, validate the whole build/removal footprint, ground, neighbour halos, entity-query boxes and each light's four-cell radius. The deterministic chunk-border test loads only its own chunk, leaves the light/neighbor halo unloaded, and verifies both operations refuse without loading a chunk or changing the gate/record. It releases only its own ticket.
7. **Plate threshold:** unchanged at half opacity, as explicitly accepted in this follow-up. JUDGMENT-CALL 2 is retained. The orchestrator owns the HUB.md 3.6 wording correction; this branch's fixes do not edit the design document.
8. **Downgrade:** recorded as an accepted known limit below; no new ownership ledger was added for hand-built gates.
9. **Sign clearance:** the build checks air above the gate for the rotating text and background, before placing anything. The overhang regression requires refusal and an unchanged snapshot. The original chest-neighbour fixture moved behind the upper edge so it continues testing the neighbour guard outside the newly reserved sign space; its chest-specific assertion remains.
10. **Configurable size:** default-picture assertions, client gate spacing, the default top-corner check, the walk-past path and the side-view offset derive from `GateNumbers.SIZE`. Explicit size-12 worked examples remain.

**Trigger wording corrected:** two **new entries in the same tick** open nothing. Entering one new zone while still touching a previously entered zone may open the new one. Return uses the snapped exit point, which need not be the exact original player position.

### JUDGMENT-CALL

- The sign's clearance reserves its full configured width in both horizontal axes because it rotates. Its height conservatively allows one wrapped line per code point, avoiding server dependence on client fonts. This can refuse a close ceiling that would fit the actual rendered text. Rejected: assume all names fit one line or import client font classes into the server planner. Tightening the bound later changes only `GatePlan.signSpace()` and its tests; no saved format or sign appearance changes.
- The doormat and conditional dirt-to-grass restoration follow the explicit follow-up decisions. An intentional dirt replacement at a recorded grass position is indistinguishable from decay and receives the same specified restoration.

### Known limits

- Grass/dirt the owner laid himself cannot be distinguished from generated grass/dirt. A doormat can still be laid there when the complete ring qualifies; removal puts the recorded block kind back.
- After going back to an older AresOS that does not know gates, saving zones there, and upgrading again, the older writer has dropped the gate cleanup records. `logo remove` leaves the blocks (including hidden lights), and the sign/ground metadata are lost. The owner removes the remaining blocks in Build mode. Package 36's town logos will use their own file, which older mods never rewrite. Read compatibility of an old file does not establish downgrade/resave cleanup compatibility.

### Verified

- Before each heavy step, `free -g` showed at least 7 GiB available; scripts performed their own room checks. One heavy step ran at a time. Both client invocations waited for the shared lock as needed; neither used `--force`.
- `mod/dev/build.sh` on final code (`1b2cefc8`): exit 0, `All 52 required tests passed :)`, `BUILD SUCCESSFUL in 36s`; 75 unit tests passed with zero failures/errors in the JUnit XML.
- `mod/dev/build.sh` again on the same final code: exit 0, `All 52 required tests passed :)`, `BUILD SUCCESSFUL in 25s`; the unchanged unit-test task was up to date.
- `mod/dev/client-test.sh`, first full pass on final code: `33 client checks passed: four gates by command ... nine screenshots`, `BUILD SUCCESSFUL in 7m 20s`, `Client tests ended with exit code 0 after 7 min 22 s` on the NVIDIA GeForce RTX 4060 Laptop GPU. It checked gate building/refusal, niche-only entry, single launch/return, Live protection, removal by name/here/rejoin, and wall compatibility. All nine screenshots 0033–0041 were inspected against `reviews/hub-design-v1/gate.png`; the geometry and appearance remain as designed, including the previously documented rear sign occlusion.
- `mod/dev/client-test.sh`, second full pass on the same final code: again `33 client checks passed: four gates by command ... nine screenshots`, `BUILD SUCCESSFUL in 7m 18s`, `Client tests ended with exit code 0 after 7 min 20 s` on the RTX 4060. All nine final screenshots were inspected; only this package's changed captures 0033–0041 are committed.
- Initial development checks were not green: the first `mod/dev/build.sh` printed `random has protected access in Level` and `BUILD FAILED in 7s`; the test now uses `level.getRandom()`. The second printed `a chest two cells above the logo refused with: Area isn't clear ...` and `BUILD FAILED in 15s`; the newly reserved sign space correctly intercepted that fixture, so the chest was moved behind the upper edge to retain its neighbour-specific coverage. Its assertion was not weakened. Both final builds passed afterward.
- The server and client suites intentionally log injected inventory/launcher failure cases; their final summaries above passed. No production app was launched; the client suite uses its fake launcher.
- `git diff --check` passed. Screenshot cleanup used `git checkout -- reviews/`, restored only this package's captures, and removed untracked pictures outside `reviews/33-gate-logo/`. Only changed package-33 pictures are included.
- `javap -p -cp ~/.gradle/caches/fabric-loom/26.2/minecraft-common.jar ...` inspected the 26.2 hanging-entity, light, palette-special and glass APIs; the all-sixty callback check also ran in the passing server suite.
- Scripts use a single-use Gradle daemon and stop their systemd scope at exit. No direct `./gradlew` or separate `gradle --stop` was run, avoiding interference with other builders.
- Closing `.work/` inventory: no files over 500 MiB; only small screenshot backups, no large downloads or extracted images.

### Not verified

- Human play in the owner's real session; no window was opened there.
- Long-term weather/mob/day-cycle behaviour and real app icon recognition were not rechecked in this rules-only follow-up.
- The orchestrator's separate HUB.md correction and future package 36 ledger integration are outside this branch's permitted scope.

## Review fixes 2

Built by Codex, gpt-6.1-sol, for `briefs/33-review-fixes-2.md`; finding 11 is committed as `2f16bf76` on PR #49.

**Done:** removal has its own retained-block check. It inspects inherited survival, neighbour and tick callbacks rather than block IDs or full-cube geometry. In 26.2, the default callbacks do nothing; verified dry slab, stair, wall, fence and pane updates only retain the state or recompute connections. Unknown overrides still refuse with the block ID and coordinates. Placement retains its stricter check. The changed-block regression now preserves a top stone slab, horizontal quartz pillar and top stair with their exact states. Another regression checks wall/fence/pane connections after removal. Torch, sand and item-frame refusals still compare the whole world, sign and record; wet slabs and reactive waxed copper bulbs are covered too. A dry slab still refuses placement.

**Verified:** all commands below used the final source code unless explicitly identified as the initial compile failure.

- `mod/dev/build.sh`, twice: exit 0, `All 53 required tests passed :)`, `BUILD SUCCESSFUL in 35s` and `BUILD SUCCESSFUL in 25s`. JUnit XML reports 75 unit cases: 69 passed, six Windows-only skips, zero failures/errors; the second unit task was up to date.
- `mod/dev/client-test.sh --keep-screenshots .work/33-review-fixes-2/client-3-screenshots`: exit 0, `33 client checks passed: four gates by command ... nine screenshots`, `BUILD SUCCESSFUL in 7m 23s`, `Client tests ended with exit code 0 after 7 min 23 s` on the headless NVIDIA GeForce RTX 4060 Laptop GPU. All nine captures 0033–0041 were inspected and refreshed here: fronts, thickness, mirrored back, doorways, signs, spacing and night lighting remain as designed, including the known rear sign occlusion. Other packages' tracked pictures were restored with `git checkout -- reviews/`; untracked pictures outside this package were removed after both client runs.
- The initial `mod/dev/build.sh` failed at `compileGametestJava`: `COPPER_BULB` is a collection in 26.2, so `defaultBlockState()` was unavailable; `BUILD FAILED in 7s`. The fixture now resolves a waxed bulb through the registry, exercising its neighbour callback without weathering.
- The first full client run, using `--keep-screenshots .work/33-review-fixes-2/client-screenshots`, timed out before the gate test: `Timeout has been exceeded`, `BUILD FAILED in 10m 5s`, exit 1 after 10 min 7 s. It passed mounted Nether rejoin, then stopped producing progress during the existing 04b mounted Overworld rejoin. The next invocation exited 75: `Only 5.7 GB of memory is available and a run needs 6 GB`. After a blocking `sleep 180`, the unchanged full retry above passed all three 04b regressions and the remaining suite. The earlier timeout remains unexplained; the passing retry does not establish repeatable client-suite success.
- `free -g` preceded every heavy step; the scripts enforced memory checks and the shared client lock. No `--force`, direct Gradle invocation, test filtering, timeout change or daemon-stop command was used. `javap -p -c` inspected cached 26.2 `BlockBehaviour`, `Block`, shape/update helpers, pillar, fluid, gravity and reactive callbacks. `git diff --check` passed. The normal `git push` published the fix successfully. Closing `.work/` inventory: no files over 500 MiB; only small logs and screenshot backups.

**Not verified:** human play, the six Windows-only unit cases, and the cause of the intermittent 04b timeout. The full client suite has one passing run on this code, as requested by this brief, with the earlier failed run disclosed above.

**JUDGMENT-CALL:** none beyond the brief's explicit allowance for cosmetic connection changes. **PLAN-GAP / Open questions:** the existing 04b mounted Overworld rejoin can stall the full suite; diagnosis or changes to those tests are outside this fix's permitted paths.
- GitHub reports PR #49 open and unmerged, but `mergeable: false` against current `main`. Integration/merge-conflict resolution is not verified by these worktree checks and was not attempted in this scoped fix run.

### PLAN-GAP and open questions

- No new blocker. The conservative sign-clearance bound and the two accepted ownership/downgrade limits are documented above.
