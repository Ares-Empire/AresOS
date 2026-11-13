# 32 flat home: builder handoff

Working notes for the next builder. Delete this file in the last commit before the PR is ready.

Rules for whoever continues: read `AGENTS.md`, `briefs/32-flat-home.md` and `docs/design/HUB.md` (sections the brief lists) first. Work in steps; after each step commit, update this file and push. Build and test only with `mod/dev/build.sh` and `mod/dev/client-test.sh` (never `--force`, never `./gradlew`). Do not edit `mod/dev/`. Before finishing: `git fetch origin`; if PR #44 (package 29) has merged into `main`, merge `origin/main` and take main's `mod/dev/` on conflict. The owner answered the logo height: `SIZE` stays 12.

## Done

- Step 0 (this commit): everything the brief says to read has been read; the plan below is the result. **No code is written yet.**

## Left, in order

1. Check the real 26.2 names with `javap` (list under "Still to look up"). Write what you find into this file.
2. `hub/HubLayout.java` (numbers and group table, pure data) and its JUnit test.
3. `world/FlatHome.java` (generator settings, rules, provisioning of a flat home), `hub/HubData.java` (`hub.dat`), `hub/FlatHub.java` (builds the fixed things through one `place` function). Manifest gets the home kind. Provisioning decision pulled out of `NetherHome.register()` so it can be tested.
4. Protection hooks: `zone/WalkInZones.java` break hook and `mixin/LogoExplosionMixin.java`.
5. Client side: `HomeCreateScreen` choice, `HomeButton.createFlat`.
6. Server game tests (`FlatHomeGameTests`), including the ten-minute no-mob test.
7. Client game test (`FlatHomeClientGameTest`) with the screenshots; one added click in the two existing Nether client tests so they still create a Nether home.
8. `mod/dev/build.sh`, then `mod/dev/client-test.sh` twice. Look at every screenshot.
9. `mod/README.md`, `README.md` ("Home is the Nether" line), `reviews/32-flat-home/REPORT.md` with a "try this" note (`mod/dev/run-hub.sh`, click AresOS).
10. Fetch, merge main if #44 merged, delete this file, push, `gh pr create` against `main`. Do not merge.

## The plan (decided while reading; nothing here is tested yet)

**Files.** New package `dev.aresos.hub` so nothing collides with packages 33 (`zone/LogoBuilder.java`, `zone/LogoPixels.java`) and 34 (`item/`, `config/`, `shell/`, `catalogue/`, `client/AppsScreen.java`).

- `hub/HubLayout.java`: the constants of HUB.md 3.1 (`SIZE` 12, `DEPTH` 3, `FIRST` 4, `PITCH` 14, `ROW0` 20, `STEP` 14, door columns 5 and 6 / height 3 / depth 2, `EXIT` 6, `ROAD` 5), the look name `flat-1`, the home block (0, 64, 0), and `enum Group { N, E, S, W }` with name, outward vector, right vector, yaw, concrete (block ID as text) and text colour. One method for "outward a, sideways b" → `home + outward × a + right × b`. Keep it free of `Blocks` and registries so a plain JUnit test can load it. No place-to-blocks math for logos (package 36).
- `hub/HubData.java`: `SavedData` with ID `aresos:hub`, which lands in `data/aresos/hub.dat` (the same way `aresos:nether_home` lands in `data/aresos/nether_home.dat`). Shape: `look` ("flat-1"), `numbers` (name → int), `home` (dimension and block), `fixed` = `blocks` (list of `{pos, block}` with the block ID as text) and `names` (the four display UUIDs). Only ever read with `get` (may be null); never `computeIfAbsent`, or an unreadable file would be overwritten by an empty one.
- `hub/FlatHub.java`: builds pad, avenues and names. Every block goes through one `place(level, pos, block)` that sets it only where the untouched grass block still is, and records `{pos, block}`. A position that holds anything else is left alone and not recorded (brief, "If unsure").
- `world/FlatHome.java`: the flat generator settings, `applyRules` (calls `NetherHome.applyRules`, then the two extra rules), and `initialize(server, site)`.

