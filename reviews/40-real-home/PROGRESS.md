# Package 40: progress

Step 1 (Fable 5.2) is running. This file is the handoff: a fresh agent continues from the commits and from here.

## Done

- Causes of B and C found (evidence below). Nothing built yet in this commit.

## Left, in order

1. C in the mod: no pause menu on focus loss, never fullscreen and never iconified in a desktop session (F11 does
   nothing), mouse released while an app is in front. Driven by the helper's `shell_focus`, not by GLFW's focus (see
   "What the code doesn't show").
2. `rc.xml`: second `aresos-desktop` rule with `ToggleAlwaysOnBottom`, its assertion in `test_aresos_desktop.py`.
3. The helper: focus paths with an always-on-bottom desktop; the new `shell_covered` event (owner's addition 2).
4. B: every launch that does not open says why in one chat line.
5. Owner's addition 2 (2026-11-15): paused only when covered by a maximized or fullscreen window, no pause menu,
   heartbeats keep coming.
6. Steps 2 and 3 of the brief (D, the nested preview, docs, PR).

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

- The brief reads 03:18:09 as a walk-in. It was the typed `/localsend`: `command_history.txt` holds `/apps` and
  `/localsend` only, and `debug.log` has the client-command line for `localsend` in the same second. The lines at
  03:16:47 and 03:17:10 are `aresos:zone_return` packets, not typed commands.
- So the three `zone_launch` packets are two walk-ins (Terminal, Discord) and `/localsend`, and the helper's three
  `started` lines are exactly these. **No open of the fourth app was ever requested**: no walk-in packet, no command,
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
