# 34 My apps: builder handoff

Working notes for the next builder. Deleted in the last commit before the PR is ready.

## State (after builder 1)

| Step | What | State |
|---|---|---|
| A1, A2 | `ShellClient` speaks 1.1; `FakeHelper` speaks 1.0 and 1.1; example messages; `ShellListTest` | **Done**, committed |
| A3 | What the system said is kept on the app (`AppDefinition.system`, `SystemInfo`) and saved (`AppsConfig.merge`) | **Done**, committed |
| B1 | apps.json schema 3 (`mine`, `baseline`), the move from schema 2 and 1, `restoreLegacy` for both backups | **Done**, committed |
| B2 (file part) | Day one, the baseline and "joins later" inside `AppsConfig.merge(file, list, detailed, today)`; `AppsConfig.mine`; `pins` makes it his; `MyApps` holds the rules | **Done**, committed |
| A4 | The helper's icon path feeds the pixel icon; pack regenerated and reloaded, throttled | Not started |
| A5 | Vanilla look by group for an app without a picture (`catalogue/AppGroup`, `LinuxAppCatalogue.look`, `AppGroupTest`) | **Done**, committed |
| B2 (game part) | Wiring in `AresOs`, the inventory, removal from Live and saved Build, Q, commands, chat line | Not started |
| B3 | The Apps screen and the client game tests with screenshots | Not started |
| Last | README, REPORT, build once, client tests twice, fetch and merge, delete this file, PR | Not started |

**Verification so far.** See "Build result" at the end. The client game tests have not run on this branch yet: nothing visible has changed so far, and the inventory still holds every app as before (`AppInventory` is untouched).

## What is left, in order

