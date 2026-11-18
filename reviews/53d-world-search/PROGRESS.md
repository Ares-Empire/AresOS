# 53d progress: the search over the world

Brief: `briefs/53d-world-search.md`. Branch `pkg/53d-world-search`. Step 1 (the bar and its looks, a Claude agent on
Fable 5.2: design work) is written; **step 2 (the rules, Opus) is not started.** No pull request is open yet.

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
