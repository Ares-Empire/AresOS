# 53d progress: the search over the world

Brief: `briefs/53d-world-search.md`. Branch `pkg/53d-world-search`, pushed. **Step 1 (the bar and its looks, a Claude
agent on Fable 5.2: design work) is done. Step 2 (the rules, Opus) is not started.** No pull request is open.
**The owner picks the look from the pictures below before this package merges.**

## Done in step 1

- **The best-hit rule**, `mod/src/main/java/dev/aresos/config/AppSearch.java`: `ranked(apps, query)` and
  `best(apps, query)`. My apps before other programs; then a match at the start of the name or of a word before a
  match inside a word; then by name (`BY_NAME`, the ID settling equal names). `best` is null for a blank query and
  for no hit. `find` and `matches` are unchanged, so the Apps screen behaves as before; it can move to `ranked`
  later. Unit tests: `mod/src/test/java/dev/aresos/config/AppSearchTest.java` (four new).
- **The screen**, `mod/src/client/java/dev/aresos/client/WorldSearchScreen.java`: a search box, the hits (My apps
  first, then "Other programs"), the best hit framed with the word "Enter" on its line. Enter opens the best hit, a
  left click any hit, Escape goes to the world (`setScreen(null)`, never back to a screen that was open before).
  Blank query: no list, Enter does nothing. No hit: the line `No program matches "…".`, Enter does nothing. The
  pointer is free, `isPauseScreen` is false. A long list scrolls with the wheel, the arrow keys and Page Up/Down; the
  frame stays on the best hit, which is what Enter opens wherever the list is scrolled to. It closes by itself when
  the world stops being an AresOS desktop.
- **Opening on the world's screen:** the bar calls `AresOsClient.launchOnWorldScreen(id)`, which goes through
  `AppLauncher.launchOnWorldScreen` (a plain launch on Windows) to `ShellClient.open(appId, ShellClient.SCREEN_WORLD)`.
  The pending open keeps the hint, so a resend after a reconnect carries it without more code. `open_app` gets
  `"screen": "world"` only on a connection that agreed to minor 2; on an older one the key is left out and the app
  opens where the pointer is (the brief makes the key `malformed` there). Every other launch sends no `screen`.
- **The client test**, `mod/src/gametest/java/dev/aresos/test/WorldSearchClientGameTest.java`, last in the client
  suite: the pictures below, and Enter, a click, Escape, blank and no-hit against `FakeHelper` on minor 2 with
  made-up programs ("Test Web 1", "Test Tool 1" to 40) and generated icons.
  Pictures go to `reviews/53d-world-search/screenshots/` (`aresos.worldSearchReviewDir` in `mod/build.gradle`).

- **No crosshair under the bar:** `mod/src/client/java/dev/aresos/client/mixin/SearchCrosshairMixin.java`. Two looks
  leave the world sharp, and the crosshair showed through the hits and crossed out a letter (first pictures). The
  pointer is free meanwhile, so there is nothing to aim at.

## The looks

All three do the same and differ only in where things stand and what is behind them. Each line is the Apps screen's
row: icon, name, his `/name` in gold, the kind of program in gray. The best hit has a white frame and the word
"Enter" at its right end. The pictures use the laptop screen's size (1920 x 1080 at the game's scale 4) at noon, as
in his flat home.

**Bar (the default; the one I recommend).** A search box 260 wide, a fifth of the way down the screen, on a dark
plate with a thin light rule around it. The world behind it stays sharp: no blur, nothing dimmed. With nothing typed
the plate is just the box. Typing lets it grow downward: the Apps screen's two headings ("My apps", "Other
programs", each with its count and a rule on both sides), up to nine lines, then the game's own scroll bar. Why: it
is what the design calls it, a search bar over the world. The world stays the home screen he is in, the framed hit
stands right under what he types and he reads downward as in any list, and it is wide enough for the name, the
command and the kind. It stands above the middle, so the hotbar and the ground stay in view.

**Menu.** The Apps screen's sibling: the game's blurred menu background, the title "Search", a box 200 wide, the
hits in the game's dark band between its two separator lines, 300 wide as the Apps screen's rows, and a gray line
at the bottom ("Enter opens the framed program · Esc closes"). Why: nothing in it is new, he knows it from E,
"Apps…". Against it: it blurs the whole world away for one line of typing, so Super feels like opening a menu
rather than searching over the world, and AresOS would have nearly the same screen twice.

**Hotbar.** The box is exactly as wide as the hotbar (182) and stands on it. The hits stack upward, the best one
right above the typing; there is no room for headings, so a thin rule sets his apps apart from the other programs.
The world is sharp. Why: in AresOS apps are hotbar items, so the search reads as the hotbar growing upward. It is
the most Minecraft-like of the three, the best hit never moves while he types, and two thirds of the world stay
free. Against it: 182 pixels are narrow (a long kind is cut, and the framed line drops its `/name` to fit
"Enter"), the list reads from the bottom up, and on a large monitor all of it happens at the screen's lower edge.

**Recommendation: Bar.** It is the only one that is both clearly a bar over the world and comfortable to read.
Hotbar is the charming alternative if he wants it to feel like part of the game's own HUD.

