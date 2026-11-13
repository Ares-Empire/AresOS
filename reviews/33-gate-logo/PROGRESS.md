# 33 gate logo: builder handoff (delete in the last commit before the PR is ready)

Read `briefs/33-gate-logo.md` first. This file holds only what the code and the brief don't show.

## Coordinator's rules, 2026-11-13

- Work in steps. After each step: commit, update this file, push. After roughly 80 tool calls, or at a natural break, end the turn with one line on what is left; a fresh builder continues from here.
- The owner answered the height question: **12**. `SIZE` stays one number, and the tests for 10, 14 and 16 stay.
- Do not edit `mod/dev/`. Before finishing: `git fetch origin`; if PR #44 (package 29) is in `main`, merge `origin/main` and take main's `mod/dev/` on any conflict there.

## Done

- Step 0: read the brief, HUB.md 2.3, 3.1, 3.2, 3.6, 5, all of `zone/`, the explosion mixin and the five tests. No code written yet.

## Left, in order

1. **Measure block colours** (development-only; nothing but numbers enters the repo). The game's textures are in `~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar` under `assets/minecraft/textures/block/`. Measure the 12 new blocks and re-measure today's 48; note here how (plain sRGB mean per channel, or other) and where the 48 differ from `LogoPixels.PALETTE`. Check each of the 12 in 26.2: full cube, plain (`Block.class` or say which class), no gravity, not flammable, no random tick, no block entity.
2. **Picture rules** as pure functions with unit tests (`zone/GatePicture` or similar): cut, plate test, enlarge, scale, Oklab match with lightness halved, tidy, door. Size is a parameter; `SIZE = 12` and `DEPTH = 3` live in one place.
3. **Plan** as plain data (no player in it): blocks, niche, black back, posts, trigger zone, exit point, sign, two light blocks, doormat. Server game tests against the worked examples of HUB.md 3.2.
4. **Build, record, remove:** `AppZone` gets optional fields (placed `{pos, block}`, the sign's entity ID, a gate marker); old zones files must still load (test with a file written before this package).
5. **Commands:** `/aresos logo <app>` builds the gate (new default), `wall` and `floor` unchanged, `/aresos logo remove <app | here>`.
6. **Neighbour check** accepts the mod's palette blocks, the sign, light blocks and doormat; still refuses plants, circuits, fluids, special blocks.
7. **Client game tests** with screenshots under `reviews/33-gate-logo/screenshots/`, then the real-icon look (scratch only).
8. `mod/README.md`, `REPORT.md`, two full `client-test.sh` passes, PR.

## Things a fresh builder must know

- **Wall and floor must stay exactly as today.** `LogoPixels.convert`, `LogoPixels.nearest` (plain RGB) and the 48 numbers in `LogoPixels.PALETTE` feed them and a frozen layout test (`LogoPixelsTest`, `logos/compass-layout.txt`). The gate gets its own match (Oklab) and its own palette table (48 + 12); do not change the old numbers under the wall.
- **The sign:** every setter on `Display` and `Display.TextDisplay` is private in 26.2. Create it from NBT: `EntityType.create(EntityTypes.TEXT_DISPLAY, TagValueInput.create(ProblemReporter, registries, tag), level, EntitySpawnReason)` or `EntityType.loadEntityRecursive(...)`. `Display.hurtServer` is `final` and returns false, and a display has no hit box, so the sign cannot be hit in any mode; a test should still assert it.
- **Entity type constants** are in `EntityTypes` in 26.2 (`EntityTypes.TEXT_DISPLAY`), not `EntityType`.
- **Doormat colour:** `AppDefinition` has no categories today (they come with packages 30/34). Keep the four group concretes and the first-fit rule of HUB.md 2.2 in one place in `zone/`; the command can only know the three fixed starters (`browser` north, `terminal` and `notepad` south) and uses light grey for the rest.
- **No icon or a fully transparent icon:** HUB.md 2.3 says the gate is then a plain front in the group's colour. Today's wall refuses instead; the wall keeps doing so.
- **Shared single-line files:** `mod/src/gametest/resources/fabric.mod.json` lists test classes on one line and `mod/build.gradle` holds the screenshot folders as system properties. Packages 32 and 34 edit the same lines, so expect a one-line merge conflict; say so in the report. Server game tests can go into the existing `ZoneGameTests` / `ZoneSafetyGameTests` without touching the manifest.
- **`runClientGameTest` has a ten-minute timeout** and the suite takes about seven minutes here. Keep the new client test short (one world), and name the timeout in the report as a risk once 32 and 34 add theirs.
- **Real-icon look (not committed):** scratch folder `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg33/`. Environment variables reach the game through `client-test.sh` (Gradle passes its environment to the forked game), so an opt-in variable naming a folder of PNGs needs no `mod/dev/` change.
- **Tools:** Java is `~/.local/opt/jdk-25/bin`; `javap -p -cp ~/.gradle/caches/fabric-loom/26.2/minecraft-common.jar <class>` shows the 26.2 API (names are Mojang's own).

## Dead ends

None yet.
