# 36: The town builds itself: report

Brief: `briefs/36-town.md`. Built in four steps by Claude agents: steps 1 to 3 on Opus 5.5 (places, records, keeping in
step, roads, rebuild), step 4 on Fable 5.2 (the pictures, the tuning, the docs). This file is the report: a Claude
builder's file tool cannot create `REPORT.md`, so the orchestrator renames it.

## Done

- **One notion of a group** (`catalogue/AppGroup`): which group an app belongs to (HUB.md 2.2, or the group he chose by
  hand) and everything about a group (title, colour, concrete, direction, letter, key). `hub/HubLayout.Group` and
  `zone/GateGroup` are gone; a hand-built gate takes its doormat and plain front from the app's real group.
- **Places** (`hub/Place`): `N0L0` and back, a group's places nearest first (rows 0 to 63), from a place to the gate's
  plan (HUB.md 3.2). **Who stands where** (`hub/Assignment`): a pure function from his apps, their saved places and the
  blocked places to an assignment; nothing that has a place moves.
- **The logo's picture** comes from `AppIcons` (his own icon path first, otherwise the helper's picture within its limits).
- **Saved with the apps:** `place` and `group` as optional fields of schema 4 (`AppsConfig.spots`, `AresOs.saveSpots`).
  **Saved with the world:** the standing logos in `data/aresos/town.dat` (`HubData.Logo`: app, place, the hash of the
  blocks, the converter's version, the name and short name on the sign, the zone, every block placed); `hub.dat` keeps
  package 32's shape.
- **One function for every block the hub places or removes** (`zone/Placing`), used by the pad, the roads and the gates.
- **The town** (`hub/Town`, `hub/TownKeeper`): one pass compares what should stand with what stands, takes down, builds,
  renews, saves the places, paves the roads on and writes the counts; it runs when the host enters, when a complete
  program list arrives and when My apps changes, retries every 5 seconds while a place or a road is not loaded, and
  says its lines to the host (`hub/TownLines`: one line for more than five changes).
- **Protection:** the town's blocks like the pad's in Live mode, with a refusal that names the logo; explosions never
  break a logo. **`/aresos hub rebuild`** (`hub/HubCommands`). `/aresos zone remove` and `logo remove` leave the town alone.
- **Step 4:** `TownPicturesClientGameTest` (last in the list) and thirteen pictures; two things tuned from the pictures
  (below); `mod/README.md` ("The town"), `README.md`'s status line, HUB.md's corrections.

### What step 4 tuned, and why

1. **The count on a group name was cut off.** In the first pictures "SYSTEM & TOOLS · 2" touched the front logo and
   "SYSTEM & TOOLS · 14" read "· 1" from the pad. With its count a name is up to 103 text pixels wide: 7.7 blocks at
   scale 3, in the 7 blocks between the two front logos, and it hangs in the logos' front layer. `HubLayout.NAME_SCALE`
   is now 2.5 (6.4 blocks). A name that an earlier version built takes the new scale when its count is written
   (`mixin/DisplayAccess`, one more private setter). `HubLayoutTest` and `FlatHomeGameTests` pinned 3 and now pin 2.5.
2. **A new program got two lines that both begin "Spotify is new":** My apps' ("… is new and joined My apps.") and the
   town's. Where the town speaks (`TownKeeper.speaks`: a flat home and a complete list) `MyAppsGame` drops its own line;
   in AresOS worlds without a town it says it as before. The pictures test checks that no "joined My apps" line is said.
3. **Only in the test** (how the pictures are taken, nothing he sees): the pictures wait until the game has loaded the
   new item icons (the first forty-apps picture had the loading bar over it); nearer cameras for three pictures; the
   name of the held item fades before the picture after a mode switch.

Looked at and left as it is: the signs (readable from the pad, none hidden), the road lines (clear from the pad and
from above), the drawn logos at arrival distance, the removal's two lines (the command's answer, then the town's), the
new app's line, which wraps by one word in Work & Media and System & Tools, and day one's five lines (JUDGMENT-CALL 3).

## Verified

All on the laptop under AresOS, 2026-11-14, through the dev scripts only.

- `mod/dev/build.sh` on the final code (the tree that became `8a4727ce`): exit 0, "All 92 required tests passed :)",
  `BUILD SUCCESSFUL in 1m 29s`. Before it in this step: twice green on the way (`in 1m 28s`, `in 1m 3s`). The unit
  test count was not read in this step (step 3: 202 run, 6 skipped, 0 failed; this step changed one expectation).
- `mod/dev/client-test.sh`, five runs:
  - run A: **exit 1** after 9 min 27 s (`BUILD FAILED in 9m 25s`). Every earlier test passed; the new test timed out
    in the test API's `waitForChunksRender`, because it entered the world at render distance 12. Cause in the test,
    fixed: the distance is raised after the world has opened, and the pictures wait for the renderer's own
    `hasRenderedAllSections`.
  - run B: exit 0, `BUILD SUCCESSFUL in 9m 5s` (9 min 6 s), 15 "client checks passed" lines and "36 pictures taken".
    The first pictures.
  - run C, **final code**: exit 0, `BUILD SUCCESSFUL in 9m 10s` (9 min 12 s). The pictures after tuning 1, committed.
  - the private run (`ARESOS_TOWN_LOOK=<scratch folder> mod/dev/client-test.sh`): exit 0, `BUILD SUCCESSFUL in 8m 32s`
    (8 min 33 s); `git status` afterwards showed nothing of it.
  - run F, **final code**: exit 0, `BUILD SUCCESSFUL in 9m 15s` (9 min 16 s), 15 "client checks passed" lines and "36
    pictures taken". Its thirteen pictures were compared with the committed ones of run C pixel by pixel (a
    difference of more than 40 of 255 counts): eleven are the same, `0064` differs in one pixel and `0065` in 62 on
    the horizon line. The committed ones stay.
