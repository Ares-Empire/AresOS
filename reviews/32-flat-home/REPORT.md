# 32: The flat home world: report

Brief: `briefs/32-flat-home.md`. Builders: two Claude agents (Fable 5.2) one after the other, on the owner's laptop
running AresOS, as the user `ares` (the first stopped at a usage limit). Nothing under `os/` or `mod/dev/` changed.

This file was committed by the orchestrator from the second builder's text, because the builders' file tool refuses to write report files.

## Try this

```
mod/dev/run-hub.sh
```

Click **AresOS** on the title screen. If an `AresHub` from before exists in the development client, click
**New AresOS world…** and **Keep old & continue** instead (the old world is kept under a dated name). The create
screen shows **Home: Flat**; click **Create**. You stand on the dark pad with the gold block under you and look north
along the road with the light blue line; INTERNET hangs over it. Turn around for GAMES (east, red), SYSTEM & TOOLS
(south, yellow) and WORK & MEDIA (west, purple). Try to break the gold block: it stays, with a line over the hotbar.
Press **G**, fly up and look down at the cross; in Build mode he can change every block; the names are the mod's
and change with the look (package 36). Leave and click
**AresOS** again: you are back on the pad, facing north, and what you changed is still as you left it.

## Done

**The world** (`world/FlatHome.java`).
- `dimensions()`: a normal world's three dimensions with the Overworld generator replaced by a flat one: bedrock at
  y -64, 123 stone, 3 dirt, grass at y 63, plains, an empty structure set, no features, no lakes. Seed 0.
- `HomeButton.createFlat` creates it through the game's own create flow (`createFreshLevel`), as `create` does for
  the Nether home: survival, normal difficulty, cheats off, save folder `AresHub`. Both now share one `createWorld`.
- `initialize()` runs once, after the provisioning claim is written: it refuses a manifest that is not the flat site
  and a world whose Overworld is not this flat generator; then the rules, difficulty normal, the clock at 6000, clear
  weather, the fixed things, the world spawn on (0, 64, 0) facing yaw 180 and pitch -8, the desktop marker, the home
  data and `hub.dat`.
- `applyRules()`: `NetherHome.applyRules` plus `advance_time` and `advance_weather` off. Both rule names exist in
  26.2 as the design guessed. Nothing sets a rule after creation.

**Home data and provisioning** (`world/NetherHome.java`; a Nether home behaves as before).
- The manifest `aresos-home.properties` keeps `version=1`. A flat home's has one more key, `home=flat`; a manifest
  without the key is a Nether home, and a Nether manifest is written exactly as before. An unknown value is refused.
- The flat home's data is the site (seed 0, floor (0, 63, 0), yaw 180) plus an exact home (Overworld,
  (0.5, 64, 0.5), yaw 180, pitch -8), in the same `data/aresos/nether_home.dat` and format. So arrival on every
  join, respawn, `/aresos home`, `home set` and `home info` use the code paths the Nether home already had.
- The decision a starting server takes (nothing, the missing-data message, refuse, provision) is now one function,
  `startPlan(directory, hasHomeData, newWorld)`, so the promises can be tested without a real save. `provision`
  reads the kind and calls `FlatHome.initialize` or the unchanged `initialize(server, site, placeholder)`.

**The hub** (new package `dev.aresos.hub`).
- `HubLayout`: the numbers of HUB.md 3.1, the look name `flat-1`, the home block, and the group table (letter, name,
  outward, right, yaw, concrete, text colour) as data, with one method for "outward a, sideways b, height h".
  Packages 33 and 36 read them here. It touches no registry, so a plain unit test loads it.
- `FlatHub.build`: the 5 x 5 pad with the gold block, the four avenues from outward 3 to 24, and the four names as
  text displays (scale 3, upright billboard, full brightness, seen from 160 blocks). Every block goes through one
  `place`, which paves only untouched grass with air above it and records `{pos, block}`; anything else is left and
  logged.
- `HubData`: `data/aresos/hub.dat` with `look`, `numbers`, `home` (dimension and block) and `fixed` (`blocks` as
  `{pos, block}` with the block ID as text, `names` as the four display IDs). It is only ever read with `get`, so a
  missing or unreadable file is never replaced by an empty one.

