# 53d report: Super opens a search over the world (helper and mod)

Brief: `briefs/53d-world-search.md`. Branch `pkg/53d-world-search`. Step 1 (the bar and its looks) was built by a
Claude agent on Fable 5.2 (design work); step 2 (the rules) by a Claude agent on Opus. **The owner chose the Bar look
(board #382, 2026-11-19, "Bar (recommended)")**; the other two looks are gone from the code and the pictures.

## Done

### Step 1: the bar (Fable)

- **The best-hit rule**, `mod/src/main/java/dev/aresos/config/AppSearch.java`: `ranked(apps, query)` and
  `best(apps, query)`. My apps before other programs; then a match at the start of the name or of a word before a
  match inside a word; then by name. `best` is null for a blank query and for no hit. `find` and `matches` are
  unchanged, so the Apps screen behaves as before and can move to `ranked` later.
- **The screen**, `mod/src/client/java/dev/aresos/client/WorldSearchScreen.java`: a search box and the hits (My apps
  first, then "Other programs"), the best hit framed with the word "Enter" on its line. Enter opens the best hit, a
  left click any hit, Escape goes to the world (`setScreen(null)`, never back to a screen open before). Blank query:
  no list, Enter does nothing. No hit: the line `No program matches "…".`, Enter does nothing. The pointer is free,
  `isPauseScreen` is false. A long list scrolls (wheel, arrows, Page Up/Down); the frame stays on the best hit. It
  closes by itself when the world stops being an AresOS desktop.
- **Opening on the world's screen:** the bar calls `AresOsClient.launchOnWorldScreen(id)` → `AppLauncher` (a plain
  launch on Windows) → `ShellClient.open(appId, SCREEN_WORLD)`. `open_app` carries `"screen": "world"` only on a
  connection that agreed to minor 2; the pending open keeps the hint for every resend.
- **No crosshair under the bar:** `mod/src/client/java/dev/aresos/client/mixin/SearchCrosshairMixin.java`.

### Step 2: the rules (Opus)

- **The helper, `os/config/usr/libexec/aresos-shell`:**
  - `SearchSignal`: `main()`'s first statement is `search = SearchSignal.install()`, which installs the SIGUSR1
    handler before `parse_args` and `build()`. The handler only sets a flag. `signal.set_wakeup_fd` on a
    non-blocking, close-on-exec pipe wakes the serving loop; `Server` registers the pipe in its selector, drains it,
    and after each round's events reads the flag (so a signal from before the pipe existed is not lost) and calls
    `Helper.search()`. `return_to_desktop` is not used.
  - `Helper.search()`: signals within 300 ms count as one (from the first of them). It acts only for a desktop on
    minor 2 that offered `shell_search` and has sent `world_ready` on that connection (a heartbeat with
    `"ready": false` takes it back), with window tracking on and the world's window known; otherwise it logs why and
    does nothing. It requests the world's activation with the existing `activate_window`; the compositor's
    activation then reaches `follow_windows` like a click on the world, whose `uncover()` minimizes a maximized or
    fullscreen window on the world's screen (`covering(known_screen=True)`) and sends the usual `shell_focus`
    `desktop_activated`. Then `shell_search` is sent. With the world already active it is sent at once (see
    JUDGMENT-CALL on uncovering then). A failed activation request sends nothing.
  - The capability: offered only to a minor-2 desktop with window tracking, never to a view; `emit_to` refuses it
    below minor 2 (`LATER_CAPABILITIES` checks only minor 1).
  - `open_app`'s `"screen"`: accepted only from a minor-2 desktop, only `"world"`; anything else, from a view or a
    minor-1 desktop, is `malformed`. It is kept in the launch's journal entry, through a pending check (the first
    request's), duplicates and a journal reload. Replies are unchanged. No placement.
- **The wire contract (1.2):** `docs/design/LAPTOP-HOME.md` section 5, two new bullets. Example messages in
  `mod/src/test/resources/shell-1.2/` (`desktop-hello-*`, `shell-search-event`, `open-app-world-*`,
  `open-app-bad-screen-*`, README lines), read by the helper's contract test and the mod's `WorldSearchShellTest`.
- **The mod:**
  - `ShellClient` offers `shell_search` and calls `Listener.search()` for the event only on a minor-2 connection.
  - `ShellFocusClient.register` hands the event to the client thread: `WorldSearchScreen.requested(client)`.
  - `SearchMoment` (new, `mod/src/client/java/dev/aresos/client/SearchMoment.java`) holds the rule: ignored while
    `ShellFocusClient.readyWorld(client)` is null; ignored while the bar is open already (what he typed stays);
    ignored while a typing screen is open (`ChatScreen`, `AbstractSignEditScreen`, `BookEditScreen`, `AnvilScreen`,
    `AbstractCommandBlockEditScreen`, or any screen whose focus is an `EditBox` or `MultiLineEditBox`); otherwise an
    open container closes the normal way (`player.closeContainer()`) and the bar opens over any other screen.
  - The Menu and Hotbar looks, the `Look` enum and `lookForTests` are removed; Bar is the screen's only look.
  - `FakeHelper` offers `shell_search` on minor 2.