- The pictures test also checks: day one's places (Chrome and Discord in row 0 north, Lunar Client at `E0L0`, Notepad
  and Terminal in row 0 south); Spotify at `W0L0` with the brief's line; after `/aresos app remove spotify` the grass
  of `W0L0` back and `WORK & MEDIA · 0`; Mail at `N1R0` with "N1L0 is blocked by something of yours, so Mail stands at
  N1R0." and his hut untouched; forty logos after 34 more programs in one list, "The town changed: 34 logos built. …",
  the counts `INTERNET · 10`, `GAMES · 8`, `SYSTEM & TOOLS · 14`, `WORK & MEDIA · 8`. So a list that arrives while he
  is in the world, which step 3 had not exercised, is exercised three times.
- Earlier steps (their notes, shortened): step 1 on GitHub (Mod run 43524445082); steps 2a to 3 `mod/dev/build.sh`
  green after each commit ("All 85", "87", "91", "92 required tests passed"); step 3 one full client pass, exit 0,
  `BUILD SUCCESSFUL in 8m 14s`.

### The pictures (`reviews/36-town/screenshots/`, 960 x 540: half his screen, the game's scale 2)

Every icon in them is the test's own drawing (a figure on a tile or a disc, or a bare shape), not a real app's icon.

| Picture | What it shows | Against the design |
|---|---|---|
| `0063_town-first-arrival` | Day one as the world opens: the two front logos, and five chat lines over the lower left | Matches section 1, plus the five lines (JUDGMENT-CALL 3) |
| `0064_town-arrival` | Chrome's logo left and Discord's right of the north road, their signs with `/chrome` and `/discord`, `INTERNET · 2` between them, the road with its light blue line | Matches. The item in his hand hides the right logo's lower corner (PLAN-GAP) |
| `0065_town-east` | Lunar Client left of the east road, `GAMES · 1`, the red line | Matches |
| `0066_town-south` | Notepad left and Terminal right of the south road, `SYSTEM & TOOLS · 2` whole between them | Matches, except that the two stand the other way round than HUB.md 3.2's table (PLAN-GAP) |
| `0067_town-west` | The purple road, `WORK & MEDIA · 0`, nothing built | Matches |
| `0068_town-join` | Spotify's logo at `W0L0` with its sign, `WORK & MEDIA · 1`, one chat line | Matches section 1's "Later" |
| `0069_town-removal` | The same view after `/aresos app remove spotify`: grass, `· 0`, the command's answer and the town's line | Matches |
| `0070_town-above-build` | Build mode, straight down from 50 blocks: the cross, five logos with their fronts and doormats | Matches "a small town in the shape of a cross" |
| `0071_town-blocked` | From the air: his hut behind Chrome's logo in `N1L0`, Mail's logo one place on at `N1R0`, the two lines | Matches 2.5 |
| `0072_town-forty-above` | Forty apps straight down: rows 0 to 2 in every group, row 3 south (its two logos touch the lower edge of the picture), his hut in the north | Matches the plan drawing |
| `0073_town-forty-from-the-air` | Forty apps from the south-east: the town as a cluster of fronts, signs over each | Matches |
| `0074_town-forty-south` | From the pad along the south road: the front two, `SYSTEM & TOOLS · 14` whole, row 1's outer logos and one sign showing beside and between | Matches 2.2: the rows behind are mostly hidden |
| `0075_town-forty-south-past-row-0` | Standing behind row 0: row 1's two inner logos large left and right, rows 2 and 3 along the road, no sign in view | Shows the design's cost: this close a sign is above the screen (PLAN-GAP) |