**Protection** (`zone/WalkInZones.java` 3 lines, `mixin/LogoExplosionMixin.java` 3 lines).
- In Live mode a recorded position whose block is still the recorded block cannot be broken by hand ("The home pad
  and roads are protected. Press G for Build mode.") or by an explosion.
- A block he changed leaves the record immediately and permanently, including when he puts the original material
  back. Successful block-kind changes at the server chunk remove the entry and dirty the saved data. An observed
  mismatch in `holds` also removes it. The saved shape stays `{pos, block}`.
- Text displays take no damage from anything in 26.2 (`Display.hurtServer` is final and returns false). In version 1
  the names belong to the mod and change with the look (package 36), including in Build mode. The name-survival
  test stays; block editing is unrestricted in Build mode.

**The create screen** (`client/HomeCreateScreen.java`): one button, "Home: Flat" or "Home: Nether", Flat first. The
seed label and box, the three seed buttons, the placeholder toggle and the Build-mode hint show only for Nether.

**Tests.**
- `src/test/.../hub/HubLayoutTest.java`: 6 unit tests, the layout against HUB.md 3.2 in world coordinates,
  including rows of the day-one table.
- `src/gametest/.../FlatHomeGameTests.java`: 7 server tests (rules; layers, biome, no structures or features; the
  fixed things and the record; nothing built where something stands; Live protects and Build does not; the
  provisioning rules; no mob in ten minutes, with a control that shows the same place does spawn mobs when the rule
  is on).
- `src/gametest/.../FlatHomeClientGameTest.java`: the real client, from the create screen to a restart and a save
  with missing home data.

**Documentation.** `mod/README.md` describes the flat home next to the Nether home; `README.md` says home is a flat
world with the Nether as a choice.

**Files outside `world/`, the hub package, the two home screens and the protection hooks:**
- `mod/build.gradle`: one line, `systemProperty 'aresos.hubReviewDir'`.
- `mod/src/gametest/resources/fabric.mod.json`: the two new test classes in the two lists.
- `test_environment/flat_home.json` and `flat_hub.json`: two new test batches.
- `NetherHomeClientGameTest`: one click on "Home: Flat" so it still creates a Nether home, and one check that a
  Nether home has no hub record. `HomeChoiceClientGameTest`: the same click twice, and the same check for a world
  marked with `/aresos desktop on`.

## Verified

All on the laptop, 2026-11-13, through the two scripts only.

- `mod/dev/build.sh` (unit tests and server game tests), seven runs by the second builder:
  1 and 2 passed back to back ("All 45 required tests passed", 6 unit tests), the second over the world the first
  left behind. 3 failed in `liveModeProtectsHubBlocksAndBuildModeDoesNot` ("An explosion removed a group name"):
  PLAN-GAP 5. 4 failed the same way on purpose, with the test pinned to the chunk alignment that causes it. 5 passed
  with the fix, 6 passed with the tuned names, 7 passed with the final code. Three passes in a row since the fix.
- The no-mob test: with mob spawning on, a mob appeared at the test's home after 83, 52, 44, 819 and 1179 ticks
  (slimes; once a creeper and a spider). Then, under the flat home's rules, 12000 ticks with a survival player at
  home in a marked world: no mob, every run.
- `mod/dev/client-test.sh` (13 client tests, headless on the RTX 4060): run 1 `BUILD SUCCESSFUL in 7m 7s`, before the
  names were tuned; run 2 `BUILD SUCCESSFUL in 7m 10s` on the final code. The flat home test takes 20 seconds and
  needed no change after it was written. Run 3, by the orchestrator on the final code (`d682fedc`): `BUILD SUCCESSFUL in 7m 25s`, all client tests passed; its pictures are the committed ones.
- Screenshots (taken in run 2 and again in run 3), all looked at: `reviews/32-flat-home/screenshots/0033_create-flat.png`,
  `0034_create-nether.png`, `0035_arrival.png` (flat grass to the horizon, the pad, the north road with its light
  blue line, INTERNET over it), `0036_east.png`, `0037_south.png`, `0038_west.png`, `0039_above-build.png` (the
  cross from above in Build mode), `0040_rejoin.png` (his diamond block still in the road after a restart),
  `0041_missing-home-data.png`.
- PR #44 (package 29) was still open, so `origin/main` was not merged in.

## Not verified

- With his shader pack (Iris): the tests run without shaders. Whether the names read well against a shader sky and
  whether the noon sun looks as HUB.md expects needs his eyes.
- In his own session through `mod/dev/run-hub.sh`: the tests drive the same title-screen buttons, but headless.
- Breaking blocks with the mouse and real TNT: the tests call the server's own break and explosion paths, which is
  where the protection sits.
- A real LAN guest. Server tests cover a creative non-owner with no identifiable host, and the client test covers
  the real host. Explosions now follow only the host's mode; an unknown host keeps protection.

## JUDGMENT-CALL

1. **Explosions spare the hub's blocks in Live mode and break them in Build mode.** The brief's acceptance asks for
   "protection in Live mode and none in Build mode". Logos keep today's rule (explosions never break them, in either
   mode). So TNT beside a road in Build mode breaks the road but not a logo. Rejected: making the hub explosion-proof
   in both modes like logos (contradicts the acceptance). Changing it later is one line in `HubData`; package 36
   moves both onto one function and can settle one rule.
