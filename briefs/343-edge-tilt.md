# 343: edge look tilts up and down; a shorter admission listing

Board brief 343, board item T528. Two small follow-ups, both for release 29 (the owner wants them in it, 2026-11-26).

**Builder:** Codex `gpt-6.2-sol` `xhigh`: rules and tests on a small, well-mapped change. **Review:** a fresh read-only Codex context after the build. **This brief's review:** one Codex review before the build (a small follow-up; Claude's week is tight, so no Claude round): `reviews/343-edge-tilt/BRIEF-REVIEW-1.md`, NOT READY on the two-pass rule, fixed with its three should-fixes.

**Branch `pkg/343-edge-tilt`, worktree `~/AresOS-343-edge-tilt`.** Item 2 changes package 333's code: the lead merges `main` into this branch once PR150 has merged, before the build starts. Check that `os/config/usr/libexec/aresos-shell` has `SCOPE_TIMEOUT` and the admission's `list_scopes` call; if not, stop and say so.

## 1. Edge look can look back down

**The problem** (`reviews/328-look-around/REVIEW-166-1.md`, Known limits 1): with `look = edge`, the top edge tilts the view up, but nothing tilts it back down. `EdgeTurn.edges` only ever lowers pitch, through the top band. `EdgeTurn.keys` turns only left and right. Mouse turning is cancelled while the pointer is free. Once the owner tries the top edge, the sky stays until he presses H, uses `/home` or restarts. He tries this prototype by feel, so it must work both ways before his trial.

**The fix:** the Up and Down arrow keys tilt the view, as Left and Right already turn it.
- Up looks up and Down looks down, at `EDGE_TURN_DEG_PER_S`. Minecraft's pitch counts negative upwards (`EdgeTurn.Rate`).
- **An arrow wins over the top band.** While exactly one of Up and Down is held, the pitch is that key's, at the top speed, wherever the cursor rests: Down must bring the view down even with the cursor parked on the top edge's last pixel (simply adding the key to the band would cancel there). Up and Down held together cancel their key part, and the band alone counts, as Left and Right cancel today. Yaw keeps today's rule.
- Minecraft keeps pitch within ±90° itself. Check that a held arrow at the limit does nothing odd.
- No bottom edge band: the hotbar is there, and the outside bar will reveal there (`docs/design/HOME-OUTSIDE.md`, section 8).
- The arrows act only where Left and Right act today (`EdgeLook.frame`'s gates: the world in front, no screen or overlay, no app in front).
- **Check the arrows are free in play:** all four arrows unbound in vanilla 26.2's default controls, and no gameplay handler in the mod catches them (`ClickToLook.key`, `HomePointer`, the key mixins). Up and Down already move through the search and Apps lists, and vanilla's menus use the arrows: those stay as they are, and the tilt only polls behind `EdgeLook.frame`'s existing gates (no screen or overlay), so using a menu or the search never changes the pitch. Report any clash instead of moving the keys.
- Keep `EdgeTurn` the place for the rules and the tunables. `EdgeTurn.direction(key)` serves only tests today: extend it to the two new keys or replace it, whichever stays clearer.
- Update every text that says "left and right arrows" for edge mode: `EdgeTurn` and `EdgeLook` Javadoc, `mod/README.md`'s look table (the `look = edge` row), and the "How to try it" text if one is in the repo for the owner's trial.

**Tests:**
- Unit (`mod/src/test/java/dev/aresos/focus/EdgeTurnTest.java`): Up, Down, both together, each with and without the top band (the clamp), and the key codes against GLFW's.
- Client (`EdgeTurnClientGameTest`): with the cursor parked on the top edge (the view tilting up), holding Down brings the pitch down past level; Up raises it again; both together leave only the band's tilt. With the search or another screen open, holding Down leaves the pitch unchanged. Keep the test's existing release of held keys in its cleanup, with the two new keys added. Add new client cases inside this test class, so no later screenshot is renumbered.

## 2. The admission listing answers within one second

**The problem** (`reviews/333-open-apps/RECHECK-6.md`, nit 6; `reviews/333-open-apps/REPORT.md`, PLAN-GAP): package 333's launch admission lists the user manager's scopes from the helper's serving loop with the five-second `SCOPE_TIMEOUT` (`os/config/usr/libexec/aresos-shell`, the `list_scopes` call in the admission path). While systemd's user manager is stalled, each admission blocks the loop for up to five seconds, and three or four queued ones hold back the desktop's heartbeats long enough for the supervisor's transient `unready` notice.

**The fix:** the admission listing gets its own named timeout of one second, per admission. The watcher thread and the startup reconciliation keep `SCOPE_TIMEOUT`. Both timeout answers are already safe (a view's launch is refused with `journal_full`, the desktop's goes through), so only the wait changes. Update the PLAN-GAP paragraph in `reviews/333-open-apps/REPORT.md` to say it is done, and the code comment if it names five seconds.

**Tests:** extend package 333's unreadable-list fallback test in `os/tests/test_aresos_shell_views.py` with a fake `run` that raises `subprocess.TimeoutExpired`: assert the admission passes the one-second timeout to `run` and still refuses a view's launch with `journal_full`, and that a watcher check still passes `SCOPE_TIMEOUT`. Run only that module, once.

## Rules for this package

- `AGENTS.md` in full. The owner's real home runs on this laptop: never touch it, its Prism instance, `~/.local/state/aresos`, the running `aresos-desktop` or `aresos-shell`, `~/AresOS-try` or `hub-try`. Never use `WAYLAND_DISPLAY=wayland-0` or `DISPLAY=:0`.
- Build and test only with `mod/dev/build.sh` and `mod/dev/client-test.sh --session`: **two** full passes, both fully green (`AGENTS.md`, "Verification"). Before each, wait until no other Gradle build runs and 6 GB is free. On exit 75, wait about five minutes and retry, at most six times. Afterwards restore only the screenshots the suite overwrote in other packages' `reviews/` folders (`git checkout -- <those paths>`), keep this package's own report and screenshots, and delete only untracked screenshots your runs created outside `reviews/343-edge-tilt/`.
- Only the named `os/tests` module, never the whole suite, and never `test_owner_update.py`.
- `os/` changes are read by the OS lead (`linux-aresos`) before merge: keep item 2 to the timeout.
- Write `reviews/343-edge-tilt/REPORT.md`: what changed, the arrow-key check, test results, Known limits. Commit with the trailer `Codex-Model: gpt-6.2-sol xhigh`, push, open a PR into `main`. Never merge, never push to `main`, never `--no-verify`.

## The bar for review

Decision 24 (`docs/design/CONTROL.md`, "The bar"): fix real harm; low-harm edge cases go under Known limits with the reason.
