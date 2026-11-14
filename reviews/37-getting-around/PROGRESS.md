# 37: Getting around the town: progress

Brief: `briefs/37-getting-around.md`. Built in steps by fresh Claude agents (Opus 5.5). This file is kept up to date
after each step; the last step turns it into the report.

## Step 1: `/go`, `/home`, the H key, places in `/apps` (done, 2026-11-14)

Commits on `pkg/37-getting-around` (on `df82fabc`):

- `8ff8f426` 37: step 1: a place in words, and its exit point
- `be5d87bf` 37: step 1: /apps says where each logo stands
- `235794e0` 37: step 1: /go, /home and the H key
- `37: step 1: the /apps row in package 35's client test, and PROGRESS.md` (this file)

### Done

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
   - It never opens anything, never changes a block, holds no chunk. After the teleport `WalkInZones.arrived` takes
     the zones he touches as already entered, so arriving can never count as walking in (also for a hand-made zone
     whose exit lies in its own box).
6. **`/home`** (`world/GettingAround`, `world/HomeCommands.home`): runs `/aresos home`'s own path. `/aresos home`,
   `home set` and `home info` are unchanged; the teleport they share is `HomeCommands.teleport`.
7. **The H key** (`client/AresOsClient`, `world/HomeKeyPayload`, `HomeCommands.key`): "Home" in the AresOS key
   category, default H, changeable in Controls, registered and consumed like G. The client sends `aresos:go_home`
   only with a player, no screen open, the debug modifier (F3 unless rebound) not held, and in an AresOS
   singleplayer world (`acceptsAppCommands`). The server checks the host and the AresOS world again and does what
   `/aresos home` does; a refusal ("No readable AresOS home …") shows above the hotbar.

### Tests

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

### What ran (from the worktree root, 2026-11-14)

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

### Decisions (JUDGMENT-CALL)

- **1-1. `/go` looks among his apps first.** The keys are `/open`'s, but a program that is not his never hides one
  that is (`/go st` with Steam his and Stellarium not goes to Steam). Only when none of his apps matches does it look
  at the rest, to say how to add one. Rejected: `/open`'s result filtered afterwards (an exact match of a stranger
  would hide a prefix of his own).
- **1-2. Arrival checks may load a chunk.** To check the exit point of a place that is not loaded, its blocks are
  read before the teleport, which loads that chunk synchronously (the same chunk the teleport loads anyway a tick
  later). No ticket is added and nothing is held. Rejected: moving him unchecked (into a wall, against "If unsure");
  refusing for an unloaded place (against the brief's "it also works while the logo is not built yet").
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

### Not verified

- The town building a not-loaded logo as he arrives by `/go`: that is package 36's pending retry, tested there
  (`keepingFar`); here the test checks only where he arrives.
- `/go` in a frozen town and with a refused town file: by reading only (no server test; the brief's list has none).
- F3+H in the real client (the debug-modifier check is in the code; no client check, because F3+H writes to the chat
  and toggles advanced tooltips, which the next picture of that test would show).
- H with a screen open, and H in a non-AresOS world: by reading only.
- `NO_PLACE` with an app whose old saved place is blocked: the assignment keeps such a place saved, so `/apps` says
  "being built" for it while every place of its group is blocked (needs 4160 blocked places).

### For step 2

- **Place to words:** `Place.words()` (`hub/Place.java`). Use it for the lines of `swap` and `move`.
- **How `/go` finds the exit point:** `Place.exit(hub.home().dimension(), hub.home().pos())`, the exit of the
  `GatePlan` of that place with a plain front, the same point the town's zone returns him to. The arrival search is
  `GettingAround.arrival(level, place, exit)`: the exit point, then each block nearer the door up to the layer in
  front of the logo, the first one `HomeSites.isSafe` passes.
- **Which place an app has:** `Whereabouts.of(server, app, TownKeeper.complete())`; `STANDS` gives the record's
  place. After a `swap` or `move` the saved places change first and the record follows with the pass, so `/apps` and
  `/go` follow the record (where the logo really stands) until then.
- `/apps` shows the group a place belongs to, so a move across groups shows there by itself.
- The server tests own the hub record in their own batches (`go_town`, `go_no_town`); step 2's tests need batches of
  their own too. `Host.lines()` drains the chat: never call it inside a failure message (use `Host.ran`).

## Step 2: `swap` and `move` (done, 2026-11-14)

Commits on `pkg/37-getting-around` (on `daf7ee66`):

- `a6a2eb26` 37: step 2: the checks before a swap or move use the town's own functions
- `3c0323ae` 37: step 2: /aresos app swap and move
- `107970ea` 37: step 2: server tests for swap and move; step 1's Nether test leaves no home record
- `37: step 2: a longer wait for far-off chunks, and PROGRESS.md` (this file)

### Done

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

### How the checks and the pass are kept from disagreeing

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
  command.
- **If they still disagree** (something no check foresees), the command says so in one line instead of its own, and
  the pass's lines say what happened; the places stay saved and the town's pending work goes on.

### Tests

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

### What ran (from the worktree root, 2026-11-14)

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

### Decisions (JUDGMENT-CALL)

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

### Not verified

- The "town did not finish" line: no test makes the pass disagree with the checks (that would need the world to change
  between them, which one tick does not allow).
- A swap or move refused for a logo whose own place is not loaded (`Town.checkRemove` → `NotLoaded`): by reading; the
  test covers a new place not loaded and (by `Whereabouts`) an app whose place is not loaded.
- Frozen town and refused town file for swap and move: by reading (the same lines and checks as `hub rebuild`).
- The typed commands with a complete program list in a real game (the test server has none unless another test gave
  one; then the typed part with the town's line is skipped and only the "nothing matches" line is checked).
- That a reload is what registers `/aresos` on the game test server: inferred from the batch order of two runs.

### For step 3

- **Pictures to take:** the town from above before and after a swap across two groups (e.g. Chrome N0L0 with Lunar
  Client E0L0: doormats change colour, counts stay); the chat line of a refused swap (his torch on a doormat:
  "Nothing was swapped: Discord's logo at Internet, north, front row, left cannot come down. Logo could disturb
  neighboring minecraft:torch at …"). Client tests reach the town's own keeper through the typed command, which needs a
  complete program list in that client world (the fake helper gives one).
- **`mod/README.md`:** `/aresos app swap <a> <b>`, `/aresos app move <app> <north|east|south|west>`; what they refuse
  (frozen or refused town, no list yet, a logo the town is still moving or has not built, a picture not read yet, a
  logo of the town that cannot come down because something of his hangs on it, a place not loaded: "Stand at home and
  try again", a new place his build blocks for this logo); that a swap across groups and a move set the hand-set group,
  and moving back removes it.
- **`docs/design/HUB.md` corrections:** the Apps screen shows no group (the brief's point 4 assumed one); the town
  keeps icon-or-plain pictures, not per group; a town logo that cannot come down makes a swap or move refuse, while the
  town's own pass keeps the new app waiting at that place.
- Known limit: the test world is kept between runs, so a test that leaves saved data behind breaks the next run, not its
  own (2-5); `mod/dev/build.sh` twice is what catches it.
