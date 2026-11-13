# 34: My apps: report

Package 34, brief `briefs/34-my-apps.md` (empire board brief 282). Built by three Claude agents (Fable 5.2) in turn.

The branch still carries the merge of `pkg/29-linux-dev-rig` (PR #44, open when this was written): the Linux build scripts in `mod/dev/` come from it. Merge #44 first, or review this PR against that branch.

This file was committed by the orchestrator from the last builder's text (the pull request's description), because the builders' file tool refuses to write report files.

## Try this

On the laptop, in the AresOS world:

1. Press **E**. Your inventory holds your apps and nothing else. On the first start with the new helper those are Chrome, Terminal, Notepad, Lunar Client and Discord. (Until the helper speaks 1.1, package 30, it is the three starters and what you had pinned.)
2. Click **Apps…** above the inventory. Type `pdf`: the list shrinks to the programs that deal with PDFs, also those without "pdf" in their name.
3. Click one. It gets a check mark, appears under "My apps" at the top, and its item is in your inventory. The screen stays open. The line above Done says "Added … to My apps."
4. Right-click it under "My apps". It is gone from there and from the inventory, and still under "All programs".
5. Clear the search and click one of your apps: you are back in the inventory holding its item. Put it in the hotbar.
6. In the chat: `/aresos app list`, `/aresos app add ` and Tab, `/aresos app remove ` and Tab.
7. Try to throw an app away with Q. Nothing happens.

## Done

**The protocol (A1 to A3).** `shell/ShellClient.java` offers `aresos-shell/1.1`: it pages `list_apps` with `cursor` and `next`, starts again when the revision changes (three times, then the old list stays), reads the optional entry fields into `config/SystemInfo`, ignores unknown ones, and lists again on `apps_changed`, at most once every two seconds. With a 1.0 helper nothing changes. The example messages are in `mod/src/test/resources/shell-1.1/` with a README; they are the contract for package 30 and have not changed since they were first committed. The fake helper (`mod/src/testShared/java/dev/aresos/shell/FakeHelper.java`) speaks both versions and serves the unit tests and the client game tests.

**Icons (A4, A5).** `icon/AppIcons` is the one reader of an app's picture: the owner's own `icon` as before, otherwise the system's path if it is a regular file of at most 1 MiB that is a PNG of at most 512 x 512. Startup and later lists use `icon/IconRefresh` in the background; each file read has a three-second deadline and its own disposable worker. The game (`client/IconReload`) reloads changed resources at most every five seconds. Items already in the inventory get the new look on the next tick. An app without a picture looks like its group (`catalogue/AppGroup`, one table; `minecraft:paper` when the system said nothing).

**The apps file (B1 to B3).** `config/AppsConfig` writes schema 3: `mine` per app, `system` per app, `baseline` for the file. A schema-2 or schema-1 file is moved with a backup beside it (`apps.json.schema-<version>-<id>.bak`); pinned apps and the starters start as his. Schema-2 fields, including Windows commands, are preserved. A schema-1 file migrated on Linux drops Windows commands from the working file: they survive only in the untouched backup, as OS-BASE.md B1 specifies. `AppsConfig.merge` takes one complete list: the first one with origins is day one (`config/MyApps`), later a new program joins unless it came with the image or the system. An incomplete list never reaches it.

**My apps in the game (B2, B4, B6 to B8).** `item/MyAppsGame` never edits an inventory on the spot: a change raises a counter, and on a tick on which it is safe (no mode switch pending or running, his own inventory menu, nothing on the cursor or in the crafting grid) each player's inventories are brought in step. Items of programs that are not his leave the inventory he holds and, through the new `ModeInventories.mapInactive`, the saved one; in Live his apps without an item get one in the first free slot 9 to 35. With no free slot the app is his without an item and the chat says so once. Q is refused in three places (`mixin/AppDropMixin`, `AppInventory.keeps…`). `item/AppCommands` has `/aresos app add|remove|list` with completion over the right list. A program that joins later gets one chat line, at most five at once.

