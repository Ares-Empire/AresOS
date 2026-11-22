# Package 333 review

## Done

- The shell helper offers `apps_state` and `activate_app` to 1.3 desktops and views that request them and have compositor activation available. Both use catalogue window ownership. Window state is reported after hello and on changed snapshots. The laptop home's 1.2 view keeps its `apps_running` stream.
- Restore chooses the last focused live window and waits for the compositor to confirm focus on it or its modal child. With no open window, it joins an existing launch or takes the `open_app` path. Joined clients receive replies and launch updates under their own request IDs. Deliberate `open_app` requests can start independent launches.
- The helper keeps stderr and writes a rotating 512 KiB `~/.local/state/aresos/shell.log` (or under `XDG_STATE_HOME`) with one backup, both mode 0600. The log uses safe diagnostic fields. Unknown IDs are represented by their length, spawn errors by type and errno, and unexpected errors by type and helper line.
- The world hotbar draws a vanilla-sprite mark for each pinned app with windows. Left click, held use, a short name, a gate and world search open or bring back the app. A free-pointer right click requests a fresh invocation when the helper offers activation. The mod retains its 1.2 launch and gesture behavior.
- Updated HUB.md and added shared 1.3 wire examples. The 1.2 examples remain intact.
- Review 1 fixed the `activate_app` fallback after both immediate and deferred executable checks. The helper drains queued compositor events and uses the current window and launch state before spawning. Requests that joined the check get the restore or launch outcome under their own IDs. Deliberate `open_app` requests still have their own launch path.
- Recent activation replies, joins and fallback launches keep their replay records through view-history churn. The helper keeps ordinary histories for four view names and retains protected replies when their histories rotate out.
- The rotating file handler detaches on a write or rollover failure before closing its stream. It contains flush and close failures and keeps diagnostics and subsequent records going to stderr.
- Recheck 1 moved executable checks, processes, scopes and window tracking into the helper's per-app launch state. Each launch keeps its own ID and survives eviction of its request history. The helper saves live launch records alongside the replay journal so a restart can recover launches whose history was evicted. An activation joins a live unwindowed launch, including a process still alive after its window wait expired.
- The 1.2 laptop home can open an app after four other view histories record protected replies. Refusals and unjoined fallback launches retain their retry protection.

## Verified

### Recheck 1 fix

Each touched module ran by filename with `python3 reviews/333-open-apps/headless.py <filename>` in a disposable home, runtime, state directory, headless labwc and D-Bus session.

| Filename | Output |
|---|---|
| `test_aresos_shell_open_apps.py` | `Ran 18 tests in 0.505s`, `OK` |
| `test_aresos_shell_views.py` | `Ran 30 tests in 0.478s`, `OK` |
| `test_aresos_shell.py` | `Ran 75 tests in 18.646s`, `OK` |
| `test_aresos_shell_followups.py` | `Ran 11 tests in 0.264s`, `OK` |
| `test_aresos_shell_protocol.py` | `Ran 21 tests in 0.648s`, `OK` |
| `test_aresos_shell_review_fixes.py` | `Ran 31 tests in 0.334s`, `OK` |
| `test_aresos_shell_review_fixes_2.py` | `Ran 16 tests in 2.746s`, `OK` |
| `test_aresos_shell_review_fixes_3.py` | `Ran 12 tests in 0.186s`, `OK` |
| `test_aresos_shell_search.py` | `Ran 34 tests in 0.344s`, `OK` |
| `test_aresos_shell_windows.py` | `Ran 33 tests in 9.135s`, `OK` |

