# 34 My apps: builder handoff

Working notes for the next builder. Deleted in the last commit before the PR is ready.

## State (after builder 2)

| Step | What | State |
|---|---|---|
| A1, A2 | `ShellClient` speaks 1.1; `FakeHelper` speaks 1.0 and 1.1; example messages; `ShellListTest` | **Done** |
| A3 | What the system said is kept on the app (`AppDefinition.system`, `SystemInfo`) and saved (`AppsConfig.merge`) | **Done** |
| A4 | The helper's icon path feeds the pixel icon (`icon/AppIcons`); the pack is regenerated and reloaded, throttled (`icon/IconRefresh`, `client/IconReload`) | **Done**, unit tests; no client test yet (see B3) |
| A5 | Vanilla look by group for an app without a picture | **Done** |
| B1 | apps.json schema 3 (`mine`, `baseline`), the move from schema 2 and 1 | **Done** |
| B2 | Day one, baseline, "joins later" in the file; in the game: the inventory holds My apps only, removal from Live and saved Build, Q, the three commands, the chat line (`item/MyAppsGame`, `item/AppInventory`, `item/AppCommands`, `mixin/AppDropMixin`) | **Done**; server game tests for the inventory rules; the commands and the chat line need a host, so they wait for the client tests (B3) |
| B3 | The Apps screen and the client game tests with screenshots | Not started |
| Last | README, REPORT, build once, client tests twice, fetch and merge, delete this file, PR | Not started |

## What is left, in order

1. **B3, the Apps screen** (`client/AppsScreen.java`, brief B5, HUB.md 2.4). Search box on top (name, `system.genericName`, `system.keywords`), "My apps", then "All programs" by name, each row icon and name. Left-click on a program that is not his adds it and keeps the screen open; left-click on one of his picks up its item as today (`TakeAppPayload`); right-click on one of his removes it. Typing goes to the search box, Enter acts on the only match, Escape closes. 200 programs: scroll or page, say which in the report.
   - The server side is there: `MyAppsGame.add(player, id)` and `MyAppsGame.remove(player, id)` return the line for the chat and throw `IOException` with the reason. The screen needs one serverbound payload (say `MyAppPayload(id, mine)`), registered beside `TakeAppPayload` in `AppInventory.register()`; its receiver must check the host and the AresOS world the way `AppCommands.host` does, call add or remove, and send the line (`sendSystemMessage`, or the overlay). `take` now refuses a program that is not his.
   - The screen reads `AresOs.apps()`; an add or remove replaces that list (integrated server, same JVM), so rebuild the rows when the list object changes, not once in `init`.
   - `AppsScreen.active` is true in Live only, as before.
2. **B3, the client game tests** (brief, Acceptance): with the fake helper and icons the tests draw themselves: the inventory on day one (five items); the Apps screen with 150 programs, with a search typed, after an add and after a remove; an item's pixel icon in the hotbar. Screenshots under `reviews/34-my-apps/screenshots/` (add `systemProperty 'aresos.myAppsReviewDir', ...` in `build.gradle` like the others). They must also cover what the server game tests cannot, because it needs the singleplayer host:
   - `/aresos app add`, `remove`, `list` and their completion (add: programs that are not his; remove: his);
   - the chat line of a program that joins after the baseline ("Spotify is new and joined My apps."), none on day one;
   - "No free inventory slot: X has no item for now." if cheap;
   - Q on an app's item in the hotbar (the client refuses it in Live through `ModeSwitchDropMixin`, the server refuses it in any mode);
   - the icon path end to end: a list with `icon` paths arrives, `MyAppsGame.pictures` regenerates, `IconReload` reloads (only when `client.gui.overlay()` is null), `AresOs.generatedIcons` gets the ID, the next tick's tidy-up gives the item in the inventory the model `aresos:apps/<id>`. Wait for the model on the client's stack, then screenshot.
3. **The last step** of the table. `mod/README.md` already has schema 3, the move, the `icon` limits and reload, and a "My apps" section (day one, the three commands, `/aresos give`, when the inventories change, Q). Still to write there: the Apps screen. The sentence "**E → Apps…** opens a paged catalogue ... Pick an app to put its item on the inventory cursor" near the end of "App configuration" describes the old screen; and the line "On Linux, `aresos-shell/1.0` is a stub until the OS helper arrives" is older than this package and no longer true (the helper exists; this package speaks 1.1). `REPORT.md` with the lists below.
4. Until B3 is done the old Apps screen is in between: it still lists every app, and a click on a program that is not his does nothing (the server refuses to hand out its item).

## How the game part works (read before changing it)

