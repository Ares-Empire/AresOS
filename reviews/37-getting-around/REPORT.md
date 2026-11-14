# 37: Getting around the town: report

Brief: `briefs/37-getting-around.md` (empire board brief 287; HUB.md section 6, row 6, the last piece of home screen
version 1). Built in three steps by fresh Claude agents (Opus 5.5), one per step, on branch `pkg/37-getting-around`.

**What he sees.** In his flat home:

- **`/go steam`** (any name `/open` takes, among his apps first; Tab completes them) puts him on the ground in front of
  Steam's door, looking at it; one step and he is in. Arriving opens nothing and changes no block. A logo whose ground is
  not loaded yet is built as he arrives; if his own build stands where he would arrive, he arrives at the nearest free
  spot on the way in.
- **H**, or **`/home`**, puts him back home (the pad, facing north, unless `/aresos home set` moved it), from any
  dimension.
- **`/apps`** says where every logo stands ("Lunar Client: /lunar. Games, east, front row, left") or why one has none.
- **`/aresos app swap chrome discord`** makes two logos change places; **`/aresos app move steam west`** puts Steam among
  Work & Media, and it stays there. Both are all or nothing: when anything is in the way (his torch on a logo, a place
  that is not loaded), nothing changes and one line says what is in the way and what he can do.

**Try this** (a new flat home in a game whose app helper lists his programs, so the town stands):

1. `/apps`: every row says where its logo stands. Click a row: the app opens.
2. `/go discord` (or `/go dc`): he stands at Discord's door. Look up for its sign. One step forward: Discord opens.
3. Walk away, press **H**: back on the pad, facing north. `/home` does the same.
4. `/aresos app swap chrome lunar`: Chrome's logo stands on the east road with a red doormat, Lunar Client's on the north
   road with a light blue one; the counts over the roads stay. `/apps` says the new places. Swap them back: both stand
   where they stood, and `config/aresos/apps.json` holds no hand-set `group` for them.
5. `/aresos app move notepad west`: Notepad stands on the west road and `WORK & MEDIA` counts one more.
   `/aresos app move notepad south` brings it back.
6. Press G, put a torch on a logo's doormat, press G again and swap that app with another: one red line ("Nothing was
   swapped: … cannot come down. Logo could disturb neighboring minecraft:torch at …"), and nothing changed. Break the
   torch (Build mode) and swap again: it works.

## Done

### Step 1: `/go`, `/home`, the H key, places in `/apps`

Commits on `pkg/37-getting-around` (on `df82fabc`):

- `8ff8f426` 37: step 1: a place in words, and its exit point
- `be5d87bf` 37: step 1: /apps says where each logo stands
- `235794e0` 37: step 1: /go, /home and the H key
- `daf7ee66` 37: step 1: the /apps row in package 35's client test, and PROGRESS.md

1. **A place in words** (`hub/Place.words()`): the one function from a place to words. Group title, direction,
   "front row" for `r = 0` and "row N" (counted from 1) after it, "left" or "right" as he sees it walking out from
   home (the place's side, L or R), and "Nth from the road" when `k > 0` (2nd, 3rd, 4th … 11th, 12th, 13th … 21st,
   22nd). `N0L0` is "Internet, north, front row, left"; `W1R1` is "Work & Media, west, row 2, right, 2nd from the
   road". `/apps` and `/go` use it; step 2's lines should too.
2. **The exit point** (`hub/Place.exit(dimension, home)`): HUB.md 3.2's exit point and facing, taken from the gate
   that would stand there (`GatePlan.of(...).exit()` with a plain front; the exit does not depend on the picture), so
   it is the very point the town's zone returns him to. Yaw is the group's outward yaw, pitch -10
   (`GateNumbers.EXIT_PITCH`).
3. **Where an app's logo is** (`hub/Whereabouts.of(server, app, complete)`): one answer for `/apps` and `/go`. In
   order: no flat home of these rules → `NO_TOWN`; the town's record holds a logo of the app → `STANDS` at the
   record's place (also in a frozen town); a refused town file → `STANDS` at the saved place when `zones.dat` holds
   the app's doorway there (the record cannot be read), otherwise `REFUSED`; frozen → `FROZEN`; a saved place that is
   not loaded → `WAITS`; no complete program list in this game → `NO_LIST`; no saved place → `NO_PLACE`; a loaded
   saved place without a logo → `BUILDING`. It reads only; it never loads a chunk.
4. **`/apps`** (`names/ProgramCommands`): each row is now "Lunar Client: /lunar. Games, east, front row, left"
   (clickable as before). Without a standing logo: "…, built when you come near" (WAITS), "…, being built"
   (BUILDING), "Games: no logo until the system has listed your programs", "Games: no free place", "Games: the town
   is frozen", "Games: the town's file does not fit this world", "Games: no town in this world". Apps that are not
   installed keep their grey "not installed" row. `/open`'s list of choices keeps its old row (name, commands, group).