**The Apps screen (B5).** `client/AppsScreen.java`, rewritten. One scrolling list built from the game's own widgets (`HeaderAndFooterLayout`, `EditBox`, `ObjectSelectionList`, the vanilla list background, separators and check-mark sprite): the title and a search box on top, the heading "My apps" with his apps by name, the heading "All programs" with every program by name. A row is the program's item icon, its name and, in gray, the generic name the system gives ("Document Viewer"); under "All programs" a check mark marks the ones that are his.
- Left-click on a program that is not his: `item/MyAppPayload` to the server, `MyAppsGame.asked` adds it, the screen stays open. Left-click on one of his: `TakeAppPayload` as before, back in the inventory with the item on the cursor. Right-click on one of his: removed. Right-click on another program: nothing.
- Typing always goes to the search box. The search (`config/AppSearch`) looks in the name, the generic name and the keywords; every word typed must be found. Enter is a click on the program if exactly one is found; the text is then selected so the next letters start a new search. Up, Down, Page Up and Page Down scroll. Escape and Done go back to the inventory.
- **200 programs: scrolling, not pages.** The wheel moves three rows a notch (the game's default is half a row), the scroll bar can be dragged, and a search starts at the top.
- The line above Done explains the clicks and shows for five seconds any chat line that arrives while the screen is open ("Added Okular to My apps.", "No free inventory slot: …", "Spotify is new and joined My apps."), because the chat itself is blurred behind the screen.
- When the list changes under him, the row under the pointer stays where it is if the list can scroll that far. The second action of a double-click is ignored, including when reflow puts a neighbour under the pointer in a short list.
- The item of one of his apps is picked up when the mouse button is let go, not when it goes down. The inventory screen places what is on the cursor on a release; the old screen closed on the press, so the release could put the item straight into the slot under the pointer.
- The screen does not pause the game: a pause would stop the integrated server and an add would get no answer while the screen is open.

**Windows.** Unchanged except B2's rule: nothing joins by itself; his are the pinned apps, the starters and what he adds.

### Files changed under `shell/`, `config/`, `item/` and `mode/`

- `shell/ShellClient.java`
- `config/AppDefinition.java`, `config/AppsConfig.java`, `config/RestoreLegacyApps.java`; new: `config/MyApps.java`, `config/SystemInfo.java`, `config/AppSearch.java`
- `item/AppInventory.java`; new: `item/AppCommands.java`, `item/MyAppsGame.java`, `item/MyAppPayload.java`
- `mode/ModeInventories.java` (one new method, `mapInactive`, with its helpers; the switch itself is untouched)

Shared files, registration lines only: `AresOs.java` (`saveMine`, `takeIn`, `mergeHelperApps`, the merge and log lines in `onInitialize`, `generatedIcons` now `volatile`, `.then(AppCommands.app())`, one line in `give`) and `client/AresOsClient.java` (`IconReload.register(...)`). Nothing under `os/`, `world/`, `zone/`, `mod/dev/` or the home screens.

### What an older mod does with the new apps file

Read from its code (`AppsConfig.parse` before this package), not run: it refuses a schema-3 file with "Invalid apps.json; original left intact: Unsupported schemaVersion (expected 2)", leaves the file untouched, starts with no apps, and says "AresOS apps disabled: …" in the chat on join. To go back for good, the `restoreLegacyApps` task restores the schema-2 backup and keeps the schema-3 file beside it (`mod/README.md`).

## Verified

All on the laptop (AresOS, Java 25, RTX 4060), 2026-11-13, through `mod/dev/build.sh` and `mod/dev/client-test.sh` only.

- **`mod/dev/build.sh` on the final code (`895e3f03`): exit 0**, `BUILD SUCCESSFUL in 23s`, server game tests "All 42 required tests passed" (the 38 from before and the four of `MyAppsGameTests`). Gradle did not run the unit tests again in that build, because only the client test had changed since the build of `be1a17d9` (exit 0, `BUILD SUCCESSFUL in 42s`): 86 unit tests passed, 6 skipped (the Windows-only catalogue tests), none failed. Five of the 86 are the new `AppSearchTest`.
- **`mod/dev/client-test.sh` twice in a row on the final code (`895e3f03`), headless: exit 0 and exit 0**, 7 min 1 s and 7 min 2 s, `BUILD SUCCESSFUL in 7m` both times. Each log has eleven "client checks passed" lines: 01c, 04, 04c, 07, 07b, 08, 09, 09b, 09c, 09d and the new "34 client checks passed: …".
- Two earlier runs while the screen was refined passed as well (`8c641ab0`, 7 min 1 s; `be1a17d9`, 7 min 2 s). No client run of this builder failed. The commits after `895e3f03` add screenshots and remove the handoff notes; they change no code.
- **Suite time now: 7 min 1 s to 7 min 2 s** of the ten-minute limit of `runClientGameTest`. It was 6 min 49 s before the new test; `MyAppsClientGameTest` takes 13 to 14 s (one flat world).
- **What `MyAppsClientGameTest` asserts**, with the unit tests' fake helper on a real socket, 150 programs in four pages and pictures the test draws itself:
  - day one: exactly Chrome, Terminal, Notepad, Lunar Client and Discord are his, in memory and in the apps file, with a baseline; five items in the inventory, only the pinned Notepad in the hotbar; no chat line; Discord's item shows the helper's picture; a program without a picture has no pixel icon;
  - the Apps screen: five rows under "My apps", 150 under "All programs" in order of name, the search box has the keyboard; Down, Page Down, Page Up and Up scroll; the wheel reaches the last program; "pdf" finds three programs by name and keyword and starts at the top; Enter with three matches does nothing; a real left click adds a program, keeps the screen open, shows it under "My apps", says "Added Okular to My apps." in the screen and leaves the keyboard with the search box; "archiv" finds Ark by its generic name and Enter adds it and selects the search text; a real right click on one of his removes it from My apps and from the server's inventory and leaves it under "All programs"; a right click on a program that is not his does nothing; a left click on one of his puts its item on the cursor in the inventory, and placing it in the hotbar pins it; Escape goes back to the inventory, Escape again closes it;
  - the commands as the host: completion of `app add` offers the 144 programs that are not his (and only "okular" for "ok"), `app remove` exactly his six; `app list` prints "My apps: 6" and one line each, with ", in the hotbar" for the pinned ones; `app add`, a second `app add`, `app remove` and an unknown ID say their lines and reach the apps file; with every slot full the program becomes his without an item, the chat says "No free inventory slot: Okular has no item for now.", and no other slot changes;
  - later: after `apps_changed` with two new programs the one installed for his user gets exactly one chat line ("Spotify is new and joined My apps.") and an item; the one that came with the system is listed and not his; the item that was already in the inventory gets the pixel icon once the pack was made again and the game reloaded it by itself (the model `aresos:apps/spotify`, the texture in the game's resources);
  - Q on the app's item in the hotbar: it stays, on the client and on the server, and nothing lies on the ground.
- **Screenshots** in `reviews/34-my-apps/screenshots/`, from the second final run, each looked at by the builder (960 x 540, the layout of the laptop's screen at the game's own scale):
  - `0033_34-day-one-inventory.png`: five items, Notepad in the hotbar, the "Apps…" button;
  - `0034_34-apps-150-programs.png`: the screen as it opens;
  - `0035_34-apps-scrolled-to-the-end.png`: the last rows, the scroll bar at the bottom, an app without a picture with its group's look;
  - `0036_34-apps-search-pdf.png`: the search typed;
  - `0037_34-apps-after-add.png`: the added program under "My apps" and with a check mark under "All programs", and the line "Added Okular to My apps.";
  - `0038_34-apps-after-remove.png`: after the right-click;
  - `0039_34-hotbar-pixel-icons.png`: the pixel icons of Notepad and Ark in the hotbar and the chat line of the program that joined.
- From the earlier builders, in the same green build: `ShellListTest` and `ShellClientTest` (both protocol versions, paging, a revision change, a list that never ends, 150 programs, hostile values), `AppsConfigTest` (the schema move and back, the backup, a broken file left alone, day one, the baseline, a new program per `source`), `AppIconsTest`, `IconRefreshTest`, `AppGroupTest`, and the server game tests `MyAppsGameTests` (add and remove with the saved Build inventory, a pending mode switch, a full inventory, Q).

## Not verified

- **The real helper.** Everything ran against the fake helper. The helper on the laptop speaks 1.0 until package 30 lands; with it this build behaves as before (three starters, no origins, no baseline).
- **The owner's own screen.** The screenshots are 960 x 540 at the game's scale 2: the layout of 1920 x 1080 at scale 4, with half the pixels. Fullscreen on the laptop, a trackpad instead of a wheel, and how the reload of the resource packs feels in play (the game shows its loading bar for a moment when a newly installed program's picture arrives) need his eyes.
- **The older mod on a schema-3 file** was read from its code, not run.
- **No test:** the tidy-up after a login that restored the Live inventory (he quit in Build); `giveBack` while a mode switch is pending; the Windows start (its code path changed only by `IconPack.Result`); the Apps screen narrated or driven with Tab; the row under the pointer keeping its place (only seen in a list too short to scroll, where it cannot); the mouse release reaching the inventory (the test's click presses and releases within the Apps screen).
- The six Windows-only catalogue unit tests skip on Linux, as before.

## JUDGMENT-CALL

1. **A new program whose origin the system does not say does not join My apps by itself.** An app nobody asked for in the inventory is the worse mistake, and he can add it with one click. Rejected: treating "unknown" as "he installed it". Changing it later is one line in `MyApps.joinsLater`.
2. **`/aresos give <app>` makes the program his.** Otherwise the given item would vanish at the next tidy-up, since the inventory holds My apps and nothing else. Rejected: refusing `give` for programs that are not his. One line to change.
3. **Q is refused instead of "drop and put back".** The item stays in its slot or on the cursor, preserving its pin. This covers player drops only; app items in external containers can produce copies and world drops (see Review fixes 1). The cost: a click outside the inventory window with an app's item on the cursor does nothing; he puts it in a slot or closes the inventory. Rejected: letting it fall and making a new item, which loses its hotbar place.
4. **"All programs" lists every program, his included, with a check mark.** HUB.md 2.4 calls it "the full list", and a removed app "stays in All programs". The cost: a search that finds one of his shows it twice. Rejected: listing only the programs that are not his, which makes a row vanish under the pointer on every add. Changing it is one filter in `AppsScreen.ProgramList.show`.
5. **One list that scrolls, in one column, instead of pages or a grid.** A row has room for the generic name now and for package 35's short name. Rejected: the old three-column pages (names cut after about 15 letters) and pages in general (a search result should not have a page 2). At the laptop's scale about nine rows show at once, so 200 programs without a search are over 20 screens; the search and the scroll bar are the way through.
6. **Superseded by Review fixes 1:** a double-click adds the first program and ignores its second action. The old implementation could act on a neighbour after reflow. A subsequent deliberate click can still pick the item up.
7. **Escape and Done go back to the inventory, not to the world**, as the old screen did: the new items are there to be pinned. A second Escape closes the inventory.
8. **The chat line of a program that joins** reads "<name> is new and joined My apps." HUB.md 2.4 also wants its place and its command; those come with packages 36 and 35.

## PLAN-GAP

1. **The baseline is written only by a list with origins (a 1.1 helper).** The brief says "when the first complete program list arrives". With the 1.0 helper on the laptop today that list has three starters; setting the baseline then would make the 1.1 helper's first list add the Flatpaks Bazzite ships as "newly appeared".
2. **The chat line cannot name the place and the command yet** (HUB.md 2.4): places are package 36, short names package 35.
3. **Logos cannot use the helper's picture yet.** `zone/LogoBuilder.readIcon` reads the owner's `icon` only, and `zone/` is off limits here. Package 36 should call `AppIcons.read(app).image()`.
4. **Fixed in Review fixes 1:** startup subscribes before connecting and applies all lists through that callback. The startup readiness wait never reapplies an old snapshot.
5. **The chat is unreadable behind any screen** (the game blurs it), and HUB.md 2.4 only says "the chat says where". The Apps screen repeats the lines itself; the brief did not ask for that.
6. **HUB.md 2.4 gives each row a short name.** That is package 35; the row keeps room for it on the right.
7. **Package 07's client test clicked through the old pages.** It now finds its app with the search and Enter and asserts the same pick-up and pin; its screenshot is now called `07-apps-search`. The tracked `reviews/07-real-apps/screenshots/0001_07-apps-page-2.png` still shows the old screen, as package 07's record.
8. **Fixed in Review fixes 1:** the "Apps…" button is above the inventory, with four pixels between its bottom and the panel's top.

## Open questions

- Should "My apps" in the screen say which apps are in the hotbar? `/aresos app list` does; the screen does not.

## Left in `.work/`

Nothing: this package downloads nothing and has no `.work/` folder.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH

## Review fixes 1

Built by Codex, GPT-6.1 Sol, on `pkg/34-my-apps` for PR #52, following `briefs/34-review-fixes-1.md` and `REVIEW-1.md`. This section supersedes the original report where the behavior or verification differs.

### Done, per finding

| Finding | Change and regression coverage |
|---|---|
| 1 | Every JOIN starts with removal and Live addition work pending. A successful initial Live population credits only its captured catalogue version and leaves saved-inventory removal work pending; Build population and full inventories cannot claim completion. `everyLoginRemovesStaleAppsFromBothInventories` saves a deferred removal, explicitly loads the saved player, and exercises the real JOIN callbacks for both ordinary Live login and Build-to-Live restoration; ordinary items survive. The server fixture has no home, so it calls production's pre-login `enterLiveBeforeLogin` itself. |
| 2 | Apps pickup refuses a nonempty crafting grid; `/aresos give` moves an existing active-inventory item, and refuses busy inventory state. The client test sends an actual pickup payload with Notepad in the crafting grid, then executes `give` twice and asserts one item. Containers are an accepted limit, below. |
| 3 | Startup queues cached pictures before starting helper callbacks; it does no icon-file I/O itself. Reads use disposable daemon workers with a three-second deadline, retain the byte/PNG/dimension limits, and open the final component with `NOFOLLOW_LINKS` where supported. Tests cover a file replaced by a symlink, a file replaced by a FIFO, an interruption-resistant blocked read, and a succeeding later read while the blocked worker remains stuck. |
| 4 | A newly discovered starter ID becomes mine with a 1.0 helper too, without a baseline. Existing removed starters stay removed through repeated 1.0 discovery and the first detailed list. The test starts with no apps file and a real fake-helper socket negotiating 1.0. |
| 5 | Initial population still places pins at the previous population moments. Later reconciliation only removes unwanted stacks, refreshes presentation in place, and fills slots 9–35. A server test leaves a configured pin outside a now-free hotbar and verifies add, remove and icon refresh never move it. |
| 6 | Missing items leave addition work pending. Safe ticks check for room and retry as soon as there is a free slot, keeping warning suppression. The full-inventory test frees a slot without calling `MyAppsGame.changed()` for recovery. Another test covers a returned cursor item over a full inventory and during an unacknowledged mode switch, including return to Live. |
| 7 | The second action of a double-click is ignored. The client test adds Xournal++ from three PDF matches in a list too short to scroll, confirms Okular moved under the same pointer, sends the second click there, and checks that neither neighbour became mine. |
| 8 | Every 1.1 page requires a nonempty string revision. Missing, null, numeric, object and empty revisions are tested both at startup and on either page of a refresh; no partial list is published, no baseline is set at startup, and the prior apps file remains byte-for-byte unchanged. |
| 9 | Production subscribes before `start()`. Immutable `AppList` snapshots carry their own details flag; the startup wait only waits, and never merges its old result. The client test invokes production's start method, checks the first list before any repair event, applies a second startup list, then confirms returning to the old readiness result cannot replace the saved list. A unit test retains a 1.0 snapshot across reconnect to 1.1. |
| 10 | Documentation corrected; migration code stays as designed in OS-BASE.md B1. For schema 1 on Linux, Windows commands survive only in the original backup, not the working file. The existing migration test still asserts this. |
| 11 | A pending open remembers the last connection it was sent on. Normal sends and both replay paths use one writer-owned send-once method. The deterministic callback/latch test forces the normal send before startup replay, uses the later `world_ready` as a writer barrier, and asserts one received request for the ID on that connection. Existing reconnect tests still require replay on a new connection. |
| 12 | Announcements retain names beyond the five-per-tick limit. The client fixture installs seven programs at once and checks one named line per program, with no anonymous remainder. |
| 13 | Add/remove and give completion apply the same host/world restriction as execution. Client checks cover the owner in an ordinary world, a guest and console in an AresOS world, and positive host completion. |
| Button | The 70×20 Apps button is centred above the inventory, four pixels clear of its top edge. The client asserts its bounds and saves the inventory screenshot. |

Changed production files in this round under the requested core directories: `shell/ShellClient.java`; `config/AppsConfig.java`; `item/AppInventory.java`, `item/AppCommands.java`, `item/MyAppsGame.java`. Also changed the helper/startup/command registration in `AresOs.java`, `icon/AppIcons.java`, the description in `icon/IconRefresh.java`, `client/AppsScreen.java`, and the drop mixin's overly broad comment. No mode-switch implementation change, no protocol fixture change, and no `mod/dev/` change.

### Verified

All commands ran in this worktree, without sudo, through the approved scripts. `free -g` was checked before each heavy step; they ran sequentially. Java 25 comes from the scripts. Their systemd scope cleanup stops their game/compositor/Gradle processes; no separate Gradle command was run.

- Preliminary `mod/dev/build.sh` attempts: `BUILD FAILED in 7s` (test used a removed Fabric `getButtons` method), `BUILD FAILED in 24s` (new reconnect fixture had not loaded saved player data), `BUILD FAILED in 48s` (protocol round-trip fixture waited for focus rather than returning a focused launch), then `BUILD SUCCESSFUL in 45s`. These were fixture corrections; assertions and production requirements were retained.
- Before client verification, code `3dcb2f62` passed `mod/dev/build.sh --rerun-tasks` twice: `BUILD SUCCESSFUL in 53s` and `49s`, 45 required server tests and 94 applicable unit tests passing. The first client attempt then printed `BUILD FAILED in 20s`, exit 1 after 21 seconds: `Unsupported real client retained Live`. The login counter was still pending after the desktop marker had successfully populated Live, so a later tick refilled an intentionally edited slot. Fixed production completion bookkeeping and added `completedInitialLivePopulationDoesNotRepeatOnTheNextTick`; no existing assertion was changed. The subsequent intermediate build printed `BUILD SUCCESSFUL in 48s`, with all 46 server tests passing.
- Revised production code `68846be4`: `mod/dev/build.sh --rerun-tasks` twice in succession, exit 0 both times: `BUILD SUCCESSFUL in 50s` and `BUILD SUCCESSFUL in 48s`. Both printed `All 46 required tests passed :)`. Both reran all 100 unit tests: 94 passed, 6 Windows-only tests skipped, 0 failures/errors (JUnit XML totals).
- The next headless attempt printed `BUILD FAILED in 32s`, exit 1 after 33 seconds: `Timeout recovery retained inactive Live`. It had passed the previous unsupported-client assertion. Its ordinary mode-recovery fixture omitted the owned starter while reserving an empty pickup slot; required login reconciliation correctly filled that slot. The fixture now places owned apps in other slots before its original snapshot. Every exact inventory and 12-emerald assertion remains. The exact original assertions were retained.
- Code and fixtures `94cb29a0`: `mod/dev/build.sh --rerun-tasks`, exit 0, `BUILD SUCCESSFUL in 49s`, followed by `mod/dev/build.sh`, exit 0, `BUILD SUCCESSFUL in 21s`. Both printed `All 46 required tests passed :)`. The first reran all 100 unit tests (94 passed, 6 Windows-only skipped, 0 failures/errors); the second reported `:test UP-TO-DATE`.
- The third headless attempt printed `BUILD FAILED in 1m 52s`: the existing package-07 test timed out waiting for an unpin. Recovery, restart, shell-focus, logo and package-07b checks had passed. Automatic overflow recovery now fills slot 9 after URL pinning, so the following two-click unpin swaps with a real item and leaves it on the cursor. The package-07 test now asserts this automatic refill and completes the three-click swap; all original unpin, pin and restart assertions remain.
- Final code and fixtures `3e118445`: `mod/dev/build.sh` twice, exit 0 both: `BUILD SUCCESSFUL in 24s` and `BUILD SUCCESSFUL in 23s`, each with all 46 server tests passing and `:test UP-TO-DATE` (unit source/production code unchanged since the repeated full unit runs above).
- Final headless client verification and screenshot inspection: pending at this report checkpoint; results will be added before the final push.

### Known limits and not verified

- **Containers are not policed.** A chest, another container or nested storage may hold an app item. Reconciliation searches only the player's inventory and may supply a fresh item while that stored copy remains; breaking the container may drop the stored copy into the world. There is no global item uniqueness guarantee. The player-drop/Q rule remains, and `mod/README.md` documents the limit explicitly.
- **Icon threat model:** broken or stuck files, not a hostile program running as the owner's own user. Pre/post path attributes, final-component no-follow, handle size and bounded reads help with ordinary replacements. They do not constitute a security boundary against an adversary rewriting directories or files. A filesystem call that ignores interruption may leave a daemon worker blocked; later reads use a fresh worker and never wait for it.
- No real helper, real app launch, Windows startup, owner's session/window, trackpad feel, narrated/Tab-driven Apps interaction, or older-mod downgrade was run. The helper and icons are test fixtures. The screenshots use the headless client.
- No additional product decision beyond the follow-up brief. No new plan gap or open question was found in these fixes.
- `.work/` contains no files over 500 MB; no large downloads were made.
