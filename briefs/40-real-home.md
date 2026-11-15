# 40: The real home screen (apps over the world, fly and speed, an app that didn't open)

The owner tried the town on 2026-11-15 (`hub-try`, the development client on his screen). His words:

> Okay very cool but its not done yet, Ill list some things: A) Its not a homescreen yet, its a minecraft world. The plan is that when I boot into aresos, that world is what I see immediately, that is my homescreen which I use. B) some apps dont open I think, at least [one app] didnt. C) apps that open close the world which is not pretty and not how a homescreen works. they should open on top of it like with a normal homescreen. D) Lets per default put the user into creative and give him speed to travel faster. The logos look good, really good work so far. But I think before we move on we need to make this the actual homescreen first right?

This package does B, C and D, and makes `hub-try` show what the session will look like. A (booting into the world) is package 23's supervisor, which is on main but reaches the laptop only with the next AresOS release (`linux-aresos`'s work, and publishing is the owner's call). This package must keep working with that supervisor, which starts the game as the `aresos-desktop` window with `fullscreen:false` (`os/config/usr/libexec/aresos-desktop`, `game_options()`), and must fit into that release.

**Builders:** step 1 is a Claude agent on **Fable 5.2**: the causes of B and C are not known yet, and how windows behave over the world is new design that has to be right before it reaches the owner. Steps 2 and 3 are Claude agents on **Opus 5.5** against what step 1 leaves. **Review:** a fresh Claude reviewer on Opus 5.5.

## What he must see when it is done

1. The world is the desktop. It fills the screen, has no title bar and is always below every app window.
2. An app opens **on top of the world**, at the size the app chooses (Terminal stays maximized as today). Around and behind it the world is still there and still moving: no pause menu, no blur, no minimized or black game window. The game lets go of the mouse while an app is in front.
3. Closing the app (its X, or Alt+F4) puts him back in the world with the mouse captured, as today. Minimizing it does the same.
4. Clicking the world while apps are open gives the world the keyboard and mouse again; the apps stay where they are, above the world (as clicking the desktop on Windows). Alt+Tab still reaches every app.
5. Every app that shows a logo or appears in My apps opens when he walks in, types its short name or right-clicks it in the hotbar, or he reads one chat line saying why not. Nothing happens silently.
6. In Live mode he flies like in creative (double-tap space), takes no damage, has no hunger and sees no hearts or hunger bar. He walks and sprints faster than today. Live mode still breaks and places nothing, and the hotbar is still his taskbar. G still switches to Build mode, which is unchanged apart from the speed.
7. `hub-try` shows points 1 to 4 on his screen as the session will, not as a plain window in his current desktop.

Small details on these points (frame rate behind an app, the exact speed, the wording of a line) are the builders' calls within this brief, written into the report and shown at the try-out.

## B: an app that didn't open

Evidence from his try-out (2026-11-15 03:15 to 03:18, `~/AresOS-try/mod/run/logs/latest.log` and `debug.log`, `~/.cache/aresos-dev/run-hub-helper.log`):
- `debug.log` shows `aresos:zone_launch` reaching the client at 03:16:35, 03:17:02 and 03:18:09 (three walk-ins) and two typed commands at 03:16:47 and 03:17:10. `/apps` ran at 03:17:59 and listed the app at "System & Tools, south, front row, right". At 03:18:09 he walked in, very likely into that logo; at 03:18:18 the game paused and at 03:18:19 he quit.
- The helper logged `started` for three apps only (Terminal, Discord and one more of his programs). Nothing about the fourth: no `started`, no failure. No chat line said why. So the open never reached the helper, or the helper refused it without a log line, and the game said nothing.
- The app is a user desktop entry in `~/.local/share/applications/` whose `Exec` is an absolute path in his home, through a symlink into `~/.local/opt/`. The helper's own `desktop_exec` parses it to that one path, and the file is executable. Its window's app ID is very likely the desktop ID. Discord and that third program were probably already running before he opened them (single-instance programs hand the request to the running copy and open no new window).
- Leads, none checked: a launch still waiting for a window (an already-running app that opens none) blocking the next one in the mod or the helper; the walk-in path dropping a launch while another is pending; a refusal the mod does not turn into a chat line.