- The reported sequence covers a desktop activation waiting for its executable check, a 1.2 view's deliberate open, three protected histories and a fifth view evicting the open's history before a browser window maps. It records exactly one spawn and a later focus event under the desktop activation's ID.
- The view eviction test checks that the original launch object, process and state survive eviction. That launch also survives restart while its scope is live. Its later exit leaves a reused request ID's reply and events alone.
- The laptop home's ordinary open succeeds with four protected histories and a full protected-reply quota. The refusals replay after the target window closes and after a helper restart. A separate timeout test checks that activation joins the original live process until it exits.
- The core test module printed unclosed-socket `ResourceWarning` messages from its fixtures and reported `OK`. `git diff --check` passed. This fix touched only the helper and its Python tests. The earlier mod results are recorded below. The worktree's `.work/` had zero files over 500 MB.
- `gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the hosted checks on `568c892a`. `gh run watch 45055856996 --exit-status --interval 60` exited 0. The regression job printed `Ran 2508 tests in 2745.581s` and `OK (skipped=24)`. The hosted system manager check reported 437 unit files and 478 unit names. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45055856996)

### Review 1 helper and hosted checks

- `python3 reviews/333-open-apps/headless.py test_aresos_shell_open_apps.py` printed `Ran 15 tests in 0.425s` and `OK`. The runner used a private home, runtime, state directory, headless labwc and D-Bus. Five new tests cover a window queued during an immediate or deferred executable check with zero spawns, joining a deliberate open that started during a check with one spawn, refused activation and unjoined fallback replay through five distinct views, and `ENOSPC` on flush followed by `EIO` on close.
- `gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the checks on `672d5adb`. `gh run watch 45049949887 --exit-status --interval 60` exited 0. The regression job printed `Ran 2505 tests in 2699.975s` and `OK (skipped=24)`. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45049949887)

### Pre-review helper and hosted checks

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
- `gh workflow run "OS image" --ref pkg/333-open-apps -f checks_only=true` and `gh run watch 45016125590 --exit-status --interval 60` passed. The hosted regression job printed `Ran 2500 tests` and `OK (skipped=24)`. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45016125590)
- The PR's hosted Mod and home-path checks passed before Review 1. [Mod checks](https://github.com/Ares-Empire/AresOS/actions/runs/45018661689/job/137196458841) [Privacy check](https://github.com/Ares-Empire/AresOS/actions/runs/45018661594/job/137196458398)

### Mod builds and client tests

Both complete passes ran on `672d5adb`, after the review fixes. Each command started after other Gradle builds had stopped and at least 6 GiB of memory was available. All four commands exited 0 on their first attempt.

| Command | Output |
|---|---|
| Pass 1 `mod/dev/build.sh --rerun-tasks` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 52s` |
| Pass 1 `mod/dev/client-test.sh --session --keep-screenshots .work/review1-client-1` | `333 open app checks passed`, `BUILD SUCCESSFUL in 16m 5s` |
| Pass 2 `mod/dev/build.sh --rerun-tasks` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 46s` |
| Pass 2 `mod/dev/client-test.sh --session --keep-screenshots .work/review1-client-2` | `333 open app checks passed`, `BUILD SUCCESSFUL in 15m 58s` |

The Java unit suite recorded 341 tests, six platform skips and zero failures. The tracked screenshot shows active Chrome, minimized Notes and open Terminal. Sampled at render scale 2, the marks measure 28, 16 and 16 image pixels wide and their RGB levels are 236, 107 and 181. [Hotbar app marks](screenshots/0105_333-hotbar-app-marks.png)

After both passes, `git checkout -- reviews/` restored 66 tracked screenshots and 25 generated untracked screenshots were removed from `reviews/`. There are no files over 500 MB in `.work/`.

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
- The four ordinary view histories can rotate while protected replies stay available in the same atomic journal. Keeping whole histories would spend more space on replies outside the protection window. Dropping protected replies would allow a retry to spawn. The aggregate quota for new protected view requests is 160, enough for four full histories and a fifth view's quota. Changing that bound later is a constant change with no wire update. The desktop and ordinary view opens keep their own quotas.

## PLAN-GAP

- The examples in HOME-OUTSIDE section 5 use `chrome`. The shipped catalogue names the app `browser`, with `/chrome` as a short name. The new fixtures use `browser`.

## Known limits

- Restore selects one window. Restoring a whole layout is deferred. `activation_target` is the selection point for that work.
- A window without a catalogue attribution contributes no app mark. The world's nine slots remain the owner's pins. Unpinned open apps and the full app menu belong to the later outside bar.
- The free-pointer shortcut requires a visible slot and a free pointer. Minimizing the foreground app can return input to the world. The short name still works after capture.
- Right click sends the usual launch command. A new window depends on the app. The reviewed Chrome command has no explicit new-window flag.
- The helper journals and starts the origin of a pending-check join before it saves the joining request ID. A restart between these writes can lose the joining ID. The retry can join a surviving launch, restore an existing window, or start a fresh launch if both have gone.
- After 160 protected view requests accumulate, a new view activation can receive `journal_full` until enough protected replies age out. The ordinary `open_app` path stays available within each view's 32-entry quota. The helper still accepts four simultaneous named view connections.

## Open questions

- How Chrome behaves on a fresh invocation in the owner's normal session.