## The looks (owner's choice: Bar, board #382)

Step 1 drew three, all doing the same and differing in where things stand and what is behind them:
- **Bar (chosen, recommended):** a 260-wide box a fifth of the way down the sharp world, on a dark plate with a thin
  light rule that grows downward with the hits (the Apps screen's headings, up to nine lines, then a scroll bar).
- **Menu (removed):** the Apps screen's sibling: blurred menu background, a title, the list in the game's dark band.
- **Hotbar (removed):** as wide as the hotbar and standing on it; the hits stack upward, a rule instead of headings.

Pictures (`reviews/53d-world-search/screenshots/`): `0095_53d-bar-1-empty.png`, `0096_53d-bar-2-several-hits.png`,
`0097_53d-bar-3-no-hit.png`, `0098_53d-bar-4-long-list.png`. The Menu and Hotbar pictures (0099–0106) are deleted.

## Verified

Step 2, on the last code (all runs on the laptop under AresOS):
- **Helper, in-process, each module by name** (`python3 -m unittest <module>` in `os/tests`):
  `test_aresos_shell_search` (new) 15 OK; `test_aresos_shell_views` 23 OK (its contract test reads the new
  examples); `test_aresos_shell` 74 OK; `test_aresos_shell_protocol` 21 OK; `test_aresos_shell_home` 13 OK;
  `test_aresos_shell_windows` 33 OK; `test_aresos_shell_hardening` 26 OK; `test_aresos_shell_review_fixes` 31 OK,
  `_2` 16 OK, `_3` 12 OK, `_4` 11 OK; `test_aresos_shell_launch_hints` 13 OK; `test_aresos_shell_discovery` 36 OK.
  Never the whole `os/tests`, never `test_owner_update`, no helper subprocess, no real `WAYLAND_DISPLAY` or
  `XDG_RUNTIME_DIR` (the `main()` test uses a temporary runtime folder and stops at a patched `build()`).
- **What `test_aresos_shell_search` covers:** the handler in place before `parse_args` and `build()` (both patched
  to read `signal.getsignal(SIGUSR1)`); the handler only sets the flag (no event, activation, minimize or write);
  a real `signal.raise_signal(SIGUSR1)` wakes `Server.step` through the pipe, which is drained, and only then the
  loop acts; a flag from before the pipe is not lost; the capability offered only to a minor-2 desktop with window
  tracking, never to a minor-1 desktop or a view; the event only to a minor-2 desktop that offered it, never to a
  view; nothing with no desktop, no `world_ready`, `world_ready` taken back by a heartbeat, a new connection
  without its own `world_ready`, no window tracking, or no known world window; a maximized window on the world's
  screen minimized after the compositor's activation, a small window and a maximized window on the other screen
  left; no `shell_focus` of its own; the world already active; a failed activation sends nothing; coalescing at
  300 ms; `open_app`'s `screen` valid, seven bad values, from a view, from 1.1, and kept through a duplicate, a
  pending check with its duplicate, and a journal reload (no second launch).
- **Mutation check:** five deliberate breaks of the helper (no minor-2 gate in `emit_to`, the handler installed
  after `build()`, no uncover with the world active, no per-connection `world_ready`, the hint not stored) each
  made `test_aresos_shell_search` fail; the file was restored from git after each.
- **`mod/dev/build.sh`:** `BUILD SUCCESSFUL in 3m 40s` (320 unit tests, 6 Windows-only skipped, and the server
  game tests). New: `SearchMomentTest` (5) and `WorldSearchShellTest` (6: minor 2 and `shell_search` offered
  both ways, the example event reaches the listener, a minor-1 connection ignores it, `"screen": "world"` as the
  example shows and only on minor 2, the hint kept on a resend after a reconnect). The first build failed one
  check, `ShellListTest.theExampleMessagesAreWhatTheClientSendsAndReads`, which lists the 1.2 capabilities the
  client offers beyond the 1.1 example: `shell_search` was added to that list.
- **`mod/dev/client-test.sh`, the full suite, run 1:** `Client tests ended with exit code 0 after 12 min 58 s`
  (RTX 4060, headless), with `53d world search checks passed: shell_search opens the bar, in four states; …`.
- **Run 2:** `Client tests ended with exit code 0 after 12 min 57 s`, the same line. Both runs wrote the four Bar
  pictures byte for byte as committed.
- **The client test** (`WorldSearchClientGameTest`, still last in the suite) now opens the bar only through
  `FakeHelper`'s `shell_search` and the session's own wiring (`ShellFocusClient.register`): the four pictures;
  typing and Enter make `FakeHelper` record `open_app` with `"screen": "world"` and the bar closes; a click does
  the same; Escape returns to the world, also over the inventory, which closes first; `shell_search` leaves the
  chat (with typed text) alone, and leaves an open bar and its typing alone.
- After each suite run only the tracked pictures it rewrote were restored, and the untracked pictures it wrote
  for older packages were deleted.

Step 1 (Fable): `mod/dev/build.sh` passed and the full client suite passed twice (13 min 8 s and 13 min 5 s).

## Not verified (needs the laptop trial, once 23c's keybind and `search` command land)

Nothing sends SIGUSR1 until 23c. To try on the laptop with the monitor, pressing and releasing Super alone:
1. From inside the world with the pointer captured: the bar opens over the world; the pointer is free; Escape
   returns to the world and captures the pointer again on the next click.
2. From a small app window over the world: the world gets the keyboard, the app stays where it is, the bar opens.
3. From a maximized app on the world's screen: the app is minimized, the bar opens; Alt+Tab brings the app back.
4. From an app on the other screen (the laptop's): that app stays; the world on the monitor gets the keyboard and
   the bar.
5. With the pointer on the laptop screen: the bar opens over the world on the monitor; Enter opens the app on the
   world's screen (needs 23c's placement; until then it opens where labwc puts it).
6. Typing right after Super from a terminal: the first letters land in the bar, not in the terminal (the activation
   races the typing; this is the one to watch).
Also: Super twice quickly opens it once; Super while chat or a sign is open does nothing; Super over the inventory
closes it first; Super during a home switch or loading does nothing.

## JUDGMENT-CALL

- **The look: Bar**, the owner's choice (board #382). Menu and Hotbar are deleted; bringing one back means
  restoring it from commit `810384a3` (step 1's last).
- **Nothing is listed until he types** (step 1). Alternative: his apps at once. One line in `WorldSearchScreen.show`.
- **"Other programs", each program once** (step 1): the Apps screen says "All programs" and repeats his apps there.
- **What counts as a start** in the best-hit rule (step 1): every word of the query begins the name, a word of it,
  or one of his short names; a generic name or keyword match counts as "inside a word". Changing it is
  `AppSearch.startsWords`.
- **The crosshair is hidden while the bar is open** (step 1, a small HUD mixin).
- **With a helper below minor 2 the mod leaves the hint out**, so the app opens where the pointer is instead of
  the launch failing as `malformed` (step 1).
- **With the world already active, Super uncovers at once.** A maximized window that opened over the active world
  without taking the focus would otherwise hide the bar, and no activation would come to run `uncover()`. It is the
  same `uncover()`, by the same rule (only windows known to be on the world's screen), not a second minimize path.
  Alternative: never minimize when the world is active (the bar could then open unseen).
- **A focused text box counts as typing** beyond the brief's five screens: Super does nothing from the Apps screen's
  search or the creative inventory's. Alternative: replace those screens with the bar (his typing there is lost).
- **Super is his own choice, like a click on the world:** it clears a restored desktop's one-time "keep the app in
  front" rule (B2) and its follow-up, so Super right after a desktop restart is not undone.
- **Coalescing counts from the first signal of a burst**, so a held or hammered key opens the bar at most every
  300 ms; ignored signals count too.
- **A duplicate `open_app` keeps the first request's hint**, whatever the duplicate says (it is the same launch).

## PLAN-GAP

- **The placement on the world's screen is 23c's** (`linux-aresos`): moving the pointer to the world's output just
  before the launch, and moving the launch's first window once if it maps elsewhere. 53d only carries the hint: it
  is in the journal entry (`entry['screen'] == 'world'`, keyed by client and request ID), where 23c's placement can
  read it from `Helper.journal.entries` when the launch's first window is claimed in `follow_windows`. Until then
  an app from the bar opens wherever labwc puts it, which with the pointer on the laptop screen is the laptop screen.
- **The sender is 23c's:** the supervisor's `aresos-desktop search`, starting the helper with SIGUSR1 ignored, and
  the `rc.xml` keybind. Nothing sends the signal before then.
- The brief's "the world's window is known" uses the desktop's ready toplevels (`Windows.of(SHELL)`), as
  `return_to_desktop` does; with two (a restored desktop beside the old one) it activates the last, as that does.

## Open questions

- None blocking. The owner may want his apps listed before he types (one line, see JUDGMENT-CALL).

## Hosted run

One hosted run of the OS checks was started after the last code push and not watched:
`gh workflow run "OS image" --ref pkg/53d-world-search -f checks_only=true`, run **44434514723**
(https://github.com/Ares-Empire/AresOS/actions/runs/44434514723). Its result is for the lead to read.

## The lead (2026-11-19)

The owner chose Bar (board #382). JUDGMENT-CALLs beyond the brief are accepted as technical: an immediate uncover when the world is already active (same `uncover()` rule), a focused text box counts as typing, Super clears a restored desktop's keep-in-front rule as a click on the world would, coalescing from the first signal of a burst, and a duplicate `open_app` keeps the first hint.