Find the cause by reproducing it (a user desktop entry like his, with a program of your own; never his programs). Fix it for every app of its kind, so that point 5 holds. Add a test that fails without the fix. Never name his programs in the repo; "a program from a user desktop entry" is enough.

## C: apps on top of the world

What is known (none of it verified; step 1 checks each):
- His development client had `fullscreen:true` and `pauseOnLostFocus:true` in `~/AresOS-try/mod/run/options.txt`. A fullscreen window that loses focus may be iconified by the windowing library (GLFW's auto-iconify, on by default; check what 26.2 uses), and losing focus opens the pause menu, which pauses the integrated server and blurs the world.
- `FocusReturn` closes the focus-loss pause screen when the app hands the focus back; the menu is up the whole time the app is open.
- In the session, `rc.xml` (`os/config/usr/share/aresos/labwc/rc.xml`) maximizes the `aresos-desktop` window without decorations but does not keep it below other windows. labwc 0.9.6 has `ToggleAlwaysOnBottom` (`man labwc-actions`). **Do not use `skipTaskbar`:** it removes the foreign-toplevel handle the helper tracks windows by.
- The helper activates the desktop window when the last app window closes, and keeps a restored desktop below a window in front (`aresos-shell`, the `shell_focus` code around lines 3400 to 3515).

Do:
- In an AresOS desktop world (the desktop marker) with a helper connected: no pause menu on focus loss, no iconify in fullscreen or windowed, the world keeps rendering, and the mouse is released while an app is in front and captured again when the world gets the focus back. Esc still opens the normal menu. Outside desktop worlds, or with no helper connected, the game behaves as vanilla.
- A lower frame rate while the world is not focused, if the measurements show it is needed (the laptop runs on battery). Measure and report the GPU and CPU load behind an open app, before and after.
- `rc.xml`: the `aresos-desktop` window keeps always on bottom. This is an `os/` change: `linux-aresos` owns `os/` and has been told (2026-11-15). **Keep the existing rule line byte for byte:** `os/ci/image-checks.sh` (line 602, not ours to change) greps for exactly `<windowRule identifier="aresos-desktop" serverDecoration="no"><action name="Maximize" /></windowRule>`, and `os/tests/test_aresos_desktop.py` (around line 2860) checks it too. Add a second rule for the same identifier with `<action name="ToggleAlwaysOnBottom" />` (labwc applies every matching rule; check that it really does, and that a toggle in a rule cannot flip back, for example when the window maps again after the game restarts). Add the matching assertion next to the one at `test_aresos_desktop.py` line 2860 and run only that test. The PR's description must say what happens with an always-on-bottom desktop when he makes the game fullscreen (F11), and what package 23's focus hand-back does (the supervisor and its wrapper, `aresos-desktop` and `aresos-desktop-java`): `linux-aresos` asked for both. The orchestrator sends them the PR for a read of the `os/` diff.
- The helper: check that every focus path still holds with an always-on-bottom desktop (an app closing, minimizing, clicking the world, Alt+Tab, an app that opens no window, a dialog of an app). Change only what has to change, with tests.
- Reproduce before and after in a headless labwc with the image's `rc.xml` (`WLR_BACKENDS=headless`, never his screen, never `WAYLAND_DISPLAY=wayland-0`), with the helper and the development client. Use Terminal or a small test window of your own as the app. Screenshots with `grim` against that compositor. Pictures of the world with our own test window may go into `reviews/40-real-home/screenshots/`; nothing of his programs.
- A client test or server test for what can be tested in code (the pause screen not opening on focus loss in a desktop world; the focus messages). Say in the report which behaviour only the headless-labwc reproduction shows.

## D: fly and speed in Live mode

- Live mode today is `GameType.SURVIVAL` and Build mode `GameType.CREATIVE` (`mode/LiveMode.java`, `mode/ModeInventories.java`, which keys the two inventories on the game type). Get point 6 without breaking that split: for example, Live stays its own game type but gets flight, no damage, no hunger and no hearts or hunger bar. Do not make Live mode `CREATIVE`: the creative inventory would let any block into the taskbar, and left-click would break logos at once.
- Speed in both modes: a hidden, permanent effect or attribute (no particles, no icon in the corner), also after death, respawn, a mode switch and joining. Pick the amount with the town's distances in mind (HUB.md "How the numbers were made": walking 4.3 blocks a second, sprinting 5.6) and say it in the report.
- Only in AresOS desktop worlds. A world without the desktop marker is vanilla.
- Server tests: a joining player in Live can fly and takes no damage; speed survives death, respawn and both mode switches; Live still refuses to break and place.

## `hub-try` shows the session

`~/.local/bin/hub-try` is outside the repo and calls `mod/dev/run-hub.sh` from `~/AresOS-try`. Give `run-hub.sh` a way to run the helper and the development client inside a **nested labwc** that uses the image's `rc.xml` (from the checkout), covering his screen, so he sees points 1 to 4 as the session will. The plain window stays possible. Builders never start it on his screen: test it headless. Say what the preview cannot show (keys the outer desktop takes first, such as Alt+Tab, and single-instance programs already running outside, which open their window outside). The orchestrator changes `hub-try` itself.

## Steps

1. **(Fable)** Reproduce B and C, find the causes, build C (mod, helper, `rc.xml`) and B's fix with their tests. Commit, push, keep `reviews/40-real-home/PROGRESS.md` (done, what's left in order, what the code doesn't show).
2. **(Opus)** D with its tests; the nested preview in `run-hub.sh`.
3. **(Opus)** Docs: HUB.md gets a "Corrections from making it the home screen (package 40)" section (what he sees, points 1 to 7, and the numbers chosen); `mod/README.md`; OS-BASE section 4 only if the session's behaviour changes against what it says. Three `build.sh` runs on the final code, one `client-test.sh` run if a client test changed. The report text goes into `PROGRESS.md` (the orchestrator commits it as `REPORT.md`). Open the PR with `gh pr create`.

Each step is a fresh agent, about 250k tokens. Commit and push after every part that works, with `PROGRESS.md` current: the weekly allowance may run out mid-step (2026-11-15), and the next agent starts from your commits.

## Verification

- `mod/dev/build.sh` three times on the final code, all passing; say if a run fails, with its line.
- `mod/dev/client-test.sh` when a client test changes.
- The helper's own tests for what changed in `aresos-shell`, run alone: `python3 -m unittest` on that test module only. **Never the whole `os/tests` suite on the laptop.**
- The report: per point what changed, which tests fail without it (say which claims are from reading), the headless-labwc reproduction before and after, the load measurements, and the known limits.

## Rules

- Worktree `~/AresOS-40-real-home`, branch `pkg/40-real-home`, from main `32fd16ec`. Push with `git push origin pkg/40-real-home`. Never merge, never push to main, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`. Never `./gradlew`, never `--force`. Before either, check that `free -g` shows at least 6 GiB available.
- Headless compositors only. Never open a window on, reconfigure or send input to his session (`WAYLAND_DISPLAY=wayland-0`). Never start his programs. Stop only processes you started, by PID, never by name.
- Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. `~/AresOS-try` is read-only for you (its logs are evidence).
- Under `os/` only these may change: the added `aresos-desktop` rule in `os/config/usr/share/aresos/labwc/rc.xml`, its assertion in `os/tests/test_aresos_desktop.py`, and `os/config/usr/libexec/aresos-shell` with its tests. Never `os/ci`, never the root `.gitattributes`.
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons, no screenshots of his screen or his programs, never the names of his installed programs (Chrome, Discord and Lunar Client are already named by the design).
- `gh` only for `gh pr create` at the end.
- Commits end with `Co-Authored-By: Claude <your model> <noreply@anthropic.com>` (the model you run on).