2. **Settled by review fix 3:** only the singleplayer host's mode controls explosions. Guests are ignored, and an
   unidentifiable host means protection stays on. This replaces the original any-creative-player decision.
3. **Settled by review fix 2:** a changed block is removed from the saved list. Putting the same material back never
   restores ownership. This replaces the original comparison-only decision.
4. **The home kind is one extra key in the existing manifest** (`home=flat`, version still 1). Rejected: a version 2
   manifest or a second file; both would make "a Nether `AresHub` behaves exactly as before" harder to keep. An
   older mod reading a flat manifest would take it for a Nether manifest, but only a world it had just created is
   ever provisioned, so nothing can come of it.
5. **The mod builds only on untouched grass with air above.** In a new flat world that is every position, so he
   sees no difference; it is the brief's "leave a thing unbuilt rather than place a block where something stands"
   made literal, and each skipped position is logged.
6. **One toggle button for the choice**, in the style of the placeholder toggle, with the text written in the code
   like the screen's other labels. Rejected: two buttons or a new language key (the language file is shared with
   package 34).
7. **The names hang on a dark plate, and two of them are lighter than their concrete.** On the game's default plate
   (black at 25 %) against the noon sky the first run's pictures showed INTERNET at a contrast of about 1.4 to 1,
   GAMES and WORK & MEDIA about 1.9, SYSTEM & TOOLS 2.5. Changed: the plate is black at 75 %
   (`HubLayout.NAME_BACKGROUND`); the text of GAMES went from 0xB02E26 to 0xFF6257 and of WORK & MEDIA from 0x8932B8
   to 0xC774F2, lighter tints of the same hues, because the two dye colours stay near 2 to 1 even on the dark plate.
   Light blue, yellow, the concretes and the size (scale 3) are as HUB.md 3.2 says. He sees a dark label behind each
   word instead of a faint grey one. Rejected: leaving them as designed (INTERNET nearly vanishes in the sky), and
   white text on a plate in the group's colour (white on yellow cannot be read). Changing it later is three
   constants, but only for a new world: an existing hub keeps the names it was built with. HUB.md 3.2 still says "in
   the group's colour" and knows no plate.

## PLAN-GAP

1. **Brief point 7 against its own acceptance.** Point 7 says explosions are stopped "the way logos are protected
   today"; logos are protected in both modes. The acceptance says none in Build mode. See JUDGMENT-CALL 1.
2. **Misleading names** (the brief asks to say so, not to rename): the class `NetherHome`, its saved data
   `data/aresos/nether_home.dat` and the test helper `NetherHomeGameTests.assertRules` now also serve the flat home.
3. **Time is a clock in 26.2.** There is no `setDayTime`; noon is `clockManager().setTotalTicks(overworld clock,
   6000)` and is read with `getOverworldClockTime()`. HUB.md 2.1 only says "the time set to noon (6000)", which holds.
4. **The server test world can be kept between runs on this laptop**, so a test must not assume untouched ground at
   fixed coordinates. The hub tests now build relative to their own plot, which the test server places at new random
   coordinates every run. Worth a line in `AGENTS.md` for packages 33 to 37, which build big things in server tests.
5. **A chunk loaded in the same tick does not show its entities yet.** A text display added to the chunk that was
   loaded last exists but cannot be looked up by ID until the server has run the chunk's queued promotion (before the
   next tick). The game is unaffected; a server test that builds and looks up in one tick is. One run in three failed
   on it before the cause was found; the test is now pinned to that chunk alignment and runs the queued tasks.
   Package 36 will meet the same thing with signs.
6. **In a server test nobody is the host** (`isSingleplayerOwner` is false for every test player), and a marked world
   refuses a mode switch from a client that cannot acknowledge it. Host-only behaviour is therefore checked in the
   client test.

## Open questions

- Should explosions follow one rule for logos and for the pad and roads (JUDGMENT-CALL 1)? Package 36 is the place
  to settle it.
- Nothing is left in `.work/`; this package downloaded nothing.

