# 37: Getting around the town

Empire board brief 287. Mod package. `docs/design/HUB.md`, section 6, row 6: the last piece of home screen version 1. It starts from `main` at `41927e99`, which contains package 35 (slash names, `cdfab755`) and package 36 (the town builds itself, `41927e99`), merged into this branch on 2026-11-14.

**Builders:** three steps, one fresh builder per step: Claude agents on Opus 5.5. Codex's week is at 97% and is kept for reviews (orchestrator, 2026-11-14); the rules below are decided, so the work is carrying them out. Each step ends with a commit, a push and an updated `reviews/37-getting-around/PROGRESS.md`. **Review:** a fresh reviewer that isn't a builder.

## Why

The owner (2026-11-13): "there will be a decent amount of apps and good navigation is important."

After package 36 his apps' logos stand along four roads. With forty apps the far rows are a walk of a hundred blocks, and a logo stands where the rules put it. He can't jump to one, can't jump home, and can't arrange them.

**Goal:** he types `/go steam` and stands in front of Steam's door, looking at it; one step and he is in. He presses H, or types `/home`, and stands on the pad looking north. `/apps` says where every logo stands. `/aresos app swap chrome discord` makes the two logos change places; `/aresos app move steam west` puts Steam among Work & Media, and it stays there.

## Read first

`docs/design/HUB.md`: the status block with its corrections, then 2.5, 2.6, 3.2 to 3.5. Then the code as it is on `main`:

