# 34: My apps

Empire board brief 282. Mod package. `docs/design/HUB.md`, section 6, row 3, together with the mod's side of the interface additions (HUB.md 3.8).

**Builder:** a Claude agent (Fable 5.2): it changes the saved app list and takes items out of his two saved inventories, the area that needed the most fix rounds so far (packages 09 to 09d). **Review:** a fresh reviewer that isn't the builder.

## Why

Once the system lists the owner's installed programs (package 30, the OS helper), the mod will know 60 to 200 of them. Today every known app becomes an item in his inventory and the "Apps…" screen is a plain paged list.

**Goal:** his inventory holds his apps and nothing else: on day one Chrome, Terminal, Notepad, Lunar Client and Discord. E, "Apps…" shows a search box, his apps, and below them every program on the laptop; a click makes a program his, a right-click takes it out again. A program he installs later joins by itself, with one line in the chat. Each app item shows the program's own icon.

## Read first

`docs/design/HUB.md` sections 2.4, 2.5 (the table), 3.5 ("With the apps"), 3.7 and 3.8. Then `mod/src/main/java/dev/aresos/`: `AresOs.java`, `shell/ShellClient.java`, `catalogue/`, `config/`, `icon/`, `item/`, `mode/` (how the Live and Build inventories are saved and swapped) and `mod/src/client/java/dev/aresos/client/AppsScreen.java`, `RuntimeIconPack.java`; the tests `ShellClientTest`, `FakeHelper`, `AppsConfigTest`, `ModeInventory*`, `RealApps*ClientGameTest`. On Linux the app list comes from the OS helper; `os/config/usr/libexec/aresos-shell` shows what it sends today (1.0).

## Build

### A. The mod speaks `aresos-shell/1.1` (HUB.md 3.8)

