# 36: The town builds itself, progress

Brief: `briefs/36-town.md`. Steps 1 to 4, one fresh builder per step. The last step deletes this file.

## Where it stands

**2026-11-14, the orchestrator (read this first; it replaces what the step-1 text below says about the build):**

- Step 1 compiles and its tests pass on GitHub: Mod run 43524445082 on `c346e617` (the laptop refused all evening
  because the owner's game ran). Nothing of "First thing for whoever continues" below is open any more.
- Package 35's branch (`pkg/35-slash-names` at `aeb82bec`: schema 4 with `names` and `absent`) and `origin/main`
  are merged in (`27874445`, `0797c409`). One conflict, `GateBuilder.planInFrontOf`: package 35's main short name
  on the sign, this package's group concrete. Mod run 43535095427 on `0797c409` passed (build, unit and server
  tests, jar reproduced).
- The brief's step 2 changed accordingly (schema 4, `absent` programs are not wanted, which three files of package
  35 to stay out of). Step 2 starts from here.

**2026-11-14, step 2a (Opus 5.5): points 1 to 3 of step 2 are done and green** (the saved fields, the town's record,
the one function). Points 4 and 5 (keeping in step, protection) are step 2b: read "Done in step 2a" and "What step 2b
calls" below, then "What is left, in order".


