# Package 40: progress

Step 1 (Fable 5.2) is running. This file is the handoff: a fresh agent continues from the commits and from here.

## Done

- Causes of B and C (evidence below).
- **C, the mod** (`client/HomeScreen.java`, `mixin/WindowHomeScreenMixin.java`, `MinecraftFocusMixin`,
  `WindowIdentityMixin`, `ShellFocusClient`):
  - In a desktop world with the helper connected, another window having the focus never opens the pause menu. Esc
    still opens the game menu. Outside it, Minecraft's own rule is untouched.
  - In a session (the game was started with the session's launch identity: the supervisor or `run-hub.sh`) the
    window is never the game's own fullscreen: a saved `fullscreen:true` is ignored and F11 does nothing. GLFW's
    auto-iconify is switched off as well.
  - Mouse and held keys are let go when an app is in front and the mouse is captured again when the world has the
    focus back, from the helper's `shell_focus` and, where GLFW does notice, from GLFW.
- **C, `rc.xml`**: a second `aresos-desktop` rule with `ToggleAlwaysOnBottom`; the first line is unchanged. Its
  assertion is in `test_aresos_desktop.py` (`test_recovery_terminal_shortcut_is_kept`).
- **B**: every launch that does not open says why in the chat (and over the hotbar as before); a program that
  started but showed no window the helper can tell is its own is reported as that after the open deadline instead
  of "no answer from the app helper"; a walk-in the client refuses says so; the helper logs every refusal and every
  launch that fails after starting.

## Left, in order

1. **Owner's addition 2 (2026-11-15): paused only when covered.** Not built. Design, ready to build:
   - Helper: read `maximized`, `minimized` and `fullscreen` from the foreign-toplevel state array
     (`ForeignToplevels.dispatch`, opcode 4: values 0, 1 and 3; today only 2, activated, is kept). Covered = any
     ready toplevel that is not the desktop, is not minimized and is maximized or fullscreen. Send it as a **new
     event `shell_covered` with `covered: true|false`**, offered as a capability in `WINDOW_CAPABILITIES`. The
     helper sends an event only to a client that offered its name (`Helper.emit`), so a 1.0 or 1.1 mod never gets
     it and an older helper never sends it: no field of `shell_focus` changes meaning. Send the current value after
     every `hello` (set `windows_pending`, as `hello` does for the registry) and whenever it changes. Limit to
     write down: one screen is assumed; with two screens a maximized window on the other one counts as covering.
   - Mod: add `shell_covered` to `ShellClient.CAPABILITIES`, a `Listener.covered(boolean)`, and reset to false
     when the connection is lost (a dead helper must never leave the world paused). While covered in
     `HomeScreen.active`: pause the integrated server without a screen and render at a minimal rate.
     `Minecraft.runTick` computes `pause` from the open screen; `IntegratedServer` reads `Minecraft.isPaused()`.
     A frame-rate cap goes through `FramerateLimitTracker.getFramerateLimit()` (the iconified limit there is 10).
     `RenderSystem.limitDisplayFPS` waits out the whole frame time, so the cap is also the worst delay before the
     world shows again: 10 a second means 100 ms.
   - **Heartbeats (linux-aresos's condition):** `ShellClient` sends `heartbeat` from its own timer thread
     (`watch()`, every `Settings.heartbeat`), and `world_ready` from the writer thread when the world name changes.
     Neither waits for a frame. What they report is `ShellFocusClient.readyWorld`, set on every client tick: it is
     null only with no player, no level, an overlay or the loading screen, so a pause without a screen keeps it.
     Client ticks still run while paused (at most 10 a frame). Add a test that heartbeats with `ready: true` keep
     arriving at the fake helper while covered.
   - Measure GPU, CPU and memory with a small window in front against covered (numbers for today's code are below).
2. Step 2 of the brief: D (fly and speed), the nested preview in `run-hub.sh`.
3. Step 3: docs, three `build.sh` runs, one `client-test.sh` run, the PR.

## Evidence

The rig: a headless labwc 0.9.6 (`WLR_BACKENDS=headless`, socket `wayland-1`, its own Xwayland `:1`, 1280 x 720)
with the worktree's `rc.xml`, the worktree's helper and the development client on the RTX 4060. The helper ran with
a home folder of its own, so the only user desktop entry was the rig's test program. Input came from a virtual
keyboard and pointer on that compositor's seat. The tools are in `reviews/40-real-home/rig/` (`start.sh` starts
it; `vinput.py` is the keyboard and pointer, `tl.py` lists and drives windows, `shot.sh` takes a picture; every
tool refuses `wayland-0` and `:0`). The copy of `start.sh` in the repo also writes the test program and its desktop
entry, which I had made by hand: that part was checked with `bash -n` only.

### C: what closed the world

- **The game window minimized itself.** His client was fullscreen (he switched it at 03:16:23: `debug.log` shows
  the monitor being selected). GLFW's X11 code iconifies a fullscreen window on every `FocusOut` (auto-iconify,
  on by default; Minecraft 26.2 sets no hint: `Window.createGlfwWindow` only sets `GLFW_VISIBLE`). In the rig a
  fullscreen client showed `['minimized', 'fullscreen']` in the foreign-toplevel list and a black screen
  (`screenshots/before-1-fullscreen-game-minimized-itself.png`), and minimized itself again within a millisecond of
  every unminimize.
- **No pause menu opened in his try-out**, although `pauseOnLostFocus` was on. His statistics say so: play time 2505
  ticks against 2636 ticks with the world open, so the server was paused for 6.5 s in all (the Esc at 03:16:18 and
  the one before quitting), not during the 12 s and 8 s an app was in front. Cause: when a Wayland window takes the
  focus, wlroots sets the X focus to PointerRoot. The X pointer is still inside the game window, so the game gets
  `FocusOut` followed at once by `FocusIn` (detail NotifyPointer), and GLFW takes that for the focus. Measured with
  an X event log in the rig (`rig/xwatch.py`). So under labwc **GLFW's focus says "focused" while an app is in
  front**. With the X pointer elsewhere the menu would open; the mod must not depend on either.
- **Without always-on-bottom a click on the world hides the apps.** Windowed client, old `rc.xml`, a small test
  window in front: one click on the world and the world covered the test window (still open, behind it).

### C: after

Same rig, new mod, helper and `rc.xml`, with `fullscreen:true` and `pauseOnLostFocus:true` saved in `options.txt`:

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

Not tried in the rig, from reading only: a dialog of an app (it follows its parent in `Windows._owner`, and stacks
above it whatever the desktop's layer); a restarted game window under a window in front (`keep_foreground`: the
helper still hands the focus back, and the new window gets the rule again because it is a new window); the mouse
capture itself (no cursor in a headless compositor); two screens.

`rc.xml`, checked: labwc applies both `aresos-desktop` rules (the window is maximized without a frame and stays
below). The toggle did not flip when the window was minimized and brought back. Not checked: an X window that the
client itself unmaps and maps again; the game does not do that once fullscreen is off.

### Load (GPU utilisation and power from `nvidia-smi`, the game's CPU from `/proc`, 6 s each, 1280 x 720, 60 a second, render distance 8)

| State | GPU | GPU power | Game CPU (one core = 100 %) | Game memory |
|---|---|---|---|---|
| Before: world focused, app behind | 19.7 % | 2.6 W | 53 % | 1678 MiB |
| Before: small app in front | 12.0 % | 2.4 W | 21 % | 1674 MiB |
| After: world focused, no app | 19.0 % | 2.9 W | 44 % | 1294 MiB |
| After: small app in front | 17.8 % | 2.9 W | 48 % | 1294 MiB |
| After: maximized app in front (covered) | 19.0 % | 3.0 W | 65 % | 1329 MiB |

Single runs, so differences of a few points are noise; the two "before" rows were taken from inside a doorway and
right after the world was made, the "after" rows in the open. What they show: the world costs the same whether it
has the focus or not, also fully covered. **No lower frame rate for an unfocused world was added**: with a small
window in front the owner wants the world moving, and the saving belongs to "paused only when covered" (left, point
1), which these numbers are the "before" for. His screen is 1920 x 1080 at 144 a second, so his numbers are higher.

### B: the app that never opened

- The brief reads 03:18:09 as a walk-in. It was a typed short-name command for the third app: `command_history.txt`
  holds `/apps` and that command only, and `debug.log` has its client-command line in the same second. The lines at
  03:16:47 and 03:17:10 are `aresos:zone_return` packets, not typed commands.
- So the three `zone_launch` packets are two walk-ins (Terminal, Discord) and that typed command, and the helper's
  three `started` lines are exactly these. **No open of the fourth app was ever requested**: no walk-in packet, no
  command, no helper request, and only Notepad was in his hotbar.
- The world's saved data is in order: the app's zone and gate exist at "south, front row, right", built like the
  other six. He ran about 320 blocks in two minutes, far more than the two walk-ins need.
- In the rig a program of my own from a user desktop entry (absolute `Exec` through a symlink in a home folder),
  which the town put at the same place, opened by walking in and by its short name, before and after.
- **So the cause of his "didn't open" is not in the logs, and I could not reproduce a failure for an app of that
  kind.** What I found instead are the ways a launch ended without a word, and fixed those:
  - every failure was shown only over the hotbar, for three seconds, some of them half a minute after he walked in;
  - a program that starts but shows no window the helper can tell is its own (another app ID, a tray program, a
    copy already running elsewhere) kept the helper waiting for as long as it ran, and the game said "no answer
    from the app helper" after 45 s;
  - a refused launch (unknown app, program missing) and a launch that failed after starting left no line in the
    helper's log, so a log like his cannot tell "never asked" from "refused";
  - a walk-in packet the client refused (not in Live mode on the client) was dropped silently.
- After, in the rig: a program that exits with an error gives the chat line "Couldn't open Test App: it failed to
  start" at once; a program that runs without a window gives "Couldn't open Test App: it started, but no window of
  it appeared" after 45 s; the helper's log has "failed after starting: exited with status 1 before showing a
  window".

## Tests

| Test | Fails without the change? |
|---|---|
| `ShellClientTest.aStartedProgramWithoutAWindowIsNotReportedAsAMissingAnswer` | yes (it was a `TimeoutException`) |
| `ShellClientTest.onlyAGameTheSessionStartedIsADesktopSession` | yes (new method) |
| `HomeScreenClientGameTest` (client test, last in the list): the pause menu opens on focus loss outside the home screen and not in it, the mouse is let go, Esc still opens the menu, F11 does nothing in a session, a failed launch leaves a chat line | yes for each check after the first; the first shows Minecraft's own rule still works |
| `os/tests/test_aresos_shell_home.py` (3 tests): refusals and a launch without a window are logged | yes (no such lines before) |
| `test_aresos_desktop.py`, `test_recovery_terminal_shortcut_is_kept`: the second rule, once, and no `skipTaskbar` | yes |

Ran: `mod/dev/build.sh` once, passing (BUILD SUCCESSFUL, 2 min 17 s; `ShellClientTest` 20 tests).
`python3 -m unittest discover -s os/tests -p 'test_aresos_shell_home.py'` (3 tests OK), `-p 'test_aresos_shell.py'`
(74 OK), `-p 'test_aresos_desktop.py' -k recovery_terminal_shortcut` (1 OK). `mod/dev/client-test.sh`: still running when this was written; see the last commit of step 1.

Only the rig shows: that the window is not fullscreen and not minimized, that it stays below the apps, what labwc
does on click, Alt+Tab, minimize and close, and that GLFW's focus is wrong under labwc.

## JUDGMENT-CALL

1. **Borderless maximized, not real fullscreen** (owner's addition 1). The window stays what package 23's
   supervisor starts (`fullscreen:false`) and what `rc.xml` makes of it: maximized, no frame, always on bottom. In a
   session the mod ignores a saved `fullscreen:true` and F11. Why not real fullscreen: a GLFW fullscreen window
   minimizes itself on focus loss (the cause of C), labwc treats fullscreen windows apart from its layers, and the
   supervisor and the image checks already expect the maximized window. It looks the same as long as nothing reserves
   screen space (the session has no panel). Changing it later means one mixin and the `rc.xml` rule.
2. **Two conditions.** The window rules (no fullscreen, no F11, no iconify) hold for a game the session started,
   from the title screen on, whatever world is open and also while the helper is away. The focus rule (no pause
   menu) holds only in a desktop world with the helper connected, as the brief says. `hub-try` starts the game with
   the session's identity, so it gets both, also as a plain window on his desktop.
3. **Failures go to the chat as well as over the hotbar.** The existing line over the hotbar stays (tests read it).
4. **No lower frame rate for an unfocused world** (see Load).
5. **The 45 seconds** before "it started, but no window of it appeared" are the existing open deadline (the
   helper's 30 s window wait plus a margin). Shorter would tell slow programs they failed.

## PLAN-GAP

1. **B's evidence** is read wrongly in the brief (above): nothing shows he asked for that app. Worth asking him
   what he did (walked in, clicked in the Apps screen, something else). A click on one of his apps in the Apps
   screen picks its item up and opens nothing, which may be what he saw.
2. **"Terminal stays maximized as today" is not what happens.** The game's Terminal runs foot as `aresos.terminal`
   (`os/config/usr/share/aresos/apps/terminal.json`); the `rc.xml` rule maximizes `foot`, the recovery terminal.
   In the rig the game's Terminal opened at foot's own size. Not changed: only the added rule may change in
   `rc.xml`. It matters for addition 2: Terminal will not pause the world unless he maximizes it.
3. **Alt+Tab to the world under a maximized app** gives the world the focus while the app still covers it. The
   brief does not say what should happen (bring nothing forward, as now, or minimize what covers it).
4. An earlier commit on this branch (`4f387f44`) names one of his programs in this file; the next commit removed
   it. A squash merge keeps it out of `main`; the branch's history keeps it until the branch is deleted.

## For the PR's description (linux-aresos asked)

- **F11 with an always-on-bottom desktop:** nothing. In a session the mod cancels the game's fullscreen toggle and
  ignores a saved `fullscreen:true`, so the window labwc manages is always the maximized, frameless one.
- **Package 23's focus hand-back:** unchanged and still needed. A restarted game window maps at the bottom now but
  still takes the focus when it appears; the helper's `keep_foreground` gives it back to the window in front. The
  supervisor and its wrapper are untouched. Not run in the rig (it needs the supervisor): from reading.

## What the code doesn't show

- Under labwc with Xwayland, `Window.isFocused()` stays true while a Wayland app is in front. Only the helper's
  `shell_focus` says where the focus really is; `HomeScreen.appInFront` keeps it.
- The rig needs a keyboard on the seat (`rig/vinput.py`), or labwc never gives the game the focus.
- A world opened in the rig keeps the town of the apps the rig's helper lists. Pictures for the repo are cut so
  that no logo made from a real icon is in them.
- `HomeScreen.session()` is read once from the environment; client tests set it with `HomeScreen.forTests`.
