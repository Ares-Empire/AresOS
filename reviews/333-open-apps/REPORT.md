# Package 333 review

## Done

- The shell helper offers `apps_state` and `activate_app` to 1.3 desktops and views that request them and have compositor activation available. Both use catalogue window ownership. Window state is reported after hello and on changed snapshots. The laptop home's 1.2 view keeps its `apps_running` stream.
- Restore chooses the last focused live window and waits for the compositor to confirm focus on it or its modal child. With no open window, it joins an existing launch or takes the `open_app` path. Joined clients receive replies and launch updates under their own request IDs. Deliberate `open_app` requests can start independent launches.
- The helper keeps stderr and writes a rotating 512 KiB `~/.local/state/aresos/shell.log` (or under `XDG_STATE_HOME`) with one backup, both mode 0600. The log uses safe diagnostic fields. Unknown IDs are represented by their length, spawn errors by type and errno, and unexpected errors by type and helper line.
- The world hotbar draws a vanilla-sprite mark for each pinned app with windows. Left click, held use, a short name, a gate and world search open or bring back the app. A free-pointer right click requests a fresh invocation when the helper offers activation. The mod retains its 1.2 launch and gesture behavior.
- Updated HUB.md and added shared 1.3 wire examples. The 1.2 examples remain intact.
- Review 1 fixed the `activate_app` fallback after both immediate and deferred executable checks. The helper drains queued compositor events and uses the current window and launch state before spawning. Requests that joined the check get the restore or launch outcome under their own IDs. Deliberate `open_app` requests still have their own launch path.
- The rotating file handler detaches on a write or rollover failure before closing its stream. It contains flush and close failures and keeps diagnostics and subsequent records going to stderr.
- Recheck 1 moved executable checks, processes, scopes and window tracking into the helper's per-app launch state. The helper saves live launches alongside the replay journal and recovers them across restart.
- Step A gives the desktop and each admitted view name separate launch records and activation receipts. View hello admits up to eight names. Package 53a's rewritten test checks that all five view names retain their replies across reconnect and restart.
- Step B lets a live launch answer for its origin's request ID after the reply is gone.
- Step D starts a tray-resident app again after its last window closes. A second bring-back joins the new start while it waits for a window.
- When a view's quota blocks a launch at check completion, a joined desktop request reuses the check under the desktop's quota. The view receives `journal_full`. The desktop keeps its own request ID and screen hint and can still restore a window that appeared during the check.
- The sixth fix reads systemd's active `app-aresos-*.scope` units on each new launch admission. A bounded journal map records who started each scope. Unknown names count toward the shared view cap of 32. The desktop has its own cap of 256. An unreadable list returns the existing `journal_full` reply for views and allows desktop launches within their replay limits.
- Bring-back joins pending checks and windowless starts that are still within their window deadline. Discovered apps can still complete a handoff after that deadline and update existing replies. A saved start with a scope that is absent or unconfirmed at restart becomes a replayable `launch_uncertain` failure. A scope can register later and count toward the cap at the next admission. The scope watcher still follows outcomes and keeps origin IDs available for replay while their apps run.

## Verified

### Native click-to-look follow-up after merging PR166

`WAYLAND_DEBUG=server mod/dev/client-test.sh --session` reproduced the zero-degree failure with Minecraft grabbed and focused. Labwc sent `locked()` at 17:40:12.236709 UTC. It received the first relative move at 17:40:12.238502 UTC and the twentieth at 17:40:12.554021 UTC, forwarding all 20 to Xwayland under the same lock. A focused run with temporary motion logging reproduced the failure at the second tick. Minecraft had accumulated 152.12 units of horizontal motion, and yaw was still −32.25°. On the third tick, yaw reached −9.43° with the pointer still captured.

The native test keeps the deliberate hitch and retries small relative moves for up to three seconds afterward. It requires a turn greater than one degree while captured and still checks release and cursor restoration. `PointerRulesTest` covers both secondary-click outcomes on an app slot in edge mode. Updated `EdgeLook`, `HomePointer` and `PointerRules` to document the app shortcuts and Minecraft's fallback.