**Home kind.** `aresos-home.properties` keeps `version=1` and gets one extra key `home=flat` for a flat home. A Nether manifest is written exactly as today (no new key), so absent means Nether. Any other value is an invalid manifest (refuse, as today). The home data keeps its format: a flat home is `Site(seed 0, x 0, y 63, z 0, yaw 180)` plus an exact `Home(OVERWORLD, (0.5, 64, 0.5), yaw 180, pitch -8)`. `Site.y` 63 passes `readManifest`'s 33..100 check. `NetherHome` needs one small package-private method to store that pair (its `TYPE` and constructor are private).

**Provisioning.** Same gates as the Nether home, same code path: `createNewWorld` refuses an existing `level.dat` or claim file, `SERVER_STARTING` requires uninitialised level data, the claim file is written with `CREATE_NEW` before the first block. Then, for `home=flat`: check the Overworld's generator really is our flat one (else refuse and build nothing), rules, difficulty normal, time 6000, clear weather, fixed things, world spawn on the home block, desktop marker on, home data, `hub.dat`, `saveEverything`, claim `complete`.
**Do not change `NetherHome.initialize(MinecraftServer, Site, boolean)`**: the test mixin `ProvisioningAuditMixin` injects into exactly that signature.
To test the rules of brief point 8 without a real save, pull the decision at the top of the `SERVER_STARTED` handler (nothing / missing-data message / refuse / provision) into a function of the directory and two flags, and test that plus `createNewWorld` with temp directories. End to end stays in the client test.

**Protection.**
- By hand: extend the `PlayerBlockBreakEvents.BEFORE` hook in `WalkInZones.register()`: in Live mode, a position recorded in `hub.dat` whose block is still the recorded block cannot be broken. Own message ("The home pad and roads are protected. Press G for Build mode.").
- A block he changed in Build mode is his: protection and any later removal compare the world's block with the record, so nothing has to be written when he edits. The record is never mutated in this package.
- Explosions: `LogoExplosionMixin` also drops recorded hub blocks from the affected list. **Open choice, record as JUDGMENT-CALL either way:** today's logos resist explosions in both modes ("explosions are never an edit gesture"); the brief's acceptance says "protection in Live mode and none in Build mode". Plan: follow the acceptance literally (hub blocks are explosion-proof unless the host is online in Build mode) and say in the report that logos and hub blocks then follow two rules until package 36 unifies them.
- Group names: text displays have no hitbox. Check `Display.hurtServer` with `javap`; if it does not already refuse all damage, set them invulnerable. Test with a player attack and an explosion.
- All of it only while the desktop marker is on (`LiveMode.isLive`), and only in the hub's dimension.

**Create screen.** A button "Home: Flat" / "Home: Nether", Flat first and default. Seed label, seed box, the three seed buttons, the placeholder toggle and the Build-mode hint are visible only for Nether. Literal strings like the existing ones (the lang file is shared with package 34). `HomeButton.createFlat` uses `createFreshLevel` like `create`, with `WorldOptions(0, false, false)` and a dimensions function that replaces the Overworld generator with a `FlatLevelSource`.

