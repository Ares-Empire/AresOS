# Package 40: the real home screen (report)

Brief: `briefs/40-real-home.md`. Branch `pkg/40-real-home` from main `32fd16ec`. Builders: step 1 a Claude agent on
Fable 5.2 (causes of B and C, C and B's fix), steps 2 to 4 Claude agents on Opus 5.5 (step 2: paused only when covered;
step 3: D and the session preview; step 4: docs, final verification, this report, the pull request).

## Summary

Apps now open over the world. The world is the maximized, frameless window below every app; around a small app it
keeps moving, no pause menu, no blur, no minimized or black window, and the mouse is let go while an app is in front.
Clicking the world gives it the focus and leaves the apps above it. A maximized or fullscreen app on the world's screen
pauses the world without a screen and lets it draw 10 frames a second; activating the world then minimizes what covers
it. Every open that does not happen says why in the chat. In Live mode he flies, nothing hurts him, there is no hunger
and the HUD is the hotbar only; both modes walk 1.5 times faster. `run-hub.sh --session` shows all of it on his screen
inside a nested labwc with the image's `rc.xml`.

Point A of his try-out (booting into the world) is package 23's supervisor, on main, which reaches the laptop with the
next AresOS release. This package works with that supervisor's `fullscreen:false` maximized window.

## What changed, per point of the brief

**1. The world is the desktop: whole screen, no title bar, below every app.**
- `os/config/usr/share/aresos/labwc/rc.xml`: a second `aresos-desktop` rule with `ToggleAlwaysOnBottom`. The existing
  rule line is byte for byte unchanged (the image check greps for it). Assertion in `os/tests/test_aresos_desktop.py`,
  `test_recovery_terminal_shortcut_is_kept`: the new rule, exactly one `ToggleAlwaysOnBottom`, no `skipTaskbar`.
- Mod (`client/HomeScreen.java`, `mixin/WindowHomeScreenMixin.java`, `mixin/WindowIdentityMixin.java`): in a game the
  session started (its launch identity in the environment: the supervisor or `run-hub.sh`), the window is never the
  game's own fullscreen. A saved `fullscreen:true` is ignored, F11 does nothing, GLFW's auto-iconify is off. labwc
  makes the window maximized, frameless and always on bottom.

**2. An app opens on top of the world; the world keeps moving; the mouse is let go.**
- Mod (`HomeScreen`, `MinecraftFocusMixin`, `ShellFocusClient`): in a desktop world with the helper connected, focus
  loss never opens the pause menu; Esc still does. Mouse and held keys are let go when the helper's `shell_focus` says
  an app is in front (and when GLFW notices the focus leaving), and the mouse is captured again when the world has the
  focus back. Outside desktop worlds, without the helper, or in a game the session did not start, Minecraft's rule is
  untouched.
