# Package 343 review

## Done

- `EdgeTurn` and `EdgeLook` use Up and Down to tilt at 120° per second. One tilt arrow takes priority over the top band. Holding both lets the band supply the pitch. The same frame gates apply to all four arrows, and `Entity.turn` clamps pitch to ±90°.
- Updated the mod README and package 328's trial instructions. The client checked the shipped key mappings and found all four arrows free. The gameplay input paths in `ClickToLook`, `HomePointer` and the keyboard mixin leave them available. Search, Apps and vanilla menus still handle arrows on their own screens.
- The shell helper uses `ADMISSION_SCOPE_TIMEOUT` of one second per launch admission. The watcher and startup reconciliation still use the five-second `SCOPE_TIMEOUT`. A timed-out list refuses a view with `journal_full` and lets the desktop attempt its launch. Updated package 333's report.

## Verified

Each mod command started with at least 6 GiB available and zero other Gradle builds. The display variables were unset before the dev scripts ran. Both full passes used the same mod code, and all four completed commands exited 0.

| Command | Pass 1 | Pass 2 |
|---|---|---|
| `mod/dev/build.sh --rerun-tasks` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 59s` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 46s` |
| `mod/dev/client-test.sh --session` | `BUILD SUCCESSFUL in 16m 38s` | `BUILD SUCCESSFUL in 16m 36s` |

- Each build recorded 365 unit cases, six platform skips and zero failures. The original second build attempt exited 143 during unit tests after all 106 server game tests passed. The Gradle daemon logged `client disconnection detected, canceling the build`. The full retry passed with the same code and test settings.
- Both full client runs used the headless two-output labwc/Xwayland session on the RTX 4060. They verified recovery below level while the cursor was at the topmost pixel, both pitch limits while held, both arrows together in and out of the band, and steady pitch with the inventory open. They printed `343: Down beat the top band, Up and Down reached the pitch limits, and both left the band in control`, `328c edge-turning checks passed` and `333 open app checks passed`.
- The second-pass screenshots show the ground at the lower pitch limit with Down held and the sky at the upper limit with Up held. The cursor position is asserted through the game test's input. [Down at the top edge](screenshots/343-down-at-top-edge.png) · [Up at the upper limit](screenshots/343-up-at-upper-limit.png)
- `TMPDIR="$PWD/.work/343-edge-tilt" PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` printed `Ran 35 tests in 1.819s` and `OK` on the corrected fixture. The first run printed `FAILED (failures=1)` because the watcher fixture supplied no scopes. The corrected test gives the watcher an explicit fake scope, asserts a one-second timeout for view and desktop admissions and checks that the watcher keeps `SCOPE_TIMEOUT` and returns `UNKNOWN`. This was the only OS test module run.
- Restored 67 tracked screenshots and removed 25 generated untracked screenshots from other packages. Package 333 still generated `0105_333-hotbar-app-marks.png`. `git diff --check` passed. `.work/` contains no files over 500 MB.
- The first push's local privacy hook reported that its public-terms file was missing or empty, so it skipped that check.

## Not verified

- Camera feel with the owner's physical keyboard and monitor setup remains for the trial.
- The systemd timeout was exercised through a fake subprocess in the OS test. Timing against a stalled live user manager remains unmeasured.

## JUDGMENT-CALL

- Screenshots use Fabric's counter-free names inside the existing edge-turn test. Moving the entire test after package 333 would also preserve the screenshot numbering, at the cost of changing the suite order. This choice is local to the screenshot options.

## PLAN-GAP

- Package 333 now runs after the edge-turn test. Adding numbered screenshots from inside the edge-turn test would have renumbered package 333's screenshot. Fabric's counter-free option preserves the brief's requested test placement and existing screenshot names.

## Known limits

- A custom binding on an arrow can act alongside edge turning during gameplay, as already possible with Left and Right. The shipped mappings leave the arrows free.
- The one-second limit applies per listing. Queued admissions can still add their waits together while the user manager is stalled.

## Open questions

- Does the 120° per second tilt feel right on the owner's two-display setup?
