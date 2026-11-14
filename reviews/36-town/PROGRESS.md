# 36 review fixes 1: progress

Brief: `briefs/36-review-fixes-1.md`. Step A (the ledger, points 1 to 5) is done, by a Claude agent on Opus 5.5.
Step B (points 1 to 8 of step B) is next, on a fresh builder; it moves this text into the report's "Review fixes 1"
section and deletes this file.

## Step A: done

| Commit | Point |
|---|---|
| `b3e0ee83` | 1. The seal: `data/aresos/town-seal.dat` written right after every `level.dat`, checked when the world opens |
| `747d8675` | 2. Unsealed means frozen; `/aresos hub trust` ends it |
| `439a041d` | 3. A `town.dat` that does not fit is refused and kept, never replaced |
| `d64b0878` | 4. A loaded ledger goes through `add`'s checks before any of it is used |
| `bbd7cfa1`, `851ae11f` | 5. The server test; a failed run of it leaves the kept test world usable |

### 1. The seal (`hub/TownSeal`, `mixin/TownSealMixin`, `mixin/LastPlayedMixin`, `mixin/ServerStorageAccess`)

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

### 2. Frozen (`HubData.frozen`/`trust`, `TownKeeper`, `HubCommands`)

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

### 3. Refused (`HubData.join`, `refusal()`)

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

### 4. Checks on load (`HubData.check`)

One check for `add`, the constructor with logos, and every file read in (`adopt`, used when the world opens and by
`store`): two logos of one app, in one place, on one block, with one sign ID or one zone ID; a pad or road block, or a
group name's ID, in a logo; a place name that is no place; a logo whose recorded positions (placed blocks, the ground
under its doormat, its grass) lie outside its place's box as the town plans it from the home. The first overlap is
named and refuses the whole file.

### 5. Tests

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

## What ran (all `mod/dev/build.sh` from the worktree root, on the laptop under AresOS, 2026-11-14)

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

`mod/dev/client-test.sh` was not run (step B runs it).

## Decisions the brief did not settle

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

## What step B needs to know

- **B1 (lights):** `HubBlockChangeMixin` still lets go only on a block-kind change. The `holds` call to remove is in
  `TownGameTests.keepingNear` ("A light he changed is his and stays").
- **B2 (signs and zones):** `Town.remove` now refuses a frozen logo first; put the identity checks after that (and in
  `GateBuilder.takeDown` for the sign). `HubData.check` already refuses two records with one sign or zone ID.
- **B5 (missing zones):** a frozen logo's missing zone: restoring adds and takes nothing down, so the principle allows
  it if nothing else claims the box; decide and say so.
- **B6 (first build, one line):** `TownLines.said(first, …)`; the frozen lines are `Kind.WAY`.
- **B7 (reopen):** reuse the server test's helpers `storage`, `reopen`, `copy`, `opened`, `olderModSaves`. The client
  test's save, leave and join is **the only run of the real `Minecraft.doWorldLoad` path** (the seal carried as a world
  opens): check there that no line "This world was saved without the town's records…" appears after the reopen. A
  server test that saves the world mid-way must clean up on failure as `sealing` does (a failed check stops the test
  server without its last save); a kept test world in a bad state is reset by deleting `mod/build/run/gameTest/world`.
- **B8 (report and HUB.md):** this file's text goes into the report's "Review fixes 1" section; HUB.md's corrections
  need the seal, the freeze, `/aresos hub trust` and the refused `town.dat` (with how to start afresh), and the claim
  that the two files "cannot disagree" corrected (B5).
- New API: `HubData.open`, `townFile`, `refusal`, `frozen`, `frozenCount`, `trust`; `TownKeeper.notice`, `trust`,
  `refused`, `FROZEN`; `TownSeal`.

## Not verified

- The real client: `Minecraft.doWorldLoad` carrying the seal as a world opens (only the same call on a copy without a
  server, in the server test), the two entering lines in chat, and `/aresos hub trust` through the real command (the
  test calls `TownKeeper.trust`, which the command calls after its host check).
- A real older mod (packages 32 to 35) on a town world: played by writing `level.dat` without the seal. A real crash
  between the two writes: modelled in the unit test. Optimize World and a dedicated server's start: same method, by
  reading.
- Windows: the seal's atomic replace (`ATOMIC_MOVE` with `REPLACE_EXISTING`), by reading.