**Step 1 is written but not yet built** (Opus 5.5, 2026-11-13): places, groups and the logo's picture, as pure
functions with unit tests. The build could not run (the owner's game was open the whole time; see "Verified"), so
step 1 ends when `mod/dev/build.sh` passes. Nothing is built in a world yet. Commits on `pkg/36-town`:

- `36: one notion of a group`
- `36: places, their order and their gates`
- `36: who stands where`
- `36: the logo's picture through AppIcons`

Build: not run yet, see "Verified" below.

## Done in step 1

1. **One notion of a group** (`catalogue/AppGroup.java`). The enum that already sorted an app into its group (HUB.md
   2.2's first-fit rule, unchanged) now carries everything about a group: `title()`, `look()` (item), `outward()` and
   `right()` (its avenue, as `Direction`s), `yaw()`, `letter()` (N, E, S, W), `concrete()`, `colour()`, and
   `block(home, outward, sideways, height)` (HUB.md 3.2's "outward a, sideways b"). `AppGroup.ofLetter(char)` and
   `AppGroup.clockwise()` (N, E, S, W) were added. Nothing it had was renamed. `hub/HubLayout.Group` and
   `zone/GateGroup.java` are gone; `FlatHub` and the game tests use `AppGroup`. `/aresos logo` takes its doormat and
   plain front from `AppGroup.of(app)`, so every app has its group's colour (the light grey "unknown group" is gone).
   `HubLayout`'s gate numbers (`SIZE`, `DEPTH`, the door, `EXIT`) now come from `GateNumbers`: one place for them.
2. **Places** (`hub/Place.java`): record `Place(AppGroup group, int row, Side side, int k)`, `Side { L, R }`, rows 0
   to 63. `name()` / `toString()` give `N0L0`; `Place.parse(String)` gives `Optional<Place>` (one spelling only).
   `Place.inOrder(group)` lists a group's places nearest first: row, then `k`, then L before R. `front()` (a0),
   `sideways()` (column 0's b), `origin(home)`, `facing()` and `plan(picture, dimension, home, name, shortName)`,
   which is `GatePlan.of` with the group's concrete as the doormat. `GatePlan` itself is unchanged.
3. **Who stands where** (`hub/Assignment.java`): `Assignment.of(List<Assignment.App>, Predicate<Place> blocked)`,
   pure. See "Decisions" for its exact rules.
4. **The logo's picture through `AppIcons`**: `GateBuilder.picture(app, size)` reads `AppIcons.read(app)` (the
   owner's own path first, otherwise the helper's picture within its limits) and falls back to a plain front in the
   group's concrete. `GatePalette.name(id)` turns `minecraft:yellow_concrete` into the gate's `yellow_concrete`.

Tests (unit, `mod/src/test`):
- `hub/PlaceTest`: names both ways and the names that are refused; the order (HUB.md 3.3's list for north, 42
  places in rows 0 to 5, 4160 in all); the five day-one places and `W1R1` against HUB.md 3.2's table (box, niche,
  exit, yaw, pitch, sign, and on N0L0 the lights and doormat); "places never collide" for rows 0 to 5 of all four
  groups: no two gates share a block of their spaces, floor, doormat ring, walkway, lights or exit, none reaches the
  pad or a road paved to row 5, no name hangs into another gate, two names never come within turning reach of each
  other, and every exit has five clear blocks before the row in front.
- `hub/AssignmentTest`: day one (the design's table), pinned first, a new app (and a pinned newcomer that takes no
  saved place away), a removed app's place staying free and taken back, a place taken while its app was away, two
  apps with one saved place, a saved place of another group, blocked places skipped and named (each place asked
  once), a group with nothing free, forty apps with fourteen in one group (and one leaving, one joining).
- `zone/GatePictureSourceTest`: a drawn picture at a helper-style path becomes the logo; the owner's own path wins
  (also a BMP over 512 pixels, as before); a helper picture over the limits or not a PNG, a missing file, or none
  gives the plain front in the group's concrete.
- `catalogue/AppGroupTest`, `hub/HubLayoutTest`: the table reached from an app's group, letters, clockwise order.
- Game tests changed only where they named the old types (`FlatHomeGameTests`), and one client-test expectation:
  `GateLogoClientGameTest`'s "gate-tree" app (no categories) now gets a yellow doormat, not light grey. Client
  tests were not run in step 1.

## Verified

**Nothing yet: step 1 has not been compiled or run.** `mod/dev/build.sh` refused with exit 75 eighteen times over
about 45 minutes (2026-11-13 to 14), every time with "The owner's Minecraft (Lunar Client) is running". No `--force`,
no Gradle by hand.

**First thing for whoever continues (before step 2):** run `mod/dev/build.sh` and fix what it shows, in this order of
likelihood:
- compile errors in the new code (it was checked by reading only);
- `PlaceTest` calls `Bootstrap.bootStrap()` in plain JUnit; if that does not work outside the game, move the
  GatePlan-based tests (`dayOneAndW1R1...`, `placesNeverCollide...`) into a server game test next to
  `GateGameTests.planMatchesTheWorkedExamplesOfTheDesign` and keep the rest as unit tests;
- `AppGroup` now loads `net.minecraft.core.Direction`; its static initialiser needs no registries (checked with
  `javap`), so the unit tests that load `AppGroup` without bootstrap should still run;
- `FlatHomeGameTests` checks the group names in the order N, E, S, W; `AppGroup.clockwise()` relies on
  `Direction.Plane.HORIZONTAL` being in that order.

## Decisions step 1 took (not settled by the brief or HUB.md)

- **One enum, not two tables.** `HubLayout.Group`'s data moved into `AppGroup` instead of keeping a look-table keyed
  by `AppGroup`: two four-value enums kept in step is what the brief asked to remove. If a second look (the Nether)
  ever lays the groups out differently, the direction moves into that look; today it is one table.
- **`concrete()` is the full block ID** (`minecraft:light_blue_concrete`), the form the hub records and the registry
  uses. A gate names its blocks without the namespace (`GatePicture.at`), so the gate converts with
  `GatePalette.name`. Letter and yaw are derived from the avenue's direction, not stored a second time.
- **The pad iterates `AppGroup.clockwise()`** (N, E, S, W) rather than `AppGroup.values()`, so the group names are
  built and saved in the same order as before; `AppGroup`'s constant order was left alone (package 35 may rely on it).
- **Rows end at 63** (`Place.ROWS = 64`). The brief says "without end"; a bound keeps coordinates small and keeps the
  search finite when every place of a group is blocked. It is 4160 places a group, 900 blocks out.
- **Place names have one spelling:** upper case, no leading zeros, `k <= row`. Anything else parses as no place
  (step 2: treat a saved place that does not parse as no saved place).
- **Assignment rules**, in this order:
  1. A wanted app keeps its saved place if that place belongs to its group, no app before it in the list kept the
     same place, and it is not blocked. All of these are settled before anyone looks for a new place, so a
     newcomer (even a pinned one, listed first) never takes a saved place away.
  2. A saved place of another group is ignored: the app stands in its own group. (Package 37 writes `group` and
     `place` together, so this only matters when the categories changed.)
  3. Every other wanted app, in list order, takes the first place of its group that is neither taken nor blocked.
  4. An app that is not wanted holds no place: its place is free for others. Its saved place stays in `saved()`
     until another app stands there, then it is dropped, so a returning app takes its place back only "if the
     place is still free" (HUB.md 2.5). Two absent apps with the same place: the first keeps it.
  5. A wanted app with nowhere to go (every place of its group blocked) is in `unplaced()`, gets no logo, and keeps
     its saved place in `saved()`.
  6. `skipped()` lists, per app, the blocked places it passed, its own saved place first. Two apps that pass the
     same blocked place both list it; the chat can name each blocked place once.
  7. `blocked` is asked at most once a place and only about places no app has taken yet.
- **`Place.plan` refuses a picture whose size is not `HubLayout.SIZE`**: the places are laid out for that size.
- **`PlaceTest` bootstraps the game** (`SharedConstants.tryDetectVersion()`, `Bootstrap.bootStrap()`), because a
  `GatePlan` holds its exit as a `NetherHome.Home`, whose codec initialises `Level`. The other new tests need no
  bootstrap.
- **The owner's own icon path now has `AppIcons`' 3-second read limit** too (it was an unbounded `ImageIO.read`);
  the formats it accepts are the same.

## What step 2 calls

```java
AppGroup AppGroup.of(AppDefinition app)                   // the group by the rules; step 2 uses the saved `group` when there is one
String   group.concrete() / title() / int colour() / float yaw() / char letter()
Direction group.outward() / right()
BlockPos group.block(BlockPos home, int outward, int sideways, int height)
List<AppGroup> AppGroup.clockwise()                       // N, E, S, W
Optional<AppGroup> AppGroup.ofLetter(char)

record Place(AppGroup group, int row, Place.Side side, int k)
Optional<Place> Place.parse(String name)                  // "N0L0"; empty for anything else
String   place.name()
Stream<Place> Place.inOrder(AppGroup group)               // nearest first, rows 0..63
BlockPos place.origin(BlockPos home); Direction place.facing(); int place.front(); int place.sideways()
GatePlan place.plan(GatePicture picture, ResourceKey<Level> dimension, BlockPos home, String name, String shortName)

record Assignment.App(String id, AppGroup group, Place saved /* nullable */, boolean wanted)
Assignment Assignment.of(List<Assignment.App> apps /* pinned first, then file order */, Predicate<Place> blocked)
  Map<String, Place>       standing()   // wanted app -> where its logo stands, in list order
  Map<String, Place>       saved()      // every app's `place` after this run; missing = write no place
  Map<String, List<Place>> skipped()    // blocked places each app passed, for the chat
  List<String>             unplaced()   // wanted apps with no place: no logo, one chat line

GatePicture GateBuilder.picture(AppDefinition app, int size)   // AppIcons first, else the group's plain front
String      GatePalette.name(String blockId)                   // "minecraft:x" -> "x"
```

How step 2 should feed it (advice, not built):
- `wanted` = in My apps and installed by a **complete** list. Apps of My apps that are not installed go in with
  `wanted = false` and their saved place, so the "remembered until taken" rule works.
- `blocked(place)` = the place is loaded and `GateBuilder` would refuse there (HUB.md 3.3's three spaces, ground
  that is grass or the mod's). A place where a town logo stands is **not** blocked: its app keeps it, or, if that
  app moved or left, step 2 takes it down before building. An unloaded place is not blocked either: its build
  stays pending, and if it turns out refused once loaded, the next run moves the app on.
- Write `saved()` back into the apps file (and clear `place` for apps not in it).

## Done in step 2a

Commits on `pkg/36-town`, one per point, each built green:

- `d6b647dc` **A test that package 35's parser reads `place` and `group` and keeps them**, committed before any parser
  change, so on that commit it tests package 35's own parser: fixture `mod/src/test/resources/apps/schema-4-town.json`,
  `AppsConfigTest.aSchema4FileWithPlacesAndGroupsIsReadAndEveryEditKeepsThem`. GitHub run 43537089294 on `d6b647dc`
  passed (both checkouts: "All 85 required tests passed", that test PASSED).
- `ba903460` **Point 1, saved with the apps.** `AppDefinition` gains `place` and `group` (raw text, null for none;
  `withSpot`). `AppsConfig` reads both and `AppsConfig.spots(file, Map<id, Spot>)` writes exactly the given pair per
  listed app (null removes the field), editing the file in place like every other edit. `AresOs.saveSpots` keeps the
  list in memory in step (only these two fields, as `assignNames` does for names). `AppGroup.key()` / `ofKey(String)`;
  `AppGroup.of(app)` now returns the group he chose by hand when `group` names one, else the rules.
  **No new schema number:** package 35's parser ignores fields it does not know, and all of its edits (pins, My apps,
  merge, names) change the parsed JSON in place, so it keeps `place` and `group`. The only path that writes from records
  (`AppsConfig.save`) runs when there is no file yet (and in tests). So the brief's expectation "when it saves, the
  places are dropped" does not happen: a package-35 mod keeps them; nothing is given out again.
- `b9ac38ca` **Point 2, saved with the world.** `HubData.Logo(app, place, picture, converter, name, shortName, zone,
  gate)`, `gate` being package 33's `AppZone.Gate` (every block `{pos, block}`, the doormat's ground, the sign's ID, the
  grass under it). `hub.dat` gains `logos` (optional: a file of packages 32 to 35 loads with none). The record's block
  index covers the logos, so `holds`, `blockChanged`/forget and `protectsFrom` work for them as for the pad: a block he
  changes leaves its logo's record at once. A zone of `zones.dat` is the town's while a logo names its ID
  (`HubData.town(server, zone)`); `/aresos zone remove`, `zone list` (`| town`) and `/aresos logo remove <app>|here`
  leave such zones and their logos alone and say "The logo of X belongs to the town and stays: /aresos app remove <id>
  takes it down." `Neighbors` counts the hub's blocks and the town's signs as the mod's own. `GatePicture.CONVERTER`
  (1) and `GatePicture.hash()` (SHA-256 of the size and every cell's block).
- `b7ba13a7` **Point 3, one function.** `zone/Placing.set(level, pos, recorded, next[, flags])`: where the record holds
  nothing (`recorded == null`) it places only on untouched ground (air, or grass or dirt with air above); where it holds
  a block it changes it only while that block is still there (`Placing.still`: same block; a light only at level 15 and
  dry). Returns `Optional<Placing.Change(pos, block, before)>`, empty = not the mod's to change, nothing happened.
  `FlatHub.place` goes through it (still grass only, still `UPDATE_CLIENTS`). `GateBuilder` is split: `prepare` (every
  refusal, nothing changed; `GateBuilder.NotLoaded extends IOException` when not loaded), `place` (every block through
  `Placing`, undone through it if the world changed since `prepare`), `takeDown` (through `Placing`); `build` and
  `remove` for hand-built gates are these plus `zones.dat`, behaviour unchanged. `HubData.holds` uses `Placing.still`.
  `hub/Town.java`: `check`, `build`, `remove`, `plan` for the town's logos (below). Tests: `TownGameTests` (batch
  `aresos-test:town`, alone: builds a flat home 15000 blocks from its plot, holds its chunks with its own ticket, puts
  the server's previous hub record back): Discord at N0R0 built and checked block by block against the plan, the
  record, the sign, the zone (no gate, no blocks, `town` true; a zone of his false), the codec round trip, refusals
  that change nothing (same app twice, a taken place), a blocked place (his planks in N0L0, not `NotLoaded`), the
  ground rule (stone under N1L0's way in), a block he changes leaving the record, and the removal (world as before but
  his block, no sign, zone or record). `theOneFunctionChangesOnlyUntouchedGroundOrTheBlockItRecorded` (desktop batch,
  own plot) checks `Placing`'s rule cell by cell. Unit: `HubDataTest`, `AppGroupTest`, `AppsConfigTest`,
  `GatePictureTest` additions.

**Verified:** `mod/dev/build.sh` at `b9ac38ca`: exit 0, "All 85 required tests passed", unit 195 run, 6 skipped (the
Windows-only ones), 0 failed. At `b7ba13a7`, twice: exit 0, "All 87 required tests passed" (the town batch "1 tests",
desktop "39 tests"), `BUILD SUCCESSFUL in 1m 9s` and `in 43s`. Earlier tries refused with exit 75 (memory under 6 GB).
Packages 32 and 33's tests pass unchanged; no existing test was edited. Client tests not run (step 3).

## Decisions step 2a took (not settled by the brief)

- **`group` is saved as the group's key** (`internet`, `games`, `work_media`, `system_tools`), not the letter: a
  letter is the flat look's direction, a group he chose must mean the same in another look. Package 37 writes it with
  `AppsConfig.spots` / `AresOs.saveSpots`.
- **Lenient values, strict types:** `place` or `group` text that names nothing means none (the app stands by the
  rules), so a later mod's file is never refused for it; a value that is not text refuses the file, as every field does.
- **`AppGroup.of(app)` honours the saved group everywhere**: the town, a hand-built gate's doormat, the `/apps` line.
- **"Marked as the hub's" is the logo record naming the zone's ID**, not a field in `zones.dat`: one fact in one file,
  so an older mod rewriting either file cannot make them disagree. The town's zone in `zones.dat` has no gate and no
  `blocks`; its blocks are protected through `hub.dat`. A mod of packages 33 to 35 sees a plain zone: walking in works,
  its `logo remove` finds no logo there, it does not protect the town's blocks.
- **The picture's hash is of the cells as built**, not of the icon file: what stands is what is compared, a plain
  front (no icon) has a hash too, and an icon change that draws the same blocks rebuilds nothing.
- **The logo also records the name and short name on its sign** (not in the brief's list), so step 2b can tell a
  changed name without the sign's chunk loaded.
- **Untouched ground for the one function is air, or grass or dirt with air above**: package 33's doormat goes on dirt
  too and its tests stay unchanged. Callers may ask for less: the pad grass only, the town's floor grass or the hub's
  own (HUB.md 3.3, in `Town`).
- **`Town` refuses unless `hub.dat`'s look is `flat-1`**: places are laid out for those rules.
- **`Town.build` takes the picture as an argument** and reads no icon, so step 2b can read icons off the server
  thread (`AppIcons.read` may wait 3 seconds an app).

## What step 2b calls

```java
// The apps file (config)
String app.place() / app.group()                         // raw text or null; Place.parse(app.place()) for the place
AppGroup AppGroup.of(app)                                // the group he chose, else the rules: feed Assignment.App with it
void AresOs.saveSpots(Map<String, AppsConfig.Spot> spots) // record Spot(String place, String group); exact pair, null = none
List<AppDefinition> AppsConfig.spots(Path file, Map<String, AppsConfig.Spot> spots)

// The town (hub/Town.java); every call does it all or changes nothing
void         Town.check(MinecraftServer, AppDefinition, Place, GatePicture) throws IOException
             // returns: buildable now; throws GateBuilder.NotLoaded: not loaded (pending, not blocked);
             // any other IOException: blocked, its message names what is in the way
HubData.Logo Town.build(MinecraftServer, AppDefinition, Place, GatePicture) throws IOException   // same refusals
GateBuilder.Removal Town.remove(MinecraftServer, String appId) throws IOException
             // NotLoaded: pending; other IOException: something of his hangs on it, leave it standing
GatePlan     Town.plan(HubData, AppDefinition, Place, GatePicture)

// The record (hub/HubData.java)
HubData HubData.get(server)            // null: not a flat home; hub.look() is "flat-1" for this town
List<Logo> hub.logos(); Optional<Logo> hub.logo(appId); Optional<Logo> hub.logoOfZone(zoneId)
Optional<Logo> hub.logoAt(level, pos)  // the logo whose record holds this block (for explosions in Build mode)
boolean hub.holds(level, pos); static boolean HubData.town(server, zone); Set<UUID> hub.signs()
record Logo(String app, String place, String picture, int converter, String name, Optional<String> shortName,
            String zone, AppZone.Gate gate)

// Pictures (zone)
GatePicture GateBuilder.picture(app, HubLayout.SIZE)    // reads AppIcons: up to 3 s an app
String picture.hash(); int GatePicture.CONVERTER

// The one function, for roads in step 3 (zone/Placing.java)
Optional<Placing.Change> Placing.set(ServerLevel, BlockPos, String recorded /* null: none */, BlockState next[, int flags])
boolean Placing.still(BlockState, String recorded); BlockState Placing.state(String id); String Placing.id(BlockState)
```

Refresh (HUB.md 3.4.4) needs nothing new: compare `logo.picture()` with `picture.hash()`, `logo.converter()` with
`GatePicture.CONVERTER`, `logo.name()` / `logo.shortName()` with `app.name()` / `NameRules.mainName(app)`; then
`Town.remove` and `Town.build` in the same place (a sign-only rewrite is an optimisation, not needed).

## What is left, in order

**Step 2b** (points 4 and 5 of the brief's step 2):
1. Keeping in step (HUB.md 3.4): a runner on the server thread, triggered when the host enters the flat home, when a
   complete program list arrives (`AresOs.takeIn` / `MyAppsGame.listed`), and after `/aresos app add` and `remove`
   (without touching `item/AppCommands.java`, `names/OwnedNodes.java` or its mixin: hook where My apps changes, e.g.
   `AresOs.saveMine`, or `MyAppsGame`). Only when `HubData.get` is non-null with look `flat-1`, only on a complete list.
   Wanted = `mine && !absent`; feed every app of the file to `Assignment.of` (pinned first, then file order), with
   `AppGroup.of(app)` and `Place.parse(app.place())`; `blocked` = `Town.check` throws something other than `NotLoaded`.
   Take down logos whose app is not wanted or whose place changed, build the missing ones, refresh changed ones; write
   `saved()` back with `AresOs.saveSpots` (keep each app's `group`). `NotLoaded` work stays pending and is retried every
   few seconds while he is in the world and when he comes near; no forced chunks. One chat line per change, none when
   nothing changed.
2. Protection: town blocks in Live mode already follow `hub.holds` (`HubData.protectsFrom`, the Live break check in
   `WalkInZones`, whose message still says "The home pad and roads are protected"); explosions must spare a town logo's
   blocks in Build mode too (`LogoExplosionMixin`: `hub.logoAt(level, pos).isPresent()`); signs are text displays and
   cannot be hit.
3. Server tests for both, with a fake program list and drawn pictures; `mod/dev/build.sh` twice; commit, push.

**Step 3:** roads grow with their group (never shrink); `INTERNET · 2` counts; `/aresos hub rebuild`; re-render on a
new converter version; the sign's second line with package 35's short name; a new world gets the same town; one
full client-test pass.

**Step 4 (Fable):** client screenshots under `reviews/36-town/screenshots/`, the real three for the builder's eyes
only, docs (`mod/README.md`, `README.md`, HUB.md corrections), the report, delete this file, merge `origin/main`,
`gh pr create`.

## Found on the way (for steps 2 to 4)

- **Name spaces overlap at the corners, harmlessly.** `GatePlan.signSpace()` is a square of ±6.1 blocks around a
  name. Diagonal neighbours across a lane (for example N0R0 and E0L0, Discord and Lunar Client on day one, and
  `N(r)R(r)` with `E(r)L(r)` in every row) share a few of those cells at heights 76 and up. The space only has to be
  air, and the names' turning circles stay 14.8 blocks apart (more than the 12.2 they need), so nothing collides;
  but step 2 must not treat a gate's sign space as its own (in a "blocked" check or in the record).
- **HUB.md 3.3 asks for grass or the mod's ground under all three spaces;** `GateBuilder.build` today checks only
  that the walkway is sturdy and the exit safe, and paves the doormat only when its ring is grass or dirt. Step 2
  decides whether "blocked" adds the ground check.
- **The picture's hash** (step 2's `hub.dat`): `GatePicture` has no `equals`/`hashCode`, and `GateBuilder.picture`
  does not return the icon's bytes. Hash the icon's bytes from `AppIcons.read` (an icon change) and keep the
  converter's version separately, or hash the 12 x 12 cells.
- **`AppIcons.read` can wait up to 3 seconds per app** on the calling thread; `GateBuilder.picture` runs on the
  server thread. A first build of forty apps with a hanging file system could stall; step 2 may read pictures off
  the server thread.
- **Client test expectation changed** (`GateLogoClientGameTest`, the "gate-tree" doormat is yellow now). Step 3's
  client run checks it; its screenshot of that gate changes colour at the doormat.

- **(Step 2a) A town light he changes blocks the logo's removal.** Changing a light's level or waterlogging it is his
  edit, so the record forgets it; `Neighbors.checkRemoval` then refuses because a light that is not the mod's is not
  "inert" (package 33 accepts only its own lights, which hand-built gates keep in their record). The logo then stays
  with a chat line every run. Step 2b may accept any dry light as stable on removal in `Neighbors` (its comment's
  reasoning holds for every dry light) or keep it as "leave the logo standing".
- **(Step 2a) A mod of packages 32 to 35 rewrites `hub.dat`** (when a pad or road block changes) and drops `logos`; HUB.md's
  correction "an older mod never rewrites hub.dat" holds only for mods before package 32. After going back to such a
  mod and changing the pad, the newer mod no longer knows the standing logos: their places look blocked and the apps
  move on. Step 4 should put this in HUB.md's corrections; a separate file for the logos would avoid it.
- **(Step 2a) `/aresos logo remove here` at a town logo** uses the zone's area (the niche to the exit), so he must stand
  in front of the door, as for a hand-built gate.

## Dead ends

- None that cost time. Considered and dropped: a three-state "free / blocked / not loaded" input to `Assignment`
  (treating an unloaded place as not blocked gives the same result with less code), and reordering `AppGroup`'s
  constants to N, E, S, W (could change what package 35 sees).
