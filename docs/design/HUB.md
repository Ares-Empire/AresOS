# AresOS home screen, version 1: the flat hub

Design, 2026-11-13, by a Fable design agent. Nothing here is built yet.

**Status (2026-11-13).** Accepted by the orchestrator as the plan for the hub packages (briefs 32 to 37). What the owner has said so far and what was decided for him:
- His pointers of 2026-11-13 are the base (flat Overworld first, logos built from blocks with an opening at the front and not too tall, the hotbar as the taskbar, `/name` in chat; "This is not set, neither the logos nor the walk in etc. You can find better solutions but in minecraft as a homescreen").
- Logo height (section 7, question 1): he chose **12** on 2026-11-13 (board #207, with the picture of the four sizes). It stays one number (`SIZE`).
- Questions 2 and 3 of section 7 were not put to him as questions: a program he installs gets a logo by itself, and the four groups stand as designed. Both were shown to him with the design and are cheap to change (a rule and a table).
- Section 3.8 (the interface additions) was added by the orchestrator so the mod and the helper are built to one description.

**Corrections from building it (2026-11-13).** Where the packages found the text wrong or silent, the text follows the build:
- **3.6, step 2 (the plate test):** a pixel counts as visible from half opacity, not from the 12% of step 1. With 12% the glow around Lunar Client's tile counts as figure and the moon is not enlarged, against 2.3; with half, the 24 test icons give exactly the four named there (package 33).
- **Signs and group names** stand on a dark plate (three quarters black); the default plate was too pale against the noon sky. GAMES is written in a lighter red (`0xFF6257`) and WORK & MEDIA in a lighter purple (`0xC774F2`) for the same reason (packages 32 and 33).
- **The group names are the mod's.** In Build mode he can change every block, but a name cannot be removed or edited by hand in version 1; names change with the look (package 36).
- **The ground under a logo:** grass under a solid block turns to dirt after a while. A gate records the grass it stands on and puts it back when it is removed, so a freed place is "untouched grass" again for 3.3 (package 33).
- **Hand-built gates and an older mod:** a gate built with `/aresos logo` is recorded in the zones file. If an older mod (after going back to an older AresOS) saves that file, the record is lost and `logo remove` leaves the blocks. A mod of packages 33 to 35 that saves the file keeps a gate's record but drops the sign's place and text that package 36 adds (review fixes 2), so that gate's sign stays when it is removed. The town's logos are recorded in a file of their own, `town.dat`, which an older mod never rewrites (see the corrections of package 36 below; `hub.dat`, where they were planned, is rewritten by the mods of packages 32 to 35).
- **App items and chests:** an app's item is not unique. If he puts one into a chest, the mod may put a fresh one into his inventory (package 34).

**Corrections from building the town (package 36, 2026-11-14).**
- **3.5, where the standing logos are saved:** in the world's `data/aresos/town.dat` (the home block and the logos), not in `hub.dat`. A mod of packages 32 to 35 writes `hub.dat` again whenever a pad or road block changes, in the shape it knows, and would drop the logos from it. The newer mod would then no longer know what stands, take every standing logo for something of his, and build each app a second time one place on. So `hub.dat` keeps package 32's shape (look, numbers, home block, fixed things) and the logos have a file of their own that no older mod touches.
- **3.5, a logo's record** also holds the name and the short name on its sign, so a change is noticed without loading the sign. Its hash is of the 12 x 12 blocks as built, not of the icon file: an icon change that gives the same blocks rebuilds nothing, and a plain front has a hash too.
- **3.5, "marked as the hub's":** a zone is the town's while a logo's record names its ID and the zone is still the one the town made (the same app, dimension and box; review fixes 1). Nothing is added to `zones.dat`. The two files can still disagree: a mod of packages 33 to 35 sees the town's zones as plain zones, and its `zone remove` takes one away while the logo's record stays. So every pass checks each standing logo's zone: a missing one is put back as the town made it if no other zone lies in its box or at its exit; otherwise the logo stays without a doorway and one chat line names it ("The logo of Spotify opens nothing: …"). A zone of his that took the recorded ID is his and stays.
- **3.5, the apps file:** `place` and `group` are optional fields of schema 4 (package 35's schema). No new schema number was needed: package 35's parser keeps fields it does not know, also when it saves. `group`, which package 37 will write when he moves an app by hand, holds the group's key (`internet`, `games`, `work_media`, `system_tools`) and not its letter: the letter is the flat look's direction, and a group he chose must mean the same in another look.
- **3.4, when it runs:** on a complete program list that arrived in this game session (after a restart with the helper down the town waits), and only while the host is in the world, so its lines reach him. A short name that changes (`/aresos app name`, `unname`, or a name given or moved by itself) also starts a pass, so the signs follow (review fixes 1). On Windows, where nothing lists the programs, there is no town. Work for a place or a stretch of road that is not loaded is tried again every 5 seconds.
- **3.3, blocked** is decided for the place, with a full 12 x 12 front, not for the picture of the app that asks: a place is a place for every app.
- **3.4 point 6, the chat:** more than five changes in one pass are said in one line ("The town is built: 12 logos. /apps lists them.", or "The town changed: 7 logos built, 2 moved, 1 renewed, 3 taken down. /apps lists where your apps stand."); a first build of forty apps would otherwise fill the chat. `hub rebuild` always says one line. Lines about something of his in the way are said one by one. A first build (no logo stood before) is always one line, whatever the count: day one's five apps say "The town is built: 5 logos. /apps lists them." (review fixes 1; it was five lines).
- **1 and 2.4, a new program:** in a flat home the town's line ("Spotify is new. It stands in Work & Media, west. /spotify opens it.") is the only line about it. Package 34's "Spotify is new and joined My apps." is said in AresOS worlds without a town. The first pictures showed both, two lines beginning "Spotify is new" (tuned in step 4).
- **2.6, the counts:** the number is the apps that have their place in the group, also one whose logo waits for its place to load. An empty group says `· 0` once the town has run; a new flat home shows the bare names until then.
- **3.2, the group names' scale is 2.5, not 3.** With its count a name is up to 103 text pixels wide ("SYSTEM & TOOLS · 14"): 7.7 blocks at scale 3, in the 7 blocks between the two front logos. In the pictures the last digit hid inside the logo and the name read "· 1". At 2.5 it is 6.4 blocks. A name that an earlier version built takes the new scale when its count is written (tuned in step 4).
- **2.5, `hub rebuild`** builds the logos again. The pad, the roads and the names are not taken down: the same rules give the same blocks, and a road is never unpaved, also when its group shrinks.
- **2.5, his lights:** a light block he changed stays his and does not hold a logo up; the logo comes down around it. Any change of its state counts (its level, water in it), at the moment it happens, also when he changes it back later (review fixes 1).
- **3.4, what the town takes down (review fixes 1):** only on the strength of a record that is provably its own and still current; when that cannot be shown it changes nothing that exists, says so in one chat line, and builds only on free ground. A logo's sign is taken down only while it is a text display at the place the town plans for it with the text the record says, and its zone only while it has the recorded ID, app, dimension and box. A sign he edited, or an entity or zone of his that took a recorded ID, is his and stays.
- **Hand-built gates' signs (review fixes 2):** a gate built with `/aresos logo` records its sign's planned place and text in its record in `zones.dat` (an optional field). `/aresos logo remove` takes the sign down only while it is a text display at that place with that text, as the town checks its own; anything else stays and is his. A record without them (built by packages 33 to 35, or saved again by one of them, which reads the field and drops it) never takes its sign down: the gate's blocks come down, the sign stays, and the reply says it is his.
- **3.5, the seal (review fixes 1):** every time the game writes `level.dat` this mod writes `data/aresos/town-seal.dat` right after it: the `LastPlayed` just written, the world's seed and a fingerprint of `town.dat`'s records. A town with logos is trusted only when its seal matches the world as it opens. A whole-world copy or rename stays sealed; a world saved since by packages 32 to 35 or plain Minecraft, a `town.dat` restored from a backup or copied from another world, and a crash between the two writes come out unsealed (the last is a false alarm on the safe side). The seal is checked whenever the world has a seal file or `town.dat` holds logos (review fixes 2): a world with neither needs no seal, nor one whose seal and `town.dat` both show a town without logos of this home. Every other world whose seal does not hold is unsealed, also with an empty or missing `town.dat`.
- **2.5 and 3.4, frozen, and `/aresos hub trust` (review fixes 1 and 2):** an unsealed world freezes the whole town, one state and not a set of logos: a restored `town.dat` can leave out a logo that still stands, and the town cannot tell that app from a new one. Until he trusts the records the town builds no logo (also not for an app its records do not know), takes none down, renews or rebuilds none, paves no road and puts no missing zone back; `hub rebuild` refuses with the freeze's line. What stays: recorded blocks, signs and zones protected, doorways working, a light he changes leaving the record, `/apps`, and his hand-built gates. While frozen, My apps says its own line about a new app. He reads one line as he enters, also when `town.dat` holds no logo ("This world was opened without the town's records since its last visit, so the town builds and removes nothing. Look over its 2 logos, then type /aresos hub trust."). `/aresos hub trust` (host only, where it is parsed) ends the freeze: the records are taken as they are, anything of a logo they do not hold is his from then on (the town may build that app a logo of its own), and the next save renews the seal. Until then the freeze lasts across visits. Nothing else ends it.
- **3.5, a `town.dat` that does not fit (review fixes 1):** one that cannot be read, was saved for another home than `hub.dat`'s, or holds overlapping records (two logos of one app, place, block, sign or zone, or a block outside its place) is refused whole: kept as it is and never replaced, and the town builds, takes down and paves nothing in that world. One line as he enters names the file. **To start the town afresh** he closes the world and moves that file out of the world's folder. The seal beside it then no longer fits, so the town is frozen once more as he comes back and asks for trust (review fixes 2); after `/aresos hub trust` the old logos are plain blocks of his, and the town builds anew on free ground.
- **3.2, day one's table:** on a fresh AresOS Notepad is pinned, and pinned apps are placed first, so Notepad stands at `S0L0` and Terminal at `S0R0`, the other way round than the table.
- **2.2, what he reads from where:** from the pad the front row's signs are in view. Closer than about 14 blocks to a logo its sign is above the top of the screen at the arrival pitch, so behind a row he sees the next row's logos but must look up for their names.

**Corrections from getting around (package 37, 2026-11-14).**
- **2.4 and 2.6, the Apps screen shows no group.** Its rows show an icon, the name, the kind of program and the main short name; nothing in the screen reads a group (the brief assumed one). A `swap` or `move` across groups shows in `/apps`, on the road and on the counts, and nowhere in the screen. Version 1 adds nothing there (no new buttons).
- **2.6, a place in words** counts rows from 1 for him: `N0L0` is "Internet, north, front row, left", `W1R1` is "Work & Media, west, row 2, right, 2nd from the road". The place names keep counting from 0. Left and right are as he sees them walking out from home. `/apps`, `/go` and the lines of `swap` and `move` all use this one wording (`Place.words()`).
- **2.6, `/go`** puts him at the logo's exit point (3.2), the very point its doorway returns him to, looking at the door at pitch -10; arriving never counts as walking in. If his own build stands there, he arrives at the nearest free spot on the way in, never in the doorway; with none free he stays and one line says so. No block is changed and no chunk held: the checks read the arrival's blocks, which loads that one chunk a tick before the teleport would. For a place that is not loaded he arrives anyway and the town builds the logo as he comes; a place that is loaded but has no logo yet (the town is still at work) is refused with "Try again in a moment" rather than putting him in front of nothing. In a world without a town it goes to the exit of the nearest zone of that app he made by hand.
- **2.6, home:** `/home` and the H key do exactly what `/aresos home` does: his home spot, which is the pad facing north until `/aresos home set` moves it. H does nothing while a screen is open or F3 is held. `/home` and `/go` exist only for the host of an AresOS world, and only where no other mod has the name.
- **2.5, `swap` and `move` are all or nothing.** Before changing anything they check that every logo involved stands where its place is saved, that the town holds the pictures of the new logos (otherwise "try again in a moment", and the town reads the picture off the server thread), that every logo involved can be taken down, and that each new place takes its new logo once those came down; each check is the function the town's own pass then uses, in the same tick. They refuse in a frozen town, with a `town.dat` that does not fit, before the system has listed his programs, and when a place involved is not loaded ("Stand at home and try again"). From home the first six rows of every group are loaded.
- **2.5, a town logo that cannot come down** (his torch on its doormat) makes a `swap` or `move` into that place refuse. The town's own pass keeps an app that is given such a place waiting there instead (it is not blocked, it waits), so an app is never sent on to the next place because an old logo has not come down yet.
- **2.5, "it stays there":** a `move`, and a `swap` across two groups, write the app's group by hand (`group` in the apps file, 3.5); moving or swapping it back to its own group removes it again. A `move` takes the first place of the new group that the town's planning gives it, and passes by up to three places where only its own logo cannot stand (a longer name needs more room above the sign), as the pass would. A move to the group it already stands in changes nothing and says so.
- **3.6 and 3.4, the town's pictures** are the icon as read, or the fact that the app has none; a plain front is made on the spot in the colour of the group the app has now. Kept per group, as before, a group change needed a new read, and a check's read for the new group was read over by the next pass for the old one: a swap across groups of an app without an icon would have said "try again" forever.

It follows the owner's pointers of 2026-11-13: a flat Overworld first, app logos built from blocks that he walks into, the hotbar as the taskbar, `/name` in chat, logos that are not too tall and have an opening at the front. It replaces the Nether home of [DESIGN.md](DESIGN.md) as the first home. The Nether can come back later as a second look that uses the same rules.

Drawings (my own, no app icons):
- [day one](../../reviews/hub-design-v1/plan-05.png), [40 apps](../../reviews/hub-design-v1/plan-40.png), [100 apps](../../reviews/hub-design-v1/plan-100.png)
- [the names of the places](../../reviews/hub-design-v1/slots.png)
- [the logo](../../reviews/hub-design-v1/gate.png)
- [the layouts that were compared](../../reviews/hub-design-v1/concepts.png)

Pictures made from real app icons were used to decide, but they are not in this repo.

**How the numbers were made.** One script turned 24 real icons from the laptop into block pictures and drew the world from the player's eyes (1.62 blocks up, field of view 70, a 1920 x 1080 screen). A second script laid out each plan and measured the walk from the home spot to every doorway, around the logos in the way. Speeds: walking 4.3 blocks a second, sprinting 5.6, sprint-jumping 7.1. Nothing was run in Minecraft. Block colours for the new blocks are close guesses; section 2.3 says what the builder must measure.

---

## 1. What he will see

He switches the laptop on. The Mojang logo, then the world.

He stands on a small dark stone pad with one gold block under his feet. Flat green grass to the horizon. It is noon and the sky is clear. It never rains, it never gets dark, and no animal or monster ever appears.

A dark road with a light blue line down its middle runs straight ahead, north. Left and right of it, twenty steps away, stand two builds made of blocks, each twelve blocks tall: on the left Chrome's red, yellow and green ring, on the right Discord's white face on a dark blue front. Each has a dark doorway at the bottom. Above each floats a sign with its name, and under the name its short name: `/chrome`, `/dc`. Between the two, over the road, hangs the word INTERNET.

He turns right. A road with a red line runs east. Beside it stands a black front with a moon: Lunar Client, `/lunar`. The word over this road is GAMES. Behind him a road with a yellow line runs south, with Terminal and Notepad: SYSTEM & TOOLS. To his left a road with a purple line runs west. WORK & MEDIA hangs there, and nothing stands on it yet.

**Opening Discord, three ways.**
1. **Hotbar.** With Discord pinned, he selects it in the hotbar and right-clicks. Discord opens on top of the game. This is the taskbar: nine apps, no walking.
2. **Walking.** He runs at the dark blue front and through its doorway. It takes under four seconds. A sound, a puff of purple particles, and Discord opens.
3. **Typing.** He presses T and types `/dc`. Discord opens.

**Coming back.** He closes Discord. He is in the world again. After the hotbar or `/dc` he stands exactly where he stood. After the doorway he stands a few steps in front of it, looking at the door.

**Later.** He installs Spotify. The next time he is in the world, a line in the chat says: "Spotify is new. It stands in Work & Media, west. `/spotify` opens it." A new build stands on the purple road, the first one there. Nothing else has moved.

With forty apps the four roads have grown. Along each road the logos stand in rows, left and right, and every one faces him as he walks out from home. `/go steam` puts him in front of Steam's door. The H key or `/home` brings him back to the pad.

G switches to Build mode. He flies up and sees the whole thing: a small town in the shape of a cross, with his apps as its houses.

---

## 2. The decisions

### 2.1 The flat world

| What | Decision |
|---|---|
| Kind | A flat Overworld. The AresOS button creates it as the save `AresHub`, as today. The create screen gets a choice "Home: Flat / Nether" with Flat first; the seed field shows only for Nether. |
| Layers, bottom to top | 1 bedrock (y -64), 123 stone (y -63 to 59), 3 dirt (y 60 to 62), 1 grass block (y 63). As a preset string: `minecraft:bedrock,123*minecraft:stone,3*minecraft:dirt,minecraft:grass_block;minecraft:plains`. |
| Biome | Plains, everywhere. |
| Structures and features | None. No villages, no lakes, no ores, no trees. |
| Seed | 0. It changes nothing in a flat world. |
| Mode and difficulty | Survival (Live mode), normal difficulty, cheats off. As the Nether home does today. |
| Game rules | The ones the Nether home already sets (no mob spawning, no fire spread, no mob griefing, keep inventory, no phantoms, patrols or traders). Two more: the day cycle is off with the time set to noon (6000), and the weather cycle is off with clear weather. In 26.2 these rules should be called `advance_time` and `advance_weather`; the builder checks the names. |
| Home spot | His feet are in block (0, 64, 0): position x 0.5, y 64, z 0.5. He looks north (yaw 180) and slightly up (pitch -8). The world spawn is set to the same block. |

Reasons:
- **Deep ground.** A flat world cannot be given more layers later; chunks that already exist keep theirs. 127 blocks of ground cost nothing and leave room for cellars, ponds or a lava pit when he gives the world his own look. The surface is at the usual Overworld height, so clouds and the horizon look normal.
- **Noon.** With his shader pack the sun then stands overhead and lights all four sides the same. Without shaders the sun's place does not change how blocks look.
- **No mobs by rule, not by biome.** Plains is the plain Overworld he asked for. Later companions are mobs that are put there on purpose, which this does not block. The builder tests that the world is still empty after ten minutes; slimes are the usual pest in flat worlds.
- **Looking slightly up.** At pitch -8 the two front logos and their signs sit in the middle of the screen. Looking level, the signs touch the top edge.

### 2.2 Where the logos go, and how he finds one

**Decision: four avenues, and rows of logos that face home.**

- Four straight avenues leave the home pad: north, east, south, west. Each belongs to one group of apps and has its colour.

  | Direction | Group | Colour | What goes there (from the program's `Categories`) |
  |---|---|---|---|
  | North, straight ahead | Internet | light blue | `Network` |
  | East, to his right | Games | red | `Game` |
  | West, to his left | Work & Media | purple | `Office`, `Development`, `Education`, `Science`, `Graphics`, `AudioVideo`, `Audio`, `Video` |
  | South, behind him | System & Tools | yellow | everything else (`System`, `Settings`, `Utility`, or nothing) |

  The first rule that fits wins, in this order: `Game`, then `Network`, then the Work & Media list, then the rest. So Steam (`Network;FileTransfer;Game`) is a game. The three starter apps are fixed: `browser` north, `terminal` and `notepad` south.

- Along each avenue the logos stand in rows, left and right of the road. Every logo faces home. Row 0 has one logo on each side. Row 1 has two on each side, row 2 three, and so on. Seen from above, each group is a wedge that widens as it goes out, and the four wedges make a cross.
- A logo is 12 blocks wide. Logos in a row stand 2 blocks apart. Rows are 14 blocks apart.
- Every logo has a fixed place with a name, for example `N0L0`: north, row 0, left of the road, first from the road. A new app takes the nearest free place of its group. Nothing else ever moves by itself.

How far it is (doorway to home, measured around the logos in the way):

| Row | Front of the row, blocks from home | Logos per group | All four groups, up to this row | Blocks to the door | Walking | Sprinting | Sprint-jumping |
|---|---|---|---|---|---|---|---|
| 0 | 20 | 2 | 8 | 21 | 4.9 s | 3.7 s | 2.9 s |
| 1 | 34 | 4 | 24 | 36 to 41 | 8.3 to 9.4 s | 6.4 to 7.2 s | 5.0 to 5.7 s |
| 2 | 48 | 6 | 48 | 50 to 60 | 11.5 to 14.0 s | 8.8 to 10.7 s | 7.0 to 8.5 s |
| 3 | 62 | 8 | 80 | 64 to 80 | 14.7 to 18.5 s | 11.3 to 14.3 s | 8.9 to 11.2 s |
| 4 | 76 | 10 | 120 | 78 to 100 | 18.0 to 23.1 s | 13.8 to 17.8 s | 10.9 to 14.0 s |
| 5 | 90 | 12 | 168 | 92 to 115 | 21.2 to 26.6 s | 16.3 to 20.4 s | 12.8 to 16.1 s |

For real mixes of apps, with System & Tools always the biggest group:

| Apps | Rows in use | Farthest door | Sprinting there |
|---|---|---|---|
| 3 (today: Chrome, Terminal, Notepad) | 0 | 21 blocks | 3.7 s |
| 5 (day one: plus Discord and Lunar Client) | 0 | 21 blocks | 3.7 s |
| 9 | 0 and 1 | 36 blocks | 6.4 s |
| 20 | 0 to 2 | 50 blocks | 8.8 s |
| 40, 14 of them in one group | 0 to 3 | 64 blocks | 11.3 s |
| 100, 34 of them in one group | 0 to 5 | 100 blocks | 17.8 s |

The first nine apps are on average 24 blocks from home: 4.3 seconds sprinting.

**What each way in is for.**
- **The hotbar** is for the nine apps he uses all the time. Right-click, no walking, no typing. A pinned app costs no seconds.
- **`/name`** is for when he knows what he wants. About two seconds of typing, from anywhere.
- **The world** is the home screen itself, like icons on a desktop. It is where all his apps stand, where he looks around, and where he finds the one whose name he forgot. It is the slow way on purpose; 4 seconds to the front row and about 11 to the farthest of forty is the price of logos big enough to recognise.

**What he sees and reads from where he stands.**
- At home he sees the front logos, up to 8, by turning once. Two fit on the screen at a time. Each is about 475 pixels wide and tall on a 1080p screen, a quarter of the screen's width. They fill the view from 10 to 38 degrees left and right of the road.
- The rows behind are hidden by the row in front. That is the cost of this plan (see section 5 for the plans that show more). He sees a row when he has passed the one before it: then it faces him, left and right of the road.
- A sign's letters are 0.8 blocks tall. They are easy to read at 20 blocks and can still be read at about 60, which is three rows away.

**Why this plan.** Six plans were compared. Four of them were laid out for 5, 9, 20, 40 and 100 apps and measured the same way; section 5 has all the numbers and [this drawing](../../reviews/hub-design-v1/concepts.png) shows those four at 40. One street is the simplest but the fortieth logo is 277 blocks away. One ring shows everything but puts every logo 80 to 96 blocks away and has to be torn down and rebuilt each time it grows. A plaza with four streets of shop fronts is close to the owner's first idea of a path, but a street only grows in length (101 blocks at 40 apps, 241 at 100) and its logos are seen edge-on. The chosen plan keeps the path: the avenues are the paths he pictured. It turns the logos to face the walker, and it lets each group grow sideways as well as outward, so the walk grows with the square root of the number of apps instead of with the number itself.

**No Speed effect in version 1.** The mod could give Speed II in the hub; that makes everything 1.4 times faster (front row 2.7 s, farthest of forty 8.1 s). It also widens the field of view all the time, which changes how the world feels. It is one number to switch on later.

### 2.3 The logo itself

**Decision: a "gate". The icon as a block build 12 wide, 12 tall and 3 thick, standing on the ground, with a doorway at the bottom middle.** See [the drawing](../../reviews/hub-design-v1/gate.png).

- **Size.** One size for all: 12 x 12. This is the smallest size at which Chrome, Discord and Lunar Client were all still recognisable in the pictures. At 10 Lunar turns to mush. At 14 and 16 they are clearer but taller. Twelve blocks is under seven player heights, about a tall tree. Today's builder makes walls up to 32 tall.
- **Upright, not on the floor.** A logo lying on the ground is a thin stripe from eye height: one that is 12 deep and starts 8 blocks ahead covers 7 degrees of height against 46 of width.
- **Shape.** The build has the icon's own outline: a round icon gives a round build. Each of the 12 x 12 columns is 3 blocks deep and one kind of block, so the logo is a solid thing with coloured sides, not a thin sheet. From behind he sees the same picture mirrored.
- **Figure on a plate.** Many icons are a small figure on a plain plate (Discord's face on its blue disc, Lunar's moon on its black tile). At 12 blocks the plate would eat the pixels. So if the icon's rim is one colour, the figure is enlarged and the plate's colour fills the whole 12 x 12. Discord becomes a dark blue front with a big white face. Tested on 24 icons: it enlarged Discord, Lunar Client, Haruna and ProtonPlus and left the other 20 alone. The exact test is in section 3.6.
- **Doorway.** 2 wide, 3 high, 2 deep, always in the bottom middle. It is cut out of the picture: 6 of the 144 cells. The block at the back of the niche is black concrete. If the icon has no blocks beside or above the doorway, black concrete fills in the two posts and the bar over the door, so there is always a real door to walk into.
- **Trigger.** The niche itself, and nothing else. Stepping into it opens the app. Walking past a logo, or along its front, does nothing. Today the whole front of a wall is the trigger.
- **Exit.** When the app closes he stands on the doorway's centre line, 5.5 blocks in front of the logo's front face, looking at the door.
- **Name.** One text display floats above the logo: the app's name in white, and on a second line its main short name with the slash, in gold. It always turns to face him and it is as bright at night as by day.
- **Doormat.** The two floor blocks under the niche and the two rows in front of it are concrete in the group's colour. It marks the door and tells him which group he is in.
- **Night.** There is no night in version 1. If he ever turns the day cycle on, two hidden vanilla `light` blocks in front of each logo keep it lit without lamps. They are built from the start, so nothing changes later.
- **Loose pixels.** No frame and no backing wall are needed. The 3-block depth makes every part a solid piece, plate icons become a full front, and averaging down to 12 x 12 removes thin bits: none of the 24 test icons was left with a single loose cell. A cell that touches nothing would be dropped (section 3.6).
- **No icon.** If a program has no readable icon, its gate is a plain front in the group's colour. The sign says what it is.

**The palette is not good enough as it is. Add 12 blocks, and compare colours differently.**
- With today's 48 blocks, Chrome's red comes out orange, Spotify's green comes out cyan, and some light greys come out pinkish (white terracotta is the nearest thing).
- Add: `red_mushroom_block`, `emerald_block`, `lapis_block`, `amethyst_block`, `snow_block`, `iron_block`, `polished_diorite`, `smooth_stone`, `smooth_sandstone`, `honeycomb_block`, `prismarine_bricks`, `blue_ice`. All are full, plain blocks that do not fall, burn or change. In the test (the 24 icons at 12 x 12, plus 38 well-known brand colours), 31% of the cells picked one of these twelve, and the average colour error fell by 14%.
- Pick the nearest block in the Oklab colour space with lightness counted half (section 3.6). Today's plain RGB distance prefers the right brightness over the right colour, which is how red became orange.
- The builder measures each new block's average colour from the game's own textures on his machine and writes only the numbers into the code, as was done for the 48. No texture enters the repo.
- No vanilla block is Discord's blue-purple. Discord comes out dark blue. The face makes it Discord.

Reasons: the owner asked for built logos that are not too tall and have an opening at the front. The gate is that, and it is still made from the icon by the mod alone. The doorway as the trigger fixes a real fault of the wall: with walls in rows he would open apps by brushing past them.

### 2.4 Which apps get a logo

**Decision: one list, "My apps". It decides the logos, the inventory, the hotbar and the short commands. "All programs" is the full list he picks from.**

| | My apps | All programs |
|---|---|---|
| What it is | The apps he cares about. Roughly 5 to 40. | Everything the system lists. 59 on the laptop today, up to about 200. |
| A logo in the world | Yes, each one. | No. |
| An item in the inventory | Yes. The inventory holds My apps and nothing else. | No. |
| Hotbar | He pins from My apps. Pinning a program makes it one of his. | |
| `/name` | Yes: `/chrome`, `/dc`. | `/open <name>` opens any of them. |
| Where he sees the list | His inventory, the plaza, `/apps`. | E, then "Apps…": a list with a search box. |

**Day one, without him doing anything.** My apps holds:
1. the starter apps from the image's reviewed list (`browser`, `terminal`, `notepad`), and
2. what he installed himself: programs from his own folder and Flatpaks installed for his user.

On the laptop today that gives exactly five: Chrome, Terminal, Notepad, Lunar Client, Discord. Everything else (settings tools, KDE utilities, the Flatpaks Bazzite ships) stays in All programs.

**After day one.** A program that newly appears and did not come with the system image is added to My apps by itself: he installed it, so he wants it. A chat line says so and names its place and its command. Programs that arrive with a new AresOS image are never added by themselves.

**Adding one.** E, "Apps…", click the program. Three actions; typing a few letters in the search box narrows the list. The program becomes his: its item lands in the first free inventory slot, its logo is built, the chat says where. The screen stays open so he can add more. Or one line: `/aresos app add steam`.

**Removing one.** E, "Apps…", right-click it. Three actions. Its item leaves the inventory, its logo comes down, its commands go. It stays in All programs and remembers its place, so adding it again puts it back where it stood. Or: `/aresos app remove steam`.

**The Apps screen.** A search box on top. Then "My apps", then "All programs" by name. Each row shows the icon, the name and the short name. The search looks in the name, the short names, and the entry's `GenericName` and `Keywords`, so "mail" or "pdf" finds the right program. Left-click on one of his apps picks up its item, as today, to pin it.

**Dropping an item** (Q) never removes an app. Removing is a right-click in the Apps screen or the command, so it cannot happen by accident.

**More than fits.** The inventory has 27 slots beside the hotbar. If he ever has more apps than that, the rest have no item but keep their logo, their command and their row in the Apps screen.

Reasons: one notion is easier to live with than three. "What is in my inventory is mine, and it has a house" is something Minecraft already teaches. The default is small because most of the 59 entries on the laptop are system tools he will never look for in the plaza, and three clicks add anything.

### 2.5 Change

| What happens | What the mod does |
|---|---|
| He installs a program | It joins My apps (2.4). It gets the nearest free place of its group, its logo is built, its short name is saved. One chat line. Nothing else moves. |
| A program is removed from the system | Its logo comes down and its place becomes free. Its entry, its pins and its place are remembered. If it comes back and the place is still free, it stands there again. The mod only acts on a complete list from the system: if the helper is down, nothing is torn down. |
| A program is renamed | The sign shows the new name. Its short names stay as they are. |
| A program gets a new icon | Its logo is rebuilt in the same place. |
| He removes an app from My apps | As a removed program, by his choice. |
| He wants another order | `/aresos app swap <a> <b>` swaps two logos. `/aresos app move <app> <direction>` (north, east, south or west) moves one to the nearest free place of another group, and it stays there. |
| The rules change (a new look, other sizes) | `/aresos hub rebuild` takes down everything the mod placed and builds it again from the rules, every app in its saved place. A better picture converter re-renders the logos in place by itself. |
| He creates a new AresOS world | The places are saved with the apps, not with the world, so the same town is built there. |

**His own builds.** The rule stays: the mod never destroys a block it did not place.
- The mod builds only where nothing is: the space a logo needs must be air, and the ground under it must be the untouched grass or the mod's own paving.
- If something of his stands in a place, that place is skipped. The logo goes to the next free place and the chat says which place is blocked.
- The mod remembers every block it placed and which block it was. It removes or replaces a block only if it is still that block. If he changed one in Build mode, it is his from then on and stays.
- So he can build in the plaza, between the rows, or on the avenues. The town grows around his builds.
- Logos and zones he makes by hand (`/aresos logo`, `/aresos zone`) keep working and are his.

**Protected in Live mode:** every block the mod placed (logos, doormats, avenues, the home pad). They cannot be broken by hand and explosions do not break them, as for today's logos. The signs cannot be hit at all. In Build mode he can change anything.

**Pins do not move logos.** A logo's place does not change when he pins or unpins the app. The hotbar and the world are two things, like a taskbar and a desktop. On the very first build, pinned apps are placed first, so they get the front places of their groups.

### 2.6 Getting around

- **The roads.** Four avenues, 5 blocks wide, dark stone with a coloured line down the middle. They are paved as far as the group has logos. A road always leads home.
- **Everything faces home.** Wherever he is, the logos look towards the pad. Walking against their gaze is the way out, with it the way home.
- **Group names.** Over each avenue, between the two front logos, hangs the group's name and how many apps it has: `INTERNET · 2`.
- **Colours.** Each doormat has its group's colour, and so does the line on the road.
- **Signs.** Every logo carries its name and its command. They turn to face him, so he reads them from the side and from behind too.
- **`/go <app>`** puts him at that logo's exit point, looking at its door. One step and he is in.
- **`/apps`** lists his apps in the chat with their commands and where they stand ("Lunar Client: /lunar. Games, east, front row, left"). Clicking a line opens the app.
- **Home.** The H key or `/home` puts him on the pad, facing north. `/aresos home` stays. `/aresos home set` still moves only the spot where he arrives; the town stays where it is.
- **No map and no beacons in version 1.** The cross is simple enough to hold in the head, and a beacon hums. A vanilla map on a wall at home would show the coloured roads and can be added with his own look.

### 2.7 Short names for `/name`

- Every app in My apps gets one main short name, worked out from its name, its program file and its desktop file ID. A small built-in table adds well-known nicknames that no rule can find (`dc`, `ff`, `vscode`, `tg`). Section 4 has the rules, the table and 27 real examples.
- His three: Lunar Client is `/lunar`. Discord is `/discord` and `/dc`. Chrome is `/chrome` and `/browser`.
- **Minecraft's commands always win.** A name that Minecraft or AresOS already uses is never given to an app. The mod checks against the game's real command list at the moment it registers names, so commands that a future Minecraft adds are covered too. The app then gets its next-best name. Example: the GNOME program called "Help" would be `/yelp`, after its program file, because `/help` is Minecraft's.
- **Two apps, one name.** The app that had the name first keeps it. The other gets its next-best name. Names are saved once given and never change by themselves.
- **He changes them** with `/aresos app name <app> <new name>` (adds a name and makes it the one on the sign) and `/aresos app unname <name>`. A name another app holds is refused, and the message says which app.
- **He lists them** with `/apps`, and each logo's sign shows the main one.
- **Tab completion.** The names are real commands, so `/ch` and Tab gives `/chrome`. Only My apps get such commands, so the list stays short. `/open`, `/go` and `/aresos app …` complete program names.
- **`/open <name>`** opens any program in All programs, also one without a logo.
- **When the app is already open,** `/chrome` does exactly what a right-click on Chrome in the hotbar does: the same request goes to the system, and the program decides. For Chrome that is a new window (the owner's answer on board #155). A program that keeps one window comes to the front.
- **Where they work.** In an AresOS world, for him alone, in Live and in Build mode. In a normal world and on servers these commands do not exist.

---

## 3. The layout rules

Everything here is data and a few rules, so a restyle changes numbers and a later look (the Nether) swaps 3.2 for its own.

### 3.1 The numbers

| Name | Value | Meaning |
|---|---|---|
| `SIZE` | 12 | logo width and height |
| `DEPTH` | 3 | logo thickness |
| `FIRST` | 4 | sideways block index where the first logo beside the road starts |
| `PITCH` | 14 | from one logo to the next in a row (12 + 2 free) |
| `ROW0` | 20 | outward block index of the front layer of row 0 |
| `STEP` | 14 | from one row to the next |
| `DOOR` | columns 5 and 6, rows 0 to 2, 2 deep | the doorway |
| `EXIT` | 6 | the exit block is the 6th block in front of the front layer |
| `ROAD` | 5 | avenue width (sideways -2 to 2) |

### 3.2 From a place to blocks

**Home block** `H` is the block he stands in: (0, 64, 0). The floor is the layer below it (y 63). "Height 0" means y 64.

**Each group has two directions,** seen from home:

| Group | Letter | Outward | Right | Yaw that looks outward |
|---|---|---|---|---|
| Internet | N | north (z - 1) | east (x + 1) | 180 |
| Games | E | east (x + 1) | south (z + 1) | -90 |
| System & Tools | S | south (z + 1) | west (x - 1) | 0 |
| Work & Media | W | west (x - 1) | north (z - 1) | 90 |

"Outward `a`, sideways `b`" means the block `H + outward × a + right × b`.

**A place** is group, row `r` (0, 1, 2 …), side (L or R, as he sees it from home looking outward) and `k` (0 … r, counted from the road). It is written `N0L0`, `S2R1`.

For place (group, r, side, k):
- **Outward:** the front layer is at `a0 = ROW0 + STEP × r`. The logo fills `a0`, `a0 + 1`, `a0 + 2`.
- **Sideways:** column `u` (0 to 11, counted from his left as he looks at the front) is at `b = FIRST + PITCH × k + u` on side R and at `b = -(FIRST + PITCH × k + 11) + u` on side L.
- **Height:** row `v` (0 to 11) is at height `v`.
- **Niche:** columns 5 and 6, heights 0 to 2, at outward `a0` and `a0 + 1`, are air. The same columns and heights at `a0 + 2` are black concrete.
- **Trigger zone:** exactly the niche: 2 x 3 x 2 blocks.
- **Exit point:** outward: the middle of block `a0 - 6`. Sideways: the edge between columns 5 and 6. Height 0. He looks outward (the yaw in the table), pitch -10. Measured from the middle of `H`, that is outward `a0 - 6` and sideways `9.5 + 14 × k` on side R, minus that on side L.
- **Sign:** a text display on the same centre line, over the front layer, its lower edge at height 12.5. Scale 4, line width 120, turns around the upright axis only, full brightness, seen from 160 blocks.
- **Light:** `light` blocks at level 15 at outward `a0 - 1`, columns 2 and 9, height 6.
- **Doormat:** the floor blocks under columns 5 and 6 from outward `a0 - 2` to `a0 + 1`, in the group's concrete.

**Fixed things:**
- Home pad: the floor from x -2 to 2 and z -2 to 2 is polished blackstone bricks; the block under him is a gold block.
- Avenue of a group: the floor at sideways -2 to 2, from outward 3 to `ROW0 + STEP × R + 4`, where `R` is the group's farthest row in use (0 if it has no apps). Sideways 0 is the group's concrete, the rest polished blackstone bricks. All four are built with the world.
- Group name: a text display at outward 20, sideways 0, height 9, scale 3, in the group's colour.
- Group concretes: `light_blue_concrete`, `red_concrete`, `yellow_concrete`, `purple_concrete`.

**Why places never collide.** Row `r` reaches sideways to `15 + 14 × r` and stands at outward `20 + 14 × r`, so each group stays 5 blocks inside its quarter. Between two groups an open diagonal lane, at least 4 blocks wide, runs from the pad outwards. An exit point always has 5 clear blocks between it and the back of the row before.

**Day one, worked out** (world coordinates; the builder's test can check these):

| App | Place | Blocks | Niche | Exit point | Yaw |
|---|---|---|---|---|---|
| Chrome | `N0L0` | x -15 to -4, y 64 to 75, z -22 to -20 | x -10 and -9, z -20 and -21 | (-9.0, 64, -13.5) | 180 |
| Discord | `N0R0` | x 4 to 15, y 64 to 75, z -22 to -20 | x 9 and 10, z -20 and -21 | (10.0, 64, -13.5) | 180 |
| Lunar Client | `E0L0` | x 20 to 22, y 64 to 75, z -15 to -4 | x 20 and 21, z -10 and -9 | (14.5, 64, -9.0) | -90 |
| Terminal | `S0L0` | x 4 to 15, y 64 to 75, z 20 to 22 | x 9 and 10, z 20 and 21 | (10.0, 64, 14.5) | 0 |
| Notepad | `S0R0` | x -15 to -4, y 64 to 75, z 20 to 22 | x -10 and -9, z 20 and 21 | (-9.0, 64, 14.5) | 0 |

One more to check the rows: `W1R1` fills x -36 to -34, z -29 to -18; its exit is (-27.5, 64, -23.0), yaw 90.

### 3.3 Order

- **Places of a group, nearest first:** by row, then by `k`, then L before R. For north: `N0L0`, `N0R0`, `N1L0`, `N1R0`, `N1L1`, `N1R1`, `N2L0`, `N2R0`, `N2L1`, `N2R1`, `N2L2`, `N2R2`, …
- **A new app** takes its saved place if it has one and the place is free and can be built on. Otherwise it takes the first place of its group, in that order, that is free and can be built on. The place is then saved.
- **The first build** (and any time several apps have no place yet) handles pinned apps first, then the others in the order of the apps file.
- **A place can be built on** when three spaces are air and the floor under them is the untouched grass block or a block the mod placed: the logo's whole 12 x 12 x 3 box; the layer right in front of it (12 wide, 12 high, 1 deep); and the way in (columns 4 to 7, 3 high, from there out to the exit block). Anything else is his, and the place is skipped.

### 3.4 Keeping the world in step

The mod compares what should stand with what stands. It does this when he enters the world, when the system's program list changes, and after `add`, `remove`, `move`, `swap` and `hub rebuild`. It only runs on a complete program list.

The town is built only in a world that was created as the flat home. Other AresOS worlds (the old Nether home, a world marked with `/aresos desktop on`) get My apps, the inventory and the commands, but no town.

1. **Wanted:** the apps in My apps that the system says are installed.
2. **Take down** every standing logo whose app is not wanted, or whose saved place has changed: remove each block the mod placed there if it is still that block, remove the sign, remove the zone.
3. **Build** every wanted app that has no standing logo, in its place (3.3).
4. **Refresh** every standing logo whose icon, converter version or name changed: rebuild the blocks in place, or just rewrite the sign.
5. **Roads and names:** extend each avenue to its group's farthest row; write the counts on the group names.
6. **Tell him** in the chat what was added, removed or blocked. One line each, none if nothing changed.

Every block change goes through one function that records the position and the block placed. Removal checks that record.

### 3.5 What is saved

**With the apps** (`config/aresos/apps.json`, per machine; the file gets a new schema number). For each app, beside today's fields:

| Field | Meaning |
|---|---|
| `mine` | true if it is in My apps |
| `names` | its short names; the first is the main one |
| `place` | its place, for example `"N0R0"`; kept when it is removed, so it can come back |
| `group` | only if he moved it to another group by hand |
| what the system said | origin, categories, desktop file ID, program file, so names and groups can be worked out without the helper |

And once for the file: `baseline`, the day the first full program list was taken. Before that day nothing is added by itself; after it, new programs are.

Moving today's file over: an app that is pinned today, or is a starter, starts with `mine` set. All others follow the day-one rule of 2.4 when the first full list arrives.

**With the world** (`data/aresos/hub.dat`):

| Field | Meaning |
|---|---|
| look and numbers | which rules built this town (`flat-1`) and the table of 3.1, so a change is noticed |
| home block | the origin of all coordinates |
| standing logos | app, place, the icon's hash, the converter's version, every block placed (position and block), the sign's ID, the zone's ID |
| fixed things | every block placed for the pad, avenues and doormats (position and block), the group names' IDs |

The trigger zones and exits stay in `data/aresos/zones.dat` as today, marked as the hub's so `/aresos zone` commands do not mix them up with his own. The home spot stays in today's home data, now with the Overworld as its dimension.

### 3.6 From an icon to 12 x 12 blocks

1. **Cut** the icon to its visible box (pixels at least 12% opaque).
2. **Plate test,** on a copy padded to a square and scaled to 96 x 96 pixels:
   - The rim is every visible pixel that has a see-through pixel or the picture's edge within 9 pixels, sideways or up and down.
   - The plate colour is the middle value (median) of the rim, per colour channel.
   - If at least 80% of the rim is within 0.05 of the plate colour (plain Oklab distance), the icon has a plate.
   - The figure is every visible pixel farther than 0.10 from the plate colour.
   - If the figure is at least 2% of the picture and its box is at most 80% of the picture's width and height, **enlarge:** take a square around the figure with a margin of 10% of its size on each side, kept inside the picture, and lay it on a square of the plate colour. Otherwise leave the icon whole.
3. **Scale** to fit 12 x 12 by averaging areas, keeping the proportions. A cell is solid when at least half of it is covered. An icon that is not square is centred sideways and stands on the ground.
4. **Colour:** each solid cell gets the block nearest to its average colour. Distance: turn both colours into Oklab (L, a, b), then `(0.5 × ΔL)² + Δa² + Δb²`. The palette is today's 48 plus the 12 of section 2.3.
5. **Tidy:** drop a solid cell that touches no other solid cell, not even at a corner. (None of the 24 test icons had one; this is a safeguard.)
6. **Door:** clear columns 5 and 6, rows 0 to 2. Where columns 4 and 7 (rows 0 to 2) or columns 4 to 7 (row 3) are empty, make them black concrete.
7. **Build** every solid cell as 3 blocks of its kind, front to back; then the niche's black back blocks.

### 3.7 What the system must tell the game

Used from the list the helper can already pass: the desktop file ID, `Name`, `Categories`, the program file's base name, `StartupWMClass`, where it came from, and the icon. `GenericName` and `Keywords` are used only by the search in the Apps screen and by `/open`.

Three things beyond that list:
1. **Where it came from, in four kinds, not three:** the image, a system-wide Flatpak, a Flatpak installed for his user, his own folder. The day-one rule needs to tell the Flatpaks Bazzite ships (11 on the laptop) from the one he installed (Discord).
2. **The starters' desktop file IDs.** `browser` stands for `google-chrome.desktop` and `notepad` for `org.kde.kwrite.desktop`. The helper should list such a program once, as the starter. If it lists both, the starter keeps the name and the place.
3. **The icon as a PNG at least 64 pixels wide** (128 or more is better), with its transparency. The mod works out itself when it changed.

On Windows, where the mod is developed, every program found counts as "came with the system": only the pinned ones start in My apps.

### 3.8 The interface additions (`aresos-shell/1.1`)

One description for both sides: the mod's client (package 34) and the OS helper (package 30) are built to this, and `docs/design/OS-BASE.md` Appendix B1 takes it over when the helper lands. Everything in `aresos-shell/1.0` stays as it is.

- **Version.** The helper's minor version becomes 1. `hello` works as today: the reply's `minor` is the lower of the two sides. A 1.1 helper also offers the capabilities `app_details`, `apps_changed` and `list_paging`. The mod requires none of them, so it keeps working with a 1.0 helper (three apps, no pictures, as today).
- **An older mod (1.0) with a 1.1 helper** gets exactly what it gets today: the starter apps with `id`, `name`, `available`, `reason`, in one reply. Programs found through desktop entries are listed and opened only for a client that negotiated 1.1.
- **`list_apps` in 1.1.**
  - The request may carry `"cursor"` (a string of at most 64 characters that the helper handed out; no cursor means the first page).
  - The reply carries `revision`, `apps` (one page, ordered by `id`) and, when more follow, `next` (the cursor for the next page). Every message stays within the 64 KiB limit.
  - The client asks again with `cursor` until a reply has no `next`. If a page's `revision` differs from the first page's, it starts over; after three such starts it keeps the list it had and tries again at the next `apps_changed`.
- **An entry in 1.1** has `id`, `name`, `available`, `reason` as today, and these optional fields. A missing field means "not known"; unknown fields are ignored by both sides.

  | Field | Value |
  |---|---|
  | `source` | where it came from: `image` (a starter from the reviewed list), `system` (`/usr/share/applications`, `/usr/local/share/applications`), `flatpak-system`, `flatpak-user`, `user` (his own folder) |
  | `icon` | absolute path of a PNG with transparency, at least 64 pixels wide (the helper writes 128 x 128), readable by him |
  | `categories` | the entry's categories, at most 16, each `[A-Za-z0-9-]{1,32}` |
  | `generic_name` | at most 64 characters |
  | `keywords` | at most 16, each at most 32 characters |
  | `desktop_id` | the desktop file ID, at most 128 characters |
  | `exec_name` | the base name of the program file that runs; for a Flatpak, its app ID |
  | `terminal` | true when it runs inside the terminal |

  A starter that stands for desktop entries (Chrome for `google-chrome.desktop`) is listed once, as the starter, with `source` `image`, and takes `icon`, `categories`, `generic_name`, `keywords` and `desktop_id` from the first of those entries that is installed.
- **`apps_changed`.** When the list or a picture changes while the helper runs, a client that negotiated 1.1 gets the event `{"event": "apps_changed", "revision": "<new revision>"}` (in the usual envelope). The client then lists again, at most once every two seconds.
- **Never sent to the game:** a command, arguments, an environment, or a path other than `icon`.
- **Example messages.** The mod package commits one example file per message kind under `mod/src/test/resources/shell-1.1/` (a first page with `next`, a last page, an entry with every field, an entry with none, `apps_changed`). The helper package's tests read the same files and check that the helper produces and accepts that shape.

---

## 4. Short-name rules

### 4.1 Words used below

- **Squeeze** a text: lower case, accents removed, everything but a to z and 0 to 9 removed. "KDE Connect" becomes `kdeconnect`.
- A **valid** name is 2 to 16 characters, a to z and 0 to 9, and starts with a letter.
- A name is **free** if it is valid, no other app holds it, and it is not reserved.
- **Reserved:** every command the game has at the moment the names are registered, and AresOS's own: `aresos`, `home`, `go`, `open`, `apps`.

### 4.2 The main name

Try these in order and take the first that is free.

1. **The one telling word of the name.**
   - Split `Name` at spaces, hyphens, underscores, slashes and colons. Drop anything in brackets and pure numbers. Squeeze each word.
   - Drop maker words from the front, as long as a word is left: `google`, `microsoft`, `mozilla`, `kde`, `gnome`, `gnu`, `apache`, `adobe`, `jetbrains`, `libreoffice`, `bazzite`, `system`, `the`.
   - Drop filler words anywhere: `client`, `launcher`, `app`, `apps`, `application`, `desktop`, `for`, `linux`, `browser`, `web`, `and`, `of`, `media`, `player`, `game`, `games`, `stable`, `beta`, `edition`, `configuration`, `config`, `tool`, `tools`, `manager`, `viewer`, `editor`, `studio`. If that leaves nothing, keep the words as they were.
   - If exactly one word is left, that is the candidate. "Lunar Client" gives `lunar`. "Google Chrome" gives `chrome`.
2. **The cleaned program file name,** if it is 2 to 12 long.
   - Take the base name of the program in `Exec`, in lower case. Drop the endings `.appimage`, `.sh`, `.py`, `.bin`, `.exe`, `.x86_64`.
   - If it is only a starter of other programs, skip this step: `flatpak`, `env`, `sh`, `bash`, `python`, `python3`, `pkexec`, `sudo`, `xdg-open`, `xdg-terminal-exec`, `gtk-launch`.
   - Drop these from the front, repeatedly: `bazzite-`, `gnome-`, `kde-`, `plasma-`, `org.`. Drop these from the end: `-stable`, `-bin`, `-gtk`, `-qt`, `-gui`, `-app`, `-launcher`, `-wrapper`, `-desktop`, `-client`. Drop digits at the end. Drop a maker word and its hyphen at the front. Squeeze.
   - `google-chrome-stable` gives `chrome`. `bazzite-steam-bpm` gives `steambpm`.
3. **The cleaned last part of the desktop file ID,** if it is 2 to 12 long.
   - For an ID with three or more parts between dots, take the last part. If that is `app`, `desktop`, `client`, `launcher`, `gtk`, `qt`, `gui` or `main` and there are four or more parts, take the one before. An ID with fewer parts is taken whole.
   - Clean it as in step 2. `org.gimp.GIMP` gives `gimp`.
4. **The first telling word** from step 1's list. "Btrfs Assistant" gives `btrfs`.
5. **Whatever is left:** step 2's result, step 3's result, the squeezed whole name, each cut to 16.

If none is free: the first candidate with a number, starting at 2 (`steam2`).

### 4.3 Extra names

- **The built-in table.** After the main name, add every free name from the first row that matches. A row matches on any of: the Flatpak ID, the desktop file ID, the cleaned program file name, `StartupWMClass`, the squeezed name (all in lower case).

  | Matches | Adds |
  |---|---|
  | `com.discordapp.discord`, `discord` | `dc` |
  | `org.mozilla.firefox`, `firefox` | `ff` |
  | `com.visualstudio.code`, `code` | `vscode` |
  | `org.telegram.desktop` | `tg` |
  | `org.qbittorrent.qbittorrent` | `qbit` |
  | `com.mojang.minecraft`, `minecraft-launcher` | `mc` |
  | `org.kde.dolphin` | `files` |
  | `org.mozilla.thunderbird` | `mail` |
  | `terminal` (the starter) | `term` |

  The table holds only nicknames that the rules cannot work out. It is meant to stay this small.
- **Starters** also answer to their fixed ID: `/browser`, `/terminal`, `/notepad`.
- **His own names,** added with `/aresos app name`. The newest becomes the main one.

### 4.4 When, and who goes first

- An app gets its names when it joins My apps. They are saved and do not change by themselves, also not when the program is renamed.
- When several apps get names at once: starters first, then the rest in the order they joined.
- A name he gives is checked the same way: it must be free. If another app holds it, he is told which.
- Programs outside My apps have no command of their own. `/open` finds them by the name these rules would give, by the squeezed full name, or by the unique start of either. If several fit, it lists them to click.

### 4.5 How it is wired

- Each name is a real command on the game's own command list, visible only to the host of an AresOS world. That gives Tab completion and keeps normal worlds clean.
- A name is registered only if the list has no command of that name at that moment. So vanilla commands, and those of any other mod loaded before, keep working.
- When My apps changes, new names are registered and the command list is sent to him again.
- Running a name tells his own game to open the app, the same message a doorway sends. The game accepts it only in singleplayer in an AresOS world, as today. No server can open a program on his laptop.

### 4.6 Worked list

Real entries from the laptop on 2026-11-13, run through the rules above by a script. The first five are day one's My apps.

| Name | Desktop file ID | Program file | Commands | Rule | Group |
|---|---|---|---|---|---|
| Chrome | (starter `browser`) | `google-chrome` | `/chrome`, `/browser` | 1, starter ID | Internet |
| Terminal | (starter `terminal`) | `foot` | `/terminal`, `/term` | 1, table | System & Tools |
| Notepad | (starter `notepad`) | `kwrite` | `/notepad` | 1 | System & Tools |
| Discord | `com.discordapp.Discord` | `flatpak` | `/discord`, `/dc` | 1, table | Internet |
| Lunar Client | `lunarclient` | `LunarClient.AppImage` | `/lunar` | 1 ("client" is filler) | Games |
| Steam | `steam` | `bazzite-steam` | `/steam` | 1 | Games |
| Steam Big Picture Mode | `bazzite-steam-bpm` | `bazzite-steam-bpm` | `/steambpm` | 2 | Games |
| Lutris | `net.lutris.Lutris` | `lutris` | `/lutris` | 1 | Games |
| ProtonPlus | `com.vysp3r.ProtonPlus` | `flatpak` | `/protonplus` | 1 | Games |
| Firefox | `org.mozilla.firefox` | `flatpak` | `/firefox`, `/ff` | 1, table | Internet |
| KDE Connect | `org.kde.kdeconnect.app` | `kdeconnect-app` | `/connect` | 1 ("KDE" is a maker) | Internet |
| KRDC | `org.kde.krdc` | `krdc` | `/krdc` | 1 | Internet |
| Kate | `org.kde.kate` | `kate` | `/kate` | 1 | Work & Media |
| Okular | `org.kde.okular` | `flatpak` | `/okular` | 1 | Work & Media |
| Gwenview | `org.kde.gwenview` | `flatpak` | `/gwenview` | 1 | Work & Media |
| Haruna | `org.kde.haruna` | `flatpak` | `/haruna` | 1 | Work & Media |
| Dolphin | `org.kde.dolphin` | `dolphin` | `/dolphin`, `/files` | 1, table | System & Tools |
| Konsole | `org.kde.konsole` | `konsole` | `/konsole` | 1 | System & Tools |
| KWrite | `org.kde.kwrite` | `kwrite` | `/kwrite` | 1 | System & Tools |
| KCalc | `org.kde.kcalc` | `flatpak` | `/kcalc` | 1 | System & Tools |
| Spectacle | `org.kde.spectacle` | `spectacle` | `/spectacle` | 1 | System & Tools |
| Disks | `org.gnome.DiskUtility` | `gnome-disks` | `/disks` | 1 | System & Tools |
| KDE System Settings | `kdesystemsettings` | `systemsettings` | `/settings` | 1 ("KDE" and "System" are makers) | System & Tools |
| System Monitor | `org.kde.plasma-systemmonitor` | `plasma-systemmonitor` | `/monitor` | 1 | System & Tools |
| Bold Brew | `bbrew` | `xdg-terminal-exec` | `/bbrew` | 3 (two words; the program file is only a starter) | System & Tools |
| Btrfs Assistant | `btrfs-assistant` | `btrfs-assistant-launcher` | `/btrfs` | 4 (steps 2 and 3 are too long) | System & Tools |
| Help Center | `org.kde.khelpcenter` | `khelpcenter` | `/khelpcenter` | 2 | System & Tools |

The same script, with programs that are not on the laptop (their IDs written from memory): Visual Studio Code gives `/code`, `/vscode`. Telegram Desktop gives `/telegram`, `/tg`. OBS Studio gives `/obs`. VLC media player gives `/vlc`. GNU Image Manipulation Program gives `/gimp`. Heroic Games Launcher gives `/heroic`. GNOME's "Help" gives `/yelp`, because `/help` is reserved.

Where the rules are weak, on the same machine: "Input Remapper" gives `/input`, "KDE Connect Indicator" gives `/nonplasma`, "Force Restart Waydroid" gives `/force`. None of these is in My apps by default, and one command renames any of them.

---

## 5. What I rejected and why

**Other layouts.** Farthest doorway from home, and sprinting time, for the same mix of apps:

| Plan | 9 apps | 20 | 40 | 100 | Readable from home at 40 | Grows without moving logos |
|---|---|---|---|---|---|---|
| A. One street, logos on both sides | 67 blocks, 12 s | 137, 24 s | 277, 49 s | 697, 124 s | 2 | yes |
| B. One ring around home | 28, 5 s | 47, 8 s | 96, 17 s | 245, 44 s | all 40, each about 100 pixels wide | no: the ring is rebuilt wider each time |
| C. Plaza with 8 logos and four streets of shop fronts | 31, 6 s | 45, 8 s | 101, 18 s | 241, 43 s | 8 | yes |
| D. Portals at home that jump to a court per group | 19 + jump, 4 s | 25, 6 s | 39, 8 s | 74, 14 s | none | only if courts have fixed places |
| **F. Four avenues, rows facing home (chosen)** | 36, 6 s | 50, 9 s | 64, 11 s | 100, 18 s | 8 | yes |

- **A. One street.** Closest to "the logos make a path". Good to about 8 apps. It only grows longer, and logos on a street are seen edge-on: from home only the first two can be read.
- **B. One ring.** The only flat plan that shows every logo from home. But a logo needs its share of the circle, so forty logos 12 wide need a ring whose front is 74 blocks out. Every door is then 80 to 96 blocks away, the favourite's too. And a ring cannot grow without moving what stands.
- **C. Plaza and four streets.** The runner-up. Same front row as the chosen plan. Each street only grows in length, so one big group makes a long walk: 101 blocks at 40 apps. The chosen plan is this one with the shop fronts turned to face the walker and each group allowed to widen.
- **D. Portals and courts.** The fastest at a hundred apps. But nothing stands at home except portals, every app is two steps away, and the courts are separate places far apart. It is the right answer for several hundred apps and can be added then.
- **E. Terraces, so every row is seen over the one in front.** To look over a 12-tall logo 20 blocks away, the next row must stand on ground 19.5 blocks high, the third on 44, the fourth on 72. The owner asked for logos that are not too tall; this makes a stadium.
- **A hill at home.** From a home 20 blocks up he would see the upper half of row 1 and the top third of row 2 over the front row. That is a good later look. The rules only need the home spot's height; nothing here blocks it.
- **Six or more groups.** The desktop categories would allow more. A square has four sides, and four are easy to remember by compass. Of the laptop's programs 9 are Internet, 5 Games, 5 Work & Media and 42 System & Tools; a finer split would leave roads with one or two logos.
- **The front row for pinned apps.** Then every change to the hotbar would tear down and build logos, and a slip of the hand in the inventory would move houses. Places that stay are worth more.

**Other logo forms.**
- **Today's flat wall** (up to 32 tall; a 16-pixel icon in a frame is 18). Too tall for the owner, a thin sheet, and its whole front is the trigger.
- **A floor logo with a low arch.** Unreadable from eye height: a stripe 7 degrees tall.
- **A small booth with the icon as a sign.** A build 7 or 8 blocks tall is low enough, but at 8 x 8 blocks no icon survives, so the picture would have to be something other than blocks.
- **Small blocks as display entities.** They would allow a detailed logo 3 blocks tall. But 144 entities per logo is 5,760 for forty logos, each drawn on its own every frame, and they are not blocks: he cannot build on them.
- **Maps in item frames.** The real icon, sharp, on a 2 x 2 wall. It is a poster, not a build, and frames can be knocked off the wall.
- **10 or 16 blocks.** See section 7, question 1.

**Other choices.**
- **A logo for every program.** About 59 logos on day one, most of them system tools.
- **Removing an app by dropping its item.** Q is pressed by accident.
- **Keeping a removed program's logo as a ruin.** A dead door he has to clear away by hand. Its place is remembered instead.
- **Beacons as landmarks.** They hum, and the cross does not need them.
- **Speed II by default.** Faster, but it changes the field of view and the feel. Off until he asks.

---

## 6. Build order

Six packages. Each is one thing he can see.

| # | He sees | Needs | What is hard |
|---|---|---|---|
| 1 | **The flat home.** The AresOS button creates the flat world. He arrives on the pad at noon, four coloured avenues lead off, nothing lives there. | nothing | Creating a flat world with these layers and no structures through the game's own create flow in 26.2. Setting the rules once, at creation only. Keeping today's promises: an existing save is never rebuilt or replaced. Proving no mob appears. |
| 2 | **The gate.** `/aresos logo chrome` builds the new 12-block logo with its doorway and sign where he stands. He tries it with Chrome, Discord and Lunar. | nothing | The picture rules of 3.6, tested with made-up icons. Measuring the 12 new blocks' colours without a texture in the repo. Signs and lights as things the mod must also remove. Today's builder refuses to build next to anything but plain blocks; some of the new blocks are not plain in that sense, so the check must know the mod's own blocks. Without shaders Minecraft draws east and west faces darker than north and south ones, so east and west logos will look a little dimmer; that is the game, not a bug. |
| 3 | **My apps.** His inventory holds only his apps. The Apps screen has a search box; a click adds a program, a right-click removes one. | the program list from the system (it can be built against the test helper) | Moving the apps file to a new schema without losing pins. Taking items out of two saved inventories (Live and Build) safely. The baseline day and the rule for new programs. |
| 4 | **Slash names.** `/chrome`, `/dc`, `/lunar`, `/open`, `/apps`. | 3 | Changing the command list while the world runs and sending it again. Checking for clashes at the right moment. Opening the app from a server command without opening a way for real servers. |
| 5 | **The town builds itself.** The five day-one logos stand in their places. Install or remove a program and the town follows. `/aresos hub rebuild`. | 1, 2, 3 (signs show the commands once 4 is in) | The record of every placed block, and never touching a block that is no longer the mod's. Building in chunks that are not loaded. Doing it as he arrives without a visible hitch. Blocked places. Tests with a fake program list and made-up icons. |
| 6 | **Getting around.** `/go`, `/home` and the H key, places in `/apps`, `swap` and `move`, the counts on the group names. | 5 | Little. Swapping two logos is two rebuilds in one step. |

Packages 1, 2 and 3 do not depend on each other and touch different parts of the mod (world, logos, items and screens), so they can be built side by side. Only one of them at a time can run the client tests on the laptop.

After 5 the owner has what he described. Package 6 is comfort.

Later, and not blocked by anything here: his own look for the world (a look is a table of blocks and numbers plus the function of 3.2), the Nether as a second look, a hill at home, companions walking the avenues, a key that opens the Apps screen as a search.

---

## 7. For the owner

**1. How tall may a logo be?**
I chose 12 blocks. It is the smallest size at which Chrome, Discord and Lunar Client are all still recognisable; that is under seven times your height, about a tall tree. At 10 the town is lower and tighter but Lunar's moon is a smudge. At 16 every logo is clearer, but they stand a third taller and everything is about a quarter farther away. There is a picture of the three logos at 10, 12, 14 and 16 next to a player. It is one number; the town rebuilds itself when it changes.
*Recommendation: 12. Assumed meanwhile: 12.*

**2. Should a program you install get a logo by itself?**
I assumed yes: you install Spotify, and the next time you are in the world it stands in Work & Media and `/spotify` works. A right-click removes it. Programs that came with the system, like Steam, never appear by themselves; you add those. The other way is that nothing appears until you add it in the Apps screen (three clicks). On day one you would have five logos either way: Chrome, Discord, Lunar Client, Terminal, Notepad.
*Recommendation: yes. Assumed meanwhile: yes.*

**3. Are the four groups yours?**
Internet ahead of you, Games to the right, Work & Media to the left, System & Tools behind. A program goes where its own description puts it, and you can move any logo. The groups are your map of the place, and logos keep their places for good, so this is worth getting right before forty of them stand. If you think of your apps differently (for example "daily" and "rarely"), say so now.
*Recommendation: these four. Assumed meanwhile: these four.*

Everything else in this document I decided. All of it is cheap to change: the sizes and distances are nine numbers, the blocks are a table, and `/aresos hub rebuild` builds the town again.
