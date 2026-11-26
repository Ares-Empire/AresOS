# 343: edge look tilts up and down; a shorter admission listing

Board brief 343, board item T528. Two small follow-ups, both for release 29 (the owner wants them in it, 2026-11-26).

**Builder:** Codex `gpt-6.2-sol` `xhigh`: rules and tests on a small, well-mapped change. **Review:** a fresh read-only Codex context after the build. **This brief's review:** one Codex review before the build (a small follow-up; Claude's week is tight, so no Claude round).

**Start from `main` once PR150 (package 333) has merged:** item 2 changes 333's code. Branch `pkg/343-edge-tilt`, worktree `~/AresOS-343-edge-tilt`.

## 1. Edge look can look back down

**The problem** (`reviews/328-look-around/REVIEW-166-1.md`, Known limits 1): with `look = edge`, the top edge tilts the view up, but nothing tilts it back down. `EdgeTurn.edges` only ever lowers pitch, through the top band. `EdgeTurn.keys` turns only left and right. Mouse turning is cancelled while the pointer is free. Once the owner tries the top edge, the sky stays until he presses H, uses `/home` or restarts. He tries this prototype by feel, so it must work both ways before his trial.

**The fix:** the Up and Down arrow keys tilt the view, as Left and Right already turn it.
- Up looks up and Down looks down, at `EDGE_TURN_DEG_PER_S`. Minecraft's pitch counts negative upwards (`EdgeTurn.Rate`).
- Together with the top band, pitch never goes faster than the top speed, the same clamp as `keys` uses for yaw. Up and Down held together cancel, as Left and Right do.
- Minecraft keeps pitch within ±90° itself. Check that a held arrow at the limit does nothing odd.
- No bottom edge band: the hotbar is there, and the outside bar will reveal there (`docs/design/HOME-OUTSIDE.md`, section 8).
- The arrows act only where Left and Right act today (`EdgeLook.frame`'s gates: the world in front, no screen or overlay, no app in front).
- **Check the arrows are free:** unbound in vanilla 26.2's default controls and nowhere caught in the mod (`ClickToLook.key`, `HomePointer`, the key mixins). Report any clash instead of moving the keys.
- Keep `EdgeTurn` the place for the rules and the tunables. `EdgeTurn.direction(key)` serves only tests today: extend it to the two new keys or replace it, whichever stays clearer.
- Update every text that says "left and right arrows" for edge mode: `EdgeTurn` and `EdgeLook` Javadoc, `mod/README.md`'s look table (the `look = edge` row), and the "How to try it" text if one is in the repo for the owner's trial.

**Tests:**
- Unit (`mod/src/test/java/dev/aresos/focus/EdgeTurnTest.java`): Up, Down, both together, each with and without the top band (the clamp), and the key codes against GLFW's.
- Client (`EdgeTurnClientGameTest`): after looking up (top edge or Up), holding Down brings the pitch down past level, and Up raises it again. Keep the test's existing release of held keys in its cleanup, with the two new keys added.

## 2. The admission listing answers within one second

**The problem** (`reviews/333-open-apps/RECHECK-6.md`, nit 6; `reviews/333-open-apps/REPORT.md`, PLAN-GAP): package 333's launch admission lists the user manager's scopes from the helper's serving loop with the five-second `SCOPE_TIMEOUT` (`os/config/usr/libexec/aresos-shell`, the `list_scopes` call in the admission path). While systemd's user manager is stalled, each admission blocks the loop for up to five seconds, and three or four queued ones hold back the desktop's heartbeats long enough for the supervisor's transient `unready` notice.

**The fix:** the admission listing gets its own named timeout of one second. The watcher thread keeps `SCOPE_TIMEOUT`. Both timeout answers are already safe (a view's launch is refused with `journal_full`, the desktop's goes through), so only the wait changes. Update the PLAN-GAP paragraph in `reviews/333-open-apps/REPORT.md` to say it is done, and the code comment if it names five seconds.

**Tests:** the existing admission timeout test (find it under `os/tests/`) asserts the one-second value reaches `run`, and that the watcher's own listing still uses `SCOPE_TIMEOUT`. Run only that module, once.

## Rules for this package

- `AGENTS.md` in full. The owner's real home runs on this laptop: never touch it, its Prism instance, `~/.local/state/aresos`, the running `aresos-desktop` or `aresos-shell`, `~/AresOS-try` or `hub-try`. Never use `WAYLAND_DISPLAY=wayland-0` or `DISPLAY=:0`.
- Build and test only with `mod/dev/build.sh` and `mod/dev/client-test.sh --session`, one full pass, fully green. Before it, wait until no other Gradle build runs and 6 GB is free. On exit 75, wait about five minutes and retry, at most six times. Afterwards `git checkout -- reviews/` and delete only untracked screenshots your run created.
- Only the named `os/tests` module, never the whole suite, and never `test_owner_update.py`.
- `os/` changes are read by the OS lead (`linux-aresos`) before merge: keep item 2 to the timeout.
- Write `reviews/343-edge-tilt/REPORT.md`: what changed, the arrow-key check, test results, Known limits. Commit with the trailer `Codex-Model: gpt-6.2-sol xhigh`, push, open a PR into `main`. Never merge, never push to `main`, never `--no-verify`.

## The bar for review

Decision 24 (`docs/design/CONTROL.md`, "The bar"): fix real harm; low-harm edge cases go under Known limits with the reason.
