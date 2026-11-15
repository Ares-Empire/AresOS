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

### C: what closed the world

Reproduced in a headless labwc 0.9.6 (`WLR_BACKENDS=headless`, socket `wayland-1`, its own Xwayland `:1`) with the
worktree's `rc.xml`, the worktree's helper and the development client; input from a virtual keyboard and pointer
on that compositor's seat.

- **The game window minimized itself.** His client was fullscreen (he switched it at 03:16:23: `debug.log` shows
  the monitor being selected). GLFW's X11 code iconifies a fullscreen window on every `FocusOut` (auto-iconify,
  on by default; Minecraft 26.2 sets no hint: `Window.createGlfwWindow` only sets `GLFW_VISIBLE`). In the rig a
  fullscreen client shows `['minimized', 'fullscreen']` in the foreign-toplevel list and a black screen, and
  re-minimizes itself within a millisecond of every unminimize.
- **No pause menu opened in his try-out**, although `pauseOnLostFocus` was on. His statistics say so: play time 2505
  ticks against 2636 ticks with the world open, so the server was paused for 6.5 s in all (the Esc at 03:16:18 and
  the one before quitting), not during the 12 s and 8 s an app was in front. Cause: when a Wayland window takes the
  focus, wlroots sets the X focus to PointerRoot. The X pointer is still inside the game window, so the game gets
  `FocusOut` followed at once by `FocusIn` (detail NotifyPointer), and GLFW takes that for the focus. Measured with
  an X event log in the rig. So under labwc **GLFW's focus says "focused" while an app is in front**. With the X
  pointer elsewhere the menu would open; the mod must not depend on either.
- **Without always-on-bottom a click on the world hides the apps.** Windowed client, a small test window in front:
  one click on the world and the world covers the test window (the window is still open, behind it).

### B: the app that never opened

- The brief reads 03:18:09 as a walk-in. It was a typed short-name command for the third app: `command_history.txt`
  holds `/apps` and that command only, and `debug.log` has its client-command line in the same second. The lines at
  03:16:47 and 03:17:10 are `aresos:zone_return` packets, not typed commands.
- So the three `zone_launch` packets are two walk-ins (Terminal, Discord) and that typed command, and the helper's
  three `started` lines are exactly these. **No open of the fourth app was ever requested**: no walk-in packet, no command,
  no helper request, and only Notepad was in his hotbar.
- The world's saved data is in order: the app's zone and gate exist at "south, front row, right", built like the
  other six.
- In the rig a program of my own from a user desktop entry (absolute `Exec` through a symlink in a home folder, at
  the same place in the town) opens by walking in.

## What the code doesn't show

- Under labwc with Xwayland, `Window.isFocused()` stays true while a Wayland app is in front (see above). Only the
  helper's `shell_focus` says where the focus really is.
- The rig needs a keyboard on the seat (a `zwp_virtual_keyboard_v1` client), or labwc never gives the game the
  focus.
