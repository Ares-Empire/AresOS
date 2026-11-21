# 328: look around without holding a button: two prototypes to try, and the world keeps the pointer

Board brief 328. From the owner's first try-out of R28 (2026-11-21; `docs/HUB-HANDOFF.md`, "The owner's first try-out of R28", points 1 and 4, and his answers).

**What he wants:** the cursor crosses seamlessly between the laptop and a monitor ("for a homescreen thats bad. It should be seamless"). Today the world holds the mouse to steer the camera, so he needs Esc to reach the other screen. He rejected holding the right button to look around: "we need to find another way". You can't judge mouse feel from a description, so this package builds **two prototypes he tries by feel** in `hub-try`. The product keeps today's behaviour until he picks one.

**The bug he hit:** after a click on the world beside a part-screen Chrome, the world steers the camera, but a left click sometimes lands in Chrome when the hidden pointer is over it. The game runs through **X11 under Xwayland** (its log: `X11: Standard cursor shape unavailable`). The likely cause: GLFW's disabled cursor warps the hidden pointer to the window's centre, and labwc gives pointer focus to the Wayland window on top there. Prove or disprove it.

**Builder:** Claude Opus agents, one fresh agent per step below (CLAUDE.md, "Builders work in steps"). **Review:** a fresh Codex `gpt-6.2-astra` `high` context after the last step.

## Steps

### 328a: the world keeps the pointer (the bug)

1. **Find the cause first.** Reproduce it in the session preview (`mod/dev/run-hub.sh --session`, headless labwc with the image's rules and a test app at its own size, placed over the window's centre). Write the cause in `PROGRESS.md`.
2. **Afterwards, while the world steers the camera,** no click, scroll or pointer motion reaches another window, wherever the apps stand. When the world lets go (Esc, an app taking focus, Super), the pointer is a normal pointer again.
3. **The fix stays inside the mod and the preview's test rig.** If the real fix needs `os/` (labwc rules or the compositor), stop, describe the change, and leave it to `linux-desktop`.
   - **Running the game natively on Wayland** instead of Xwayland is out of scope. Say in the report whether it would fix the bug and what else it would change.
4. **Also check his finding 5** in the same rig: a click on the world beside a part-screen app hid the app. Does the helper's covered-minimize (`os/config/usr/libexec/aresos-shell`, "minimized %d window(s) that covered it") fire for a part-screen window, or does labwc raise the world despite its ToggleAlwaysOnBottom rule? Write which, with the exact condition, in `PROGRESS.md`. Don't fix it here: it's `os/`, and the hub and `linux-desktop` act on your answer. The owner's decision is that the world stays below and a part-screen app stays visible.

### 328b: prototype A, "click to look"

- **The cursor is free by default** in a session's desktop world with the helper connected. It's a normal pointer over the world, and it moves onto any other output.
- **Look mode starts** with a click on open world (not on a hotbar slot, which keeps package 56's taskbar click) or with any movement key (walk, jump, fly up or down). In look mode the mouse steers the camera exactly as today, and clicks act as today.
- **Look mode ends** after the mouse and all movement keys have been still for `LOOK_RELEASE_MS` (start at 800 ms, one named constant). The cursor reappears where the click was, or at the centre of the world's output after a key start. Esc and an app taking focus also end it.
- **The first click** that starts look mode only starts it; it doesn't break, use or attack.

### 328c: prototype B, "edge turning"

- **The cursor is always free** in a session's desktop world with the helper connected. Movement keys walk and fly as today, in the direction the camera faces.
- **The view turns** while the cursor rests within `EDGE_PX` of the world output's left, right or top edge (start at 48 px). It turns towards that edge, faster the closer the cursor is, up to `EDGE_TURN_DEG_PER_S` (start at 120). Each is one named constant.
- **An edge that touches another output doesn't turn.** The cursor passes through it.
- **Q and E also turn left and right** at the same top speed. They're unbound in the home today; check that first and report any clash.
- **Clicks on the world** act on what the crosshair aims at, as today. Picking from the cursor's position is out of scope; note it as a limit.

### 328d: switching and handover

- **One setting picks the behaviour:** `look = classic | click | edge` in the mod's config, with `classic` (today's) as the default. No menu button, because it's a test switch until the owner chooses.
- **`hub-try`** must reach it: document the line he puts in the config file, or a `run-hub.sh` argument, in `mod/README.md`.
- **Two outputs:** both prototypes are tried with the world on one output and a second output beside it, in the headless rig (wlroots headless with two outputs) and in the report's instructions for the laptop with his monitor.
- **The report** ends with "How to try it": three short paragraphs, one per setting, written for the owner.

## Tests

- **Unit tests** for each mode's state machine: entering and leaving look mode, the release timer, edge zones, the pass-through edge, Q/E.
- **Client game tests** in the headless session (two outputs, the fake helper, a test app over the window's centre):
  - 328a: in look mode, clicks with the pointer hidden over the app reach the world, never the app (the app's test window counts zero clicks).
  - 328b: a click on open world starts look mode without breaking anything; stillness ends it; the cursor then reaches the second output.
  - 328c: a cursor at the left edge turns the view left; at the edge beside the second output it doesn't turn and the cursor crosses.
  - `classic`: today's tests still pass unchanged.
- **The builds:** in every step that changes code, two full passes of build and client tests through the dev scripts, as `AGENTS.md` requires. Add new client tests at the end of the list so the screenshot numbering stays. Put other packages' pictures back as before.

## Rules

- **AGENTS.md** applies, including rule 6: write "the owner" in anything committed.
- **The safety bar** (decision 24): fix real harm, and list low-harm edge cases under the report's Known limits.
- **Headless only,** never `WAYLAND_DISPLAY=wayland-0`. Never run `hub-try` (it opens on the owner's screen). The owner's real home is running: never touch it, its Prism instance (`~/.local/share/PrismLauncher`), `~/.local/state/aresos`, or the `aresos-desktop` processes.
- **Owner's files:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`.
- **Bound files:** `mod/` and docs only (see 328a, point 3).
- **The lock:** one client test at a time through the scripts. On exit 75, wait about five minutes and retry, at most six times.
- **Each step** commits, pushes `pkg/328-look-around`, and keeps `reviews/328-look-around/PROGRESS.md` up to date (done, left in order, what the code doesn't show). The last step turns it into the report text (a Claude agent can't create `REPORT.md`; leave the text in `PROGRESS.md` and the lead commits it).
- **The PR** (opened by the last step): titled "Package 328: look around without holding a button (two prototypes) and the world keeps the pointer". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