1. (The build is green at builder 1's last code commit; nothing to fix first.)
2. **A4 icons.** `SystemInfo.icon` is the helper's path. Keep `AppDefinition.icon` as the owner's (or Windows discovery's) own path, which wins; otherwise use `system.icon`. Read the helper's file only if it is a regular file, at most 1 MiB, and decodes as a PNG of at most 512 x 512; anything else is "no icon". Put that reader in one public place in `icon/` so package 36 can use it for logos (`zone/LogoBuilder.readIcon` still reads `icon()` only, and `zone/` is off limits here: say so in the report). `IconPack.generate` already stamps by content hash; it needs to say whether anything changed. Client side: after each complete list regenerate off the render thread, then `client.reloadResourcePacks()` only if something changed, at most once every few seconds, changes in between sharing one reload. `AresOs.generatedIcons` is a plain static read from two threads: make the swap safe. Items already in the inventory keep their old `ITEM_MODEL` until `AppInventory.populate` refreshes them, so refresh after the pack changed.
3. (A5 is done. `AppGroup.of(app)` is there for packages 35 and 36 too.)
4. **B2 game part.**
   - `AresOs.mergeHelperApps` and the startup merge must call `AppsConfig.merge(file, definitions, shell.detailed(), LocalDate.now())` and act on `Merged`: one chat line per ID in `joined` when `dayOne` is false ("Spotify is new. ..."), none on day one. The log line in `onInitialize` still says "Migrated apps.json to schema 2". Keep `AresOs.java` to registration lines: put the logic in its own class.
   - `AppInventory.populate` must place only apps with `mine` (first free slot 9 to 35, never the hotbar except pinned ones as today), and take out items of apps that are not his.
   - Removing: out of the Live inventory and out of the saved Build snapshot in `ModeInventories.stored`. Never while `ModeInventories.pending()`; never losing or duplicating another item; a removal that cannot be done now (pending switch, open container, item on the cursor, player in Build so Live is the stored one) is remembered and done at the next safe moment (tick). `ModeInventories` has no API to edit the inactive snapshot: it needs one small method that decodes `stored`, maps the item lists and re-encodes with the same "serialize, parse back, compare" check `transact` uses.
   - Q on an app item: the item comes back. Either cancel the drop server-side for `AppItems.APP` of a `mine` app, or let populate put it back and delete the dropped entity; cancelling is simpler and cannot duplicate.
   - Commands `/aresos app add|remove|list` with completion (add: not his; remove and list: his), host only, AresOS world only, as `ZoneCommands` does it. `AresOs.java` gets one `.then(...)` line.
   - Pinning: `AppsConfig.pins` already sets `mine`. Check `AppInventory.savePins` still does the right thing for an app that is not his (possible with `/aresos give`).
   - An app the system no longer lists: nothing to do in the file (it stays). Its item says it is unavailable with the helper's reason when used, as today.
   - Existing tests that must change with the rule "the inventory holds My apps and nothing else": `AresOsGameTests.catalogueFillsInventory...` (42 unpinned fixtures), `RealAppsClientGameTest` (expects the unpinned `fixture-site` in slot 9 and 40 fixtures in the inventory), `RealAppsFixesClientGameTest`, `ModeInventoriesClientGameTest`. Mark their fixtures with `.withMine(true)` where the test needs the item; do not weaken what they check.
5. **B3 screen and client tests**, then the last step of the table.

## Decisions taken (all are in code or in the examples' README now, except the last three)

- **The envelope.** `hello` carries `aresos-shell/1.1` and minor 1; every later message carries the negotiated minor. In `Connection.send`.
- **Capabilities.** The mod offers `app_details`, `apps_changed`, `list_paging` and requires none. The helper sends an event only to a client that offered its name, so `apps_changed` must be offered.
- **1.1 is the `minor` of the hello reply.** With minor 0: no `cursor`, `next` and the new fields ignored, `apps_changed` ignored, `App.system` is null. With minor 1 `App.system` is never null (`SystemInfo.UNKNOWN` when the helper said nothing).
- **Listing.** One class (`ShellClient.Listing`) takes pages for both the first list of a session (synchronous, in `session()`) and refreshes (replies routed in `dispatch` by `claim`). Three restarts, 64 pages, 1024 programs, then the old list stays and `awaitApps` fails with `list_incomplete` on a first list. The connection stays up either way, so apps still open.
- **`desktop_id` carries the `.desktop` ending** on the wire (HUB.md 3.7 writes `google-chrome.desktop`; the table in 4.6 drops it). Package 35 strips it for the name rules.
- **Program IDs** are the helper's choice; the mod needs `[a-z0-9_-]{1,64}`, unique and stable. The examples use the lower-cased desktop file ID with dots as hyphens.
- **The baseline is written only by a complete list with origins (negotiated 1.1).** On Windows and with a 1.0 helper nothing joins by itself and no baseline is written. Otherwise the 1.0 helper on the laptop today would set the baseline with three apps and the 1.1 helper's first list would add the 11 Flatpaks Bazzite ships. PLAN-GAP for the report.
- **A starter** is `browser`, `terminal` or `notepad` (`MyApps.STARTERS`, needed at the schema move), or `source` `image`.
- **"Newly appears"** means the ID was not in the apps file. A program that left and comes back keeps its `mine`.
- **A new program whose origin is not known does not join by itself** (`MyApps.joinsLater`). JUDGMENT-CALL for the report, small.
- **An entry without `mine` in a schema-3 file reads as his** (he wrote it by hand). The move and every merge write `mine` explicitly.
- **`pinned` implies `mine`** (enforced in `AppDefinition`); taking an app out of My apps unpins it (`AppsConfig.mine`, `withMine(false)`).
- **`system` is replaced whole** by each detailed list and left alone by a list without origins.
- **What the older mod does with a schema-3 file** (read from its code, `AppsConfig.parse` before this package): it refuses with "Invalid apps.json; original left intact: Unsupported schemaVersion (expected 2)", leaves the file untouched, starts with no apps, and says "AresOS apps disabled: ..." in the chat on join. Goes in the report.
- Not in code yet: (1) the 1 MiB and 512 x 512 limits apply to the helper's icon path only, the owner's own `icon` is read as today; (2) the Apps screen scrolls or pages, builder's choice, say which; (3) `AppDefinition.icon` stays separate from `system.icon`.

## Things the code does not show

- `FakeHelper` is package-private in `mod/src/test/java/dev/aresos/shell/`. The gametest source set gets `src/test/resources` (see `build.gradle`) but not `src/test/java`, so the client game tests cannot use it as it is. The brief wants the client tests "with the fake helper": make it reachable without copying it (a small shared source folder added to both source sets in `build.gradle` is the clean way; it then has to be public). In the client test the game's own `ShellClient` is created from the environment and is unavailable there (`client-test.sh` removes the `ARESOS_` variables), so the test needs a way to hand the game a `ShellClient` that talks to the fake helper, through a test accessor on `AresOs.shell` plus the same listener wiring.
- A Unix socket path is at most about 100 bytes: tests must use a short temp folder (Gradle's is `mod/build/tmp/unit-tests`).
- `AresOs.java` and `AresOsClient.java` are shared with packages 32 and 33: registration lines only.
- The Lunar Client launcher (an AppImage) may run all day; the dev scripts refuse only for the game itself.
- Other sessions run client tests often. `pgrep -af 'cage|gradlew'` shows them; wait for them before `build.sh` (one heavy step at a time).
- A quick check without Gradle is possible for classes that need only Gson: compile with `~/.local/opt/jdk-25/bin/javac` against the Gson and JUnit jars in `~/.gradle/caches/modules-2` and run JUnit's launcher. It is no substitute for `build.sh` and must not be reported as verification.

## Build result

`mod/dev/build.sh` on `42f71234` (the last code commit of builder 1, with A1 to A3, A5, B1 and the file part of B2), 2026-11-13: exit 0, `BUILD SUCCESSFUL in 39s`. 80 unit tests: 74 passed, 6 skipped (the Windows-only catalogue tests). Server game tests: "All 38 required tests passed". An earlier run on `e7148941` (without `AppGroup`) was green too (72 passed, 6 skipped, 38 game tests); the first run of all failed in two Windows catalogue tests that pinned `aresos-shell/1.0` and the schema-2 entry, fixed in `e7148941`. `mod/dev/client-test.sh` has not run.
