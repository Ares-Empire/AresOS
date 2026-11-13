# 36: The town builds itself

Empire board brief 286. Mod package. `docs/design/HUB.md`, section 6, row 5: the heart of the home screen. It starts from a `main` that contains packages 32 (the flat home), 33 (the gate logo) and 34 (My apps).

**Builders:** Claude agents in four steps, one fresh builder per step (the coordinator's allocation, 2026-11-13): steps 1 to 3 on Opus 5.5 (rules and records), step 4 on Fable 5.2 (the pictures). Each step ends with a commit, a push and an updated `reviews/36-town/PROGRESS.md`. **Review:** a fresh reviewer that isn't a builder.

## Why

The owner (2026-11-13): "In the superflat world there will be the app logos built and the user can walk into them to enter the app. […] there will be a decent amount of apps and good navigation is important."

Today the flat home has its pad and four roads, a logo exists only where he stands and types `/aresos logo`, and his apps are a list. Nothing puts the logos into the world.

**Goal:** he enters the flat home and his apps' logos stand in their places along the four roads, each with its doorway and its sign: on day one Chrome and Discord left and right of the north road, Lunar Client on the east road, Terminal and Notepad on the south road. He installs a program: the next time he is in the world its logo stands in the nearest free place of its group, and a chat line says where. He removes one: its logo comes down and the grass is back. Nothing he built is ever touched; the town grows around it. `/aresos hub rebuild` builds the town again from the rules.

## Read first

`docs/design/HUB.md`: the status block with its corrections, then sections 1, 2.2 to 2.6, 3.1 to 3.6, and 5 (what was rejected). Then the code this builds on, as it is on `main`:

- `hub/HubLayout.java`, `hub/HubData.java`, `hub/FlatHub.java` and the protection hooks (package 32): the numbers, the groups' directions, `hub.dat`, the pad and roads, and how a changed block stops being the mod's;
- `zone/GatePlan.java`, `GateBuilder.java`, `GatePicture.java`, `GateGroup.java`, `Neighbors.java`, `AppZone.java`, `ZoneData.java`, `ZoneCommands.java`, `WalkInZones.java` (package 33): a gate as a plan, its refusals, its record, its removal;
- `config/` (the apps file, schema 3), `item/MyAppsGame.java`, `catalogue/AppGroup.java`, `icon/AppIcons.java` (package 34): My apps, what the system says about a program, its group, its picture;
- the reports of 32, 33 and 34 (`reviews/3[234]-*/REPORT.md`): their known limits and PLAN-GAPs name what this package must do (the helper's picture for logos, grass under gates, places that are not loaded, entities that appear a tick after their chunk).

## Step 1: places, groups and the logo's picture (no world yet)

Pure functions with unit tests; nothing is built in a world in this step.

1. **One notion of a group.** Today three places know the four groups: `catalogue/AppGroup` (which group an app belongs to, HUB.md 2.2's first-fit rule), `hub/HubLayout.Group` (direction, concrete, title, colour) and `zone/GateGroup` (the gate's own copy of the concretes, starters only). Make them one: an app's group comes from `AppGroup.of(app)`, and everything else about a group is reached from it. `GateGroup` goes; a hand-built gate (`/aresos logo`) gets its doormat and its plain front from the app's real group. Extend, don't rename: package 35 (slash names, built at the same time) calls `AppGroup` too.
2. **Places** (HUB.md 3.2, 3.3): a place is group, row, side and `k`, written `N0L0`. Functions: a place from its name and back; the places of a group in order (row, then `k`, then L before R), without end; from a place to the gate's origin block and facing, so that `GatePlan` gives exactly the blocks, niche, exit point and sign of HUB.md 3.2. The worked examples there (the five of day one and `W1R1`) are tests, and so is "places never collide" for the first six rows of all four groups (no two gates' spaces, walkways or exits overlap, and none reaches into a road or the pad).
3. **Who stands where** (HUB.md 3.3), as a pure function from "his apps with their saved places and groups, in file order, pinned first" and "which places are blocked" to an assignment: a saved place that is free and buildable is kept; otherwise the first free buildable place of its group; nothing that already has a place moves. Tests: day one; a new app; a removed app's place staying free and being taken back when it returns; a blocked place skipped; forty apps with fourteen in one group.
4. **The logo's picture comes from `AppIcons`.** `GateBuilder.picture` reads the owner's own `icon` path only. Use `AppIcons.read(app)` (the owner's path first, otherwise the helper's picture, with its limits), so Chrome, Discord and Lunar Client get their real logos once the helper names their pictures. A test with a drawn picture at a helper-style path.

End of step 1: `mod/dev/build.sh` passes; commit, push, `PROGRESS.md`.

## Step 2: the town's record and keeping the world in step

Starts once package 35 (slash names) is on `main`, because both add fields to the apps file; the orchestrator says when.

1. **Saved with the apps** (HUB.md 3.5): `place` (kept when the app leaves, so it can come back) and `group` (only when he moved it by hand; package 37 writes it, this package reads it). No new schema number: schema 3 keeps unknown optional fields; say so in the report and test that the mod of package 34 would read such a file (its parser on a fixture).
2. **Saved with the world** (`hub.dat`): the standing logos, each with its app, place, the picture's hash, the converter's version (a number in the code that changes when the picture rules change) and everything placed for it: every block as `{pos, block}`, the grass it stands on, the doormat's ground, the sign's entity ID, its zone's ID. The town's gates are recorded here and not in the zones file, so an older mod that saves the zones file can never orphan them (package 33's known limit). Their trigger zone and exit stay in `zones.dat` as today, marked as the hub's: `/aresos zone` and `/aresos logo remove` leave them alone and say that `/aresos app remove <app>` takes the logo down.
3. **One function for every block the hub places or removes** (HUB.md 3.4): it places only on untouched ground or on the mod's own blocks, records what it placed, and removes or replaces a block only while it is still the recorded one. The pad and roads of package 32 and the gates go through it; `FlatHub`'s and `GateBuilder`'s own recording paths become calls to it, with their tests still passing. A block he changed is his for good, as package 32 built it.
4. **Keeping in step** (HUB.md 3.4, its six points), run when the host enters the flat home, when a complete program list arrives, and after `/aresos app add` and `remove`:
   - only in a world created as the flat home (`hub.dat` says `flat-1`); never on an incomplete list (My apps already knows when a list is complete);
   - take down what should not stand, build what is missing, refresh what changed (the picture's hash, the converter's version, the name on the sign);
   - a place is used only if `GateBuilder` would build there without a refusal; a refused place is blocked: the app goes to the next place of its group and one chat line names the blocked place;
   - a removal that `GateBuilder` refuses (something of his hangs on the logo) leaves the logo standing, says so in one chat line, and is tried again at the next run;
   - a place that is not loaded is neither built nor taken down now: the work stays pending and is tried again every few seconds while he is in the world, and when he comes near. No chunk is loaded by force;
   - the first build places pinned apps first, then the others in file order;
   - one chat line per change, none when nothing changed: "Spotify is new. It stands in Work & Media, west. /spotify opens it." (the command part only when the app has a short name).
5. **Protection:** the town's blocks are protected in Live mode like the pad and roads, through the same record; explosions never break a logo, as package 33 has it. Signs can't be hit.

End of step 2: server tests for every point above (a fake program list, drawn pictures; build relative to the test's own plot, never force or release chunks you don't own); `mod/dev/build.sh` passes twice; commit, push, `PROGRESS.md`.

## Step 3: roads, names and rebuild

1. **Roads** grow with their group: paved from outward 3 to the farthest row in use plus 4 (HUB.md 3.2), never shorter than package 32 built them, through the one function of step 2. A road is never unpaved when a group shrinks.
2. **Group names** show the count: `INTERNET · 2`.
3. **`/aresos hub rebuild`** takes down everything the hub placed that is still its own and builds it again from the rules, every app in its saved place. What he changed or built stays. It says what it did in one line.
4. **A better picture rule re-renders by itself:** when the converter's version differs from a standing logo's, that logo is rebuilt in place at the next run.
5. **The sign's second line** shows the app's main short name with the slash (package 35's function), and follows when the name changes.
6. **A new AresOS world** gets the same town: places are saved with the apps, so the first run in a fresh flat home builds every app in its place.

End of step 3: server tests; `mod/dev/build.sh` passes twice; one full `mod/dev/client-test.sh` pass to see nothing else broke; commit, push, `PROGRESS.md`.

## Step 4: the pictures, the docs and the pull request (Fable)

1. **Client game tests** with screenshots under `reviews/36-town/screenshots/`, with the fake helper and drawn pictures: the arrival view on day one (compare with the design's first picture: two logos left and right of the north road, their signs, `INTERNET · 2` between them); the view east and south; the town from above in Build mode; a program that joins while he stands at home (the logo appears, the chat line); a removal (the logo gone, the grass back); a blocked place (his own build stays, the logo stands one place on); forty apps from above. The test goes last in the list. Look at every picture and tune only what the pictures show to be wrong (a sign that hides behind a logo, a name that can't be read), saying what and why.
2. **The real three, for your own eyes only:** with the real icons of Chrome, Discord and Lunar Client from this laptop in a scratch folder, take the arrival view and the view east, and say in the report in words how the town looks. Nothing of it enters the repo.
3. `mod/README.md` (the town, `hub rebuild`, what he can and can't change), `README.md`'s status lines, `docs/design/HUB.md` (add to the corrections what this package found), `reviews/36-town/REPORT.md` with a "try this" note, delete `PROGRESS.md`, `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice on the final code, merge `origin/main`, push, `gh pr create`.

## Out of scope

`/go`, `/home`, the H key, `swap` and `move` (package 37). The OS helper (30). Short-name rules (35). The window frame (31). No change under `os/`.

## Already decided

- HUB.md, with its corrections. The numbers of 3.1 are data in one place; a restyle changes numbers.
- The mod never destroys or changes a block or entity it did not place, and refuses rather than disturbs. When in doubt a logo is not built, and a chat line says why.
- No forced chunk loading, no Speed effect, no map, no beacons.
- The known limits of packages 32 to 34 stand; don't reopen them.

## If unsure

Leave a place empty rather than build over something, and leave a logo standing rather than disturb what hangs on it.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-36-town`, branch `pkg/36-town`. Never merge, never push to `main`, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh` (`mod/README.md`, "On Linux"). Never pass `--force`, never run `./gradlew` directly, never open a window in the real session.
- Package 35 (slash names) is built at the same time by another builder: until it is on `main`, stay out of `config/`, `item/`, `client/AppsScreen.java` and the command registration for names, and keep changes to `zone/ZoneCommands.java` and `zone/GatePlan.java` to what step 1 needs.
- The repo is public: no personal data, no Mojang assets, no real app icons or pictures made from them.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (steps 1 to 3) or `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>` (step 4).
