# 40, review fixes 1

Follow-up of `briefs/40-real-home.md` after `reviews/40-real-home/REVIEW-1.md` (CHANGES-NEEDED) and `linux-aresos`'s read of the `os/` diff (2026-11-15). Finding 1 (names in the brief) is done by the orchestrator in `de64e47d`. Finding 3 (the hosted OS run) is the orchestrator's after this round.

**Builder:** one Claude agent on Opus 5.5, one step: every item is stated. **Review:** a fresh Claude reviewer on Opus 5.5.

## 1. The start-up cover is never covering (linux-aresos)

Package 23b (PR #70, not merged yet) adds a start-up cover: a fullscreen, always-on-top window with the app ID `aresos.cover`. The supervisor starts it before the game and closes it at `world_ready`. Today the helper counts it as covering. When the game's window maps, labwc activates it with the cover as the previous window, so `uncover()` minimizes the cover and the game's own loading screens show after all.

- In `covering()` (and everything that decides what to minimize), a toplevel with the app ID `aresos.cover` never counts as covering and is never minimized. Write the app ID once, as a named constant with a comment pointing to package 23b.
- Test: a fullscreen `aresos.cover` toplevel on the desktop's screen, then the desktop activated. Nothing is minimized and covered stays false.

## 2. No uncover right after a hand-back (REVIEW-1 finding 2)

After package 23's `keep_foreground` hands the focus back to the app in front, a second activation of the restored game window within `KEEP_WINDOW` must not minimize that app. Do it as the review suggests: remember the hand-back's target and time, and skip `uncover()` when the previous window is that target within `KEEP_WINDOW`. Test: a restored desktop activated twice within `KEEP_WINDOW` minimizes nothing; activated again after `KEEP_WINDOW`, it uncovers as usual.

## 3. Minimize only on the world's known screen (finding 4)

`uncover()` minimizes only windows whose known outputs overlap the world's. A window with no known output yet is not minimized. It still counts as covering for the pause, as JUDGMENT-CALL 7 says. Add this difference to JUDGMENT-CALL 7 in the report. Test it.

## 4. The preview and the rig (findings 5, 6, 7)

- `run-hub.sh --session`: the nested labwc and the window watcher are started without `ARESOS_DESKTOP_INSTANCE` and `ARESOS_LAUNCH_NONCE` (`env -u` on both).
- `preview-window.py --close` refuses `WAYLAND_DISPLAY=wayland-0` (and a `--display wayland-0`) itself, with exit status 2.
- When the watcher cannot find the preview window, the run must still end when the preview goes away. End it when the nested labwc has no output left, if that can be done simply. Otherwise put it in the "cannot show" list at the top of `run-hub.sh` and in the report.
- The rig (`reviews/40-real-home/rig/`): `load.sh` takes the game's PID as an argument instead of `pgrep`. Each rig script starts with a line saying it is a development aid of package 40, that it calls Gradle directly, and that it is for headless use only.

## 5. Tests for the real switches (finding 8)

- `HomeScreen.active()` against a real `ShellClient` status: false before CONNECTED, true when connected in a session and a desktop world, false again after the connection is lost.
- A window that would start with a saved `fullscreen:true` in a session starts maximized-windowed, not fullscreen. Use a client test or a unit test, whichever reaches the code without the rig.

## 6. Silent while covered (finding 9, first part)

Decision (orchestrator, 2026-11-15): while covered, the home screen is silent. Music pauses too, not only the other sounds, and everything resumes where it was when the cover ends. With a small window in front nothing changes: sound goes on as today. Test it, and correct HUB.md's sentence.

## 7. A click in the Apps screen opens the app (finding 9, second part)

The app that "didnt" open for him (brief, point B) most likely failed through a click in the Apps screen: today a left-click on one of his apps picks up its item to pin it and opens nothing, without a word (HUB.md 2.4: "Left-click on one of his apps picks up its item, as today, to pin it"). A home screen's app list opens what he clicks.

Decision (orchestrator, 2026-11-15, shown at the try-out):
- A **click** on any app in the Apps screen (My apps or All programs) opens it, through the same path as the hotbar and with the same failure lines.
- **Pinning** is a **drag**: press on one of his apps and move before releasing; that picks up its item as today. A press and release without moving is a click.
- **Right-click** stays removal, as today.
- One short hint line in the screen says so, for example "Click opens · drag to the hotbar to pin".

Whether the screen is a vanilla container or a custom list decides how the click and the drag are told apart. Pick the simplest way that never opens an app on a drag and never picks one up on a click. Tests: click opens, drag picks up, right-click removes. Update HUB.md 2.4 and add it to package 40's corrections section.

## 8. Docs and report

- HUB.md corrections section, HUB.md 2.4, OS-BASE (if the helper's behaviour text changes), `mod/README.md` (the preview's changes).
- `reviews/40-real-home/REPORT.md`: add a section "Review fixes 1" (per item: what changed, which test fails without it, what ran). Your file tool may refuse to edit `REPORT.md`. Then write the section into `reviews/40-real-home/FIXES-1.md`, and the orchestrator merges it.

## Verification

- `mod/dev/build.sh` once on the final code, passing. If unit tests show as up to date, also `build.sh test --rerun` once.
- `mod/dev/client-test.sh` once, if a client test changed.
- The helper test modules that changed, one at a time. Never the whole `os/tests` suite.

## Rules

- Worktree `~/AresOS-40-real-home`, branch `pkg/40-real-home`, head `de64e47d`. Push with `git push origin pkg/40-real-home`, never force. Never merge, never push to main, never `--no-verify`.
- Before `build.sh` or `client-test.sh`, `free -g` shows at least 6 GiB available. One game client at a time on the laptop.
- Headless compositors only; never `WAYLAND_DISPLAY=wayland-0`. Stop only processes you started, by PID.
- Under `os/` only `aresos-shell` and its tests change.
- Never name the owner's installed programs in the repo, commit messages or the PR (Chrome, Discord, Lunar Client and Terminal are fine). No screenshots of his screen.
- `gh` is not needed.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
