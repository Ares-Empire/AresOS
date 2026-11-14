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
