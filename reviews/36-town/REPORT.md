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
| `0063_town-first-arrival` | Day one as the world opens: the two front logos, and one chat line over the lower left, "The town is built: 5 logos. /apps lists them." (review fixes 1; five lines before) | Matches section 1, plus the line |
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
  through a later list ("The town changed: …"). Since review fixes 1 day one says "The town is built: 5 logos. /apps
  lists them." in both client tests.
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

- JUDGMENT-CALL 3 is settled by the orchestrator: a first build says one line (review fixes 1, step B, point 6).
- Should the converter get the two changes named above before the town reaches the laptop? Lunar Client is the one
  logo of the three that does not read without its sign.


## Review fixes 1

Brief: `briefs/36-review-fixes-1.md`, after `REVIEW-1.md` (gpt-6-astra, high: CHANGES-NEEDED, six FIX and three
SHOULD, all accepted). The principle: the town removes or replaces a block, entity or zone only on the strength of a
record that is provably its own and still current; when that cannot be shown it changes nothing that exists, says so
in one chat line, and builds only on free ground. Two steps by Claude agents on Opus 5.5: step A the ledger (FIX 1 to
3), step B what the town takes down, and the rest.

| Finding | What changed | Step, point | Tests |
|---|---|---|---|
| 1 FIX: a downgrade can make the town delete his replacement blocks | A seal written after every `level.dat`; an unsealed town is frozen until `/aresos hub trust` | A 1, 2 | `TownSealTest`; `theTownTrustsItsRecordsOnlyWhileTheWorldWasSavedWithThem` (the review's scenario: his block stays) |
| 2 FIX: the town file is not bound to its world and is silently replaced | A `town.dat` of another home, unreadable or failing the checks is refused and kept, never replaced; the seal holds a fingerprint of the records | A 1, 3 | the seal test (another home, unreadable, kept byte for byte; a `town.dat` from a backup: frozen) |
| 3 FIX: overlapping records on load | Every file read in goes through `add`'s checks; one overlap refuses the whole file | A 4 | `HubDataTest` (every kind of overlap, decoded from a file) |
| 4 FIX: light-state edits are not relinquished | Any change of a recorded light's state lets go of it at once | B 1 | `theTownKeepsInStepWithHisApps` (15 -> 3 -> 15, wet -> dry; no `holds` call) |
| 5 FIX: sign and zone cleanup trusts IDs | A sign is taken down only while it is a text display at the planned place with the recorded text, a zone only with the recorded ID, app, dimension and box | B 2 | `aTownLogoIsBuiltRecordedAndTakenDownThroughTheOneFunction` (an edited sign; his zone and his display with the logo's IDs) |
| 6 FIX: `/aresos logo` waits on a picture on the server thread | Read and converted on the reader thread, built in a later tick if he still stands where he did | B 3 | `PictureReaderTest`; `TownClientGameTest` |
| 7 SHOULD: a name change does not refresh the town | `app name`, `unname` and a main name that changes by itself ask for a pass | B 4 | `TownClientGameTest` (the real command and scheduler) |
| 8 SHOULD: a missing trigger zone is not repaired | Each pass puts a missing zone back where nothing else claims its space, otherwise one line | B 5 | `theTownKeepsInStepWithHisApps` |
| 9 SHOULD: persistence and lifecycle regressions | Server and client tests that save and read the town back; pending pictures dropped on server stop | A 5, B 7 | the seal test; `TownClientGameTest` (save, leave, join); `PictureReaderTest` |
| (orchestrator, JUDGMENT-CALL 3) | A first build says one line, whatever the count | B 6 | `TownLinesTest`; the keeping test; both client tests |

### Step A: the ledger

#### Done

| Commit | Point |
|---|---|
| `b3e0ee83` | 1. The seal: `data/aresos/town-seal.dat` written right after every `level.dat`, checked when the world opens |
| `747d8675` | 2. Unsealed means frozen; `/aresos hub trust` ends it |
| `439a041d` | 3. A `town.dat` that does not fit is refused and kept, never replaced |
| `d64b0878` | 4. A loaded ledger goes through `add`'s checks before any of it is used |
| `bbd7cfa1`, `851ae11f` | 5. The server test; a failed run of it leaves the kept test world usable |

##### 1. The seal (`hub/TownSeal`, `mixin/TownSealMixin`, `mixin/LastPlayedMixin`, `mixin/ServerStorageAccess`)

- **Where the mixins sit, and why there.** In 26.2 every write of `level.dat` that stamps a new `LastPlayed` goes
  through `LevelStorageSource.LevelStorageAccess.saveDataTag(WorldData, UUID)`: the server's saves
  (`MinecraftServer.saveAllChunks`; `GameTestServer` does not override it, so the test server seals too) and, through
  `saveDataTag(WorldData)`, the writes before a server runs (`Minecraft.doWorldLoad` every time a world is opened,
  `OptimizeWorldScreen`, the dedicated server's `Main`). `TownSealMixin` injects at its HEAD and RETURN.
  `LastPlayedMixin` (TAIL of the static `PrimaryLevelData.writeLastPlayed(CompoundTag)`, which `createTag`, the first
  call in `saveDataTag`, makes) captures exactly the value written. `ServerStorageAccess` exposes
  `MinecraftServer.storageSource`, so a save knows its server (registered at `SERVER_STARTING`, removed at
  `SERVER_STOPPED`). Not hooked, by design: `saveLevelData(Dynamic)` (used by 26.x's `FileFixerUpper` when a future
  Minecraft upgrades a world's file layout, and by the test to play an older mod) and `renameLevel` (keeps
  `LastPlayed`, so a renamed world stays sealed).
- **With a server** the seal is written from the town in memory: `LastPlayed`, the seed
  (`getWorldGenSettings().options().seed()`) and the fingerprint of the town's records. Order in `saveAllChunks`: the
  levels, then `level.dat` and the seal, then `town.dat` (`SavedDataStorage`). Not written while anything is frozen or
  the town file is refused, so a freeze lasts into the next visit. Before the save writes `level.dat`, the hub is read
  and checked against the old seal (`HubData.get` at HEAD).
- **Without a server** (the game writes `level.dat` as it opens a world, before the integrated server exists): a seal
  that holds just before the write is carried over to the new `LastPlayed`; a broken one stays broken.
- **When the world opens** (`HubData.open`, the first `get`): a town with logos is sealed only if the seal is there, was
  written for the `LastPlayed` that `level.dat` holds now, for this seed and for exactly these records. A world with no
  logos needs no seal. Otherwise every logo of `town.dat` is frozen.
- Outcomes: a whole-world copy or rename stays sealed; a world saved since by packages 32 to 35 or plain Minecraft, a
  `town.dat` restored from a backup or copied from another world, and **a crash between `level.dat` and the seal come
  out unsealed. The last is a false alarm on the safe side** (the town freezes; he types `/aresos hub trust`). So does
  a future Minecraft's world-layout upgrade (`FileFixerUpper`), once.

##### 2. Frozen (`HubData.frozen`/`trust`, `TownKeeper`, `HubCommands`)

- A frozen logo stays protected and its doorway works. No pass takes it down or replaces it: when its app leaves or
  stands elsewhere it stays with one line, said once a run ("The logo of Discord stays as it is: the town takes none of
  its logos down until you type /aresos hub trust."); a new picture, name or converter does not renew it; `hub
  rebuild` skips it and adds "Its 2 frozen logos stay as they are until you type /aresos hub trust." `Town.remove`
  refuses a frozen logo as a guard.
- Its place counts as taken: its own wanted app keeps it if it stays there; for every other app it is blocked, and the
  "blocked by something of yours" line leaves it out (it is the town's). No second logo is built for its app while it
  stands (the existing `stays` rule).
- The line as the host enters (`TownKeeper.notice`, on `JOIN`): "This world was saved without the town's records since
  the town last saw it, so the town leaves its 2 logos as they are. Look them over, then type /aresos hub trust."
- `/aresos hub trust`: host-only where parsed (the `hub` node's `requires`) and again when it runs. Says "The town takes
  its 2 logos as its own again: from now on it keeps them in step with your apps.", asks for a pass; the next save
  renews the seal. Refuses when nothing is frozen ("Nothing of the town is frozen: its records are its own.") and for a
  refused file (the refusal's line). Nothing else ends a freeze. `mod/README.md` explains it.

##### 3. Refused (`HubData.join`, `refusal()`)

- A `town.dat` that cannot be read, of another home than `hub.dat`'s, or that fails point 4 is never adopted and never
  replaced: nothing is put in its place in the data storage, so the game never writes over it. The hub holds no logo;
  `TownKeeper` passes, `hub rebuild`, `Town.build`/`remove` all do nothing or refuse; `speaks` is false (My apps says
  its own line again).
- The line as the host enters: "The town's file `<absolute path>/data/aresos/town.dat` does not fit this world (it was
  saved for a home at 100, 64, 0 in minecraft:overworld, and this world's home is at …), so the town builds nothing
  here and takes nothing down. To start the town afresh, close the world and move that file out of the world's
  folder."
- **How he starts afresh** (for the report, also in `mod/README.md`): close the world, move or rename
  `data/aresos/town.dat` out of the world's folder. Its old logos are then plain blocks of his, and the town builds anew
  on free ground.
- `town.dat` is read whole or not at all: the game's `SavedDataStorage` takes `resultOrPartial`, which would drop a logo
  it cannot read and leave its blocks nobody's. Any decode error is "cannot be read".

##### 4. Checks on load (`HubData.check`)

One check for `add`, the constructor with logos, and every file read in (`adopt`, used when the world opens and by
`store`): two logos of one app, in one place, on one block, with one sign ID or one zone ID; a pad or road block, or a
group name's ID, in a logo; a place name that is no place; a logo whose recorded positions (placed blocks, the ground
under its doormat, its grass) lie outside its place's box as the town plans it from the home. The first overlap is
named and refuses the whole file.

##### 5. Tests

- `TownSealTest` (unit, new, 2): sealed after a write together; no seal; another seed; a `town.dat` of fewer or more
  logos (backup, another world); `level.dat` written since without the seal (older mod, or a crash between the two
  writes); the same records read back give the same fingerprint; only a seal that holds is carried.
- `HubDataTest` (unit, 2 new): `aTownFileWithALogoItCannotReadIsNotReadInPart`;
  `aTownFileWithOverlappingRecordsIsRefusedWholeAsAddRefusesTheLogo`, every kind of overlap decoded from a town file
  and refused whole, and `add` refusing the same logo for the same reason.
- `TownGameTests.theTownTrustsItsRecordsOnlyWhileTheWorldWasSavedWithThem` (server, new, batch `town_seal`, ground
  `+21000`): a normal save (`saveAllChunks`) and the world's files read again (a `SavedDataStorage` of their own,
  `HubData.open`): sealed; a whole-world copy opened as the game opens a world (`saveDataTag(WorldData)` on an access of
  the copy, no server): the seal carried, sealed; a `hub.dat` of another home and an unreadable `town.dat`: refused,
  kept byte for byte after the copy's storage saves, a pass changes nothing, the line names the file; the review's
  scenario (a block of Discord's logo taken away and his own of the same kind put there, then `level.dat` written
  without the seal as an older mod does): frozen 2, the entering line, Discord leaves and its logo and his block stay
  with one line, Chrome's new name and picture do not renew it, Mail is built at `N1L0` and not in Discord's place, no
  "blocked" line, `hub rebuild` leaves the two; trust (said once), then Discord comes down and Chrome is renewed, his
  changed block stays, the next save renews the seal; a `town.dat` restored from the first save's backup into a copy:
  frozen; an empty town with its seal deleted: not frozen.
- **Which fail without the change.** Run: with the freeze disabled (an unsealed world trusted as before) the server
  test fails at "The older mod's world: frozen 0" (twice, `BUILD FAILED in 29s`, `in 25s`). By reading, not run:
  without the seal written at saves it fails at "No seal after a save"; without the carry-over at "The copy's seal was
  not carried"; with the old `attach` at "Another home"; without point 4's check the overlap unit test's
  `assertThrows`; with the game's partial decoding the cannot-read unit test (one logo comes back).

#### What ran in step A (all `mod/dev/build.sh` from the worktree root, on the laptop under AresOS, 2026-11-14)

| Run | Code | Result |
|---|---|---|
| 1 | point 1 | exit 0, "All 92 required tests passed :)", `BUILD SUCCESSFUL in 1m 33s`; unit 204 run, 6 skipped, 0 failed |
| 2 | point 2 | exit 0, "All 92 …", `in 1m 32s` |
| 3 | point 3, first try | exit 1, `BUILD FAILED in 35s`: `aTownLogoIsBuilt…` "The logo of Discord is frozen": a hub's own new town file was seal-checked when its `hub.dat` was stored again. Fixed: only a file read from the world is checked, once |
| 4 | point 3 | exit 0, "All 92 …", `in 1m 32s` |
| 5 | point 4 | exit 0, "All 92 …", `in 1m 33s`; `HubDataTest` 6 run, 0 failed |
| 6 | point 5 | exit 0, "All 93 required tests passed :)", `in 1m 10s` |
| 7 | freeze disabled (not committed) | exit 1, "The older mod's world: frozen 0", `BUILD FAILED in 29s` |
| 8 | point 5 | exit 1, "Day one: []", `in 26s`: run 7's failure had stopped the test server after the test's own mid-test save, so the kept test world held its town (logos, another home) and every new town was refused. Fixed in `851ae11f`; unit 206 run, 6 skipped, 0 failed |
| 9 | `851ae11f`, after deleting `mod/build/run/gameTest/world` | exit 0, "All 93 …", `in 1m 16s` |
| 10 | freeze disabled again (not committed) | exit 1, "The older mod's world: frozen 0", `in 25s` |
| 11 | `851ae11f`, same kept world as run 10 | exit 0, "All 93 required tests passed :)", `BUILD SUCCESSFUL in 1m 15s` |

`mod/dev/client-test.sh` was not run in step A; step B ran it (below).

#### Decisions step A took (JUDGMENT-CALL A1 to A7)

- JUDGMENT-CALL A1: **the seal holds a third field, the fingerprint of `town.dat`'s records** (SHA-256 of the town
  file's text form, whose keys the game sorts). The brief's seal (`LastPlayed` and seed) cannot make its own outcome
  true that "a `town.dat` restored from a backup or copied from another world" comes out unsealed: a lone `town.dat`
  swapped under an unchanged `level.dat` and seal would pass. Removing it later: one field and one comparison.
- JUDGMENT-CALL A2: **the seal is carried over when the game writes `level.dat` without a server.** 26.2 writes
  `level.dat` with a fresh `LastPlayed` every time a world is opened in the game (`Minecraft.doWorldLoad`), before the
  integrated server starts. Writing a fresh seal there would seal a world an older mod saved; writing none would freeze
  every world at every opening. So a seal that holds just before that write follows it; a broken one does not.
- JUDGMENT-CALL A3: **logos built during a frozen visit are not frozen in that visit, but are at the next one** (the
  seal is not renewed while anything is frozen, and the freeze is of the whole file). Trust once and all is sealed.
- JUDGMENT-CALL A4: **"its place does not match its recorded origin"**: the record holds no origin, so the place must
  parse and every recorded position must lie in the place's planned box. Also refused: a logo recording a pad or road
  block, or a group name's ID as its sign.
- JUDGMENT-CALL A5: **`store` (a flat home built just now) may start its town over an empty `town.dat` of another
  home**, which records nothing that stands; when a world opens, such a file is refused like any other. Nothing in the
  game reaches this (a new world has no `town.dat`); the tests do, every time they build a flat home of their own.
  `store` now also writes `town.dat` with `hub.dat`, so the two files on disk always belong together.
- JUDGMENT-CALL A6: the wording of the four lines (entering frozen, entering refused, a frozen logo that stays, trust)
  and the rebuild's extra line; the refusal line shows the file's absolute path.
- JUDGMENT-CALL A7: `/aresos hub trust` with nothing frozen is a failure line, not a silent success; it never takes a
  refused file.

#### Not verified in step A

- The real client: `Minecraft.doWorldLoad` carrying the seal as a world opens (only the same call on a copy without a
  server, in the server test), the two entering lines in chat, and `/aresos hub trust` through the real command (the
  test calls `TownKeeper.trust`, which the command calls after its host check).
- A real older mod (packages 32 to 35) on a town world: played by writing `level.dat` without the seal. A real crash
  between the two writes: modelled in the unit test. Optimize World and a dedicated server's start: same method, by
  reading.
- Windows: the seal's atomic replace (`ATOMIC_MOVE` with `REPLACE_EXISTING`), by reading.

### Step B: what the town takes down, and the rest

#### Done

| Commit | Point |
|---|---|
| `c61f892d` | 1. A light he changed is his, however he changed it |
| `1d8b2524` | 2. A sign or zone is taken down only while it is what the town made |
| `2f5a890a` | 3. `/aresos logo` never waits on a picture on the server thread |
| `f31cd51e` | 4. A name change reaches the signs |
| `96ac8af6` | 5. A missing trigger zone is put back |
| `1cfd284f` | 6. A first build says one line |
| `fa2eab56` | 7. Tests that reopen |
| `eb08de10` | 3. (test) the client test runs `/aresos logo` from the player's own source |
| (this commit) | 8. This section, HUB.md's and `mod/README.md`'s corrections |

1. **Lights** (`mixin/HubBlockChangeMixin`). The chunk-level hook that lets go of a changed block now also lets go of
   a light block on any change of its state (its level, water in it), at the moment it happens; changing it back does
   not give it back. Other blocks still let go only on a change of kind, so a mushroom block's faces, which follow the
   neighbours, stay the town's. The keeping test no longer calls `holds` (which had let go of the light when asked):
   one light of Mail's logo goes 15 -> 3 -> 15, the other wet -> dry; both leave the record by themselves and both
   stay, at level 15 and dry, when Mail leaves and its logo comes down. Without the change both would be recorded and
   taken down with the logo (by reading; not run).
2. **Signs and zones** (`GateBuilder.takeDown`, `Town.remove`, `HubData.zone`/`made`/`sign`/`town`). The sign is
   taken down only while the entity with its ID is a text display, within 0.001 blocks of the place the town plans
   for it, with the record's name and short name as the town writes them (the two texts compared in their saved form,
   colours included). The zone only while it has the recorded ID, app, dimension and box (the niche of its place) and
   no gate of its own. Anything else is his and stays; the logo's blocks still come down and its record goes.
   `HubData.town` (which `zone remove`, `zone list` and `logo remove` ask) uses the same zone check, so a zone of his
   with a recorded ID is his there too. Test: an edited sign stays while the logo's blocks and zone go; a zone of his
   with the logo's zone ID (its box, another app) and a text display of his with the sign's ID (4 blocks higher) stay
   while the logo's blocks go. Without the change the edited sign and his zone and display would be removed (by
   reading).
3. **`/aresos logo <app>`** (`zone/ZoneCommands`, new `zone/PictureReader`). The command checks the host and the app,
   hands the reading and converting of the picture to the server's picture reader and returns. Every tick
   (`END_SERVER_TICK`) the server looks at what it ordered: from a tick after the command, once the picture is in, it
   checks that the world is the same (`server.getLevel` gives the same level, he is still the same connected player
   in it), that he stands in the same block looking the same way and is still the host of an AresOS world, then plans,
   checks and builds the gate from where he stood when he typed it. Otherwise one line ("Logo refused: you moved while
   the picture of Terminal was read. Nothing was built; stand still and try again.", or "you left the world …").
   `PictureReader` is one daemon thread for the whole game and one reader a server; the town's keeper now reads through
   it too. Test: `TownClientGameTest` runs the command as the host on the server thread: it returns 1, one gate is
   ordered and none stands in that same tick; a few ticks later it stands and the success line is in the chat; it is
   taken down again; then the command with the player moved two blocks in the same tick: the "you moved" line, no gate.
   The client tests' shared `command` helper (`WalkInLogosClientGameTest`) now waits until no gate is ordered, so the
   older `/aresos logo` tests see the gate as before.
4. **Names** (`AresOs.name`, `unname`, `assignNames`). After a successful save each asks the town for a pass
   (`assignNames` only when a name actually changed). Test: `TownClientGameTest` types `/aresos app name browser web`
   and waits, calling no pass, until the town's own scheduler has renewed Chrome's logo: the sign says "Chrome" and
   "/web", "The logo of Chrome was renewed." is in the chat, the old sign is gone, four logos stand. Without the change
   the wait times out (by reading).
5. **Missing zones** (`TownKeeper.doorways`, once a pass after the rounds). For each standing logo: a zone with its ID
   that is the town's: nothing to do. A zone with its ID that is not (point 2): his, it stays, one line ("The logo of
   Spotify opens nothing: a zone of yours has its doorway's ID."). No zone with its ID: the zone the town makes for that
   place is put back if `ZoneData.conflict` finds nothing in its way (no other zone in its box or at its exit, the check
   every new zone passes), logged, no chat line; otherwise one line ("The logo of Spotify opens nothing: its doorway's
   zone is gone and a zone of yours is in its place."). The lines are said once a run. A frozen logo's zone is put
   back too: it adds and takes nothing down. Test (keeping): Spotify's zone removed comes back with the next pass,
   equal to the one the town made, silently; with a zone of his in its box the pass says the line once and his zone
   stays; once his zone is gone the next pass puts the doorway back. HUB.md's "the two files cannot disagree" is
   corrected.
6. **Day one** (`TownLines.said`). A pass that starts with no logo standing and only builds says one line, whatever the
   count: "The town is built: 5 logos. /apps lists them." ("1 logo. /apps lists it."), then any lines about his
   things; later passes keep the more-than-five rule. Tests: `TownLinesTest` (one, two with a blocked place, five,
   only lines about his things), the keeping test's first build ("The town is built: 2 logos."), and both client
   tests wait for day one's line and check that no line an app was said. `0063_town-first-arrival` changes (below).
7. **Reopening** (tests). The seal server test, after its first save, goes on from the records read back from the
   files (`HubData.store` of the reopened record): a pass on them says nothing and leaves the zones as they were; a new
   picture for Chrome renews it by the reloaded sign and zone IDs, after which one sign and one zone stand for it; the
   world is saved again for the rest of the test. The client test saves, leaves and joins the world
   (`TestWorldSaveImpl.open`, the game's own `Minecraft.doWorldLoad` path, where `level.dat` is written before the
   server starts and the seal follows it); then it types `/aresos app unname web`, waits until Chrome's sign says
   "/chrome" again, and checks: nothing frozen or refused, four logos, one zone each that is the town's, the other three
   logos' zone IDs as before the reopen (nothing built twice), the "/web" sign read back from the saved world taken
   down, and no chat line about the town's records or about new logos. **Pending pictures on server stop:**
   `PictureReader` registers `SERVER_STOPPING`: the server's reader is dropped, every read it waits for is cancelled, a
   read in progress stops after the app at hand and nothing new starts; `ZoneCommands` drops its ordered gates at the
   same moment, and a cancelled read makes the keeper do nothing. A server game test cannot stop its server, so the
   unit test `PictureReaderTest.aStoppedServerLeavesNoWork` checks the reader itself: a read blocked in its first app,
   a second read queued, then the stop: both cancelled, the second app and the queued read never read, a read asked
   after the stop never starts.

#### What ran in step B (from the worktree root, on the laptop under AresOS, 2026-11-14)

| Run | Code | Result |
|---|---|---|
| `mod/dev/build.sh` | point 1 | exit 0, "All 93 required tests passed :)", `BUILD SUCCESSFUL in 1m 38s` |
| `mod/dev/build.sh` | point 2, first try | exit 1, `BUILD FAILED in 7s`: a test variable named twice (compile error), fixed |
| `mod/dev/build.sh` | point 2 | exit 0, "All 93 …", `in 1m 41s` |
| `mod/dev/build.sh` | point 3 | exit 0, "All 93 …", `in 1m 38s`; `PictureReaderTest` 2 run, 0 failed |
| `mod/dev/build.sh` | point 4 | exit 0, "All 93 …", `in 1m 40s` |
| `mod/dev/build.sh` | point 5 | exit 0, "All 93 …", `in 1m 37s` |
| `mod/dev/build.sh` | point 6 | exit 0, "All 93 …", `in 1m 41s`; `TownLinesTest` 7 run, 0 failed |
| `mod/dev/build.sh` | point 7, first try | exit 1, "A whole-world copy: …": the reopen block renewed Chrome before the copy of the saved files was compared with the record in memory. Moved after that check |
| `mod/dev/build.sh` | point 7, second try | exit 1, `BUILD FAILED in 49s`, "A frozen logo's app left: [… The logo of Chrome opens nothing: …]": the review's scenario read `town.dat` from before the renewal back (the test had not saved since), so its Chrome record named a zone that was gone, and point 5 rightly found the renewed zone in its place. The test saves after the renewal |
| `mod/dev/build.sh` | point 7 | exit 0, "All 93 required tests passed :)", `BUILD SUCCESSFUL in 1m 14s` |
| `mod/dev/client-test.sh` | point 7 | run 1: exit 1, `BUILD FAILED in 5m 58s`: the game's JVM crashed (`SIGSEGV` in the NVIDIA driver's `libnvidia-glcore.so`) during the Nether-home test, before any test of this package. Not the code; run again |
| `mod/dev/client-test.sh` | point 7 | run 2: exit 1, `BUILD FAILED in 8m 20s`: every earlier client test passed; `TownClientGameTest` waited for "Built the gate of Terminal." in the chat, but it ran the command from the server's command source, whose answers go to the server log (the log shows the gate built and the line). Fixed in the test (`eb08de10`): the command runs from the player's own source, as when he types it |
| `mod/dev/build.sh` | `eb08de10` | exit 0, "All 93 required tests passed :)", `BUILD SUCCESSFUL in 1m 11s` |
| `mod/dev/client-test.sh` | `eb08de10` | run 3: exit 0, `BUILD SUCCESSFUL in 9m 15s` (9 min 17 s), 15 "client checks passed" lines (36's: "… /aresos logo builds in a later tick and not after he moved; a new name renews the sign; reopened, the town is sealed, builds nothing twice and takes down a sign read back from the saved world") and "36 pictures taken". After the reopen the log has no line "This world was saved without …" or "does not fit this world"; the town's lines in that test were day one's one line, Discord's removal, the rebuild, and "The logo of Chrome was renewed." twice (the name, then `unname` after the reopen) |
| `mod/dev/build.sh` | `eb08de10` and this section | exit 0, "All 93 required tests passed :)", `BUILD SUCCESSFUL in 1m 7s`; unit 209 run, 6 skipped, 0 failed |

**Pictures.** Of this package's thirteen only `0063_town-first-arrival` is committed anew: day one's chat is now the
one line "The town is built: 5 logos. /apps lists them." over the road; the logos, signs and `INTERNET · 2` are as
before. `0064` to `0075` and every picture of other packages were put back after the run (their content does not
change; the renumbered copies were removed).

#### Decisions step B took

- JUDGMENT-CALL B1: **a hand-built gate's sign is taken down while it is a text display**; its record (package 33's,
  in `zones.dat`) holds no place or text to check more. The town's signs are checked fully. Its lights keep package
  33's rule (a light at level 15 and dry when the gate is taken down goes with it): the light fix is for the town's
  record, which the brief and finding 4 name.
- JUDGMENT-CALL B2: **"what the town made" for a sign is compared in the text's saved form** (colours included) and
  its place within 0.001 blocks; for a zone also "no gate of its own".
- JUDGMENT-CALL B3: **`/aresos logo` says nothing until it has built or refused**; "where he stood" is the same block
  and the same facing, and the gate is planned from the exact position he typed it at. It checks the host and the
  AresOS world again when it builds. The reader thread is shared by the town and the command (one "AresOS pictures"
  thread for the game, as the town had one before), so a slow icon delays the other's pictures.
- JUDGMENT-CALL B4: **a restored zone is not said in the chat** (only logged); only a doorway that cannot come back is.
  A frozen logo's missing zone is put back too (it adds, takes nothing down). "Nothing else claims that space" is the
  check every new zone passes (`ZoneData.conflict`: other zones' boxes and exits). A zone of his with the logo's ID
  leaves the logo without a doorway, with its own line.
- JUDGMENT-CALL B5: **a first build is a pass that starts with no logo standing and only builds.** A town that went
  empty and gets one app back also says "The town is built: 1 logo. /apps lists it." instead of "Spotify is new. …".
  The wording for one logo ("lists it") is mine.
- JUDGMENT-CALL B6: `ZoneCommands.ordered(server)` (how many gates wait for their picture) is public, for the client
  tests' helper.

#### Not verified in step B

- A server stop while a picture is being read, in the game: the reader is unit-tested; the `SERVER_STOPPING` hooks
  (the reader, the ordered gates) by reading.
- A slow icon for `/aresos logo`: no test makes a read slow; the client test shows that the gate is built in a later
  tick than the command and not after he moved.
- "A main name that changes by itself" (`assignNames`) starting a pass: by reading; the client test covers `name` and
  `unname`.
- A zone put back, a zone of his in its place, his edited sign and reused IDs: server tests only, not in the real client.
- The two lines about a doorway that cannot come back were not seen in the real client.