- **Paused only when covered** (owner's addition 2, 2026-11-15): see "Covered" below.

**3. Closing or minimizing the app puts him back in the world.** Unchanged helper paths (`shell_focus` return); checked
in the rig with an always-on-bottom desktop (Alt+F4, minimize, Terminal closing its last window).

**4. Clicking the world gives it the focus; the apps stay above it; Alt+Tab reaches every app.** Comes from
always-on-bottom. Checked in the rig; no helper change was needed for it.

**Covered (step 2, owner's addition 2; per screen and the minimize, orchestrator, 2026-11-15).**
- Helper (`aresos-shell`): keeps maximized, minimized, fullscreen and each window's outputs from foreign-toplevel. It
  binds every `wl_output` (before the manager, and screens plugged in later), because labwc names outputs only to a
  client that bound them. A window **covers** the world when it is maximized or fullscreen, not minimized, and shares
  an output with the world's window (`Windows.covering`). New event `shell_covered {covered}`, offered with window
  tracking to a 1.1 desktop only (`LATER_CAPABILITIES`) and sent only to a client that offered it: once after `hello`
  when covered (at the next tick, after the reply) and on every change.
- **Per screen:** a maximized window on the other screen does not cover the world.
- **PLAN-GAP 3, decided by the orchestrator:** when the world gets the focus while covered (Alt+Tab, any activation, the
  helper's own return after an app closed), the helper minimizes the windows that cover it on its screen
  (foreign-toplevel `set_minimized`). Smaller windows and windows on the other screen stay. Not at the helper's
  start-up, and not for a restored desktop that gives the focus back (`keep_foreground`).
- Mod: `ShellClient` offers `shell_covered`, tells listeners on every change, and resets to uncovered when the
  connection ends. `HomeScreen.covered(client)` (covered and `HomeScreen.active`) pauses the world without a screen
  (`MinecraftCoveredMixin`: `runTick`'s `Gui.isPausing()`; the integrated server follows `Minecraft.isPaused()`) and
  caps the frame rate at 10 (`FramerateCoveredMixin` on `FramerateLimitTracker.getFramerateLimit`, Minecraft's own
  limit for a minimized window). The sounds the pause stopped start again when it ends.
- Heartbeats and `world_ready` are unchanged while covered (linux-aresos's condition): they come from the shell
  client's timer and writer threads, and what they report (`ShellFocusClient.readyWorld`) does not look at the pause.
- Examples (`mod/src/test/resources/shell-1.1/`): `shell_covered` in both hello files, `shell-covered-event.json`, and
  a line in that folder's README.

**5 and B. Every app opens or he reads one chat line saying why.**
- Mod (`AresOsClient`, `ShellClient`): every failure is a chat line as well as the line over the hotbar ("Couldn't open
  Test App: it failed to start"). A program that started but showed no window the helper can tell is its own is
  reported after the open deadline as "it started, but no window of it appeared" instead of "no answer from the app
  helper". A walk-in packet the client refuses (not Live on the client) now says "Couldn't open <name>: logos open in
  Live mode" instead of nothing.
- Helper: logs every refusal (`not opened: no such app`, `not opened: <reason>`) and every launch that fails after
  starting (`failed after starting: ...`), so a log like his can tell "never asked" from "refused".

**6 and D. Live flies, takes no damage, no hunger, no hearts or hunger bar; both modes faster.**
- `mode/LiveMode.java`, `mixin/LiveAbilitiesMixin.java`, `ModeInventories.sync`, `DesktopWorld.setEnabled`, client
  `mixin/LiveHudMixin.java`. Only in a desktop world.
- Live stays `SURVIVAL` (its own inventory, no instant building, the creative inventory's slot packets refused) but gets
  creative's `mayfly` and `invulnerable`: a double space flies, nothing hurts him, and in 26.2 `invulnerable` also means
  no fire on him and no exhaustion.
- Both modes walk at **0.15 instead of 0.1** (walking 6.5 blocks a second, sprinting 8.4), set as the abilities' walking
  speed and the movement attribute's base together, as the game keeps them, so the field of view does not widen and
  nothing shows (no effect, icon or particles).
- Where: right after every `ServerPlayerGameMode.setGameModeForPlayer`, which every path that sets a game mode ends in
  (the constructor, loading his save, the respawn's copy, every switch, a rolled-back switch). That setter resets the
  abilities to the mode's own, so this is the one place that keeps them. A Live player who was flying keeps flying
  across a switch.
- His client resets its abilities whenever it hears the game mode. `ModeInventories.sync` sends the game-mode event after
  vanilla's abilities packet, and the respawn sends none, so both now send the abilities again afterwards.
- `/aresos desktop off` gives every player the game's abilities for his mode and its walking speed back at once; on
  again, Live's and the speed.
- The HUD in Live shows only the hotbar: `MultiPlayerGameMode.canHurtPlayer` and `hasExperience` (asked only by the HUD)
  answer false in Live on a desktop world, so hearts, armour, air, hunger and the experience bar are gone, as in
  creative.
- G still switches to Build mode, unchanged apart from the speed.

**7. `hub-try` shows the session** (`mod/dev/run-hub.sh --session`, `mod/dev/preview-window.py`,
`mod/dev/preview-env.sh`). The helper and the development client run inside a labwc of the run's own, nested in the
owner's desktop (wlroots' Wayland backend), with a copy of the checkout's `os/config/usr/share/aresos/labwc/rc.xml` and
nothing else of that folder (its `autostart` would start the session's supervisor). `preview-window.py` asks the outer
desktop (wlr foreign-toplevel `set_fullscreen`) to show the preview's window fullscreen and exits when that window
closes; `run-hub.sh` then asks the game's window in the preview to close (`preview-window.py --close aresos-desktop`, as
its close button), so the world is saved, and stops the rest. The plain window stays the default. Tested headless only.
**For `hub-try` (orchestrator):** add `--session` to its `run-hub.sh` call, before `"$@"`; it needs a checkout that has
commit `446486ae`.

**Docs (step 4).** `docs/design/HUB.md`: "Corrections from making it the home screen (package 40, 2026-11-15)" (what he
sees, with the numbers) and `shell_covered` in 3.8. `docs/design/OS-BASE.md`: section 4 (always-on-bottom desktop, no
fullscreen in a session, the helper's `wl_output` binding, covered and `set_minimized`) and a `shell_covered` row in B1's
message table. `mod/README.md`: `run-hub.sh --session`, a section "The home screen" (the two conditions, failures in
the chat, Live mode, the tests, the rig).

## Causes found

**C, what closed the world.**
- **The game window minimized itself.** His client was fullscreen (he switched it at 03:16:23: `debug.log` shows the
  monitor being selected). GLFW's X11 code iconifies a fullscreen window on every `FocusOut` (auto-iconify, on by
  default; Minecraft 26.2 sets no hint: `Window.createGlfwWindow` only sets `GLFW_VISIBLE`). In the rig a fullscreen
  client showed `['minimized', 'fullscreen']` in the foreign-toplevel list and a black screen
  (`screenshots/before-1-fullscreen-game-minimized-itself.png`), and minimized itself again within a millisecond of
  every unminimize.
- **No pause menu opened in his try-out**, although `pauseOnLostFocus` was on. His statistics: play time 2505 ticks
  against 2636 ticks with the world open, so the server was paused 6.5 s in all (the Esc at 03:16:18 and the one before
  quitting), not during the 12 s and 8 s an app was in front. Cause: when a Wayland window takes the focus, wlroots sets
  the X focus to PointerRoot. The X pointer is still inside the game window, so the game gets `FocusOut` followed at once
  by `FocusIn` (detail NotifyPointer), and GLFW takes that for the focus. Measured with an X event log in the rig
  (`rig/xwatch.py`). So under labwc **GLFW's focus says "focused" while an app is in front**; with the X pointer
  elsewhere the menu would open. The mod depends on neither: the helper's `shell_focus` decides.
- **Without always-on-bottom a click on the world hides the apps.** Windowed client, old `rc.xml`, a small test window
  in front: one click on the world and the world covered the test window (still open, behind it).

**B, the app that never opened.**
- The brief reads 03:18:09 as a walk-in. It was a typed short-name command for the third app: `command_history.txt`
  holds `/apps` and that command only, and `debug.log` has its client-command line in the same second. The lines at
  03:16:47 and 03:17:10 are `aresos:zone_return` packets, not typed commands.
- So the three `zone_launch` packets are two walk-ins (Terminal, Discord) and that typed command, and the helper's three
  `started` lines are exactly these. **No open of the fourth app was ever requested**: no walk-in packet, no command, no
  helper request, and only Notepad was in his hotbar.
- The world's saved data is in order: the app's zone and gate exist at "south, front row, right", built like the other
  six. He ran about 320 blocks in two minutes, far more than the two walk-ins need.
- In the rig a program of our own from a user desktop entry (absolute `Exec` through a symlink in a home folder), which
  the town put at the same place, opened by walking in and by its short name, before and after.
- **So the cause of his "didn't open" is not in the logs, and a failure for an app of that kind could not be
  reproduced.** What was found instead are the ways a launch ended without a word, all fixed (point 5 above): failures
  shown only over the hotbar for three seconds, some half a minute after he walked in; a program that starts but shows
  no window the helper can tell is its own (another app ID, a tray program, a copy already running elsewhere) reported
  after 45 s as "no answer from the app helper"; refusals and launches failing after starting left no helper log line; a
  walk-in packet the client refused was dropped silently.

## Tests, and which fail without the change

| Test | Fails without the change? |
|---|---|
| `ShellClientTest.aStartedProgramWithoutAWindowIsNotReportedAsAMissingAnswer` | yes (it was a `TimeoutException`) |
| `ShellClientTest.onlyAGameTheSessionStartedIsADesktopSession` | yes (new method) |
| `HomeScreenClientGameTest` (client test, last in the list), first parts: the pause menu opens on focus loss outside the home screen and not in it, the mouse is let go, Esc still opens the menu, F11 does nothing in a session, a failed launch leaves a chat line | yes for each check after the first; the first shows Minecraft's own rule still works |
| `os/tests/test_aresos_shell_home.py`, step 1's 3 tests: refusals and a launch without a window are logged | yes (no such lines before) |
| `test_aresos_desktop.py`, `test_recovery_terminal_shortcut_is_kept`: the second rule, once, and no `skipTaskbar` | yes |
| Step 2: `test_aresos_shell_home.CoveredTest` (7 tests, over the wire with two screens): outputs bound before the manager and followed when plugged in and out; only maximized or fullscreen, not minimized, covers; a window on the other screen never covers; `shell_covered` after hello only to a 1.1 desktop that offered it; the world getting the focus minimizes only what covers it on its screen (also after the helper's own return); a restored desktop minimizes nothing; nothing at start-up | yes, all 7 (run against the old helper: 7 errors) |
| Step 2: `ShellClientTest.coveredReachesListenersAndALostHelperUncovers`: the example event, one call per change, false when the helper goes away | yes (no such event or callback before) |
| Step 2: `ShellClientTest.heartbeatsKeepSayingReadyWhileCovered`: ready heartbeats with the world and no second `world_ready` while covered | no: it guards linux-aresos's condition; heartbeats never depended on the game. It does not compile without the new callback |
| Step 2: `HomeScreenClientGameTest`, its last part: a real `ShellClient` on the fake helper, wired with `ShellFocusClient.register`; covered pauses the client and the integrated server with no screen, caps the frame rate at 10, five ready heartbeats arrive while paused and no second `world_ready`; uncovered runs again at the old cap; a dropped helper connection unpauses | yes for the pause, the cap and the reset **(from reading: without the mixins nothing pauses)**; the heartbeat part guards |
| Step 3: `LiveFlightGameTests.joiningLivePlayerFliesAndCannotBeHurt`: a joining Live player can fly (server and, replayed packet by packet, his client), is invulnerable without instant building, walks at 0.15, the server accepts his double space, fall and lava do nothing, he does not catch fire; joining again from his save he is still Live and still flying | yes, run: "Live on the server: he cannot fly" |
| Step 3: `LiveFlightGameTests.speedSurvivesSwitchesDeathAndRespawn`: the speed in Live, after G to Build, after G back, after a death in Build and the respawn, after G to Live, after a respawn in Live keeping everything (the End's); his client's abilities after each | yes, run: "Live: walking speed 0.1". Without only the resend in `ModeInventories.sync`: "Live after Build, on his client: he cannot fly". Without only the resend after a respawn: "His client walks at the game's speed after dying" |
| Step 3: `LiveFlightGameTests.hisClientIsToldTheSpeed`: the movement attribute packets his client gets end with 0.15 (ten ticks after joining Live) | **from reading**: without step 3 the last value is the game's 0.1 (the test was added after the check runs without the change) |
| Step 3: `LiveFlightGameTests.liveFlightStillBreaksAndPlacesNothing`: flying in Live, a creative slot packet puts nothing into the taskbar, left-click does not break a logo at once and breaking it is refused, a taskbar item used on the ground places nothing, no instant building | fails at its fixture (he cannot fly); its checks themselves guard (**from reading** they held before step 3 too: Live was survival then) |
| Step 3: `LiveFlightGameTests.markerOffGivesBackTheGamesSurvival`: the marker off gives the game's survival and walking speed back (server and client), on again gives Live's | yes, run: "Fixture: Live: he cannot fly" |
| Step 3: `LiveFlightGameTests.normalWorldKeepsTheGamesSurvival` (normal environment): no flight, no invulnerability, the game's speed, also on his client | no: it guards "a world without the marker is vanilla" |
| Step 3: `HomeScreenClientGameTest`, part `liveMode` (before `covered`): in Live the HUD asks for no hearts, hunger or experience bar; his client walks at 0.15 with a field-of-view modifier of 1.0; after G and G (real key) his client can still fly; a double space (real key) makes him fly on the client and the server; one picture, `0085_40-live-shows-only-the-hotbar` | yes for the HUD, speed and flight (**from reading**: without the mixins the client answers false for flight and walks at 0.1; the after-G check is the client half of the sync test above) |

"Yes, run" means the test was run against the code with the change taken out (the working tree restored to the commit
afterwards). Other "yes" rows without "run" for step 1 and step 2 were seen failing when the test was first written
against the old code, as their builders recorded; rows marked **from reading** were not run without the change.

Only the headless-labwc reproduction shows: that the window is not fullscreen and not minimized, that it stays below the
apps, what labwc does on click, Alt+Tab, minimize and close, that GLFW's focus is wrong under labwc, and the preview.

## What ran

**Step 4 (the final code, `d69e5ce9` plus docs only):**
- `mod/dev/build.sh` three times, each after `free -g` showed at least 6 GiB available (9 GiB each time):
  all three passed. Run 1 (06:02): BUILD SUCCESSFUL in 1 min 41 s, "All 104 required tests passed". Run 2 (06:04):
  BUILD SUCCESSFUL in 1 min 35 s, 104 passed. Run 3 (06:05): BUILD SUCCESSFUL in 1 min 29 s, 104 passed. No run failed.
  In all three Gradle found the unit tests up to date (their inputs unchanged since step 3's last build, which ran
  them), so a fourth run forced them (`build.sh test --rerun`, 06:07): BUILD SUCCESSFUL in 2 min 10 s, 104 server game
  tests passed, 236 unit tests with 0 failures and 0 errors (6 skipped: the Windows catalogue tests;
  `ShellClientTest` 22).
- The helper's test modules, one at a time (`python3 -m unittest discover -s os/tests -p <module>`):
  `test_aresos_shell_home.py` 10 OK, `test_aresos_shell_windows.py` 33 OK, `test_aresos_shell_protocol.py` 21 OK,
  `test_aresos_shell.py` 74 OK, `test_aresos_desktop.py -k recovery_terminal_shortcut` 1 OK. Never the whole
  `os/tests` suite.
- `mod/dev/client-test.sh`: not run in step 4 (no client test changed); step 3's full run on the same code passed
  (below).

**Step 1:** `mod/dev/build.sh` once, passing (BUILD SUCCESSFUL, 2 min 17 s; `ShellClientTest` 20 tests).
`test_aresos_shell_home.py` 3 OK, `test_aresos_shell.py` 74 OK, `test_aresos_desktop.py -k recovery_terminal_shortcut`
1 OK. `mod/dev/client-test.sh` once, passing: exit 0 after 9 min 47 s, all 18 "checks passed" lines, the last "40 home
screen checks passed".

**Step 2:** `test_aresos_shell_home.py` 10 OK (the 7 new ones against the old helper: 7 errors),
`test_aresos_shell.py` 74 OK, `test_aresos_shell_protocol.py` 21 OK (with the changed example files),
`test_aresos_shell_windows.py` 33 OK. `mod/dev/build.sh` twice, both passing (all 98 server game tests each time).
`mod/dev/client-test.sh` once, passing: exit 0 after 9 min 41 s, all 18 "checks passed" lines. The rig twice.

**Step 3:** `mod/dev/build.sh` seven times: green with the new tests (103, then 104 server game tests); three check runs
with parts of the change taken out (results in the table); the last on the final code at 05:48, passing ("All 104
required tests passed"). `mod/dev/client-test.sh` five times: the first full run failed only in the new Live part (the
speed was checked before the server's entity update had reached the client; 17 "checks passed" lines before it); three
runs of the home screen test alone (the test list cut to it in the working tree, never committed) to fix that and the
double space; then the full suite on the final code at 05:49 to 05:59, passing: exit 0 after 9 min 48 s, all 18 "checks
passed" lines, the last "40 home screen checks passed ... Live mode shows only the hotbar, walks faster with the field of
view kept, still flies after G and G and flies on a double space ...". The preview four times headless. Not run:
`os/tests` (nothing under `os/` changed in step 3).

## The headless-labwc reproduction

The rig: a headless labwc 0.9.6 (`WLR_BACKENDS=headless`, socket `wayland-1`, its own Xwayland `:1`, 1280 x 720) with
the worktree's `rc.xml`, the worktree's helper and the development client on the RTX 4060. The helper ran with a home
folder of its own, so the only user desktop entry was the rig's test program. Input came from a virtual keyboard and
pointer on that compositor's seat. Tools in `reviews/40-real-home/rig/` (`start.sh` starts it; `vinput.py` is the
keyboard and pointer, `tl.py` lists and drives windows, `shot.sh` takes a picture, `load.sh` samples load; every tool
refuses `wayland-0` and `:0`). The repo's `start.sh` also writes the test program and its desktop entry, which step 1
had made by hand: that part was checked with `bash -n` only.

**Before:** see "Causes found" (fullscreen game minimized, black screen; a click on the world hid the test window).

**After (step 1)**, same rig, new mod, helper and `rc.xml`, with `fullscreen:true` and `pauseOnLostFocus:true` saved in
`options.txt`:

| What | Result |
|---|---|
| Start with `fullscreen:true` saved | window `['maximized', 'activated']`, not fullscreen, not minimized |
| F11 in the world | unchanged: `['maximized', 'activated']` |
| Test app opened (typed short name) | app `['activated']` on top, world around it, no pause menu (`after-1-app-over-the-world.png`) |
| Click on the world | world `['activated']`, the app still above it (`after-2-world-clicked-app-stays-above.png`) |
| Alt+Tab | the app has the focus again |
| App minimized | world has the focus |
| App unminimized | app has the focus |
| The world's own window minimized and brought back, then a click on the world | the app is still above: the toggle did not flip back |
| Alt+F4 on the app | world has the focus |
| Terminal opened, maximized, closed | helper: "terminal closed its last window; returning to the desktop"; world has the focus |
| "Saving and pausing game" in the game log during all of this | 0 lines |

`rc.xml`, checked: labwc applies both `aresos-desktop` rules (the window is maximized without a frame and stays below).

**Covered (step 2)**, same rig, the app a `foot` window of the rig's own (`pkg40.TestApp`), driven with `rig/tl.py`:

| What | What labwc reported, and what happened |
|---|---|
| World open, no app | world `['maximized', 'activated'] outputs=[4]`: labwc names the output of the Xwayland game window |
| Small app in front | app `['activated'] outputs=[4]`; no "Saving and pausing game"; no `shell_covered` |
| The app maximized | app `['maximized', 'activated']`; the game log has "Saving and pausing game..." at once (the pause without a screen) |
| The world activated while covered (as Alt+Tab, through foreign-toplevel) | helper: "the desktop got the focus; minimized 1 window(s) that covered it"; app `['maximized', 'minimized']`, world `['maximized', 'activated']`; the world draws and ticks again |
| Back to the app | labwc brings it back maximized; a second "Saving and pausing game..." |
| The app fullscreen | `['maximized', 'activated', 'fullscreen']`: still covered |
| The app closed | world `['maximized', 'activated']` |
| Errors | none from the mod in the game log, none in the helper log |

**B after (step 1):** a program that exits with an error gives the chat line "Couldn't open Test App: it failed to
start" at once; a program that runs without a window gives "Couldn't open Test App: it started, but no window of it
appeared" after 45 s; the helper's log has "failed after starting: exited with status 1 before showing a window".

**The preview (step 3)**, headless: a stand-in for his desktop, a headless labwc 0.9.6 with the image's `rc.xml`
(`wayland-2`, Xwayland `:2`, never `wayland-0`), a virtual keyboard on its seat and an outer `foot` window.
`run-hub.sh --session` ran inside it with a home folder of its own, the client-test lock held, sound off, the worktree's
helper and registry, and quick play into the worktree's `AresHub`. Four runs, 05:42 to 05:47:

| What | Result |
|---|---|
| The preview's labwc | started nested (`wayland-1`, `:1`), its window in the outer desktop `'labwc' ['activated', 'fullscreen'] title='labwc - WL-1'` |
| Its size | follows the outer screen: outer output set to 1600 x 900, the preview's output became 1600 x 900 |
| The game inside | `'aresos-desktop' ['maximized', 'activated']` in the preview's labwc; nothing of it in the outer desktop. Live HUD: the hotbar only |
| `/terminal` typed in the game | helper: "started terminal"; `'aresos.terminal' ['activated']` above the world in the preview, with the session's frame; no "Saving and pausing game" |
| Terminal's environment | `WAYLAND_DISPLAY=wayland-1 DISPLAY=:1 LABWC_PID=<the preview's labwc>`, not the outer desktop's |
| Terminal closed (its close button, through foreign-toplevel) | helper: "terminal closed its last window; returning to the desktop"; the world `['maximized', 'activated']` |
| Alt+Tab on the outer seat, preview in front | the outer desktop took it: the outer terminal got the focus; the preview's own windows unchanged |
| Alt+F4 on the outer seat, preview in front | the outer desktop closed the preview window; the preview's labwc stays up without a screen; `preview-window.py` exits; run 1 (before the save step) stopped the game with TERM, nothing saved; run 2: "asking the game to save and quit", the game logged "Saving worlds", "All dimensions are saved", exit 0 |
| The game quitting (run 3) | the game saved, `run-hub.sh` exit 0, the preview window gone |
| Plain window (run 4, no `--session`) | the game as a window of the outer desktop; closing it ends the run, exit 0 |
| Left behind after each run | no `aresos-dev-*` scope, no private folder |

## Measurements

GPU utilisation and power from `nvidia-smi`, the game's CPU from `/proc`, 6 s each, 1280 x 720, 60 frames a second,
render distance 8, in the rig.

**Step 1, focused against an app in front** (before: old mod; after: step 1's):

| State | GPU | GPU power | Game CPU (one core = 100 %) | Game memory |
|---|---|---|---|---|
| Before: world focused, app behind | 19.7 % | 2.6 W | 53 % | 1678 MiB |
| Before: small app in front | 12.0 % | 2.4 W | 21 % | 1674 MiB |
| After: world focused, no app | 19.0 % | 2.9 W | 44 % | 1294 MiB |
| After: small app in front | 17.8 % | 2.9 W | 48 % | 1294 MiB |
| After: maximized app in front (step 1, before covered existed) | 19.0 % | 3.0 W | 65 % | 1329 MiB |

Single runs, so differences of a few points are noise; the two "before" rows were taken inside a doorway right after the
world was made, the "after" rows in the open. The world costs the same whether it has the focus or not, and in step 1
also fully covered. No lower frame rate for an unfocused world was added (JUDGMENT-CALL 4): with a small window in front
the owner wants the world moving; the saving is "paused only when covered".

**Step 2, small window in front against covered** (run 2: the world opened with quick play and left 90 s first, so chunk
building had finished; then each state 6 s, back to back):

| State | GPU | GPU power | Game CPU (one core = 100 %) | Game memory |
|---|---|---|---|---|
| World focused, no app | 11.2 % | 3.5 W | 25 % | 1368 MiB |
| Small app in front | 11.0 % | 3.4 W | 29 % | 1368 MiB |
| **Covered** (the app maximized) | **4.0 %** | 3.3 W | **8.5 %** | 1371 MiB |
| Small app in front again | 11.3 % | 3.4 W | 26 % | 1371 MiB |
| **Covered** again | **4.0 %** | 3.3 W | **9.9 %** | 1373 MiB |

Run 1 (measured from 30 s after the world opened, while chunks were still being built) showed the same step: small app
in front 18.5 % and 16.0 % GPU, 59 % and 41 % CPU; covered 4.0 % GPU and 8 to 10 % CPU twice. Covering cuts the game's
GPU use by about two thirds and its CPU by two thirds to three quarters; a small window in front costs what the focused
world costs. GPU power hardly moves (3.4 to 3.3 W): at this load the RTX 4060 sits near its idle floor in the headless
rig. On his 1920 x 1080 screen at 144 frames the uncovered world draws far more frames, so the saving there is larger
(not measured). Memory does not change: a paused world keeps its chunks.

**Speed (step 3, from the game's numbers, not measured in play):** walking 4.3 to 6.5 blocks a second, sprinting 5.6 to
8.4, flight unchanged at 10.9 (21.6 sprinting). HUB.md's distance table shrinks by a third: the front row 2.5 s
sprinting instead of 3.7; the farthest of forty, 64 blocks, 7.6 s instead of 11.3.

## JUDGMENT-CALL

1. **Borderless maximized, not real fullscreen** (owner's addition 1). The window stays what package 23's supervisor
   starts (`fullscreen:false`) and what `rc.xml` makes of it: maximized, no frame, always on bottom. In a session the mod
   ignores a saved `fullscreen:true` and F11. Why not real fullscreen: a GLFW fullscreen window minimizes itself on focus
   loss (the cause of C), labwc treats fullscreen windows apart from its layers, and the supervisor and the image checks
   already expect the maximized window. It looks the same as long as nothing reserves screen space (the session has no
   panel). Changing it later means one mixin and the `rc.xml` rule.
2. **Two conditions.** The window rules (no fullscreen, no F11, no iconify) hold for a game the session started, from the
   title screen on, whatever world is open and also while the helper is away. The focus rule (no pause menu) holds only
   in a desktop world with the helper connected. `hub-try` starts the game with the session's identity, so it gets both,
   also as a plain window on his desktop.
3. **Failures go to the chat as well as over the hotbar.** The existing line over the hotbar stays (tests read it).
4. **No lower frame rate for an unfocused world** (see Measurements).
5. **The 45 seconds** before "it started, but no window of it appeared" are the existing open deadline (the helper's
   30 s window wait plus a margin). Shorter would tell slow programs they failed.
6. **10 frames a second while covered**, Minecraft's own limit for a minimized window. The cap is also the longest wait
   before the world shows again when it is uncovered: 100 ms. Lower saves little more and makes the return slower.
7. **A window whose screen is not known yet counts as on the world's screen** (and a world whose screen is not known
   counts as on every screen). labwc names the screens of every window (checked in the rig); the rule matters only for a
   moment after a window maps or a monitor is unplugged, and then it errs toward pausing, as with one screen.
8. **Both sides start a connection uncovered**, so after `hello` the helper sends `covered: true` only when it is.
   Same meaning, and no event the old tests or a 1.0 desktop would see.
9. **The world's own window being minimized is not "covered".** Nothing in the session minimizes it (auto-iconify is
   off, labwc keeps it maximized); Minecraft already draws a minimized window at 10 frames.
10. **Minimizing on activation** happens when the compositor reports the world activated after another window, so it
    covers Alt+Tab, a click, the game's own window taking the focus and the helper's return after a close alike.
11. **1.5 times the game's walking speed, in both modes** (walking 6.5 blocks a second, sprinting 8.4). The front row is
    2.5 s away sprinting and the farthest of forty 7.6 s, walking alone beats the game's sprint, and it stays below
    flight (10.9), so flying remains the fast way. At 2 times, sprinting (11.2) would pass flight and a 2-wide doorway
    gets easy to overshoot. The abilities' walking speed and the movement attribute's base, not an effect or a modifier:
    the game widens the field of view by their ratio, so an effect would have widened it for good (25 % at 1.5),
    changing every picture the town was designed from. Changing the amount later: one constant
    (`LiveMode.DESKTOP_WALKING_SPEED`); a saved player takes the new value at his next mode change, join or respawn.
12. **Live's HUD hides the experience bar too**, not only hearts and hunger (and armour and air, which the game draws
    with the hearts): Live has no experience to earn, and an empty bar over the hotbar is half of survival's look. This
    is creative's HUD. Changing it: one method name in `LiveHudMixin`.
13. **Flight survives a switch to Live**: a player flying in Build still flies after G (the game lands him when he is
    near the ground, as between creative and spectator). Vanilla's switch to survival drops him.
14. **Live is invulnerable in the game's own sense**, not only by the mod's damage rule: in 26.2 that also means no fire
    on him (no flames over the screen after lava) and no exhaustion; the mod already kept food full.
15. **The preview is `--session`, fullscreen through foreign-toplevel, and ends when its window closes.** Alt+F4 on it is
    the outer desktop's (labwc has no keyboard-shortcuts-inhibit), so it closes the preview; ending the run then, with
    the game asked to save and quit first, is better than a game left running in a labwc with no screen. The
    alternative, a nested `rc.xml` with other keys, would no longer be the image's `rc.xml`.

**How each was settled:** 1 to 5 accepted by the orchestrator (2026-11-15). 11 (the speed of 0.15) and 12 (no
experience bar in Live) accepted by the orchestrator (2026-11-15). 6 to 10 follow the orchestrator's decisions on
covered (per screen, PLAN-GAP 3) and are built as stated; 13 to 15 are open for the orchestrator before merge (none of
them is hard to undo).

## PLAN-GAP

1. **B's evidence** is read wrongly in the brief (see "Causes found"): nothing shows he asked for that app. Open: worth
   asking him at the try-out what he did (walked in, clicked in the Apps screen, something else). A click on one of his
   apps in the Apps screen picks its item up and opens nothing, which may be what he saw.
2. **"Terminal stays maximized as today" is not what happens.** The game's Terminal runs foot as `aresos.terminal`
   (`os/config/usr/share/aresos/apps/terminal.json`); the `rc.xml` rule maximizes `foot`, the recovery terminal. In the
   rig the game's Terminal opened at foot's own size. Settled by the orchestrator (2026-11-15): stays as it is. So
   Terminal does not pause the world unless he maximizes it.
3. **Alt+Tab to the world under a maximized app** gave the world the focus while the app still covered it; the brief did
   not say what should happen. Settled by the orchestrator (2026-11-15): the helper minimizes the windows that cover the
   world on its screen; small windows stay. Built in step 2.
4. **An early commit on this branch named one of his programs** in this file; the next commit removed it. Settled: the
   orchestrator handles it (2026-11-15). A squash merge keeps it out of `main`.
5. **"Live mode still breaks and places nothing"** (brief, point 6) is not what Live does, before or after this package:
   Live is survival, so he can mine plain ground slowly (`FlatHomeGameTests` checks "Live mode could not break plain
   ground"); logos and the town's blocks are protected, and nothing can be placed because Live's inventory holds only
   apps. Settled by the orchestrator (2026-11-15): unchanged in this package, as before it; HUB.md says so plainly. The
   Esc-menu package that follows looks at Live's rules again.

## Known limits

- **B's cause is not known.** Nothing in his logs shows an open of that app; the fix makes every failure visible instead.
- **Live can still mine plain ground slowly** (PLAN-GAP 5).
- **Terminal opens at its own size** and does not pause the world unless maximized (PLAN-GAP 2).
- **Not tried in the rig, from reading only:** a dialog of an app (it follows its parent in `Windows._owner` and stacks
  above it whatever the desktop's layer); a restarted game window under a window in front (`keep_foreground` hands the
  focus back, and the new window gets the rule because it is a new window); an X window that the client itself unmaps
  and maps again (the game does not do that once fullscreen is off); the mouse capture itself (no cursor in a headless
  compositor); a real Alt+Tab in the covered run (`tl.py activate` asks for the same activation through
  foreign-toplevel).
- **Two screens** are tested in the helper's fake compositor only, not in the rig (one headless output there).
- **GPU power on his screen** (1920 x 1080 at 144 frames) is not measured; the rig sits near the card's idle floor.
- **Sprint-jumping speed** is not measured.
- **A LAN guest's client** still draws hearts in Live (it has no integrated server to read Live's rule from); he cannot
  be hurt.
- **"Saving and pausing game..."** now appears in the game log whenever a window covers the world: the game cannot tell
  covered from paused in its log otherwise.
- **The preview** cannot show keys the outer desktop binds (Alt+Tab, Alt+F4 ends the preview, Super+Ctrl+Escape),
  single-copy programs already running outside (they open there), D-Bus dialogs (polkit, file choosers, notifications
  open outside), a second screen, the supervisor, or Prism's client. Tested headless only, never on his screen; whether
  the game's mouse look is captured through two compositors is for the try-out. Its log is
  `~/.cache/aresos-dev/run-hub-session.log`.
- **Other packages' pictures of Live** (in their `reviews/*/screenshots/`) still show hearts and hunger: the client runs
  rewrite them with the new HUD, and they were put back with `git checkout` as the rules say, until someone commits a
  new run's pictures.

## For linux-aresos (the `os/` diff, F11 and the focus hand-back)

What changed under `os/`:
- `os/config/usr/share/aresos/labwc/rc.xml`: a second `aresos-desktop` rule,
  `<windowRule identifier="aresos-desktop"><action name="ToggleAlwaysOnBottom" /></windowRule>`. The first rule line is
  byte for byte unchanged. labwc applies a rule's actions once, when a window first maps, so the toggle cannot flip back;
  a restarted game is a new window and gets it again. Checked in the rig: both rules apply, and minimizing and restoring
  the world's window did not flip it.
- `os/config/usr/libexec/aresos-shell`: binds every `wl_output` (before the foreign-toplevel manager, and outputs
  plugged in later; an unplugged output is dropped from every window); tracks each window's maximized, minimized and
  fullscreen state and outputs; can minimize a window (foreign-toplevel `set_minimized`); the new event `shell_covered`,
  offered with window tracking to 1.1 clients only; log lines for every refusal and every launch that fails after
  starting.
- `os/tests/test_aresos_desktop.py`: the assertion for the new rule (once, and no `skipTaskbar`), next to the existing
  one in `test_recovery_terminal_shortcut_is_kept`.
- `os/tests/test_aresos_shell_home.py` (new): the helper's package 40 tests.

**F11 with an always-on-bottom desktop:** nothing happens. In a session (the game started with the session's launch
identity) the mod cancels the game's fullscreen toggle and ignores a saved `fullscreen:true`, so the window labwc manages
is always the maximized, frameless, always-on-bottom one. GLFW's auto-iconify is off as well.

**Package 23's focus hand-back:** unchanged and still needed. A restarted game window maps at the bottom now but still
takes the focus when it appears; the helper's `keep_foreground` gives it back to the window in front, and in that case
the helper does not minimize anything that covers the world. The supervisor and its wrapper (`aresos-desktop`,
`aresos-desktop-java`) are untouched. Not run in the rig (it needs the supervisor): from reading.

## What the code doesn't show

- Under labwc with Xwayland, `Window.isFocused()` stays true while a Wayland app is in front. Only the helper's
  `shell_focus` says where the focus really is; `HomeScreen.appInFront` keeps it.
- Covering is decided by the helper alone, from what labwc reports; the game never looks at other windows.
- His client gets Live's abilities (flight, the walking speed) at once and the movement attribute with the server's next
  entity update, one or two ticks later; the client test waits for it.
- Live's HUD is decided on his client by the same rule as Live on the server (a desktop world, survival), read from the
  integrated server.
- The preview's labwc outlives its own window (wlroots destroys the output, labwc keeps running), which is why
  `preview-window.py` watches the window rather than the process.
- The rig needs a keyboard on the seat (`rig/vinput.py`), or labwc never gives the game the focus.
- A world opened in the rig keeps the town of the apps the rig's helper lists. Pictures for the repo are cut so that no
  logo made from a real icon is in them.
- `HomeScreen.session()` is read once from the environment; client tests set it with `HomeScreen.forTests`.
- `ShellFocusClient.register` is public only for the client test. That test is the last client test on purpose: the tick
  listener that registration leaves behind runs only against a closed shell client afterwards.