### The town with the real three (not in the repo)

A private run put the laptop's own icons of Chrome, Discord and Lunar Client in the fake helper's list. The two
pictures are in `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg36-real/screenshots/`
(`0063_town-arrival.png`, `0064_town-east.png`); the icons and a sheet of them are one folder up.

- **Chrome** is unmistakable from the pad: a round build, red on top, yellow right, green left, a blue middle with a
  pale ring. Two flaws: the red is red mushroom block, whose white spots show at this distance, and the white ring is
  a mix of grey stone-like blocks, so it reads grey and rough.
- **Discord** is recognisable: a dark blue front with a pale face and two eyes. The cells on the face's edge are
  light blue, grey and two amethyst blocks: a fringe that makes the face look frayed.
- **Lunar Client** is the weak one: a black front with a grey-white arch and a pale shape low on the left. The moon
  cannot be made out; it needs its sign. Its thin white lines on black average into four or five greys.
- What the converter (package 33) should do better: (1) for an icon with a plate, decide for each cell whether it is
  figure or plate and paint it in one of the icon's two or three main colours, instead of the average of what falls
  into the cell; that removes the fringe on Discord and the greys on Lunar Client; (2) prefer plain blocks over
  spotted or bricked ones of nearly the same colour (red concrete before red mushroom block, one white block for the
  whole ring). Nothing of this was changed here: the converter is not this package's.

## Not verified

- **The real app helper** (package 30, merged to `main` while this was built): every test uses the fake helper. No
  run with the laptop's real program list, and real icons were seen only for the three above.
- **Walking into a town logo's doorway in the real client.** The zone and exit are server-tested; the client tests
  walk only into hand-built gates.
- **A place or road that is not loaded, in the real client** (the 5-second retry): server-tested only; every place of
  the forty stood on loaded ground.
- **A group name of an older flat home taking scale 2.5:** the code runs on every pass, but no test builds a name at
  the old scale first.
- **"The town is built: 40 logos. /apps lists them."** in the real client: unit-tested; the client test reaches forty
  through a later list ("The town changed: …").
- His screen (1920 x 1080), his shader pack, and Windows (no helper, so no town: by reading, not by a run).
- The hosted "Mod" run for the final commits was not watched.

## Known limits

- The town needs a complete program list of this game session and runs only while the host is in the world. After a
  restart with the helper down nothing is built or taken down, and `hub rebuild` refuses.
- A new program whose first free place is on ground that is not loaded (very far out) gets no chat line until he comes
  near: in a flat home My apps no longer says its own line.
- A road or a place on ground he never visits keeps a cheap pass running every 5 seconds while he is in the world.
- Blocked is decided with a full front: next to his build a sparse logo that would just fit goes one place on.
- A logo that cannot come down (something of his hangs on it) holds its place; the app meant for that place waits.
- `/aresos logo remove here` at a town logo answers only when he stands in front of its door.
- `hub rebuild` uses the pictures read in this session; an icon file changed under the same path is read at the next
  list or change of My apps.
- A mod of packages 33 to 35 opened on this world sees the town's zones as plain zones and does not protect the
  town's blocks.
- Closer than about 14 blocks to a logo its sign is above the top of the screen at the arrival pitch.
- The kept server test world remembers a failed run (`mod/build/run/gameTest/world`); deleting it resets it.

## JUDGMENT-CALL

For the owner before merge (how it feels, or hard to undo):

1. **Group names at scale 2.5 instead of 3** (step 4). Chosen because the count must be readable from the pad and a
   text scale is the smallest change. Rejected: hanging the name one block nearer to home (it would lie over the
   logos' edges), the count on a second line (another look than `INTERNET · 2`). Changing it later: one number; names
   follow at the next pass.
2. **One line for a new program in a flat home, the town's** (step 4). Rejected: both lines (three rows of chat for
   one event), rewording the town's line (the design gives its words). Cost: one line in `MyAppsGame.tick`; the limit
   about a place that is not loaded, above.
3. **Day one says five lines** (`0063`). The orchestrator's threshold stands: up to five changes are said one by one,
   and day one on the laptop is exactly five apps, so the first arrival has seven rows of chat over the lower left for
   ten seconds. One line ("The town is built: 5 logos. /apps lists them.") would be calmer and say less. Changing it:
   `TownLines.FEW`, or a rule that a first build is always one line.
4. **The count** is the apps that have their place in the group, also one whose logo waits; an empty group says `· 0`
   (step 3). Rejected: counting only standing logos, hiding `· 0`.