- **Nothing edits an inventory on the spot.** `MyAppsGame.changed()` raises a counter. On each server tick (`MyAppsGame.tick`, also called right after add and remove) every player whose inventories are behind is tidied if it is safe: no pending or running mode switch, his own inventory menu, nothing on the cursor, nothing in the crafting grid (the conditions `ModeInventories.transact` refuses a switch for). Otherwise nothing is touched and the work stays due. What is his is in the apps file before the counter moves, so work still due when the game closes is done after the next login (`populate` at JOIN; after a login that restored the Live inventory, the first safe tick).
- **The tidy-up** (`MyAppsGame.tidy`): (1) `AppInventory.sweep` takes the items of known apps that are not his out of the inventory he holds, in either mode; (2) `ModeInventories.mapInactive` does the same in the saved inventory (new method: decode, map, encode, read back and compare, refuse during a switch); (3) in Live only, `AppInventory.populate`: pinned apps to the hotbar, looks and names refreshed, each of his apps without an item into the first free slot 9 to 35. An item of an app the file does not know is left alone ("if unsure, keep").
- **A full inventory:** the app is his and has no item; the player is told once per app and session ("No free inventory slot: ..."). The item is made at the next tidy-up after a slot is free (any change, or the next login), not at the moment the slot frees.
- **Q:** three layers. `ServerPlayer.drop(boolean)` (Q, Ctrl+Q in the world) is cancelled and the slot sent again; `AbstractContainerMenu.clicked` is cancelled for THROW on an app's item and for a click outside the window with one on the cursor; and `ServerPlayer.drop(ItemStack, boolean, boolean)` never makes an entity of an app's item: it goes into a free slot (9 to 35 first, so no accidental pin), or is let go when there is no slot or a switch is pending, and the counter is raised so the item is made again. All three only in an AresOS world.
- **A program that joins:** `AresOs.takeIn` calls `AppsConfig.merge(file, list, shell.detailed(), today)` and hands `Merged` to `MyAppsGame.listed`: one line per ID in `joined` unless `dayOne`, queued and sent to the host on a tick (at most five lines at once, then "And N more new programs joined My apps."). Lines from a list that arrived before the world was open wait for the host.
- **Icons:** `AppIcons.read(app)` is the one reader (public, for package 36's logos: `AppIcons.read(app).image()`). `IconPack.generate` returns `Result(generated, changed)`. `MyAppsGame.pictures(apps)` is called after every complete list from the helper's listener (not at startup, where `onInitialize` generates before the game's first resource load). `IconRefresh` has one worker thread: wait until five seconds have passed since the last reload, take the latest list, generate, and if a file changed ask the client for one reload and wait for it; only then `AresOs.generatedIcons` (now `volatile`) is swapped and the counter raised, so the tidy-up refreshes `ITEM_MODEL` on the items he already has. A reload that failed stays owed.

## Decisions taken

All of builder 1's stand (envelope, capabilities, listing limits, `desktop_id` with its ending, program IDs, baseline only from a 1.1 list, starters, "newly appears", unknown origin does not join, missing `mine` reads as his, `pinned` implies `mine`, `system` replaced whole, what the older mod does with a schema-3 file: refuses with "Unsupported schemaVersion (expected 2)", leaves the file, starts with no apps, says "AresOS apps disabled: ..." on join). New:

- **`/aresos give <app>` makes a program his** (`MyAppsGame.own`, one line in `AresOs`). Otherwise the given item would vanish at the next tidy-up. JUDGMENT-CALL, small.
- **Q refuses instead of "drop and put back".** The item stays in its slot (or on the cursor), so a pin is never lost and nothing can double. JUDGMENT-CALL, small: a click outside the inventory window with an app's item on the cursor does nothing; he puts it in a slot or closes the inventory.
- **The 1 MiB and 512 x 512 limits apply to the system's icon path only**; his own `icon` (and Windows discovery's cache) is read as before. `AppDefinition.icon` stays separate from `system.icon`; his own wins.
- **A regular file is checked after following links** (`Files.isRegularFile`): icon themes link a lot. Size is checked on the bytes actually read.
- **The chat line** reads "<name> is new and joined My apps." HUB.md 2.4 also wants its place and its command; those come with packages 36 and 35. PLAN-GAP for the report.
- **Reload gap:** five seconds (`MyAppsGame.ICONS`).
- **After a login that restored the Live inventory** (he quit in Build) the tidy-up runs on the first safe tick, removals and new items both. Before this package such a login got no new items at all.
- **The tidy-up applies to every player in an AresOS world in Live**, as `populate` always did; add, remove and the commands are the host's.

## For the report

- JUDGMENT-CALL: unknown origin does not join by itself (builder 1); `/aresos give` makes a program his; Q refuses the drop.
- PLAN-GAP: the baseline is written only by a 1.1 list (builder 1); the chat line cannot name place and command yet; `zone/LogoBuilder.readIcon` still reads `icon()` only, so a Linux program's logo cannot be built from the helper's picture until package 36 uses `AppIcons` (`zone/` is off limits here); a tiny window at startup between the first list and `shell.addListener` in `AresOs.onInitialize` can miss one `apps_changed` (older than this package; the next change or restart heals it).
- Not covered by a test: the tidy-up after a login that restored the Live inventory; `giveBack` during a pending switch; the Windows start (unchanged code path apart from `IconPack.Result`).
- Files changed under `shell/`, `config/`, `item/` so far: `shell/ShellClient.java`; `config/AppDefinition.java`, `AppsConfig.java`, `MyApps.java` (new), `SystemInfo.java` (new); `item/AppInventory.java`, `AppCommands.java` (new), `MyAppsGame.java` (new). Check with `git diff --stat origin/main -- mod/src/main/java/dev/aresos/{shell,config,item}` at the end.

## Things the code does not show

- `FakeHelper` is package-private in `mod/src/test/java/dev/aresos/shell/`. The gametest source set gets `src/test/resources` (see `build.gradle`) but not `src/test/java`, so the client game tests cannot use it as it is. Make it reachable without copying it (a small shared source folder added to both source sets in `build.gradle` is the clean way; it then has to be public). In the client test the game's own `ShellClient` is created from the environment and is unavailable there (`client-test.sh` removes the `ARESOS_` variables), and with `aresos.disableDiscovery` (set for both test tasks) `AresOs` registers no list listener at all. So the test needs a way to hand the game a `ShellClient` that talks to the fake helper and gets the same wiring: `AresOs.mergeHelperApps` is the listener body (private; it does merge, My apps and pictures). `AppsTestAccess` (a mixin accessor on `AresOs`, client tests only) is where the existing accessor for `apps` lives.
- A Unix socket path is at most about 100 bytes: tests must use a short temp folder.
- The server game tests of My apps (`MyAppsGameTests`) run in a batch of their own (`aresos-test:my_apps`) and each runs start to finish inside one tick: they swap the app list of the whole game (`aresos.appsConfig` plus `AresOs.saveMine(Map.of())`, an edit that changes nothing and so just reads the file) and raise the global counter, which would disturb the multi-tick tests of the `desktop` batch. In the server game tests nobody is the singleplayer host, so host-only paths cannot run there.
- A fake player's sent packets are in `EmbeddedChannel.outboundMessages()`; `MyAppsGameTests.Fixture.said` reads the chat from there.
- `AresOs.java` and `AresOsClient.java` are shared with packages 32 and 33. This package's lines there: `saveMine`, `takeIn`, `mergeHelperApps`, the two merge lines and the log line in `onInitialize`, `generatedIcons` (`volatile`, `.generated()`), `.then(AppCommands.app())`, one line in `give`; in the client `IconReload.register(...)`.
- The Lunar Client launcher (an AppImage) may run all day; the dev scripts refuse only for the game itself. Other sessions run client tests often: `pgrep -af 'cage|gradlew'` shows them.
- A quick check without Gradle is possible for classes that need only Gson (javac against the jars in `~/.gradle/caches/modules-2`); it is no substitute for `build.sh`.

## Verification so far

`mod/dev/build.sh` on `4924357a` (the code commit of A4 and the game part of B2; the commits after it change only the README, one message string in `build.gradle` and these notes), 2026-11-13: exit 0, `BUILD SUCCESSFUL in 43s`. 87 unit tests: 81 passed, 6 skipped (the Windows-only catalogue tests). Server game tests: "All 42 required tests passed" (the 38 from before and the four of `MyAppsGameTests`). Two runs before it failed and were fixed at the cause: a compile error in `WindowsCatalogueFixesTest` (it compared the old return value of `IconPack.generate`), and builder 2's own oversized-PNG fixture, which was under 1 MiB until its noise used all four channels.

`mod/dev/client-test.sh` on the same code, **once**: exit 0, `BUILD SUCCESSFUL in 6m 49s` (RTX 4060, headless). The log has the "client checks passed" lines of 01c, 04, 04c, 07, 07b, 08, 09, 09b, 09c and 09d; the stack traces in it are the launch failures those tests provoke on purpose. The first try was refused for memory (exit 75), the second waited for another package's run. There is no client test of this package yet, so the run shows only that the existing twelve classes still pass under the new inventory rule. The two runs the brief asks for are still to do, after B3.

The screenshots that run wrote were put back (`git checkout`) and its untracked copies under `reviews/04`, `07`, `08`, `09` removed: a run numbers its files by test order, so it leaves new names beside the tracked ones.