1. `ShellClient` offers minor 1, pages `list_apps` with `cursor` and `next`, restarts when the revision changes (three times at most), reads the optional entry fields, ignores unknown ones, and lists again on `apps_changed` (at most once every two seconds). With a 1.0 helper everything behaves as today.
2. The test helper (`FakeHelper`) speaks 1.0 and 1.1. Commit the example messages under `mod/src/test/resources/shell-1.1/` as HUB.md 3.8 lists them; the helper package will test against the same files, so they are the contract. Tests: both versions, paging over several pages, a revision change in the middle, a page that never ends (bounded), 150 programs, hostile values (oversized strings, wrong types, a path that isn't absolute, 1000 categories).
3. What the system said about an app (origin, categories, generic name, keywords, desktop file ID, program file name, terminal, icon path) is kept on the app in memory and saved with it (HUB.md 3.5, "what the system said"), so groups and names can be worked out when the helper is down.
4. **Icons:** an app's `icon` path from the helper feeds the item's pixel icon the way a Windows app's icon does today. The mod reads that file only if it is a regular file, at most 1 MiB, and decodes as a PNG of at most 512 x 512; anything else means "no icon". When the list or a picture changes while the game runs, regenerate the icon pack and reload it once, not more often than every few seconds, and not at all when nothing changed.
5. An app without a picture gets a vanilla item look by its group (a short table in one place; `minecraft:paper` when nothing fits). The three starters keep today's looks.

### B. My apps (HUB.md 2.4 and 3.5)

1. **The apps file** gets a new schema with `mine` per app and `baseline` for the file, written atomically with a backup of the old file as the schema-2 move did. Moving over: an app that is pinned today or is a starter starts with `mine` set; nothing else is lost (IDs, names, looks, pins, Windows commands, unknown fields). A file written by this package and opened by the older mod must fail safely the way a future schema does today; say in the report what the older mod does with it.
2. **Day one:** when the first complete program list arrives, `mine` is set for the starters and for what he installed himself (`source` `user` or `flatpak-user`), and `baseline` is written. After the baseline, a program that newly appears with any `source` but `image` and `system` joins My apps by itself, with one chat line that names it. Programs with `source` `system` never join by themselves. On Windows, and with a 1.0 helper, every program counts as "came with the system": only pinned apps and starters are his.
3. **The mod only acts on a complete list.** A helper that is down, a list that never completed, or a paged list that was restarted changes nothing in My apps.
4. **The inventory holds My apps and nothing else.** Adding an app puts its item in the first free inventory slot (not the hotbar); with no free slot it has no item and says so. Removing an app takes its item out of the Live inventory and out of the saved Build inventory safely: never while a mode switch is pending, never losing or duplicating another item, and a removal that can't be done now is done at the next safe moment. Dropping an app's item (Q) never removes the app; the item comes back.
5. **The Apps screen** as HUB.md 2.4 describes it: a search box on top (it looks in the name, the generic name and the keywords; short names join in package 35), then "My apps", then "All programs" by name; each row shows the icon and the name. Left-click on a program that is not his adds it and keeps the screen open; left-click on one of his picks up its item as today; right-click on one of his removes it. Keyboard: typing goes to the search box, Enter acts on the only match, Escape closes. It must stay usable with 200 programs (scrolling or pages; your choice, say which).
6. **Commands:** `/aresos app add <app>`, `/aresos app remove <app>`, `/aresos app list` (his apps, one line each), with completion over the right list each. The host only, in an AresOS world, as the other `/aresos` commands.
7. **Pinning** a program that is not his makes it his. Unpinning changes nothing else.
8. A program the system no longer lists stays in the file with its fields; its item stays and says it is unavailable when used, with the helper's reason, as today. (Taking down its logo is package 36.)
9. Windows behaviour is unchanged except for the rule in point 2. Platform code stays behind the existing interfaces.

## Acceptance

- Unit tests for A1 to A5 and for the schema move (a schema-2 file with pins, unknown fields and Windows commands goes over and back to what the rules say; the backup exists; a broken file is left untouched).
- Unit or server game tests for day one, the baseline, a new program after the baseline per `source`, an incomplete list changing nothing, add and remove including the item in the saved Build inventory, a pending mode switch during a removal, a full inventory, Q on an app item.
- Client game tests with screenshots under `reviews/34-my-apps/screenshots/`, with the fake helper and icons the tests draw themselves: the inventory on day one (five items); the Apps screen with 150 programs, with a search typed, after an add and after a remove; an item's pixel icon in the hotbar. Look at every screenshot yourself.
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes **twice**.
- `mod/README.md` describes My apps, the Apps screen and the three commands.
- `reviews/34-my-apps/REPORT.md` in the AGENTS.md format, with a "try this" note for the owner and a list of every file under `shell/`, `config/` and `item/` you changed.

## Out of scope

The OS helper and anything under `os/` (package 30 builds the helper to HUB.md 3.8 and to your example messages). Short names, `/name`, `/open`, `/apps` (package 35). Logos and places (33 and 36): save nothing about places yet. The flat world (32).

## Already decided

- HUB.md 2.4, 3.5, 3.7 and 3.8. The example messages you commit are the contract for the helper: once the PR is open, changing one means saying so in the report.
- No new dependency.
- On AresOS the mod never starts a program itself and never reads a desktop entry itself; what it knows about programs comes from the helper.

## If unsure

Keep an app and its item rather than remove them; leave the apps file as it was rather than write a half-moved one.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-34-my-apps`, branch `pkg/34-my-apps`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- Build and test with `mod/dev/build.sh` and `mod/dev/client-test.sh` only (`mod/README.md`, "On Linux"). Never pass `--force`. Never run `./gradlew` directly.
- Packages 32 (the flat home) and 33 (the gate logo) are built at the same time in other worktrees. Stay out of `world/`, `zone/` and the home screens. `AresOs.java` and `AresOsClient.java` are shared: keep your changes there to registration lines.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