**Tests.**
- JUnit: `HubLayout` against HUB.md 3.2 with absolute coordinates (north avenue x -2..2, z -24..-3; names at blocks (0,73,-20), (20,73,0), (0,73,20), (-20,73,0)), and the day-one table rows to pin left/right (`N0L0` x -15..-4, `E0L0` z -15..-4, `S0L0` x 4..15, `W1R1` z -29..-18).
- Server game tests: rules; the build at a far-away origin in the test world (its surface is y -61, so use home y -60; the hub is 49 x 49 and must not land on other tests' plots); record contents; nothing placed where something stands; protection in Live and not in Build; the provisioning decision; `createNewWorld`.
- No-mob test: its own test environment JSON (own batch, so changing server rules cannot hit other tests). Apply the real `FlatHome.applyRules` to the server's rules, add a player at "home" so chunks load and count for spawning (Fabric `FakePlayer`, or check what `GameTestHelper` offers), run 12000 ticks, fail on any `Mob` that was not there at the start. Then a control: turn `SPAWN_MOBS` on and wait (bounded) until a mob appears, so an empty result cannot come from a world that could never spawn anything; the default flat test world has its surface below y 40, so slimes come within seconds. Restore the rules, discard the control's mobs, remove the player. The vanilla test server already has mob spawning off, which is why the control is needed.
- Client test, after `HomeChoiceClientGameTest` in the list: reach the create screen through "New AresOS world…" when an `AresHub` exists (else through "AresOS"), screenshots with Flat and with Nether chosen, create, then check the real world: Overworld, (0.5, 64, 0.5), yaw 180, pitch -8, Live, seed 0, cheats off, normal, rules, time 6000, clear, layers at a spot away from the hub, plains, no structures, world spawn, the fixed things at absolute coordinates, `hub.dat` on disk, four displays by UUID, no mob. Screenshots: arrival, east, south, west, from above in Build mode. Then edit a pad block in Build mode and change a rule, reopen: edit and rule kept, still four displays, time still 6000. Then delete `nether_home.dat`, reopen: unchanged, with the message.
- `NetherHomeClientGameTest` and `HomeChoiceClientGameTest` get one click on the home choice so they still create a Nether home. That is not a weakened test.

**Shared files I expect to touch by a line or two (name them in the report):** `mod/build.gradle` (one `systemProperty 'aresos.hubReviewDir'`, placed between the `homeReviewDir` and `seedReviewDir` lines so it merges next to what 33 and 34 append; the 10-minute `timeout` only if the suite no longer fits), `mod/src/gametest/resources/fabric.mod.json` (two test classes; a one-line list, so expect a merge conflict with 33/34), a new test environment JSON, `zone/WalkInZones.java`, `mixin/LogoExplosionMixin.java`, the two Nether client tests.

## Still to look up (26.2 is not obfuscated; no sources jar on the laptop)

Jars: `~/.gradle/caches/fabric-loom/minecraftMaven/net/minecraft/minecraft-common-deobf/26.2/minecraft-common-deobf-26.2.jar` and `minecraft-clientonly-deobf`. `~/.local/opt/jdk-25/bin/javap -p -cp <jar> <class>` shows signatures (`-c` for bytecode). Maven Central is reachable if a decompiler jar is wanted in the scratchpad; never commit decompiled code.

- `GameRules`: the real names of the day-cycle and weather-cycle rules (the design guesses `ADVANCE_TIME`, `ADVANCE_WEATHER`).
- How to set the day time to 6000 and clear weather on a `ServerLevel` in 26.2.
- `FlatLevelGeneratorSettings` / `FlatLayerInfo` / `FlatLevelSource` constructors; `WorldDimensions.replaceOverworldGenerator`; that `FlatLevelSource.spawnOriginalMobs` does nothing; that an empty structure override plus `generateStructures=false` gives no structures.
- Setting the world spawn (`setRespawnData` or its 26.2 name).
- `Display.TextDisplay`: text, billboard (vertical), brightness (full), view range (160 blocks is 2.5), scale 3 through the transformation, text colour; `hurtServer`.
- Whether spawn chunks stay loaded in 26.2 and whether `addFreshEntity` into a chunk loaded only by `setBlock` keeps the entity (the client test must find all four displays after a reopen).
- `GameTestHelper`: mock player, cleanup hook; the test environment JSON types.
- How fast the test server runs 12000 ticks (expected well under a minute; measure with `build.sh`).

## Things the code does not show

- `clickScreenButton("text")` in the client tests matches a button's literal text as well as a translation key (the existing tests click "50" and "Placeholder hub: OFF").
- The client tests share `build/run/clientGameTest/saves/AresHub`; a test must move an existing one aside or archive it through the UI, never delete it.
- `client-test.sh` takes about seven minutes today and Gradle stops it at ten.