- package 36 (`reviews/36-town/REPORT.md` with "Review fixes 1" and "Review fixes 2", and the code it names): places (`hub/Place.java`), who stands where (`hub/Assignment.java`), the town's records in `town.dat` beside `hub.dat` with their seal (`hub/HubData.java`, `hub/TownSeal.java`) and the freeze (a world opened without the town's records since its last visit: the town builds and removes nothing until `/aresos hub trust`), the one function for every block (`hub/Town.java`: `check`, `build`, `remove`), keeping the world in step (`hub/TownKeeper.java`: `run`, `ask`, `rebuild`, its pending work and the pictures it reads off the server thread through `zone/PictureReader.java`), and how places are saved (`AresOs.saveSpots`);
- package 35 (`names/`, `item/AppCommands.java`): how a typed name finds an app, the completion, `/apps`, the reserved names `home` and `go`;
- `world/HomeCommands.java` (`/aresos home`), `zone/AppZone.java` (a zone's exit point), `client/ModeSwitchClient.java` (the G key: how a key of ours is registered, sent and tested).

## Step 1: `/go`, `/home`, the H key, places in `/apps`

1. **`/go <app>`** takes any name `/open` takes for one of his apps (package 35's lookup, with its completion limited to My apps). It puts him at that logo's exit point, on the ground, looking at the door (HUB.md 3.2: the exit point and the group's outward yaw, pitch -10). It never opens the app, and arriving there must not count as walking in.
   - The target comes from the app's saved place, so it also works while the logo is not built yet because its place was not loaded; the town's pending work then builds it as he arrives.
   - In a frozen town, or one whose records file is refused, `/go` still takes him to a logo that stands in its recorded place, since it changes nothing. For an app whose logo does not stand there, one chat line says why (for a frozen town: that `/aresos hub trust` lets the town build again).
   - If his own build stands where he would arrive (the two blocks at the exit point are not free), he arrives at the nearest free spot on the way in between the exit point and the door; if there is none, nothing happens and one chat line says so. No block is ever changed for a teleport.
   - An app of his without a place (the world has no town, or every place of its group is blocked): in a world without a town, `/go` goes to the exit of the nearest zone of that app in his dimension, if he made one by hand; otherwise one chat line says that the app has no logo here.
   - A program that is not one of his apps: one chat line with the command that adds it.
2. **`/home`** does exactly what `/aresos home` does (the pad, facing north, from any dimension). `/aresos home` and `/aresos home set` stay as they are.
3. **The H key** ("Home", in the mod's key category, default H, changeable in Controls) does the same from the keyboard: only in an AresOS world, only while no screen is open, never while F3 is held. Build it the way the G key is built.
4. **`/apps`** adds where each logo stands: "Lunar Client: /lunar. Games, east, front row, left". The wording comes from one function from a place to words (group title, direction, "front row" or "row 2", "left" or "right" as he sees it walking out from home, and "2nd from the road" when `k` is over 0), which `/go`'s and step 2's chat lines use too. An app without a standing logo says why in a few words (waiting until he comes near; no free place; the town is frozen; no town in this world).

End of step 1: unit tests for the wording (the five of day one, `W1R1`, a `k` over 0); server tests for `/go` (position and facing for a day-one app and for one in a second row, an app whose place is not loaded yet, a blocked arrival, a program that is not his, a world without a town with and without a hand-made zone), `/home` from another dimension, and that arriving by `/go` opens nothing; `mod/dev/build.sh` passes; commit, push, `PROGRESS.md`.

## Step 2: `swap` and `move`

Both are all or nothing: they first check that every logo involved is loaded, that each can be taken down (nothing of his hangs on it) and that each new place can be built on. If any check fails nothing changes, in the file or in the world, and one chat line says what is in the way and what he can do ("Stand at home and try again" when a place is not loaded). When all checks pass, the saved places change first and the town is then brought in step through package 36's own function: no second way of building.

- **When they refuse before checking anything:** both change the town, so while the town is frozen or its records file is refused they refuse with the town's own line (as `hub rebuild` does), and so they do before a complete program list.
- **Pictures:** the checks plan the new logos with `Town.check` and the pictures the town already holds. A picture the town has not read yet is never read on the server thread: refuse with "try again in a moment" and ask the town to read it.
- **Timing:** the checks and the changes happen in the same server tick: save the places through `AresOs.saveSpots`, then `TownKeeper.run` (its comment already names `swap` and `move`). If that pass does anything other than what was checked (a logo that could not come down or be built), say so in one line. Say in the report how the pass and the checks are kept from disagreeing.

1. **`/aresos app swap <a> <b>`**: the two apps exchange places. If the places belong to different groups, each app also takes the other place's group as its hand-set group (`group` in the apps file, which package 36 reads); a hand-set group that equals the app's own group is removed again. Both logos come down and are built in their new places, each with its new group's doormat. One chat line names both new places.
2. **`/aresos app move <app> <north|east|south|west>`**: the app gets that group as its hand-set group (removed when it is the app's own group) and the first free place of that group that can be built on. Its old logo comes down and its old place becomes free. Moving it to the group it already stands in changes nothing and says so. One chat line names the new place.
3. **A place that still holds the town's own logo due to come down is waiting, not blocked.** Check how package 36's step handles a place that changes hands in one run, and fix it there if an app could be sent on to the next place because the old logo had not come down yet.
4. **What follows by itself, and is tested here:** the counts on the group names, the roads (a road grows with its group and is never unpaved), the group shown in `/apps` and in the Apps screen, the signs.
5. Completion: `swap` and `move` complete his apps' names, `move` the four directions.

End of step 2: server tests (a swap inside one group; a swap across two groups with doormats, counts and the saved `group`; a swap back, which leaves no hand-set group; a swap refused because his own block hangs on one logo, with file and world unchanged; a move to a free place; a move where the first place of the group is blocked by his build; a move back to its own group; a refused move when a place is not loaded); `mod/dev/build.sh` passes twice; commit, push, `PROGRESS.md`.

## Step 3: the pictures, the docs and the pull request

1. **Client game tests** with screenshots under `reviews/37-getting-around/screenshots/`, with the fake helper and drawn pictures: `/go` to an app in a second row (the door in front of him, the sign readable); the H key from there (the arrival view of the pad); `/apps` in the chat with places; the town from above before and after a swap across two groups; the chat line of a refused swap. The test goes last in the list. Look at every picture; tune only what the pictures show to be wrong, and say what and why.
2. `mod/README.md` (the commands and the key, what `swap` and `move` refuse), `README.md`'s status lines, `docs/design/HUB.md` (add to the corrections what this package found), the full report text with a "try this" note (in `PROGRESS.md` or the pull request's description if your file tool refuses `REPORT.md`), `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice on the final code, merge `origin/main`, push, `gh pr create`.

## Out of scope

A map, beacons, a Speed effect (HUB.md 5). Places chosen by hand (`/aresos app place <app> N2L1`): `swap` and `move` are the two ways in version 1. The Apps screen gets no new buttons. The OS helper. No change under `os/`.

## Already decided

- HUB.md, with its corrections. Places, groups and the wording of directions come from the functions of package 36; don't write a second copy.
- `/go` and `/home` move him and nothing else: no block changes, no app opens, no chunk is loaded by force beyond what a teleport does by itself.
- `swap` and `move` are all or nothing (the orchestrator, 2026-11-14): a half-moved town with a logo waiting somewhere unloaded is worse than one refusal with a clear line. From home the first six rows of all four groups are loaded at the default view distance.
- A swap across groups makes both apps hand-moved, so the next run of the rules leaves them where he put them.
- The known limits of packages 32 to 36 stand; don't reopen them.

## If unsure

Refuse and say why in one chat line, rather than move him into a wall or leave the town half changed.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-37-getting-around`, branch `pkg/37-getting-around`. Never merge, never push to `main`, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh` (`mod/README.md`, "On Linux"). Never pass `--force`, never run `./gradlew` directly, never open a window in the real session.
- Game tests build relative to their own plot and never force or release chunks they don't own; new client tests go last.
- The repo is public: no personal data, no Mojang assets, no real app icons or pictures made from them.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commits end with a `Co-Authored-By:` line naming the builder's own model.