## Review fixes 1

Follow-up brief: `briefs/32-review-fixes-1.md`; review: `reviews/32-flat-home/REVIEW-1.md`.
Builder: Codex, gpt-6.1-sol. No look, world preset, home coordinates, dependency, `mod/dev/`, or OS changes.

**Done, per finding**

1. **Damaged exact home:** `NetherHome` strips partial codec results before Minecraft's saved-data reader can accept
   them. A `home=flat` manifest requires the nested exact home; an absent one is exposed as unreadable data without
   dirtying or rewriting it. The existing warning, command refusal, and no-arrival paths apply. The client regression
   opens the save with the nested home missing, malformed, and partially decodable, checks saved position and respawn,
   rules, blocks, names and record, refuses `home set`, and compares file bytes after shutdown. The Nether client
   regression explicitly checks its legacy file has no nested home, still arrives at the anchor, and remains byte-identical.
2. **Permanent ownership:** `HubBlockChangeMixin` observes successful block-kind changes at `LevelChunk.setBlockState`.
   `HubData` removes the position from both its lookup and saved `{pos, block}` list immediately and marks it dirty.
   `holds` permanently drops observed mismatches too. Server regressions cover mined/replaced gold, an intervening
   replacement changed back, direct replacement, and a stale record whose mismatch is observed. Client regressions
   repeat the same-material gold and changed-back concrete checks after closing and reopening the save.
3. **Host-only explosions:** `HubData.protectsFromExplosions(GameType)` is the small policy, with a separate server
   test for every mode and an unknown host. Server selection uses `DesktopWorld.isHost`; a creative non-owner in
   the server test cannot disable protection. The client exercises actual explosions with the real host in Build
   and Live, checking destruction, record removal, protection, and name survival.
4. **Group-name exception:** the report now says: in Build mode he can change every block; the names are the mod's.
   Version 1 names change with the look in package 36. The name-survival assertions remain.
5. **Continuous mob observation:** `MobAdditions` counts `ServerEntityEvents.ENTITY_LOAD` throughout the quiet
   interval, including mobs that disappear before an assertion. Its own server test adds and removes a zombie in
   one tick. The no-mob test retains its spawning-positive control, asserts the cumulative counter every quiet tick,
   and restores every changed rule, including `SPAWN_MONSTERS` (restored last to refresh the cached spawning flag).

**Verified so far**

- `free -g` preceded every build/test attempt; only one heavy step ran at a time in this worktree.
- `mod/dev/build.sh`: six successful runs, printing `BUILD SUCCESSFUL in 50s`, `46s`, `48s`, `37s`, `42s`, and `38s`.
  The last two were consecutive on code commit `5ad95f74`, each printing `All 47 required tests passed :)`.
  JUnit XML records 68 tests, 6 platform skips, 0 failures and 0 errors (62 passed, including all 6 layout tests).
- In the last two builds the control saw slimes after 56 and 58 ticks; both printed
  `32 server no-mob check: 12000 ticks, 0 mob additions`.
- The first `mod/dev/client-test.sh` attempt included the optional real-home vanilla tick sprint. It printed
  `Timed out waiting for predicate`, `BUILD FAILED in 9m 2s`, and exit code 1 after 9 min 3 s. A thread dump showed
  the server waiting in Fabric's `ThreadingImpl.enterPhase` / `postRunTasks` test-tick barrier while the test waited
  for the sprint. Fabric still paces those server ticks; vanilla's sprint does not bypass its synchronization.
  The optional check was omitted under the follow-up brief's explicit eight-and-a-half-minute allowance. The full
  server interval, positive control, and ordinary actual-home mob assertions remain.

**Not verified / limits**

- A 12,000-tick interval in the actual flat home through the client harness: omitted for the measured reason above.
  The server interval uses the existing vanilla flat test world under the production rules; the actual production
  preset, initialized fixed things, noon and weather are checked separately in the client test.
- Manual mouse/TNT play, shaders, and a real LAN guest remain human checks. No real session window was opened.

**JUDGMENT-CALL:** none beyond the brief's explicit decisions and optional sprint allowance. Original calls 2 and 3
are superseded above; the other calls stand.

**PLAN-GAP:** the follow-up says the orchestrator recorded the group-name exception in HUB.md. This worktree's
section 2.5 still says "In Build mode he can change anything." The report follows the explicit follow-up decision;
the design-document synchronization stays with the orchestrator because these fixes are scoped to code, tests and report.

**Open questions:** no new implementation questions.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
