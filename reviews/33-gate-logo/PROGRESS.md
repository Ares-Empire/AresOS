# 33 gate logo: builder handoff (delete in the last commit before the PR is ready)

Read `briefs/33-gate-logo.md` first. This file holds only what the code and the brief don't show.

## Coordinator's rules, 2026-11-13

- Work in steps. After each step: commit, update this file, push. After roughly 80 tool calls, or at a natural break, end the turn with one line on what is left; a fresh builder continues from here.
- The owner answered the height question: **12**. `SIZE` stays one number, and the tests for 10, 14 and 16 stay.
- Do not edit `mod/dev/`. Before finishing: `git fetch origin`; if PR #44 (package 29) is in `main`, merge `origin/main` and take main's `mod/dev/` on any conflict there.

## Done

- Palette: 60 blocks with measured colours, Oklab match (`GatePalette`, `GatePaletteTest`, development task `measureBlockColours`).
- Picture rules of HUB.md 3.6 (`GatePicture`, `GateNumbers`, `GatePictureTest`, sizes 10, 12, 14, 16).
- Plan (`GatePlan`), build, record and removal (`GateBuilder`, `AppZone.Gate`), commands (`ZoneCommands`: gate is the default, `wall`, `floor`, `logo remove <app | here>`), neighbour check (`Neighbors`), group colours (`GateGroup`).
- Server game tests (`GateGameTests`, 9 tests): the worked examples of HUB.md 3.2, every size and facing, the command's place in front of him, the palette blocks' properties, old zones files, build and removal, changed blocks survive, 15 refusals, grass, two gates side by side, the doormat rule. `mod/dev/build.sh` passes: 47 game tests, all unit tests (run twice, 2026-11-13).

## Left, in order

1. **Client game test** `GateLogoClientGameTest` with screenshots under `reviews/33-gate-logo/screenshots/` (system property `aresos.gateReviewDir` in `mod/build.gradle`, class in `fabric.mod.json`): three gates from made-up icons from 20 blocks at eye height, one from 10, one from the side, one from behind; walking past the front opens nothing; walking into the niche opens the app once and the return lands on the exit point; the commands (`logo <app>`, `logo remove <app>`, `logo remove here`, `zone remove` leaves a gate, `logo remove` on an old wall); a Live-mode break of a gate block is refused. Compare the screenshots with `reviews/hub-design-v1/gate.png`.
2. **The three real icons** (scratch only, never committed): Chrome, Discord, Lunar Client at 12, and 10, 14, 16 for comparison.
3. `mod/README.md`, `REPORT.md` (with the measured-colour differences of the 48, and the "try this" note), two full `client-test.sh` passes, merge `origin/main` if PR #44 is in, delete this file, PR.

## Things a fresh builder must know

- **Wall and floor must stay exactly as today.** `LogoPixels.convert`, `LogoPixels.nearest` (plain RGB) and the 48 numbers in `LogoPixels.PALETTE` feed them and a frozen layout test. The gate has its own match and table.
- **Never force or release chunks in a server game test.** The framework forces the chunks of each test structure and releases them when that test ends; `setChunkForced(…, false)` in one test took the chunks of four neighbouring tests away before they had started, and the run never ended (no timeout applies to a test that has not started; the log filled with progress lines). `GateGameTests.Site` holds its chunks with a ticket of its own instead. If a run prints the progress bar thousands of times a second, stop it and look for this.
- **The game-test server ticks as fast as it can** (about 70,000 ticks a second when idle), so a wait for anything from disk needs a large `maxTicks`.
- **Commands cannot run in server game tests:** `DesktopWorld.isHost` needs a singleplayer owner. They are tested in the client test.
- **The sign:** made from NBT because a display's setters are private; `Display.hurtServer` is final and returns false and it has no hit box.
- **Doormat colour:** `AppDefinition` has no categories yet; `GateGroup` holds the gate's own copy of the four group concretes and knows only the three starters.
- **Shared single-line files:** `mod/src/gametest/resources/fabric.mod.json` and the system properties in `mod/build.gradle`. Packages 32 and 34 edit the same lines; expect a one-line merge conflict and say so in the report.
- **`runClientGameTest` has a ten-minute timeout** and the suite takes about seven minutes here. Keep the new client test short (one world).
- **Real-icon look:** scratch folder `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg33/`. Environment variables reach the game through `client-test.sh`, so an opt-in variable naming a folder of PNGs needs no `mod/dev/` change.

## For the report (so far)

- JUDGMENT-CALL: `/aresos zone remove` leaves a gate's zone alone and points to `/aresos logo remove` (a gate's zone never goes without its blocks and sign).
- JUDGMENT-CALL: in the plate test a pixel counts from half opacity, not 12% (with 12% Lunar Client's glow counts as figure and the icon is not enlarged).
- JUDGMENT-CALL: the doormat is laid only when the eight floor blocks and the ring around them are one kind of natural ground (grass, dirt, stone…); any other floor may be his paving.
- JUDGMENT-CALL: a gate is refused when its place is not loaded with its entities (build and removal), instead of loading it.
- JUDGMENT-CALL: the neighbour check for a light block reaches four cells (ice melts at block light 11), for the logo two cells as today. The wall and floor now use the same check, which also accepts natural ground and the palette's own blocks.
- PLAN-GAP: grass under a gate turns to dirt after a while, as under any block. After a removal the place is dirt until grass grows back, and HUB.md 3.3 calls only "untouched grass block" buildable.
- PLAN-GAP: three of the twelve new blocks are not plain blocks (red mushroom block, amethyst block, blue ice); none falls, burns, ticks or changes, so all twelve stay.

## Dead ends

- Forcing the site's chunks in the server tests (see above).
