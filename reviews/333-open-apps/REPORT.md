# Package 333 review

## Done

- The shell helper offers `apps_state` and `activate_app` to 1.3 desktops and views that request them and have compositor activation available. Both use catalogue window ownership. Window state is reported after hello and on changed snapshots. The laptop home's 1.2 view keeps its `apps_running` stream.
- Restore chooses the last focused live window and waits for the compositor to confirm focus on it or its modal child. With no open window, it joins an existing launch or takes the `open_app` path. Joined clients receive replies and launch updates under their own request IDs. Deliberate `open_app` requests can start independent launches.
- The helper keeps stderr and writes a rotating 512 KiB `~/.local/state/aresos/shell.log` (or under `XDG_STATE_HOME`) with one backup, both mode 0600. The log uses safe diagnostic fields. Unknown IDs are represented by their length, spawn errors by type and errno, and unexpected errors by type and helper line.
- The world hotbar draws a vanilla-sprite mark for each pinned app with windows. Left click, held use, a short name, a gate and world search open or bring back the app. A free-pointer right click requests a fresh invocation when the helper offers activation. The mod retains its 1.2 launch and gesture behavior.
- Updated HUB.md and added shared 1.3 wire examples. The 1.2 examples remain intact.

## Verified

### Helper and hosted checks

Each local module ran through `python3 reviews/333-open-apps/headless.py <filename>`. That runner uses its own home, state directory, runtime, labwc compositor and D-Bus session.

| Filename | Output |
|---|---|
| `test_aresos_shell_open_apps.py` | `Ran 10 tests`, `OK` |
| `test_aresos_shell.py` | `Ran 75 tests`, `OK` |
| `test_aresos_shell_views.py` | `Ran 30 tests`, `OK` |
| `test_aresos_shell_hardening.py` | `Ran 26 tests`, `OK` |
| `test_aresos_shell_launch_hints.py` | `Ran 13 tests`, `OK` |
| `test_aresos_shell_home.py` | `Ran 15 tests`, `OK` |

- `python3 reviews/333-open-apps/headless.py` printed `PASS: real helper restored the most recently focused window on labwc with zero new spawns`. An independent foreign-toplevel observer saw the same second window unminimized and active, with the first still minimized.
- `gh workflow run "OS image" --ref pkg/333-open-apps -f checks_only=true` and `gh run watch 45016125590 --exit-status --interval 60` passed. The hosted regression job printed `Ran 2500 tests` and `OK (skipped=24)`. The OS files tested by that run are the OS files in this PR. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45016125590)
- The PR's hosted Mod and home-path checks passed on the final code. [Mod checks](https://github.com/Ares-Empire/AresOS/actions/runs/45018661689/job/137196458841) [Privacy check](https://github.com/Ares-Empire/AresOS/actions/runs/45018661594/job/137196458398)

### Mod builds and client tests

Both clean `mod/dev/build.sh --rerun-tasks` runs on the final code printed `All 106 required tests passed :)` and `BUILD SUCCESSFUL`, in 2m 50s and 2m 51s. The Java unit suite recorded 341 tests, six platform skips and zero failures.

| Command | Output |
|---|---|
| `mod/dev/client-test.sh --session --keep-screenshots .work/client-final-1` | `BUILD SUCCESSFUL in 16m 7s`; exit 0. This full run preceded the inventory fixture acknowledgement wait. |
| `mod/dev/client-test.sh --session --keep-screenshots .work/client-replay-1` | `BUILD SUCCESSFUL in 16m 10s`; exit 0. This full run included the wait. |
| `mod/dev/client-test.sh --session --keep-screenshots .work/client-replay-2` | Waiting for the shared client-test slot. |

The two completed sessions both printed `333 open app checks passed`. The final-code screenshot shows active Chrome, minimized Notes and open Terminal. Sampled at render scale 2, the marks measure 28, 16 and 16 image pixels wide and their RGB levels are 236, 107 and 181. [Hotbar app marks](screenshots/0105_333-hotbar-app-marks.png)

The tracked review screenshots were restored and generated untracked screenshots were removed after the completed passes. There are no files over 500 MB in `.work/`.

### Findings during verification

- Initial builds passed the server suite and exposed tests expecting the newest hello to advertise 1.2. The assertions now check 1.3, with a separate check for the actual 1.2 connection using the unchanged fixtures.
- The first full client attempt reached package 333 and exposed a test fixture race between a queued background event and the native press. Applying that starting focus on the client thread before the press made the ordering deterministic. The isolated package 333 diagnostic through `mod/dev/client-test.sh --session` passed both native orders and the held-item, slash name, search and gate paths.
- Another full client attempt timed out in the earlier inventory suite. Its chest-denial fixture now waits for the existing acknowledgement before pressing G. The isolated inventory diagnostic through `mod/dev/client-test.sh --session` passed all 50 switches. An earlier diagnostic attempt had an invalid generated test selection file and exited without running the test. The tracked test list and mode-switch behavior stayed intact.
- An earlier hosted run expected an unknown app ID verbatim in the log. The test now requires the redacted character count and passed in the final hosted run.

## Not verified

- Bringing back the owner's real Chrome window with its tabs and trying the marks in the owner's live home. The headless restore check uses two stand-in windows and the actual helper and compositor.
- Whether the installed Chrome turns a fresh invocation into a new window with its current settings.

## JUDGMENT-CALL

- The marks use a two-GUI-pixel strip at the foot of the vanilla hotbar. Open and hidden marks are eight pixels wide. Active is fourteen pixels wide, and hidden is dimmer than open. Full-slot tint and badges would cover parts of the pinned icons. The width and brightness can be changed in `HotbarAppMarks` without altering the protocol or the saved world.

## PLAN-GAP

- The examples in HOME-OUTSIDE section 5 use `chrome`. The shipped catalogue names the app `browser`, with `/chrome` as a short name. The new fixtures use `browser`.

## Known limits

- Restore selects one window. Restoring a whole layout is deferred. `activation_target` is the selection point for that work.
- A window without a catalogue attribution contributes no app mark. The world's nine slots remain the owner's pins. Unpinned open apps and the full app menu belong to the later outside bar.
- The free-pointer shortcut requires a visible slot and a free pointer. Minimizing the foreground app can return input to the world. The short name still works after capture.
- Right click sends the usual launch command. A new window depends on the app. The reviewed Chrome command has no explicit new-window flag.

## Open questions

- How Chrome behaves on a fresh invocation in the owner's normal session.
