# 328: look around without holding a button: two prototypes to try, and the world keeps the pointer

Board brief 328. From the owner's first try-out of R28 (2026-11-21; `docs/HUB-HANDOFF.md`, "The owner's first try-out of R28", points 1 and 4, and his answers).

**What he wants:** the cursor crosses seamlessly between the laptop and a monitor ("for a homescreen thats bad. It should be seamless"). Today the world holds the mouse to steer the camera, so he needs Esc to reach the other screen. He rejected holding the right button to look around: "we need to find another way". You can't judge mouse feel from a description, so this package builds **two prototypes he tries by feel** in `hub-try`. The product keeps today's behaviour until he picks one.

**The bug he hit:** after a click on the world beside a part-screen Chrome, the world steers the camera, but a left click sometimes lands in Chrome when the hidden pointer is over it. The game runs through **X11 under Xwayland** (its log: `X11: Standard cursor shape unavailable`). The likely cause: GLFW's disabled cursor warps the hidden pointer to the window's centre, and labwc gives pointer focus to the Wayland window on top there. Prove or disprove it.

**Builder:** Claude Opus agents, one fresh agent per step below (CLAUDE.md, "Builders work in steps"). **Review:** a fresh Codex `gpt-6.2-astra` `high` context after the last step.

## Steps

### 328a: the world keeps the pointer (the bug)

1. **Find the cause first, with the real capture.** Fabric's client tests disable real capture, so the cause needs a run of the native dev client:
   - under the shared client-test lock;
   - in a private headless labwc with the image's rules and two outputs side by side (`WLR_HEADLESS_OUTPUTS=2`; `os/tests/indicator-harness/driver.py` shows how to arrange and check the layout);
   - with a private D-Bus and the fake helper, never the desktop's bus (single-instance apps would open outside);
   - on a disposable save;
   - with an inert Wayland test app you write for the rig, which counts the pointer events it gets and stands over the game window's centre.
   
   The likely path: Minecraft 26.2's `MouseHandler` warps to the centre, then GLFW 3.5 (LWJGL 3.4.1) on X11 grabs the pointer without checking the result, and Xwayland's pointer-lock emulation decides what labwc does next. Trace it, and write the proven cause in `PROGRESS.md`. Drive Super through the fake helper's `shell_search` event.
2. **Afterwards, while the world steers the camera,** no click, scroll or pointer motion reaches another window, wherever the apps stand. When the world lets go (Esc, an app taking focus, Super), the pointer is a normal pointer again.
3. **The fix stays inside the mod and the test rig.** If the real fix needs `os/` (labwc rules or the compositor), stop 328a, describe the change in `PROGRESS.md`, and leave it to `linux-desktop`. 328b and 328c go on with today's capture, and the report says the leak stays until that fix.
   - **The safe fallback, in every mode:** the world takes the mouse only while the pointer is over the world's window and the helper's focus and GLFW's agree. Otherwise a click or a movement key never starts capture or look mode. Keys still walk if the world has the keyboard. On every release and focus loss, held attack, use and movement are cleared.
   - **Running the game natively on Wayland** instead of Xwayland is out of scope. Say in the report whether it would fix the bug and what else it would change.
4. **Also check his finding 5** in the same rig: a click on the world beside a part-screen app hid the app. Does the helper's covered-minimize (`os/config/usr/libexec/aresos-shell`, "minimized %d window(s) that covered it") fire for a part-screen window, or does labwc raise the world despite its ToggleAlwaysOnBottom rule? Write which, with the exact condition, in `PROGRESS.md`. Don't fix it here: it's `os/`, and the hub and `linux-desktop` act on your answer. The owner's decision is that the world stays below and a part-screen app stays visible.

### 328b: prototype A, "click to look"

- **The cursor is free by default** in a session's desktop world with the helper connected. It's a normal pointer over the world, and it moves onto any other output.
- **Look mode starts** with a click on open world or with any movement key (walk, jump, fly up or down), under the safe fallback above. Package 56's primary click on a hotbar slot that holds an app stays first and opens the app. An empty slot, or one without an app, starts look mode like open world. In look mode the mouse steers the camera exactly as today, and clicks act as today.
- **Look mode ends** after the mouse and all movement keys have been still for `LOOK_RELEASE_MS` (start at 800 ms, one named constant). The cursor reappears where the click was, or at the centre of the world's output after a key start. Esc and an app taking focus also end it.
- **The first click** that starts look mode only starts it; it doesn't break, use or attack (package 56 already swallows the world-entry press and release).
- **The hard hooks** to cover: vanilla's grab when a screen closes, the helper's and GLFW's focus regrabs, and putting the cursor back after a native release.

### 328c: prototype B, "edge turning"

- **The cursor is always free** in a session's desktop world with the helper connected. Movement keys walk and fly as today, in the direction the camera faces.
- **The view turns** while the cursor rests within `EDGE_PX` of the world output's left, right or top edge (start at 48 px). It turns towards that edge, faster the closer the cursor is, up to `EDGE_TURN_DEG_PER_S` (start at 120). Each is one named constant.
- **An edge that touches another output doesn't turn.** The cursor passes through it.
- **The left and right arrow keys also turn** at the same top speed. Q (drop) and E (inventory) keep their vanilla meaning; check that the arrows are unbound in the home, and report any clash.
- **Clicks on the world never capture** in this mode. They act on what the crosshair aims at, through a click path that doesn't grab, because vanilla grabs first. Package 56's taskbar click and its rule that the world ignores the mouse while an app is in front stay. Picking from the cursor's position is out of scope; note it as a limit.
- **The shared edge** comes from the real output layout, plus the pointer's leave event. A partly shared edge lets the cursor through only where it touches the other output, and turns elsewhere.

### 328d: switching and handover

- **One setting picks the behaviour:** `look = classic | click | edge` in the mod's config, with `classic` (today's) as the default. No menu button, because it's a test switch until the owner chooses.
- **`hub-try`** must reach it: document the line he puts in the config file, or a `run-hub.sh` argument, in `mod/README.md`.
- **The owner's two-screen trial:** `run-hub.sh --session --outputs 2` starts the nested preview with two outputs (`WLR_WL_OUTPUTS=2`): two windows, one he puts on the laptop screen and one on the monitor, side by side as in his real layout. It uses a disposable dev world and never his running home. `hub-try` passes the argument through. The lead points `~/AresOS-try` at this branch for the trial and back afterwards; you don't touch it.
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