To change the default: `WorldSearchScreen.look`'s first value and the fallback in `lookForTests(null)` (two places
in one file). When the owner has picked, the other looks and the switch can be deleted.

### The pictures (`reviews/53d-world-search/screenshots/`)

| | Nothing typed | Several hits ("web") | No hit ("zzz") | A long list ("test", 47) |
|---|---|---|---|---|
| Bar | `0095_53d-bar-1-empty.png` | `0096_53d-bar-2-several-hits.png` | `0097_53d-bar-3-no-hit.png` | `0098_53d-bar-4-long-list.png` |
| Menu | `0099_53d-menu-1-empty.png` | `0100_53d-menu-2-several-hits.png` | `0101_53d-menu-3-no-hit.png` | `0102_53d-menu-4-long-list.png` |
| Hotbar | `0103_53d-hotbar-1-empty.png` | `0104_53d-hotbar-2-several-hits.png` | `0105_53d-hotbar-3-no-hit.png` | `0106_53d-hotbar-4-long-list.png` |

I looked at all twelve. In "several hits" his two apps come first, "Test Web 1" (a word starts with "web") before
"Cobweb Test" (inside a word), then the other programs the same way.

## Verified (step 1)

- `mod/dev/build.sh`: `BUILD SUCCESSFUL in 4m 28s` on the last code (unit tests and server game tests; the ten
  `AppSearchTest` tests pass). Earlier attempts ended with exit 75 (under 6 GiB free) and were retried after a wait.
- `mod/dev/client-test.sh`, the full suite, run 1: `Client tests ended with exit code 0 after 13 min 8 s` on the
  RTX 4060, with `53d world search checks passed` in its log.
- The full suite, run 2: not run yet.
- Before those, the new test ran alone twice to look at the pictures (the suite list cut down in the working tree
  only, restored after each run, never committed).
- After each suite run only the tracked pictures it rewrote were restored, and the untracked pictures it wrote for
  older packages under new numbers were removed.

## Calls for the report's JUDGMENT-CALL section (step 2 carries them over)

- **The look:** the owner's pick, see above.
- **Nothing is listed until he types.** Alternative: his apps at once. One line in `WorldSearchScreen.show`.
- **"Other programs", and each program once.** The Apps screen says "All programs" and lists his apps there again
  with a check mark; here a hit shows once, so the second group is the rest and is called that.
- **What counts as a start** in the best-hit rule: see "What step 2 needs to know".
- **The crosshair is hidden while the bar is open** (a small mixin on the HUD).
- **With a helper below minor 2 the hint is left out** and the app opens where the pointer is, instead of the
  launch failing as `malformed`.

## The test hook that opens the screen

`WorldSearchScreen.open(Minecraft client)`, on the client thread. It closes an open container the normal way
(`player.closeContainer()`, as the Apps screen does before it opens a program) and sets a new `WorldSearchScreen`.
It decides nothing about the moment: no check of `readyWorld`, of a typing screen or of a bar already open. The
client test calls it directly (`context.runOnClient(WorldSearchScreen::open)`).

The looks: `WorldSearchScreen.lookForTests(Look)` before opening; `null` brings the default back. What the test
reads: `found()`, `best()`, `note()`, `headings()`, `scrolled()`, `middleOf(id)`.

## What step 2 needs to know

- **Open from the event:** in the `shell_search` handler, on the client thread, apply the three ignore rules, then
  call `WorldSearchScreen.open(client)`. The container close and "Escape returns to the world" are already in it
  and in `onClose`.
- **The best-hit rule lives in `AppSearch.ranked`/`best`,** not in the screen. Its reading of "at the start": every
  word of the query begins the program's name, a word of its name, or one of his short names (`names()`). A program
  found only inside a word, or only through its generic name or a keyword, counts as "inside a word". A word starts
  at the name's start or after any character that is not a letter or digit. The other reading (a keyword's start
  counts as a start) would put a viewer with the keyword "pdf" level with "PDF Arranger"; change `startsWords` if
  the lead wants it.
- **The hint on a resend** is already kept (`PendingOpen.screen`, `openRequest(Connection, PendingOpen)`); step 2
  only has to test it. `ShellClient.open(appId, screen)` throws `IllegalArgumentException` for any screen but
  `"world"` or null.
- **`FakeHelper` already negotiates minor 2** when a test sets `helper.minor = 2`; it does not yet advertise
  `shell_search`, and it ignores `open_app`'s `screen` (the test reads it from `helper.received("open_app")`).
- **The client test for the event** can extend `WorldSearchClientGameTest`: its `search(context, query)` is the one
  place that opens the bar.
- Nothing was changed in the helper, in `ShellClient`'s capabilities, or in any keybind.

## Not in the code

- The bar shows nothing until he types (a list of every program would hide the world it is over). The owner may
  want his apps listed at once instead: one line in `WorldSearchScreen.show`.
- A click outside the bar does nothing; only Escape closes it. Arrow keys scroll and do not move the frame: the
  brief makes Enter open the best hit. Both are ideas for later, not built.
- The lines are drawn by the screen itself, not by the game's list widget, so the narrator reads the box and the
  title but not the hits.
