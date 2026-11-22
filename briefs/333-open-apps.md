# 333: open apps and "bring back": `apps_state`, `activate_app`, the hotbar's marks, a right click for a new window

Board brief 333. Package 2 of `docs/design/HOME-OUTSIDE.md` (section 10). It fixes two findings from the owner's first try-out of R28 (`docs/HUB-HANDOFF.md`, points 7 and 10):
- "an open app thats not looked at rn should be in the taskbar right? ... In taskbar apps theres also no indication of which app is open or active rn which other OS have and I think we need that too."
- Chrome was minimized with one tab open, and then `/chrome` or a click on its slot opened a new Chrome window without the tab. His proposal: "a left click opens an app normally ..., a right click opens the app options like on windows. so like open new window etc."

The owner's answer T483 keeps the world's own hotbar, so these marks and clicks live in the world's hotbar as well as, later, in the bar outside (package 4).

**Builder:** Codex `gpt-6.2-sol`, `xhigh`: protocol, helper logic and tests in a well-specified package. **Review:** a fresh Codex `gpt-6.2-sol` `high` context (`mac-capacity`, 2026-11-21: Astra only for a final security look). **Brief review:** one Codex review before the build (the Claude week is tight).

## What changes

### The helper (`os/config/usr/libexec/aresos-shell`)

1. **`aresos-shell/1.3`:** `MINOR` becomes 3. Everything in 1.2 stays, byte for byte, for a client that speaks 1.2: the laptop home pins minor 2 and must keep working unchanged. Minor 3 brings exactly two capabilities, as HOME-OUTSIDE section 5's table defines them:
   - **`apps_state`** (event, to the desktop and to views): `{"apps": [{"id": "chrome", "windows": 2, "active": true, "hidden": false}]}`. It lists every catalogue app with at least one window. `active` means one of its windows has the keyboard; `hidden` means all its windows are minimized. It's sent once after `hello` and on each change, coalesced as `apps_running` is. `apps_running` stays for 1.2 clients.
   - **`activate_app`** (request, from the desktop and views): `{"app_id": "chrome"}`.
     - **The app has a window:** the helper activates its most recently active window, un-minimizing it if needed (labwc through foreign-toplevel). There's no launch. The reply is `{"state": "activated"}`.
     - **A launch of that app is still starting** (from any client): the reply is that launch's, and no second launch starts.
     - **Otherwise:** it does exactly what `open_app` does with this request ID.
     - **Layouts** (COMPONENTS.md 4.3's "a layout that went down together comes back whole") don't exist yet. Leave a named place for them and write it as a Known limit.
   - **Clients** send `activate_app` only to a helper that offered it, and `open_app` otherwise, as today.
   - **Example messages** go to `mod/src/test/resources/shell-1.3/`. The 1.2 examples stay and pass unchanged.
2. **Window to app:** use the helper's existing window tracking (foreign-toplevel; launch owners and catalogue matching as `app_windows` and `covering` already do). An app's window that the helper can't attribute counts for no app. Don't guess.
3. **The helper's log goes somewhere.** On R28 the supervisor starts the helper without redirecting it, so its stderr is the console (`/dev/tty1`) and nothing is kept. The helper adds a rotating log file at `~/.local/state/aresos/shell.log` (512 KiB, one backup, as the supervisor's `desktop.log`), and keeps stderr. The supervisor is `linux-aresos`'s file, so don't change it. Never log a nonce, an environment or a command line.

### The mod

4. **It negotiates 1.3** and asks for both capabilities. Against a 1.2 helper it behaves exactly as today.
5. **The hotbar's marks**, in a session's desktop world, from `apps_state`, drawn on the world's own hotbar:
   - **open:** the app has a window;
   - **active:** one of its windows has the keyboard;
   - **hidden:** all its windows are minimized.

   Use one small mark under the slot, as a taskbar does: a short bar for open, longer and brighter for active, dimmer for hidden, drawn in the game's own style from vanilla's GUI sprites at run time. `linux-desktop` designs the bar outside later and may restyle these, so keep the drawing in one class. No assets are committed.