5. **`hub rebuild` builds only the logos again;** the pad, roads and names stay. It refuses before a complete list
   (step 3).
6. **"A complete program list" is one that arrived in this game session,** and the town runs only while the host is in
   the world (step 2b). Rejected: trusting the apps file's last list across restarts.
7. **The logos in their own `town.dat`,** `hub.dat` in package 32's shape (the orchestrator, step 2b); `group` saved
   as the group's key; no new schema number (step 2a).
8. **A light he changed does not hold a logo up;** the refusal in Live mode names the logo (the orchestrator, step 2b).
9. **Rows end at 63;** place names have one spelling (step 1).
10. **The pictures:** 960 x 540; the render distance raised to the game's own 12 after the world opens; forty reached
    in the same world by one list of 34 more programs; four pictures more than the brief lists (the first arrival, west,
    from the air, behind row 0); `TownClientGameTest`'s four helpers opened to the new test instead of copied.
11. **Six pictures of packages 33 and 34 are committed anew** (the orchestrator's point 4). After the final run their
    differences were cut out and looked at: `0052`, `0055` and `0056` (the Apps screen) differ only by package 35's gold
    short names in the rows; `0049` and `0050` only by `/notepad` on the "No Picture" gate's sign; `0043` by that
    sign line and by the neighbouring tree gate's doormat, yellow since step 1 (the reason step 3 committed `0044`).
    Every other earlier picture went back; the renumbered copies were removed.

Smaller decisions of steps 1 to 3 (assignment rules, refresh as take down and build, rounds, the road paved on from
its last recorded block, "loaded" meaning loaded with entities) are in the code's comments and in the history of this
file (`git log -p reviews/36-town/PROGRESS.md`).

## PLAN-GAP

- **HUB.md 3.2's day-one table:** on a fresh AresOS Notepad is pinned, and pinned apps go first, so Notepad stands at
  `S0L0` and Terminal at `S0R0`. Recorded in HUB.md's corrections.
- **The item in his hand** (package 34's pixel icon as a held item) covers the lower right of the view and a corner
  of the right-hand logo in every picture from the pad. Not this package's; an empty first hotbar slot or a smaller
  held item would clear the arrival view.
- **The converter** with real icons: see "The town with the real three".
- **Signs from close by:** standing behind a row he sees the next row's logos but not their names (`0075`).
- **Many programs at once:** in AresOS worlds without a town My apps still says one line a program (34 lines for 34).
- **The test API's `waitForChunksRender`** does not end when a world is entered at render distance 12; the test
  default is 5. Later client tests that want the game's own distance must raise it after the world has opened.
- **`README.md`'s status** still says the tests "run on Windows, not in CI"; that predates the dev scripts and
  `mod.yml` and was left alone.
- The brief expected a package-35 mod to drop `place` when it saves; it keeps it (step 2a, tested).

## Try this

In the development game on AresOS with the app helper running (the orchestrator starts it):

1. On the title screen click **AresOS**, then **New AresOS world…** if a world exists, leave **Home: Flat**, create.
   You stand on the gold block and look north. Left of the road stands Chrome's logo, right of it Discord's, each with
   its name and command above it, and `INTERNET · 2` hangs between them. The chat says one line for each of your five
   apps. Turn right: Lunar Client and `GAMES · 1`. Behind you: Notepad and Terminal. To your left: `WORK & MEDIA · 0`
   and an empty road.
2. Install a program for your user (a Flatpak) while the game runs, or type `/aresos app add <id>` (Tab completes).
   Within a few seconds its logo stands in the nearest free place of its group and the chat says, for example,
   "Spotify is new. It stands in Work & Media, west. /spotify opens it."
3. Type `/aresos app remove <id>`. The logo is gone, the grass is back, the number on the group's name is one lower.
4. Hit a logo's block: "The logo of Discord is part of the town and protected. Press G for Build mode."
5. Press **G**, fly up and look down: the cross with your apps. Build something 34 blocks north of the pad, left of
   the road (behind Chrome's logo), then add another Internet program: its logo stands right of the road instead, and
   the chat says "N1L0 is blocked by something of yours, so … stands at N1R0." Your build is untouched.
6. Change a block of a logo in Build mode, then type `/aresos hub rebuild`: "The town was rebuilt from the rules: …"
   Your block is still there; because it is now in the way of that logo, the logo stands one place further out and
   the chat names the blocked place.
7. Walk into a doorway: the app opens. Close it: you stand a few steps in front of the door.

## Open questions

- JUDGMENT-CALL 3: five lines on day one, or one?
- Should the converter get the two changes named above before the town reaches the laptop? Lunar Client is the one
  logo of the three that does not read without its sign.
