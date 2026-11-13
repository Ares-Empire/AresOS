# 36: The town builds itself, progress

Brief: `briefs/36-town.md`. Steps 1 to 4, one fresh builder per step. The last step deletes this file.

## Where it stands

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

## What is left, in order

**Step 2** (starts when package 35 is on `main`; the orchestrator says when): `place` and `group` in the apps file
(schema 3, no new number, test that package 34's parser reads such a file); the standing logos in `hub.dat` with
every block, grass, doormat ground, sign and zone IDs, picture hash and converter version; the town's zones in
`zones.dat` marked as the hub's; one function for every block the hub places or removes (`FlatHub` and
`GateBuilder` go through it); keeping in step (HUB.md 3.4's six points: flat-1 worlds only, complete lists only,
take down / build / refresh, blocked places, refused removals, unloaded places pending, pinned first on the first
build, one chat line per change); protection in Live mode; server tests for all of it.

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

## Dead ends

- None that cost time. Considered and dropped: a three-state "free / blocked / not loaded" input to `Assignment`
  (treating an unloaded place as not blocked gives the same result with less code), and reordering `AppGroup`'s
  constants to N, E, S, W (could change what package 35 sees).