| Command | Pass 1 | Pass 2 |
|---|---|---|
| `mod/dev/build.sh --rerun-tasks` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 57s` | `All 106 required tests passed :)`, `BUILD SUCCESSFUL in 2m 46s` |
| `mod/dev/client-test.sh --session` | `333 open app checks passed`, `BUILD SUCCESSFUL in 16m 36s` | `333 open app checks passed`, `BUILD SUCCESSFUL in 16m 31s` |

All four commands exited 0 on the first attempt. Each build recorded 363 unit tests, six platform skips and zero failures. Both native runs turned 22.82° and confirmed the click position, the second output and the key-start position. `git checkout -- reviews/` restored 64 tracked screenshots. Cleanup removed 25 generated untracked screenshots. `git diff --check` passed and `.work/` contains zero files over 500 MB.

### Sixth fix (RECHECK-5)

Each local command used `python3 reviews/333-open-apps/headless.py <filename>` with a private home, runtime, state directory, headless labwc compositor and D-Bus session.

| Filename | Output |
|---|---|
| `test_aresos_shell_open_apps.py` | `Ran 27 tests in 3.183s`, `OK` |
| `test_aresos_shell_views.py` | `Ran 35 tests in 1.436s`, `OK` |
| `test_aresos_shell.py` | `Ran 77 tests in 21.860s`, `OK` |

- The tests exercise both RECHECK-5 sequences, including replay of the failed start and its joined request after restart. They also exercise a fresh activation after an expired start or a clean launcher exit, a live child whose scope counts immediately, ended handoffs that continue following their shared window, and an unreadable list that refuses a view and allows the desktop. The 1.2 refusal retains its error code and text.
- All tests listed under invariants I1–I8 in the third-fix table passed. The desktop-cap test also fills the cap after the originating replies expire, and the owner-map test verifies its bound and persistence under churn.
- In the first runs, an authentication fixture used the private session's real scope listing and a restart fixture omitted the scope for the window it was meant to adopt. They now supply the successful scope listings for those cases. The final shell module run printed the existing unclosed-socket `ResourceWarning` messages. `git diff --check` passed. The worktree's `.work/` had zero files over 500 MB.

The first hosted run on `6e7bbe29` printed `Ran 2523 tests in 2761.680s` and `FAILED (failures=1, skipped=24)`. A resident Discord handoff lost its existing reply grace period when its launcher exited and the next scope check found it gone. Commit `899cabbb` restores that grace period with a separate retry time for window tracking. Its regression test checks that a fresh activation starts independently after the deadline and that the original request can still finish its handoff. [First hosted run](https://github.com/Ares-Empire/AresOS/actions/runs/45135676493)

`gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the final checks on `899cabbb`. `gh run watch 45142256338 --exit-status --interval 60` exited 0. The regression job printed `Ran 2524 tests in 1798.131s` and `OK (skipped=24)`. The Discord handoff case and the new regression both passed. The hosted system manager check reported 434 unit files and 421 unit names. The ways-back source check passed and the full model step was skipped. [Final hosted run](https://github.com/Ares-Empire/AresOS/actions/runs/45142256338)

### Fifth fix (RECHECK-4)

Each command used `python3 reviews/333-open-apps/headless.py <filename>` with a private home, runtime, state directory, headless labwc compositor and D-Bus session.

| Filename | Output |
|---|---|
| `test_aresos_shell_views.py` | `Ran 34 tests in 1.370s`, `OK` |
| `test_aresos_shell_open_apps.py` | `Ran 23 tests in 3.067s`, `OK` |
| `test_aresos_shell.py` | `Ran 76 tests in 20.673s`, `OK` |

- The new test simulates a reviewed launcher's child mapping a window in the launcher's scope. With 31 other view launches, a second view with replay room gets `journal_full` and the existing `too many launches in the last few minutes; try again shortly` message while the scope is `ACTIVE` or its status is `UNKNOWN`. The same request starts once the watcher reports `GONE`. Before the fix, the view module printed `Ran 34 tests in 1.336s` and `FAILED (failures=3)`. The 33rd launch succeeded and the watcher never registered the child's scope.
- The fourth fix's handoff test passed. Existing exit tests drive a scope poll before asserting that an ended launch has freed capacity. `test_aresos_shell.py` printed its existing unclosed-socket `ResourceWarning` messages. `git diff --check` passed. The worktree's `.work/` had zero files over 500 MB.

`gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the hosted checks on `49afa5c6`. `gh run watch 45071622587 --exit-status --interval 60` exited 0. Both the new quota regression and the fourth fix's handoff test passed. The regression job printed `Ran 2518 tests in 2799.776s` and `OK (skipped=24)`. The system manager check reported 437 unit files and 478 unit names. The ways-back job passed its source-change check and skipped the full model. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45071622587)

### Fourth fix (RECHECK-3)

Each command used `python3 reviews/333-open-apps/headless.py <filename>` with a private home, runtime, state directory, headless labwc compositor and D-Bus session.

| Filename | Output |
|---|---|
| `test_aresos_shell_views.py` | `Ran 33 tests in 1.098s`, `OK` |
| `test_aresos_shell_open_apps.py` | `Ran 23 tests in 3.189s`, `OK` |
| `test_aresos_shell.py` | `Ran 76 tests in 21.110s`, `OK` |

- The handoff test opens one discovered single-instance app 33 times across two view names, with all handoffs attached to one window. The laptop home's 1.2 connection then opens another app. The two names leave room in each name's replay journal. The test also checks that ended handoffs are removed after their view's history gives way.
- The joined-check test fills the live view quota, starts a slow executable check from a different view, and joins from the desktop. The view gets `journal_full`. The desktop launches once with its own screen hint and receives the subsequent focus event under its own request ID. Both regression tests failed on the previous helper.
- The desktop test keeps 256 processes alive after their window waits and replay records expire, verifies that just one unrelated record remains, and checks that a new launch is refused until a live process exits. In the same private runner, overriding `Helper.spawn_room` to allow every desktop launch and selecting this test with `pattern='test_aresos_shell.py'` printed `Ran 1 test in 3.495s` and `FAILED (failures=1)`. The failure showed the 257th launch returned `starting`.
- `test_aresos_shell.py` printed its existing unclosed-socket `ResourceWarning` messages. `git diff --check` passed. The worktree's `.work/` had zero files over 500 MB.

`gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the hosted checks on `a3421bfb`. `gh run watch 45067857449 --exit-status --interval 60` exited 0. All three new tests passed. The regression job printed `Ran 2517 tests in 1744.817s` and `OK (skipped=24)`. The system manager check reported 434 unit files and 421 unit names. The ways-back job passed its source-change check and skipped the full model. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45067857449)