6. **A left click brings it back.** Every way he opens an app from the world sends `activate_app` when the helper offers it: a left click on a hotbar slot with the free pointer (package 56's taskbar click), using an app item, walking into a gate, and `/name` (for example `/chrome`). So `/chrome` and a click on Chrome's slot bring back the minimized Chrome with its tab.
7. **A right click opens a new window.** A right click on a hotbar slot that holds an app, with the free pointer, sends `open_app`. Today any click there but the left one enters the world (`mod/src/main/java/dev/aresos/focus/PointerRules.java`), so this is new. A right click with an app item in hand, with the pointer captured in the world, is a different path and stays as it is. The full app menu (windows by title, Close all) comes with the bar outside, in package 4.
8. **Open apps that aren't pinned** aren't added to the world's hotbar in this package. The world's hotbar has nine slots and they are his pins. The bar outside shows the others after a gap (HOME-OUTSIDE section 8). Write this as a Known limit.

## Docs

- **HUB.md:** the shell protocol section gets 1.3, with a pointer to HOME-OUTSIDE section 5's table; the hotbar marks; and left click "open or bring back", right click "new window".
- **HUB.md section 7** (the owner's notes): one line each for the marks, bring-back, and right click.

## Tests

- **Helper unit tests:**
  - `apps_state` content and coalescing, with a fake foreign-toplevel: open, active, hidden, an unattributed window, an app closing its last window;
  - `activate_app`: an app with a window (activated, un-minimized, most recent first), a launch still starting (same reply, no second launch), no window (exactly `open_app`);
  - 1.2 clients see no 1.3 message; the log file and that it never holds a nonce.
- **Protocol examples:** the 1.3 examples parse on both sides; the 1.2 examples pass unchanged.
- **Mod unit tests:**
  - marks from `apps_state`;
  - the click rules: left click on an app slot sends `activate_app`, right click sends `open_app`, an empty slot enters the world;
  - the fallback to `open_app` against 1.2.
- **Client game tests** in the headless session, with the fake helper:
  - the marks drawn for open, active and hidden, as screenshots under `reviews/333-open-apps/screenshots/`;
  - a left click on a slot sends `activate_app`, and a right click sends `open_app`;
  - `/name` and a gate send `activate_app`.
- **The builds:** two full passes of `mod/dev/build.sh` and `mod/dev/client-test.sh --session`, as `AGENTS.md` requires, plus the helper's own test suite (`os/tests/` as the helper's earlier packages ran it). New client tests go at the end of the list, so the screenshot numbering stays. Put other packages' pictures back as before.

## Rules

- **AGENTS.md** applies, including rule 6: write "the owner" in anything committed.
- **The safety bar** (decision 24): fix real harm, and list low-harm edge cases under the report's Known limits.
- **Headless only,** never `WAYLAND_DISPLAY=wayland-0` or `DISPLAY=:0`.
- **The owner's real home runs on this laptop.** Never touch it, its Prism instance (`~/.local/share/PrismLauncher`), `~/.local/state/aresos`, the running `aresos-desktop` or `aresos-shell`, `~/AresOS-try` or `hub-try`. Test the helper only as a fresh process with a temporary home folder and socket.
- **Memory:** before each build or client test, wait until no other Gradle build from another worktree is running and 6 GB is available. On exit 75, wait about five minutes and retry, at most six times.
- **Files:** only `aresos-shell` changes under `os/` (it isn't a bound file). Don't change the supervisor, labwc's rules or the laptop home. If one of them turns out to be needed, stop and say so in the report.
- **The report:** `reviews/333-open-apps/REPORT.md`, with the changes, the tests and Known limits.
- **Commits:** end each with the trailer line `Codex-Model: gpt-6.2-sol xhigh`.
- **The PR:** push `pkg/333-open-apps` and open a PR titled "Package 333: open apps and bring back (apps_state, activate_app, hotbar marks, right click for a new window)". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