5. **`/go <app>`** (`world/GettingAround`): a root command like `/open`, installed only where no other command has
   the name, for the host of an AresOS world only. The lookup is `/open`'s (`names/OpenPrograms.find`, now with a
   filter): same keys, but among his apps first. Completion lists the keys of his apps only. Then by `Whereabouts`:
   - `STANDS` or `WAITS`: to the place's exit point, looking at the door. If the two blocks there are not free (his
     build), the nearest free spot on the way in towards the door, up to the layer in front of the logo (never in
     the doorway); if none is free, he stays and one line says so ("Something of yours stands in front of Discord's
     door (Internet, north, front row, right) with no free spot on the way in, so you stay where you are."). "Free" is
     `HomeSites.isSafe` (solid ground, two blocks of air, no fluid or fire), the check the logo's own return uses.
     `WAITS` adds one line: "The town builds Far's logo here now that you are near." (or, before a complete list,
     "Far's logo is built here once the system has listed your programs.").
   - `NO_TOWN`: the exit of the nearest zone of that app in his dimension (all zones are his there), if its exit is
     safe; otherwise "… has no logo here." or "The exit of …'s logo is obstructed …".
   - `BUILDING`, `NO_LIST`, `NO_PLACE`, `FROZEN` ("… and the town is frozen: /aresos hub trust lets it build
     again."), `REFUSED`: one line why, no move.
   - Not his: "Stranger is not one of your apps. /aresos app add go-stranger adds it." Several non-his matches: one
     line listing them with their IDs. His app that is not installed: one line. Several of his apps match: one line
     naming them with their short names.
   - It never opens anything, never changes a block. After the teleport `WalkInZones.arrived` takes the zones he
     touches as already entered, so arriving can never count as walking in (also for a hand-made zone whose exit lies
     in its own box). Review fixes 1 (below): every teleport of the mod does this now, and an arrival that is not
     loaded is loaded by the game's own ticket and checked a later tick (points 1 and 4).
6. **`/home`** (`world/GettingAround`, `world/HomeCommands.home`): runs `/aresos home`'s own path. `/aresos home`,
   `home set` and `home info` are unchanged; the teleport they share is `HomeCommands.teleport`.
7. **The H key** (`client/AresOsClient`, `world/HomeKeyPayload`, `HomeCommands.key`): "Home" in the AresOS key
   category, default H, changeable in Controls, registered and consumed like G. The client sends `aresos:go_home`
   only with a player, no screen open, the debug modifier (F3 unless rebound) not held, and in an AresOS
   singleplayer world (`acceptsAppCommands`). The server checks the host and the AresOS world again and does what
   `/aresos home` does; a refusal ("No readable AresOS home …") shows above the hotbar.

### Step 2: `swap` and `move`

Commits on `pkg/37-getting-around` (on `daf7ee66`):

- `a6a2eb26` 37: step 2: the checks before a swap or move use the town's own functions
- `3c0323ae` 37: step 2: /aresos app swap and move
- `107970ea` 37: step 2: server tests for swap and move; step 1's Nether test leaves no home record
- `66d16f81` 37: step 2: a longer wait for far-off chunks, and PROGRESS.md

1. **`/aresos app swap <a> <b>`** and **`/aresos app move <app> <north|east|south|west>`** (`item/AppCommands`, logic in
   `hub/TownMoves`). Host-only like the rest of `/aresos app`. Names are `/go`'s: `GettingAround.his` (shared now, the
   same lookup and lines as `/go`: several match, not his, not installed, nothing) and `GettingAround.suggestHis` (the
   completion of `/go`, among his apps). `move` completes the four directions (literals, one per group's avenue).
2. **Refusals before checking anything**, as `hub rebuild`: no town ("This world is not a flat home: it has no town."),
   other rules, a refused town file (`TownKeeper.refused`), a frozen town (`TownKeeper.frozen`, the freeze's own line),
   no complete program list ("The town waits for the system's list of programs. Nothing changed; try again in a
   moment.").
3. **The checks, in this order, changing nothing** (`TownMoves.check`): each app's logo stands where its place is
   saved, in its group (otherwise "the town is still moving …" or, from `Whereabouts`, why it has no logo, with "Stand
   at home and try again" for a place not loaded); the pictures of the new logos are held by the town (otherwise "the
   town is still reading the picture of X. Try again in a moment." and the town is asked to read it, off the server
   thread); the town's own planning with the places as they will be saved puts each app where the command means;
   every logo involved can be taken down now (the moved apps' own, and any town logo still standing in a new place);
   each new place takes its new logo once those came down. Every refusal starts "Nothing was swapped:" / "Nothing was
   moved:" and says what is in the way (the game's own message, e.g. "Logo could disturb neighboring minecraft:torch at
   …, then retry.") or "Stand at home and try again." when a place is not loaded.
4. **Then, in the same tick:** the places (and hand-set groups) are saved through the game's `Spots`
   (`AresOs::saveSpots`), then one pass of the town (`TownKeeper.keep`, the pass `TownKeeper.run` makes). The command
   says one line ("Chrome now stands at Games, east, front row, left, and Lunar Client at Internet, north, front row,
   right." / "Steam now stands at Work & Media, west, front row, left."), then the pass's own lines about anything else
   (another app taking a freed place, something of his in the way). If a moved logo does not stand in its new place
   after the pass, the command's line is instead "The town did not finish: X's logo does not stand at … yet. Its place
   is saved, and the town keeps trying."
5. **Swap:** across two groups each app takes the other place's group as its hand-set `group`, removed where it equals
   the app's own group (so a swap back leaves none); inside one group the groups stay as they are. **Move:** the app's
   hand-set group becomes the new one (removed when it is its own), and its place the first one the town's planning
   gives it in that group (as for a newcomer: nearest first, not taken, not blocked); a place where its own logo cannot
   stand although the place check passed (a longer name needs more air above the sign) is passed by, up to three
   times, as the pass would. To the group it stands in: "Steam already stands in Work & Media, west. Nothing was
   moved."
6. **Point 3 (a place that still holds the town's own logo due to come down waits, it is not blocked):** package 36's
   pass already does this, no change needed there: `TownKeeper.blocked` answers "not blocked" for any place a town
   logo stands in (`occupied`), and the build of the new app is skipped while that logo's removal was refused
   (`waitingFor`), so the app keeps the place and waits. Tested (below). The checks follow the same rule: a town logo
   standing in a new place is one of the logos that must come down, so a move there is refused (all or nothing), never
   sent on to the next place.
7. **Point 4, what follows by itself:** the counts on the group names, the roads (paved to the new row, never unpaved),
   the group in `/apps` (the record's place in words), the doormats and the signs all come from package 36's pass and
   are tested. **The Apps screen shows no group** (HUB.md 2.x: icon, name, short name; no client code reads a group):
   there is nothing to follow there. The test checks `AppGroup.of(app)`, the group any such display would read.
8. **Pictures** (`TownKeeper.Read`): the town now keeps the icon as read, or that the app has none; a plain front is
   made on the spot for the group the app has now. Before, a picture was valid only for the group it was read for, so
   every group change needed a new read, and a check's read for the new group would have been read over by the next
   pass for the old one: a cross-group swap of an app without an icon would have said "try again" forever.

**How the checks and the pass are kept from disagreeing.**

Each check is the function the pass itself uses, asked before the pass does it; nothing runs between them.

- **Where each app goes:** `TownKeeper.plan`, pulled out of the pass's round: the same order (pinned first, then the
  file), the same saved places, and the same `blocked` with the keeper's own state (its `refused` places, places
  occupied by town logos). The check runs it on the apps as they will be saved and requires each moved app to come out
  at its intended place.
- **Taking a logo down:** `Town.checkRemove` runs `GateBuilder.checkRemoval`, which is the first half of
  `GateBuilder.takeDown` itself (load check, then `Neighbors.checkRemoval` on exactly the blocks that would change); the
  take-down now calls the same function.
- **Building a logo:** `Town.check(server, app, place, picture, down)` is `Town.build`'s own preparation
  (`GateBuilder.prepare` plus the town's floor rule) with the picture the pass will use (the same `pictures` function),
  and the logos in `down` read as their take-down leaves them (`GateBuilder.left`, the same computation `takeDown` uses;
  their zones as gone). A block he changed in such a logo stays his and counts.
- **Timing:** the command runs the checks, saves and runs the pass in one call on the server thread, so the world and
  the keeper cannot change in between. The town's background pass runs at the end of a server tick, never inside a
  command. The catalogue can change in between (a helper refresh runs on its own thread): review fixes 1, point 2,
  takes it once and saves only while it is unchanged.
- **If they still disagree** (something no check foresees), the command says so in one line instead of its own, and
  the pass's lines say what happened; the places stay saved and the town's pending work goes on.

### Step 3: the pictures, the docs and the pull request

Commits on `pkg/37-getting-around` (on `66d16f81`):

- `1365c286` 37: step 3: README, mod README and HUB.md for getting around
- `00a6aec9` 37: step 3: client test with pictures of getting around
- `4aca5571` 37: step 3: PROGRESS.md in the report's layout, with step 3
- 37: step 3: the pictures from the final run
- 37: step 3: the report's run results (this file)
- 37: step 3: merge origin/main

1. **`GettingAroundClientGameTest`**, last in the client list; its pictures go to `reviews/37-getting-around/screenshots`
   (`aresos.goReviewDir` in `mod/build.gradle`). A fake helper lists day one with Mail (Internet's third app, so the
   second row) and Spotify (Work & Media), with the icons package 36's picture test draws; a new flat home is made
   through the title screen and the town builds seven logos ("The town is built: 7 logos. /apps lists them."). Each step
   is typed or pressed as he does it:
   - `/go mail`: he stands at Mail's exit point (N1L0), yaw 180, pitch -10; ten ticks on the spot open nothing and no
     line is said. A picture; then from the same spot looking up (pitch -45), a picture of the sign.
   - The H key (through the test input): back at (0.5, 64, 0.5), yaw 180, pitch -8, nothing said or opened. A picture.
   - `/apps`: "My apps: 7. Click one to open it." and one row per app, each its name, its commands and `Place.words()` of
     its place (Mail's is "Mail: /mail. Internet, north, row 2, left"). A picture with the chat.
   - Build mode, from above: the counts are INTERNET · 3, GAMES · 1, SYSTEM & TOOLS · 2, WORK & MEDIA · 1. A picture.
     Then `/aresos app swap chrome lunar`: Chrome stands at E0L0 and Lunar Client at N0L0, with one line ("Chrome now
     stands at Games, east, front row, left, and Lunar Client at Internet, north, front row, left."); every other app
     stands where it stood, the counts are unchanged, the doormats are red and light blue, and the apps file holds
     `group` "games" and "internet". A picture.
   - Live mode, `/go discord`, his torch on Discord's doormat (set as his own blocks are, not through the town's record),
     `/aresos app swap discord spotify`: one line, "Nothing was swapped: Discord's logo at Internet, north, front row,
     right cannot come down. Logo could disturb neighboring minecraft:torch at …"; the town's places, the torch and both
     apps' entries are unchanged. Looking down at the torch, a picture with the line.
   - With `ARESOS_TOWN_LOOK` set it skips itself with a log line (3-2).
2. **`TownPicturesClientGameTest`** (package 36): its programs, drawings and its helpers for standing, hovering, switching
   modes and taking a picture are package-wide now (only `private` dropped; 3-1). Its comment no longer says it is last.
3. **Package 35's picture of `/apps`** (`reviews/35-slash-names/screenshots/0059_35-apps-chat.png`) is committed anew from
   the final run: it shows the new rows ("Discord: /discord, /dc. Internet: no town in this world", in that test's world
   without a town).
4. **Docs.** `mod/README.md`: `/home` and H beside `/aresos home`; under "The town" which group an app has once moved,
   **Getting around** (`/go`, `/home`, H, `/apps`) and **Arranging the town** (`swap`, `move`, the saved `group`, what they
   refuse); `/apps` and the reserved names under "Short app commands". `README.md`: the status line. `docs/design/HUB.md`:
   "Corrections from getting around (package 37)", eight points (the Apps screen shows no group, a place in words, `/go`'s
   arrival, home, all or nothing, a town logo that cannot come down, "it stays there", the town's pictures).
5. This report (in `PROGRESS.md`, since a Claude agent cannot create `REPORT.md`).

## Verified

### Step 1

- Unit (`PlaceTest`): `aPlaceInWordsAsHeReadsItInTheChat` (the five of day one, `W1R1`, `N2L2`, `E1L0`, `S4R3`, the
  ordinals 11th to 13th, 21st, 22nd, 64th); `theExitPointOfAPlaceIsTheTablesExitPoint` (HUB.md 3.2's six exits from a
  home block that is not the origin, yaw, pitch -10).
- Server game tests (`GettingAroundGameTests`, two batches of their own, `go_town` and `go_no_town`):
  - `goPutsHimInFrontOfHisAppsDoors`: a town on new ground with four logos built by `Town.build`. `/apps` rows
    (standing, second row, a place not loaded, no list yet). `/go chr` → (H − 9.0, H, H − 13.5), yaw 180, pitch -10,
    no line. Ten ticks later nothing was opened; stepping into the niche then does open it (the check can see a
    launch). `/go Notes` (`W1R1`) → (H − 27.5, H, H − 23.0), yaw 90; `/go lunar client` → (H + 14.5, H, H − 9.0),
    yaw -90. His stone at Discord's exit → one block nearer the door, no block changed. His stone on the whole way in
    → no move, the line, no block changed. `/go stranger` → the add line. `/go far` (`N40L0`, not loaded, `WAITS`) →
    (H − 9.0, H, H − 573.5), yaw 180, and its line.
  - `goWithoutATownAndHomeFromTheNether`: a hub of other rules (`flat-0`) stands in for a world without a town (the
    server's hub record cannot be taken away; `Whereabouts` treats both alike, checked). `/go bare` → "Bare has no
    logo here."; two hand-made zones → the nearer one's exit; `/go other` → the add line; `/home` from the Nether →
    the home spot in the Overworld, yaw 180, pitch -8; the same through `HomeCommands.key` (the H key's server half).
- Client (`FlatHomeClientGameTest.assertHomeCommands`, no new picture): after `/aresos home`, from 30 blocks away
  `/home`, then the H key pressed through the test input, each back on the pad facing north.

From the worktree root, 2026-11-14:

| Run | Exit | What it printed |
|---|---|---|
| `mod/dev/build.sh` | 1 | `BUILD FAILED in 20s`: my test expected Newcomer (no group given) in Internet; it is in System & Tools. Test fixed. |
| `mod/dev/build.sh` | 1 | `BUILD FAILED in 28s`: "The far line: []": the test's own failure messages called `lines()`, which drains the chat, so the line was eaten before it was checked. Test fixed (`Host.ran`); the code was right. |
| `mod/dev/build.sh` | 0 | "All 96 required tests passed :)", `BUILD SUCCESSFUL in 1m 57s`; unit tests 213 run, 6 skipped (Windows), 0 failed |
| `mod/dev/client-test.sh` (run 1, 07:32 to 07:47, waited for another builder's run first) | 1 | `BUILD FAILED in 8m 12s`. Every test up to package 34 passed ("09c" … "34 client checks passed"), including `FlatHomeClientGameTest` ("32 client checks passed") with the new `/home` and H key checks. `SlashNamesClientGameTest` failed at line 118: it looked for the `/apps` row starting "Discord " and the row now starts "Discord: ". Its assertion follows the new row ("Discord: "); it still clicks the server's own row. |
| `mod/dev/client-test.sh` (run 2, started 07:48, ended 08:06) | 0 | `BUILD SUCCESSFUL in 9m 18s`; 15 "client checks passed" lines, among them "32 client checks passed" (with `/home` and H) and "35 client checks passed" (the `/apps` row clicked), and "36 pictures taken" |

After each client run the tracked pictures were put back (`git checkout -- reviews/`) and the run's untracked
renumbered pictures removed; this step commits no picture. Package 35's picture of `/apps` in the chat
(`reviews/35-slash-names/screenshots/0059_35-apps-chat.png`) now shows the new rows ("Discord: /discord, /dc. Internet: no town in this world" in that test's
world without a town); step 3 retakes the pictures.

### Step 2

- Server game tests in `GettingAroundGameTests`, two batches of their own (`go_swap`, `go_move`), each its own town on
  new ground, the host's own apps file, a `TownKeeper` of the test, the drawn ring picture:
  - `swapExchangesTwoLogos`: a swap inside one group (line, places, no hand-set group, signs and doormats, the pass
    adds no line); a swap across two groups (line, saved `group` "games"/"internet", doormats in the new groups'
    concrete, signs, counts INTERNET · 2 / GAMES · 2 / SYSTEM & TOOLS · 1, the place `/apps` names, `AppGroup.of`); a
    swap back (no hand-set group left); a picture not read (the line, the read asked for, nothing changed); his torch on
    Discord's doormat (the line, every block in ±40 unchanged, apps file and town records unchanged); an incomplete
    list (the town's line); typed: `/aresos app swap chrome nothing` (/go's line), and when the run has no complete
    list, `/aresos app swap chrome discord` and `/aresos app move lunar west` (the town's line); completion of an app
    name and of the four directions.
  - `moveSendsALogoToAnotherGroup`: to a free place (W0L0, saved group, counts, sign, doormat, E0R0 free); to the group
    it stands in (the line, nothing changed); his cobblestone in W0R0 (Lunar Client goes to W1L0, "row 2", his block
    untouched, the west road paved to row 1); back to its own group (E0L0, no hand-set group, the west road stays
    paved); point 3: Discord leaves My apps with his torch on its logo (the logo stays), a move to its place is refused
    ("Discord's logo at Internet, north, front row, right cannot come down."), a newcomer of Internet is given that
    place by the pass and waits there with no line and no logo, and once the torch is gone the pass takes Discord's logo
    down and builds the newcomer there; a place not loaded (19 placeholder apps fill System & Tools' first four rows,
    so the first free place is S4L0, outside the loaded chunks: "Nothing was moved: System & Tools, south, row 5, left
    is not loaded. Stand at home and try again.", world, file and records unchanged).
- Step 1's `goWithoutATownAndHomeFromTheNether` now takes away the home record it made (see 2-5).

From the worktree root, 2026-11-14:

| Run | Exit | What it printed |
|---|---|---|
| `mod/dev/build.sh` (main code only) | 1 | `BUILD FAILED in 1m 21s`, "2 required tests failed": `zone_safety_game_tests_explosions_preserve_logos_in_build` ("Build mode mining denied after explosions") and `ares_os_game_tests_below_bottom_returns_to_personal_spawn` ("Void recovery missed personal spawn: (-1.37487765E7, -60.0, 1.04165235E7)"). Cause: 2-5. |
| `mod/dev/build.sh` (with the new tests) | 1 | `BUILD FAILED in 1m 24s`, the same two; both new tests passed |
| `mod/dev/build.sh` (teardown fixed, leftover record removed) | 1 | `BUILD FAILED in 39s`: the swap test's typed `/aresos app swap` was "Unknown or incomplete command" (the test server had no `/aresos`; 2-6) |
| `mod/dev/build.sh` | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 1m 55s` |
| `mod/dev/build.sh` | 1 | `BUILD FAILED in 1m 25s`, "1 required tests failed": step 1's `go_puts_him_in_front_of_his_apps_doors`, "The town's chunks are not loaded yet on tick 400002", 8 seconds after it started (2-7) |
| `mod/dev/build.sh` (final code) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 1m 31s` |
| `mod/dev/build.sh` (final code, again) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 1m 32s`; unit tests 213 run, 6 skipped (Windows), 0 failed |

`mod/dev/client-test.sh` was not run: step 2 changes nothing a client test covers.

### Step 3

`GettingAroundClientGameTest` (Done, step 3, point 1). From the worktree root, 2026-11-14:

| Run | Exit | What it printed |
|---|---|---|
| `mod/dev/client-test.sh` (run 1, the test's first version) | 0 | `BUILD SUCCESSFUL in 9m 40s`; 16 "client checks passed" lines (09c, 09d, 09b, 09, 08, 07b, 07, 01c, 04, 04c, 32, 33, 34, 35, 36, 37), "36 pictures taken", "37 pictures taken". Looked at: `/go`'s picture showed no sign (3-4), the refusal's hid the torch behind the chat (3-5); both tuned. |
| `mod/dev/build.sh` (final code) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 2m`; unit tests 213 run, 6 skipped (Windows), 0 failed |
| `mod/dev/client-test.sh` (run 2, final code) | 0 | `BUILD SUCCESSFUL in 9m 35s`; the same 16 lines, "37 client checks passed: …", "37 pictures taken: …" |
| `mod/dev/client-test.sh` (run 3, final code) | 0 | `BUILD SUCCESSFUL in 9m 38s`; the same 16 lines; "Client tests ended with exit code 0 after 9 min 39 s (intel: Mesa Intel(R) Iris(R) Xe Graphics (RPL-P) (Intel))" |

Pictures from run 3, each looked at:

| Picture | What it shows |
|---|---|
| `0076_37-go-second-row.png` | After `/go mail`: Mail's logo (the drawn envelope on light blue) fills the view, the doorway straight ahead on its light blue doormat. The sign is above the screen (3-4). |
| `0077_37-go-second-row-sign.png` | The same spot, looking up 45 degrees: the sign's first line, "Mail", reads at the top; its second line, "/mail", is half hidden behind the logo's top edge (3-4). Added in step 3. |
| `0078_37-home-key.png` | After H: the arrival view from the pad, Chrome and Discord with their signs readable, "INTERNET · 3" between them, Mail's logo behind Chrome. |
| `0079_37-apps-chat.png` | `/apps` at home: "My apps: 7." and seven rows with places, e.g. "Mail: /mail. Internet, north, row 2, left"; Terminal's row wraps its last word ("right") to a second line. |
| `0080_37-swap-before.png` | From above in Build mode: Chrome (the globe) at N0L0, Discord at N0R0, Mail in row 2, Lunar Client (the star tile) at E0L0, Spotify on the west road, Notepad and Terminal on the south road. |
| `0081_37-swap-after.png` | After `/aresos app swap chrome lunar`: Lunar Client at N0L0 with a light blue doormat, Chrome at E0L0 with a red one; everything else as before. |
| `0082_37-swap-refused.png` | At Discord's door, looking down: his torch on the light blue doormat, and the red line "Nothing was swapped: Discord's logo at Internet, north, front row, right cannot come down. Logo could disturb neighboring minecraft:torch at 9, 64, -18. No blocks changed. Leave two cells clear of plants, circuits, fluids and blocks with special behavior, then retry." (3-5). |
| `reviews/35-slash-names/screenshots/0059_35-apps-chat.png` | Package 35's `/apps` picture, committed anew from run 3: "Discord: /discord, /dc. Internet: no town in this world", the other four rows the same way (that test's world has no town). |

Runs 2 and 3 gave the same pictures (compared pixel by pixel: the same except the torch's flame in `0082` and 53 pixels
along an edge in `0076`). After each run the tracked pictures of other packages were put back and the untracked
renumbered pictures removed; this step commits only its own seven pictures and `0059`.

## Not verified

From step 1:

- The town building a not-loaded logo as he arrives by `/go`: that is package 36's pending retry, tested there
  (`keepingFar`); here the test checks only where he arrives.
- `/go` in a frozen town and with a refused town file: by reading only (no server test; the brief's list has none).
- F3+H in the real client (the debug-modifier check is in the code; no client check, because F3+H writes to the chat
  and toggles advanced tooltips, which the next picture of that test would show).
- H with a screen open, and H in a non-AresOS world: by reading only.
- `NO_PLACE` with an app whose old saved place is blocked: the assignment keeps such a place saved, so `/apps` says
  "being built" for it while every place of its group is blocked (needs 4160 blocked places).

From step 2:

- The "town did not finish" line: no test makes the pass disagree with the checks (that would need the world to change
  between them, which one tick does not allow).
- A swap or move refused for a logo whose own place is not loaded (`Town.checkRemove` → `NotLoaded`): by reading; the
  test covers a new place not loaded and (by `Whereabouts`) an app whose place is not loaded.
- Frozen town and refused town file for swap and move: by reading (the same lines and checks as `hub rebuild`).
- The typed commands with a complete program list in a real game (the test server has none unless another test gave
  one; then the typed part with the town's line is skipped and only the "nothing matches" line is checked).
- That a reload is what registers `/aresos` on the game test server: inferred from the batch order of two runs.

From step 3:

- His own screen: the pictures come from the headless compositor at 960 x 540, the window package 36's pictures use as half
  his 1920 x 1080 screen at the game's scale; colours and legibility on his screen are inferred from that.
- `move` has no picture (the brief asks for none); step 2's server tests cover it.
- The doormats' colours from above are two small blocks each: the test checks them block by block; the picture only
  shows them.
- The H key on his own keyboard and with F3 held (step 1).

## JUDGMENT-CALL

From step 1:

- **1-1. `/go` looks among his apps first.** The keys are `/open`'s, but a program that is not his never hides one
  that is (`/go st` with Steam his and Stellarium not goes to Steam). Only when none of his apps matches does it look
  at the rest, to say how to add one. Rejected: `/open`'s result filtered afterwards (an exact match of a stranger
  would hide a prefix of his own).
- **1-2. Arrival checks may load a chunk** (corrected by review fixes 1, point 4). As built in step 1, the spots of a
  place that is not loaded were read in the command, which loaded their chunk synchronously: measured since, 416 ms on
  the server thread for new ground. Now nothing is read in the command where a spot's chunk is not loaded: the game's
  own teleport ticket (`PORTAL`) loads the chunks the spots' boxes touch (at most four; one in the test), a later tick
  checks them and moves him or says one line, and the tickets go then. Rejected, as before: moving him unchecked
  (into a wall, against "If unsure"); refusing for an unloaded place (against "it also works while the logo is not
  built yet").
- **1-3. `/go` refuses for a loaded place with no logo yet (`BUILDING`)** with "… is not built yet. Try again in a
  moment." The brief names only the not-loaded case as one to go to; a loaded place without a logo means the town is
  still at work (a picture being read, an old logo to take down first), so he is told instead of being put in front
  of nothing.
- **1-4. `/home` and `/go` exist only for the host of an AresOS world**, like `/open` and `/apps` (`AppCommands.allowed`
  as the requirement), and only where no other mod has the name. So in a normal world `/home` is an unknown command,
  where `/aresos home` says "Not an AresOS world"; everything else is `/aresos home`'s own path.
- **1-5. A refused town file:** a logo "stands in its recorded place" when `zones.dat` holds the app's doorway at its
  saved place (the box the town makes), since the refused records are not read. Without that doorway, one line.
- **1-6. Words:** the row is counted from 1 for him ("row 2" is `r = 1`), and an absent app's `/apps` row stays as
  package 35 had it.
- **1-7. Feedback:** `/go` to a standing logo says nothing (he sees the door); a `WAITS` arrival says one line,
  because he arrives in front of nothing for a moment.

From step 2:

- **2-1. The command's line replaces the town's "moved" lines** for the apps it moved (`TownKeeper.keep(..., quiet)`).
  Otherwise one swap says three lines about two logos. The pass's other lines (other apps, his things in the way)
  follow the command's line.
- **2-2. A place where a logo involved stands is checked as if that logo were down** (`GateBuilder.Gone`): a swap's two
  places are each held by the other logo while the checks run, and `Town.check` alone would refuse them ("Area isn't
  clear"). Rejected: taking the logos down first and building them back on a refusal (not "nothing changes": new zone
  IDs and sign entities, and a build back can fail).
- **2-3. Pictures: icon or plain front, not per group** (point 8 of Done). The smallest change that lets the
  "try again in a moment" loop end; it also spares a read on every group change.
- **2-4. Move passes by a place where only its own logo cannot stand** (up to three places, `TownMoves.TRIES`, like the
  pass's three rounds), since the brief asks for "the first free place of that group that can be built on" and the pass
  would move it on the same way. A place blocked for every logo is already passed by the planning.
- **2-5. Step 1's Nether test left a home record in the shared test world.** It called `NetherHome.recordHome` in a
  world that had none and restored only an exact home that existed before, so `nether_home.dat` kept its spot; from the
  next run on, every test player who joins is sent there (void recovery and the Build mode explosion test fail). A fresh
  world passes once, which is why step 1's last run passed. Its teardown now takes the record away again: the game has
  no call to drop saved data, so the test removes it from the data storage's loaded-data map (found by type, no field
  name) and deletes the file. The leftover file in this worktree's test world (`mod/build/run/gameTest/world/data/aresos/nether_home.dat`)
  was removed once by hand.
- **2-6. The test Host registers `/aresos app`** as the mod does on an integrated server. On the game test server
  `/aresos` exists only after some test reloads the server, so the typed check passed or failed with the batch order.
- **2-7. `LOAD_TICKS` in `GettingAroundGameTests` is now 4,000,000.** The test server ticks without pause while tests
  wait: 400,000 ticks were 8 seconds while another package's build ran, too short for a town on new ground. It only
  says how long a test waits before it fails. Package 36's tests keep their own 400,000.
- **2-8. Refusal wording:** every refusal after the first checks starts "Nothing was swapped:" / "Nothing was moved:"
  and carries the game's own reason, which already says what to do ("Move it away, then retry", "Leave two cells clear
  …"). Moving to its own group is a refusal line (red), like `hub trust` when nothing is frozen.

From step 3:

- **3-1. The new test shares package 36's helpers** (its programs, drawings, `look`, `hover`, `mode`, `picture`) by dropping
  `private`, rather than copying them: one place to change how a picture is taken. Rejected: a copy of about 150 lines;
  a new shared class (a bigger change to package 36's file than this needs).
- **3-2. The test skips itself when `ARESOS_TOWN_LOOK` is set.** Package 36's opt-in puts real icons into the shared
  drawings, and this test's pictures go into the repo: with it set they would be pictures made from real icons.
  Rejected: changing `entry` to ignore the variable (that would change package 36's opt-in).
- **3-3. Seven apps:** day one plus Mail (Internet's third app, so a second row) and Spotify (every group has a logo in the
  view from above, and the refused swap goes across groups). Rejected: forty apps (package 36 pictures those; one swap
  is hard to find among them from above).
- **3-4. The sign at `/go`'s arrival (tuned, picture only).** The first picture after `/go mail` showed the door and no
  sign: at the exit point, 6 blocks out at pitch -10 (both decided: HUB.md 3.2 and the brief), the sign of a logo 12
  tall is about 58 degrees up, above the top of the screen, as package 36's correction for 2.2 says. The arrival was not
  changed; a second picture from the same spot, looking up 45 degrees, shows the sign: its first line, the name, reads;
  its second line, the short name, is half hidden behind the logo's top edge, so from the exit point he reads the name
  only. Changing the arrival later
  is one number (the exit's pitch or its distance); see Open questions.
- **3-5. The refused swap's picture looks down at the torch (tuned).** At the arrival pitch the torch was behind the five
  lines of the chat; looking down 15 degrees from the same spot shows the torch, the doorway and the line together.
- **3-6. The picture after the swap has no chat:** from above, the chat covers the south-west, where Spotify stands. The
  test checks the line word for word, and the README quotes it.

## PLAN-GAP

- **The Apps screen shows no group** (brief, step 2, point 4, "the group shown in `/apps` and in the Apps screen"): its
  rows show icon, name, kind and main short name. Nothing there follows a move; HUB.md's corrections now say so.
- **HUB.md 2.6, "Home … puts him on the pad, facing north":** `/home` and H do exactly what `/aresos home` does (the
  brief's rule), so they go to his home spot, which `/aresos home set` can move off the pad. HUB.md's corrections say so.
- **Step 3's "/go to an app in a second row (the door in front of him, the sign readable)"** cannot be one picture at the
  decided arrival: 6 blocks out at pitch -10 the sign is above the screen (3-4).
- **The test world is kept between runs** (2-5): a test that leaves saved data behind breaks the next run, not its own.
  Running `mod/dev/build.sh` twice is what catches it; nothing in the build does.
- **Package 35's committed picture of `/apps`** (`0059_35-apps-chat.png`) showed the rows as they were before this
  package; step 3 commits it anew.

## Open questions

- **Should `/go` show the sign on arrival?** At the exit point (HUB.md 3.2), 6 blocks out at pitch -10, the door fills the
  view and the sign is above the screen; looking up, the name reads and the short name is half hidden behind the logo's
  top edge (pictures `0076` and `0077`). He typed the name, so the door is enough, and one
  step takes him in: I would keep it. The alternatives: arrive about 14 blocks out (sign and door in view, eight more
  steps), or arrive looking up (the door at the bottom edge of the screen).

Nothing else holds up the merge. The judgment calls above go to the owner before merge; the ones that change how it
feels are 1-3 (`/go` refuses a loaded place whose logo is not built yet), 1-7 (`/go` to a standing logo says nothing),
2-1 (the command's own line replaces the town's lines about the apps it moved) and 2-8 (the refusal wording).

## Review fixes 1

Brief: `briefs/37-review-fixes-1.md`, after `REVIEW-1.md` (CHANGES-NEEDED: three FIX, three SHOULD, all accepted). One
Claude agent (Opus 5.5), one step, on `pkg/37-getting-around` from `ca1c3e26`.

Commits:

- `dfb1074b` 37: fix 1, point 1: every teleport of the mod marks its arrival, so arriving never opens an app
- `34272f07` 37: fix 1, point 2: swap and move use one catalogue snapshot and save only while it is unchanged
- `3f20cf3c` 37: fix 1, point 3: the checks see which signs the take-down removes and which stay
- `61c6ee57` 37: fix 1, points 3, 5 and 6: tests (a moved sign, bounded waits, frozen and refused at the command)
- `e53c97a2` 37: fix 1, point 4: /go loads an arrival that is not loaded off the command and moves him a later tick
- 37: fix 1: the report's section "Review fixes 1" (this text)

The tests of points 3, 5 and 6 share one test file and went into one commit with point 4's first measurement.

### Point 1 (FIX 1): arriving anywhere never counts as walking in

`HomeCommands.teleport`, the shared teleport, now calls `WalkInZones.arrived` itself (and drops a `/go` still loading,
point 4). Every teleport the mod makes, found by searching the code for `teleport`, `teleportTo`, `snapTo`,
`setServerLevel` and the respawn:

| Teleport | Where | How it marks its arrival |
|---|---|---|
| `/aresos home`, `/home`, the H key | `HomeCommands.goHome` | the shared teleport (new: before, nothing marked it) |
| `/go` to a logo, `/go` to a hand-made zone | `GettingAround` through `Arrivals` | the shared teleport (before: `GettingAround` marked it after the teleport) |
| The return in front of a doorway after an app closes | `WalkInZones.returned` | the shared teleport (before: its own teleport, then the membership set to empty, so a zone touching the exit, such as a hand-made zone whose exit lies in its own box, opened again) |
| Void recovery in Live mode | `LiveMode.protect` | `WalkInZones.arrived` after the respawn teleport (new) |
| The spawn on joining an AresOS world | `NetherHome.arrive` | `WalkInZones.arrived` after `snapTo` (new; joining was already no entry, since leaving drops the membership) |
| The respawn after death (the mod picks the spot, `ServerPlayerHomeMixin`) | Fabric `ServerPlayerEvents.AFTER_RESPAWN` in `WalkInZones.register` | `WalkInZones.arrived` (new) |

The other `snapTo` calls move display entities (signs, names), not him. Vanilla moves (`/tp`, portals, ender pearls,
the End's exit) are not the mod's and still count as walking (F1).

Test (`goWithoutATownAndHomeFromTheNether`, new steps): a hand-made zone, a home recorded inside its doorway (setting a
home checks safe ground only, so Build mode allows it there; the spot is checked with `HomeSites.isSafe`), then in Live
mode `/home`: he stands in the doorway, ten ticks later no launch; stepping out and in again launches once. The same
with `HomeCommands.key` (the H key's server half). The home record is put back as it was afterwards, also on failure.
"Fails without it": from reading (without the mark, the next walk-in tick sees a newly entered zone and sends its
launch); not run against the old code.

### Point 2 (FIX 2): one catalogue for the whole command

- `TownMoves.Game` now hands out a `Snapshot` (a token and the programs) and a `Commit`. `swap` and `move` take the
  snapshot once; the checks, the saved places and the pass all use it: the pass gets the snapshot with the new places
  (the very apps the checks planned with), not a fresh read.
- `AresOs.saveSpotsIf(token, spots)` is `static synchronized`, the lock every catalogue update takes (`takeIn` from the
  helper's thread, `saveMine`, names, pins, `saveSpots`). It saves only while the list in memory is still the token
  (the very object the command took); each of those updates puts a new list there. Otherwise nothing is saved and the
  command says "Your apps changed just now. Nothing was swapped; try again." (or "moved").
- Test (`swapExchangesTwoLogos`): the commit hook rewrites the apps file with Chrome's icon path changed and reloads
  the catalogue, as a refresh would, then calls the real `saveSpotsIf`. Swap and move both refuse with that line; the
  file's bytes (as the hook left them), the town's records, the zones and every block within 40 are unchanged.
  "Fails without it": from reading (the old code saved and passed; the swap would have reported done).

### Point 3 (FIX 3): the checks see which signs come down and which stay

- `GateBuilder.checkRemoval(level, gate, sign)`, the first half of `takeDown`, now returns what the take-down will do
  (`TakeDown`: the blocks that change and what comes back, the blocks he changed, and the sign it discards or why one
  stays). `takeDown` does exactly what it returns. `Town.checkRemove` returns it too.
- `GateBuilder.Gone` is made from those take-downs (`Gone.of`): their blocks as left, their zones gone, every block of
  their records no longer the mod's, their signs' IDs no longer recorded, and the signs they discard gone. A sign a
  take-down leaves (he moved or edited it) stays in the world and counts as his.
- `TownMoves.check` also counts any other logo the pass will take down (one the plan puts elsewhere or nowhere, in a
  town not yet in step) where its take-down check passes; where it does not, the pass leaves it, and so does the check.

The inputs of the build's checks (`Town.check` → `Town.prepare` → `GateBuilder.prepare`) and how the check sees each
after the take-down:

| Input | How the check sees it | Same as the commit? |
|---|---|---|
| The app, its name and main short name, its picture | the snapshot's app (point 2); the picture from the town's cache, which changes only at the end of a server tick | yes |
| The town's record (rules, refused, frozen) | refused before any check; unchanged within the tick | yes |
| Chunks and entities loaded | from the world; a take-down loads and unloads nothing | yes |
| The logo's space must be air | through `Gone`: blocks as the take-downs leave them | yes |
| The way in must be solid | through `Gone` | yes |
| The doormat's ground (grass or dirt around it) | through `Gone` | yes |
| The floor under the logo (untouched grass or the hub's) | through `Gone` (step 2) | yes |
| Trigger zones in the way | the down logos' zones as gone (the ones `Town.remove` removes: `hub.made`) | yes |
| Entities inside the logo's blocks | the mod's signs exempt, minus the down logos' signs, plus the signs their take-downs discard: a sign left standing counts | **fixed** (before, every recorded sign was exempt) |
| Entities hanging on or standing on blocks within reach | the same set | **fixed** |
| Blocks within reach (2, lights 4) | through `Gone`; the down logos' recorded blocks are no longer the mod's | **fixed** (before, read from the world with those blocks the mod's: the same verdict except a light he changed in a logo that comes down, which was the mod's in the check and his after) |
| Which logos come down | the moved apps' own and any town logo in a new place (must come down, else refused), and any other logo the plan moves or drops where its take-down check passes | **fixed** (before, only the first two) |
| The exit point is safe | from the world, not through `Gone` | yes, by the layout: it is 6 blocks in front of its own place's front, in the 11 blocks between two rows and on its own place's centre line; no logo's blocks (its front, the lights one layer in front, the doormat at the door) reach there |
| Logos the same pass builds before this one (the other logo of a swap, a newcomer given a freed place) | not modelled | same verdict: their blocks are the town's (passed as harmless by the neighbour checks), their signs recorded, their zones in their own places |
| A logo the same pass renews in its own place (its picture or name changed) | not modelled | **not the same in one case**: if he moved that logo's sign into the new logo's blocks, the renewal leaves the sign unrecorded and the build refuses; the command then says "The town did not finish" and the place stays saved (F4) |

Test (`swapExchangesTwoLogos`): Lunar Client's sign moved (`snapTo`, as `/data` would) to the middle of a block
Chrome's logo fills at E0L0, then `swap chrome lunar`: "Nothing was swapped: Chrome's logo cannot stand at Games, east,
front row, left. An entity occupies the gate's place. Move it away, then retry."; the file's bytes, records, zones,
blocks and the sign's place are unchanged; the sign is put back. "Fails without it": from reading (the check exempted
the sign, the take-down left it and dropped its record, and the build refused after both logos came down).

### Point 4 (SHOULD 4): arriving where nothing is loaded yet

Measured in the server test (`goPutsHimInFrontOfHisAppsDoors`, `/go far` to `N40L0`, new ground, 573 blocks out):

| Code | `/go` on the server thread | Then |
|---|---|---|
| Step 1's (read in the command) | **416.1 ms** (build 1; the spots touch 1 chunk) | every spot blocked, chunks read back from disk: 13.7 ms |
| Deferred (now), build 2 | 1.06 ms | arrived 515.45 ms (2 ticks) later; every spot blocked: 1.57 ms, its line 12.89 ms (2 ticks) later |
| Deferred (now), build 4 | 1.35 ms | arrived 414.53 ms (2 ticks) later, in which one tick took 399.27 ms (the longest gap between ticks 6.83 ms); every spot blocked: 2.37 ms, its line 12.07 ms later, longest tick 6.28 ms |

416 ms is over the 50 ms bound, so the check is no longer made in the command (`world/Arrivals`): where every
spot's chunk is loaded, it checks and moves him at once, as before. Otherwise it reads nothing: the game's own ticket
for teleports (`TicketType.PORTAL`, radius 0) loads the chunks the spots' boxes touch (at most four), each server tick
looks whether they are loaded, then checks the spots (reading loaded chunks only), moves him and says the arrival's line,
or says the blocked line. It gives up after 200 ticks and 10 s, both ("… did not load in time, so you stay where you
are. Try again in a moment."). The tickets go when he arrives, when it gives up, when he leaves, and when another move of
the mod (`/home`, H, another `/go`) comes first. The command says nothing while it loads. A `/go` to a hand-made zone
does the same with its one exit.

What the numbers say: the check itself no longer holds the server thread. The game's own loading of new ground through
the ticket took one server tick of about 400 ms in the test world, which any teleport there would cause too (the
teleport loads the same chunks); read back from disk it is a few ms. Whether new ground in his flat home (a flat world)
is as slow is not measured. HUB.md (2.6, `/go`), `mod/README.md` (Getting around) and 1-2 above now say what the code
does.

### Point 5 (SHOULD 5): test tickets released however a test ends

`GettingAroundGameTests.waitFor`: every wait of these tests passes when its condition holds; after `LOAD_TICKS` ticks or
120 s on the clock, whichever comes first, it runs its cleanup (the host and the test's logos, where it has them),
releases the test's tickets and fails. The framework's bound (`MAX_TICKS = 4 × LOAD_TICKS + 1,000`, a test waits at
most four times) is never reached first, so a timeout of the framework, which runs none of the test's code, cannot
happen. Failures in the steps go through `guarded` (tickets released) as before; success releases them in the last
step. "Fails without it": from reading; no run forced a timeout.

### Point 6 (SHOULD 6): frozen and refused, at the command

In `swapExchangesTwoLogos`, with Notes' logo taken down first: the town frozen (the town file's own flag), then the town
file refused (as when `town.dat` does not fit: the hub holds no record of it). Both by reflection on `HubData`'s own
fields, within one tick and put back in `finally`, since the game has no call that freezes or refuses a town (F6).
Typed `/aresos app swap chrome discord` and `/aresos app move lunar west`: the town's own line (`TownKeeper.frozen`,
`TownKeeper.refused`), nothing else. `/go chrome` (its logo stands in its recorded place): he stands at its exit point;
in the refused town through its doorway in `zones.dat`. `/go notes` (no logo): "Notes's logo does not stand in the town,
and the town is frozen: /aresos hub trust lets it build again." and "… and the town's file does not fit this world, so
the town builds nothing here.". The apps file's bytes, the records, the zones and every block within 40 are unchanged;
Notes is built again afterwards. These tests pass with the old code too: they pin the behaviour against a later bypass.

### What ran

From the worktree root, 2026-11-14:

| Run | Exit | What it printed |
|---|---|---|
| `mod/dev/build.sh` (points 1 to 3, tests of 3 to 6, first measurement) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 2m 1s`; the cold `/go`: 416.1 ms |
| `mod/dev/build.sh` (point 4 deferred) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 2m 3s` |
| `mod/dev/build.sh` (a tick timer added to the test) | 1 | `BUILD FAILED in 19s`: package 36's `TownGameTests.keepingNear` failed at "A newcomer: []" and took the test server down; my tests had not run yet (see Not verified) |
| `mod/dev/build.sh` (the same code, final) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 1m 33s` |
| `mod/dev/client-test.sh` (final code) | 0 | `BUILD SUCCESSFUL in 9m 34s`; 16 "client checks passed" lines (09c, 09d, 09b, 09, 08, 07b, 07, 01c, 04, 04c, 32, 33, 34, 35, 36, 37), "36 pictures taken", "37 pictures taken"; "Client tests ended with exit code 0 after 9 min 35 s (intel: Mesa Intel(R) Iris(R) Xe Graphics (RPL-P) (Intel))" |
| `mod/dev/build.sh` (final code, again) | 0 | "All 98 required tests passed :)", `BUILD SUCCESSFUL in 1m 30s`; point 4: the command 1.13 ms, arrived 384.65 ms (2 ticks) later, the longest tick 373.64 ms; every spot blocked: 1.07 ms, its line 7.62 ms later, the longest tick 5.04 ms |

The test count stays 98: the new checks are steps inside the four existing tests of this package. This package's
pictures from the client run were compared with the committed ones: `0076` to `0081` differ in 0 pixels (by more than
24 in a channel), `0082` in 597 (the torch's flame), so none is committed again; every tracked picture was put back and
the run's untracked pictures removed.

### Not verified (review fixes 1)

- The cold `/go` in his own flat home: measured only in the server test world (new ground there took one tick of about
  400 ms to load through the ticket; read back from disk a few ms).
- The marks of void recovery, the spawn on joining and the respawn: by reading only; the test covers `/home`, the H
  key's server half and (through the shared teleport) `/go`. The doorway's return goes through the shared teleport;
  no test of a hand-made zone whose exit lies in its own box.
- `/go` giving up after 200 ticks and 10 s, and a `/go` dropped by `/home` while it loads: by reading.
- Every "fails without it" above is from reading; none of the new tests was run against the old code.
- Package 36's `TownGameTests.keepingNear` failed once ("A newcomer: []", build 3) and passed in builds 1, 2, 4 and the final one
  with the same main code. Its cause was not found; this round changed nothing it calls except through
  `GateBuilder.Gone.NONE`, which reads the world as before. Worth a look if it comes back.
- The residual case of point 3's list: a logo the same pass renews in its own place, whose sign he moved into a new
  logo's blocks (F4).

### JUDGMENT-CALL (review fixes 1)

- **F1. Only the mod's own teleports mark the arrival.** Vanilla moves (`/tp`, portals, ender pearls, the End's exit)
  still count as walking, as the brief lists the mod's teleports. Rejected: marking every teleport of the game (a mixin
  on the player's teleport), which would also cover his own `/tp` into a doorway on purpose. Changing it later is one
  mixin.
- **F2. The catalogue's token is the list object itself**, compared under the lock every update takes. An update that
  produces an equal list still refuses the command once (he types it again). Rejected: a revision number, which every
  writer of the list would have to remember to raise.
- **F3. The lock covers the comparison and the save, not the pass.** The pass works on the snapshot (the same object the
  checks used), so a refresh that lands during the pass cannot change what it does; the town follows that refresh in its
  next pass. Rejected: holding the catalogue's lock across block changes, which would stall the helper's thread and
  nest locks (`takeIn` calls into My apps under it).
- **F4. A renewal in the same pass is not modelled** (point 3's list, last row). Modelling it needs the keeper's private
  "changed" rule and its rebuild outcome in the check; the case needs a sign he moved from one logo into another's new
  place, and its outcome is the existing "The town did not finish" line with the place saved, nothing lost.
- **F5. Deferred `/go`:** the ticket is `PORTAL` (the game's own ticket for teleports; there is no other in 26.2 but the
  ender pearl's), radius 0, only the chunks the spots touch; nothing is said while it loads (he is moved within a few
  ticks); it gives up after 200 ticks and 10 s together, so a paused game does not count and a fast test server does
  not give up early; another move of the mod drops it.
- **F6. Tests freeze and refuse the server's town by reflection** on `HubData`'s own fields (`town.frozen`, `refusal`,
  the town file), inside one tick and put back in `finally`; `TownKeeper.frozen` is public now so the tests compare the
  exact line. Rejected: a test-only freeze method in the main code.
- **F7. The waits' clock bound is 120 s**, not the brief's example of 60 s: in step 2 a town on new ground took over
  8 s to load while another builder's Gradle ran, and a bound too short fails a test that would pass.
