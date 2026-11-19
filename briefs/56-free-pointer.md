# 56: while an app is in front, the world ignores the mouse and the hotbar opens apps; faster flying

Board brief 310, board #363. These are the owner's own notes from trying `hub-try` on 2026-11-18, and he said yes to this plan in the session.

**What he saw:** with a small app open, moving the mouse off the app turns his character. He asked: "minecraft shouldnt show the pause menu but it should effectively be paused right? … picture a regular homescreen: you can have a small app, click an app icon and it opens." He also found flying slow ("I dont seem to have speed"; he thinks of Hypixel's lobby flying).

**What HUB.md already says** (section 1, "Corrections from making it the home screen", point 1): "The game lets go of the mouse while an app is in front and captures it again when the world has the focus back." So the turning is a bug against the design.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context.

## What changes

1. **Find and fix the turning.**
   - **Find the cause first:** reproduce it in the session preview (`mod/dev/run-hub.sh --session` in a headless labwc with the image's rules, the helper and a test app at its own size), then write the cause in the report.
   - **Afterwards, while an app window has the focus,** pointer motion over the world never changes the view. This holds:
     - whether the pointer leaves the app slowly or fast;
     - over any edge of the app;
     - after Alt+Tab between apps;
     - after an app closes while another app stays open.
2. **While an app is in front, the world ignores the mouse but keeps living.**
   - **No pause menu.** Time, animations and the town go on as today.
   - **Over the world, the pointer is a normal arrow.**
   - **Nothing the pointer does reaches the world:** no turning, no block breaking or using, and no item use, except for point 3.
3. **The hotbar works as a taskbar.**
   - **While an app is in front,** a click on a hotbar slot that holds an app opens that app, exactly as using its item does: the same open path, the same chat line when an open fails, and a running app comes to the front. The world doesn't take the mouse for that click, and the opened app gets the focus.
   - **Hover:** hovering over such a slot highlights it and shows the app's name in the line above the hotbar, as when he scrolls to it.
   - **Any other click on the world,** including an empty slot or a slot without an app, enters the world as today: the world gets the keyboard, captures the mouse, and the apps stay above it.
   - **Keyboard:** the hotbar keys and the scroll wheel are unchanged.
   - **Where this applies:** only in a session's desktop world with the helper connected. A normal world and a game the session didn't start behave like vanilla.
4. **Faster flying.**
   - **In Live and Build mode in a desktop world,** flying is 1.5 times the game's flying speed: about 16.4 blocks a second, and 32.7 when sprinting.
   - **It's one named constant,** which the owner tunes after trying it.
   - **No Speed effect,** no change to the field of view, and walking stays as it is (1.5 times the game's).
   - **Outside desktop worlds,** flying is vanilla.

## Docs

- **HUB.md section 1, point 1:** the pointer rule while an app is in front and the hotbar as a taskbar.
- **HUB.md sections 2.2 and 5:** the speeds, including the new flying numbers.
- **HUB.md section 7:** a line for the owner saying the flying speed is one number to tune.

## Tests

- **Unit tests** for the input rules, including which clicks open apps and which enter the world, in and outside desktop worlds.
- **Client game tests** in the headless session with the fake helper and a test app at its own size:
  - The pointer leaves the app on each side, slowly and fast, and the view's yaw and pitch are unchanged. No pause screen opens.
  - A click on a hotbar app slot opens that app (the helper receives `open_app`), and the world doesn't grab the mouse.
  - A click on an empty slot, and a click on open world, each enter the world.
  - Flying speed is measured in both modes, with and without sprint, and the field of view is unchanged.
- **Pictures:** the hover highlight with its name line, saved as test-game screenshots under `reviews/56-free-pointer/screenshots/`.
- **The builds:** `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once. Put other packages' pictures back as before.

## Rules

- **AGENTS.md** applies.
- **The safety bar** (decision 24): fix real harm, and list low-harm edge cases under the report's Known limits.
- **Headless only,** never `WAYLAND_DISPLAY=wayland-0`.
- **Owner's files:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`.
- **The lock:** one client test at a time through the scripts. On exit 75, wait about five minutes and retry, at most six times.
- **The report:** write `reviews/56-free-pointer/REPORT.md` with the cause, the changes, the tests and Known limits.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **The PR:** push `pkg/56-free-pointer` and open a PR titled "Package 56: the world ignores the mouse while an app is in front; the hotbar opens apps; faster flying". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
