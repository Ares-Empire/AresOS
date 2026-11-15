# 35: Slash names

Empire board brief 283. Mod package. `docs/design/HUB.md`, section 6, row 4. It starts from a `main` that contains packages 32, 33 and 34 (the flat home, the gate logo, My apps).

**Builder:** Codex (gpt-6.1-sol, xhigh): the rules are written out in full in the design, with a worked list to test against, and nothing here is about looks. **Review:** a fresh reviewer that isn't the builder.

## Why

The owner (2026-11-13): "I also think in the minecraft chat "/appname" should open it. ("/chrome" opens chrome). not necessarily the full name but a good name like lunar, dc (for discord), discord, chrome etc."

**Goal:** in the AresOS world he presses T, types `/dc` and Discord opens; `/chrome`, `/discord`, `/lunar` work the same, and Tab completes them. `/open <name>` opens any program on the laptop, also one that isn't his. `/apps` lists his apps with their commands, and a click on a line opens that app. `/aresos app name discord chat` gives an app a name of his own. Minecraft's own commands keep working, always.

## Read first

`docs/design/HUB.md` sections 2.7 and 4 (all of it; 4.6 is the worked list) and 2.4 (My apps). Then, in the mod as package 34 left it: how My apps and the apps file are held (`config/`, `item/`), what the system says about a program (the fields of HUB.md 3.8), how an app is opened today from a doorway and from the hotbar (`zone/ZoneLaunchPayload.java`, `client/AresOsClient.java`), and how `/aresos` commands are registered and limited to the host (`AresOs.java`, `world/HomeCommands.java`).

## Build

1. **The name rules of HUB.md 4.1 to 4.4** as pure functions with unit tests: the main name (steps 1 to 5, the word lists, the number fallback), the extra names (the built-in table, the starters' IDs), what "valid", "free" and "reserved" mean, and the order when several apps get names at once. Every row of the worked list in 4.6, and the examples in the paragraph after it, is a test case; where the rules as written give another answer than the list, the rules win and the difference goes into the report as a PLAN-GAP.
2. **Names are given once and saved** with the app (`names` in the apps file, the first is the main one; HUB.md 3.5). An app gets its names when it joins My apps; they do not change by themselves, also not when the program is renamed. An app that leaves My apps keeps its saved names for its return but has no command while it is out.
3. **Real commands** (HUB.md 4.5): each name of each of his apps is a command on the game's own list, for the host of an AresOS world only, in Live and Build mode. A name is registered only if the list has no command of that name at that moment; a name that lost to a real command gets the app's next-best name by the rules. When My apps or a name changes, the commands follow and the command list is sent to him again, without a rejoin.
4. **Running a name** tells his own game to open the app, with the message a doorway sends, minus the visit and the return teleport: after `/dc` and after closing Discord he stands where he stood. The game accepts it only in singleplayer in an AresOS world, as today; no server can open a program on his laptop. When the app is already open the same request goes out as from the hotbar, and the program decides.
5. **`/open <name>`** opens any program the system lists: by the name the rules would give it, by its squeezed full name, or by the unique start of either; if several fit, it lists them as lines he can click. It completes program names.
6. **`/apps`** lists his apps in the chat, one line each: the name, its commands, and its group (HUB.md 2.2's rule; the place comes with package 36). A click on a line opens the app.
7. **`/aresos app name <app> <new name>`** adds a name and makes it the main one; **`/aresos app unname <name>`** removes one (the last name of an app can't be removed; say so). A name that is not valid, is reserved or belongs to another app is refused, and the message says why and, for a clash, which app holds it.
8. **Reserved** are every command the game has at that moment and AresOS's own: `aresos`, `home`, `go`, `open`, `apps`. `home` and `go` are reserved now and built in package 37.
9. **The Apps screen** (package 34) shows each of his apps' main short name beside its name, and its search also looks in the short names.
10. **The logo's sign:** a gate built with `/aresos logo` shows the app's main short name with the slash on its second line (the plan already has the field, `zone/GatePlan`; package 33 left it empty). Keep one function that gives an app's main short name, for package 36. A gate that already stands keeps its sign as it is.
11. **The client test suite's time limit** goes from 10 to 20 minutes (`mod/build.gradle`, one line): the suite takes about eight minutes now and every package adds to it.

## Acceptance

- Unit tests for point 1 as described, and for clashes: with a vanilla command (`help`, `list`, `time`), with AresOS's own, between two apps, and with a name he gave.
- Server game tests: the commands exist for the host in an AresOS world and not in a normal world; a name that equals a vanilla command is never registered and the vanilla command still runs; adding and removing an app adds and removes its commands without a rejoin; `/open` with one match, several and none; `name` and `unname` including every refusal.
- Client game tests with screenshots under `reviews/35-slash-names/screenshots/`: the chat with `/d` typed and the completion showing `/dc` and `/discord`; `/dc` opening the app once through the fake launcher and no teleport afterwards; `/apps` in the chat; the Apps screen with short names.
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes **twice**.
- `mod/README.md` describes the commands.
- `reviews/35-slash-names/REPORT.md` in the AGENTS.md format, with a "try this" note for the owner.

## Out of scope

`/go`, `/home`, the H key and places (package 37), where logos stand (36), the OS helper (30). No change under `os/`.

## Already decided

- HUB.md 2.7 and section 4. The word lists and the table are data in one place.
- Minecraft's commands always win; this is not up for trade.

## If unsure

Give an app a longer, duller name rather than one that could shadow anything.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-35-slash-names`, branch `pkg/35-slash-names`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- Build and test with `mod/dev/build.sh` and `mod/dev/client-test.sh` only (`mod/README.md`, "On Linux"). Never pass `--force`. Never run `./gradlew` directly.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commit messages name the model that built them in a trailer.