### Third fix (analysis steps A through D)

Each command used `python3 reviews/333-open-apps/headless.py <filename>` with its own home, runtime, state directory, headless labwc compositor and D-Bus session.

| Step | Filename | Output |
|---|---|---|
| A | `test_aresos_shell_open_apps.py` | `Ran 20 tests in 2.846s`, `OK` |
| A | `test_aresos_shell_views.py` | `Ran 31 tests in 0.540s`, `OK` |
| B | `test_aresos_shell_open_apps.py` | `Ran 21 tests in 3.072s`, `OK` |
| C | `test_aresos_shell_views.py` | `Ran 32 tests in 0.868s`, `OK` |
| D | `test_aresos_shell_open_apps.py` | `Ran 22 tests in 3.092s`, `OK` |

| Invariant | Passing test |
|---|---|
| I1 | `test_a_resent_deliberate_open_never_starts_a_second_instance` |
| I2, I3, I6 | `test_rotating_view_names_never_pass_the_launch_cap_or_grow_the_saved_state` |
| I3, I7 | `test_a_view_name_in_use_never_gives_way_and_a_ninth_name_is_busy` |
| I4 | `test_no_other_clients_replies_can_refuse_bringing_back_a_visible_window` |
| I5 | `test_a_full_launch_table_never_refuses_a_visible_window` |
| I6 | `test_view_cannot_fill_desktop_journal` |
| I8 | `test_a_tray_resident_app_is_started_again_not_answered_closed` |

The laptop-home negotiation test checks that the 1.3 helper's reply carries minor 2. The launch-cap test checks the 1.2 error code `journal_full` and exact message `too many launches in the last few minutes; try again shortly`.

The final ten-module rerun passed all 287 tests.

| Filename | Output |
|---|---|
| `test_aresos_shell_open_apps.py` | `Ran 22 tests in 3.036s`, `OK` |
| `test_aresos_shell_views.py` | `Ran 32 tests in 0.829s`, `OK` |
| `test_aresos_shell.py` | `Ran 75 tests in 17.695s`, `OK` |
| `test_aresos_shell_followups.py` | `Ran 11 tests in 0.308s`, `OK` |
| `test_aresos_shell_protocol.py` | `Ran 21 tests in 0.597s`, `OK` |
| `test_aresos_shell_review_fixes.py` | `Ran 31 tests in 0.306s`, `OK` |
| `test_aresos_shell_review_fixes_2.py` | `Ran 16 tests in 2.708s`, `OK` |
| `test_aresos_shell_review_fixes_3.py` | `Ran 12 tests in 0.170s`, `OK` |
| `test_aresos_shell_search.py` | `Ran 34 tests in 0.304s`, `OK` |
| `test_aresos_shell_windows.py` | `Ran 33 tests in 9.011s`, `OK` |

`test_aresos_shell.py` printed the existing unclosed-socket `ResourceWarning` messages from its fixtures. `git diff --check` passed. The worktree's `.work/` had zero files over 500 MB.

`gh workflow run 'OS image' --ref pkg/333-open-apps -f checks_only=true` dispatched the hosted checks on `a38859b5`. `gh run watch 45063694139 --exit-status --interval 60` exited 0. The regression job printed `Ran 2514 tests in 1812.286s` and `OK (skipped=24)`. The system manager check reported 434 unit files and 421 unit names. The ways-back job passed its source-change check and skipped the full model. [Hosted OS checks](https://github.com/Ares-Empire/AresOS/actions/runs/45063694139)

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

- The sixth-fix regressions use simulated window events and `systemctl list-units` output in the private session. A real launcher exiting after its child maps a window and restart during real scope registration still need a live-session check.
- Bringing back the owner's real Chrome window with its tabs and trying the marks in the owner's live home. The headless restore check uses two stand-in windows and the actual helper and compositor.
- Whether the installed Chrome turns a fresh invocation into a new window with its current settings.

## JUDGMENT-CALL

- The marks use a two-GUI-pixel strip at the foot of the vanilla hotbar. Open and hidden marks are eight pixels wide. Active is fourteen pixels wide, and hidden is dimmer than open. Full-slot tint and badges would cover parts of the pinned icons. The width and brightness can be changed in `HotbarAppMarks` without altering the protocol or the saved world.
- The lead approved eight view names with replay tables. A ninth name can take the place of one that has been disconnected for ten minutes. The five-name eviction rule would forget recent replies. The table count bounds the replay state, and changing it later is a constant change.
- The lead approved a two-minute horizon for 64 activation receipts per client and a ten-minute horizon for launch records. A ten-minute receipt horizon would need a larger table to admit the same rate of bring-backs. Two minutes covers the mod's 45-second retry window. Changing these limits later is a constant change.
- The lead approved 32 live launches across all view names and 256 for the desktop. Four separate quotas of 32 would permit 128 view-started apps. Updating a live limit later is a constant change with the same wire reply.
- The scope-owner map holds 576 names, twice the combined cap, to retain live scopes and recent names during registration. At capacity it prefers to discard names missing from the active listing. With an unreadable list it prefers to discard a view name since the default attribution is already a view. Immediate removal of absent names would lose the principal of a late-registering scope. Adjusting the map's size is a constant change.

## PLAN-GAP

- The examples in HOME-OUTSIDE section 5 use `chrome`. The shipped catalogue names the app `browser`, with `/chrome` as a short name. The new fixtures use `browser`.
- The new cap covers scopes visible to systemd at the admission snapshot. Multiple launches admitted before their scopes register can temporarily take the active count over the cap. Later admissions count those scopes as soon as they appear. The admission query uses the existing five-second systemd timeout. While systemd's user manager is stalled, each admission blocks the serving loop for up to five seconds, so three or four queued admissions can hold back the desktop's heartbeats long enough for the supervisor to show its transient `unready` notice (RECHECK-6, nit 6). The game isn't touched and nothing latches, and with the manager stalled no app could start anyway. A follow-up after Codex's reset shortens the admission listing's timeout to about one second, since both timeout answers are already safe.

## Known limits

- Restore selects one window. Restoring a whole layout is deferred. `activation_target` is the selection point for that work.
- A window without a catalogue attribution contributes no app mark. The world's nine slots remain the owner's pins. Unpinned open apps and the full app menu belong to the later outside bar.
- The free-pointer shortcut requires a visible slot and a free pointer. Minimizing the foreground app can return input to the world. The short name still works after capture.
- Right click sends the usual launch command. A new window depends on the app. The reviewed Chrome command has no explicit new-window flag.
- The helper journals and starts the origin of a pending-check join before it saves the joining request ID. A restart between these writes can lose the joining ID. The retry can join a surviving launch, restore an existing window, or start a fresh launch if both have gone.
- A ninth view name gets `busy` until a name has been disconnected for ten minutes. AresOS has one view program today. Names without records are held in memory for the lifetime of the helper.
- All views share a cap of 32 active scopes, and the desktop has a cap of 256 when the list is readable. When a launch is refused, a visible window can still be brought back.
- A client that fills its 64 activation receipts gets `journal_full` until a settled receipt is two minutes old. Each client has its own receipt limit.
- A settled receipt is eligible for removal after two minutes. A resend after removal is a new request. The mod resends within 45 seconds, and laptop home never resends an open.
- A holder of the shared view token can take a view's name, replace its connection and share its tables. A separate token per view would require a later supervisor change.
- `journal_full` says “too many launches in the last few minutes” when the live launch cap is reached too.
- When a launch outlives its saved reply, that request stops getting `app_state` events. A resend of the origin ID returns the launch's current state.
- A tray-resident app that ignores a second start can leave the launch waiting for a window. The helper reports `no_window` after 30 seconds.
- Restore traffic can grow helper memory while labwc is stalled and the whole session is already stalled. Growth stops when labwc answers.
- In the half second after a tray app's last window closes, a click can report success without opening a window. A second click opens it.
- The native click-to-look check's retries (RECHECK-7, two nits): fresh moves can supply the turn if the first batch's camera change were lost while it still reset the stillness timer, and the three seconds bound when a retry starts, not a slow socket read inside one. Test-only; the check still fails when the camera never turns while captured.

## Open questions

- How Chrome behaves on a fresh invocation in the owner's normal session.
