# Package 25, the guardian: progress

Updated after **step 8c** (2026-11-19). Run 44594035922 confirmed the shutdown save and exposed a real failure
of Ctrl+Alt+F3 during a hung shutdown. The [package report draft](#package-25-report-draft) records both boots,
the unit ordering fix and the remaining release check. Codex built steps 8b and 8c. Claude built steps 1–8a.
Brief: `briefs/25-guardian.md`; its last section ("The lead's fixes after the recheck") overrides the rest.

## Done

**Step 1: section 1, the lifecycle channel's supervisor end** (`os/config/usr/libexec/aresos-desktop`,
`aresos-desktop-java`).

- **1.1 The gate.** `game_environment()` supplies `ARESOS_DESKTOP_LIFECYCLE=1`. The wrapper allows it (`SUPPLIED`) and
  drops an inherited one (`DROPPED`). It is in the supervisor's `PRIVATE_ENVIRONMENT`, so Prism, the helper, the
  covers and the message windows never get it.
- **1.2 `lifecycle_hello`.** `Supervisor.lifecycle_refusal()` holds every check (uid, the PID and start ticks of the
  JVM the wrapper reported, the session's instance, the launch's nonce with `hmac.compare_digest`, major 1 as an
  integer, `save_world` in a list). Accepted: no reply, one log line. Refused: one log line without the nonce, and the
  connection closes. A newer accepted hello replaces the older. After the hello the loop hands that connection's lines
  only to `on_lifecycle_message()`, which reads `world_saved` and drops the rest. `status` has `lifecycle` (boolean).
- **1.3 What counts as saved.** `Supervisor.judge_save()`. Results: `saved`, `wrong_world`, `refused` (with the mod's
  reason), `timeout`, `lost`, `no_channel`, `invalid` (`SaveResult`). The active world is `Supervisor.active_world()`.
- **1.4 One in flight, one waiting.** `request_save(reason, done, wait=None)`, `send_save`, `conclude_save`,
  `save_timed_out`; each caller's deadline is an item in `pending()`.
- **1.5 `save`.** Socket op `save` (reply when the result is in) and `aresos-desktop save [--reason …]`, exit 0 only
  for `saved`. `Loop.reply()` never waits: a peer that does not take its whole line at once is dropped. `request()`
  has one deadline for connecting, sending and waiting (10 s for the old commands, `COMMAND_WAIT` 70 s for `save`).

**Tests** (each run by name under `env -i HOME=<scratch> PATH=/usr/bin:/bin python3 -B -m unittest discover -s
os/tests -p '<module>.py'`):

| Module | Result |
|---|---|
| `test_aresos_guardian.py` (new, the state machine with `FakeRunner`) | 26 tests, OK |
| `test_aresos_guardian_loop.py` (new, the real loop and wrapper, a stand-in game) | 7 tests, OK, three runs in a row, about 4 s each, no process left behind |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 171 s; the hand-off model is unchanged |

One existing assertion changed: the game's exact environment in
`test_the_game_runs_on_nvidia_only_when_its_driver_is_there` now includes the gate. `test_aresos_cover.py` and the `test_aresos_shell*.py` modules were not touched or run.

**Step 2: section 2, the one stop routine, with 3.3's `stop` to drive it** (`os/config/usr/libexec/aresos-desktop`).

- **2.1** `STOP_BUDGET` 60 s, absolute (`Stop.deadline`); the save phase ends at `STOP_SAVE_WAIT` 30 s. Every phase is
  logged with its time since the stop began (`log_phase`: `stop (kind) +1.23 s: …`), to `desktop.log` and, through
  the supervisor's stderr, to the journal. Cleanup: `kill_and_leave()` in `stop_helper`, `close_view` and
  `end_covers` waits 1 s after SIGKILL and then leaves the process to the system.
- **2.2** `request_stop(kind, done)`: `stop`, `restart`, `logout` can be called off (`CALLED_OFF_KINDS`), `shutdown`
  cannot. `Runner.system_stopping()` asks `systemctl is-system-running` (2 s).
- **2.3** The record is the optional key `stop` in `desktop.json` (`Persisted.stop`; schema stays 1), written with
  `write_durable()` (file and folder fsynced) before the save is asked and at each phase: `{open, launch, instance,
  kind, started, phase, save, why, sigterm, close, status, ended}`.
- **2.4** `step_save()`; **2.5** `step_close()` and `Runner.signal_jvm()` (`signal.pidfd_send_signal` on the watched
  pidfd, SIGTERM only), then the launch's end and `jvm_lock_held()`; **2.6** the reply: `ok`, `result` (`confirmed`,
  `unsaved`, `called_off`), `kind`, `save`, `close` (`exited`, `failed`, `overrun`, `called_off`, `none`),
  `recorded`, `seconds`, `message`.
- **2.7** `conclude()` hands a launch that an open record names to `conclude_stopped()`: `stopped`, nothing counted,
  no restart, no `killed` latch, no scope query. `stop_overrun()` at the deadline: no signal, record `overrun`,
  window `stuck` (plain stop) or no window (shutdown).
- **2.8** While a stop runs `on_jvm_start`, `begin` and `retry` refuse; a launch in hand-off is waited for; later
  `stop` ops join (`make_final()` for a shutdown that joins), `save` ops join through `ask_save()`. A replacement
  supervisor: `resume_stop()` after `adopt()`.
- **2.9** `close_stale_stop()` at a start; the latch `unsaved` (set in `close_record()`, shown at once only when the
  session is not ending); `held()` keeps `save_failed`, `stuck` and `guard` through heartbeats, the start timeout
  and a helper failure.
- **The lead's fix 2** `block_admission()`, `blocked()`, `unblock_admission()`: the file
  `$XDG_RUNTIME_DIR/aresos/desktop-stopping.json`, written when a `shutdown` or `logout` stop begins (also with
  nothing running) and before its record can close. A blocked start enters `STOPPING` with no window.
- **3.3 `stop`** Socket op `stop` (`reason: shutdown` or none; anything else `bad_reason`) and `aresos-desktop stop
  [--reason shutdown]`, one 70 s deadline; exit 0 only for a confirmed, recorded stop whose close `exited`, or when
  nothing is running. After a plain stop the `quit` window. `status` has `stopping` and `stop` (the record).

| Module (step 2, run by name as above) | Result |
|---|---|
| `test_aresos_guardian.py` | 43 tests, OK (17 new: `StopTest`) |
| `test_aresos_guardian_loop.py` | 10 tests, OK, 19 s (3 new: a confirmed stop, four saves that fail, a game that ignores SIGTERM for both kinds), no process left behind |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 175 s, no assertion changed |

**Step 3: 3.2 and 3.3, the session ending under the supervisor, `restart`, `logout`, the windows' texts**
(`os/config/usr/libexec/aresos-desktop`, `os/config/usr/share/aresos/desktop-view.bashrc`).

- **3.2 Signals.** `Loop.watch_signals()` (called by `supervise()`): `signal.set_wakeup_fd` on a pipe in the selector,
  so SIGTERM, SIGHUP and SIGINT are noticed at once. `Loop.end_session(why)` calls `Supervisor.end_session(why,
  done)`, which begins or joins a stop that cannot be called off (systemd is not asked) and lets the loop end only
  when that stop has ended. The keeper (`session()`) waits for its supervisor as before, and now also passes on a
  signal that came before it knew its child.
- **3.2 labwc.** `Supervisor.watch_session()` at start: `LABWC_PID` from the supervisor's own environment only, checked
  by `labwc_problem()` (named `labwc`, our uid, this supervisor's `XDG_RUNTIME_DIR` in its `/proc/<pid>/environ`), and
  watched by pidfd (`Runner.watch_labwc()`; the pidfd is opened before the checks and is still alive after them).
  Three outcomes: watched; gone (the session is over: nothing is started, what is adopted is stopped, the supervisor
  exits); not watched (one log line, nothing is ever signalled, `logout` is refused). When the watched labwc ends,
  `Loop.on_labwc` ends the session as a signal does.
- **The exit fits in the deadline.** A stop that ends with the supervisor's exit stops waiting `STOP_EXIT_RESERVE`
  (3 s) before its deadline. `Loop.close(by)` → `Runner.end_children(by)`: the helper, the message window and the
  covers get SIGTERM at once and share one wait (`CLOSE_WAIT` 5 s, or what `by` leaves less 1 s), then SIGKILL and
  `CLEANUP_KILL_WAIT`. `end_covers()` is gone.
- **3.3 `restart`.** Socket op and command word, and the word `restart` in the message window. After its stop
  (`finish_stop()` → `start_again()`): with a known count of zero app windows as `retry` does (`COVER_AGAIN`),
  otherwise as an automatic restart does. The session's instance stays.
- **3.3 `logout`.** Socket op and command word. `logout_refusal()` first (an app window open, the count unknown, no
  watched labwc): nothing is stopped. Then the stop; `after_close()` checks the count again and sends SIGTERM to
  labwc through the watched pidfd (`Runner.signal_labwc()`), also with no game running (the lead's fix 3); the stop
  waits in phase `logout` until labwc's pidfd fires, the session's signal comes, or the deadline (`no_logout()`:
  the reply says so, the admission block is lifted, the `quit` window shows).
- **The helper's `windows` event, the supervisor's side** (`on_windows()`, `app_windows()`); `status` has `windows`,
  `labwc` and `session_over`.
- **The admission block's kind decides who may lift it** (`block_kind`): only a logout's block is ever lifted.

| Module (step 3, run by name as above) | Result |
|---|---|
| `test_aresos_guardian.py` | 59 tests, OK (16 new: `SessionTest`) |
| `test_aresos_guardian_loop.py` | 17 tests, OK, 32 s, three runs in a row (7 new: SIGTERM through the keeper to an idle loop, SIGTERM in the middle of a save, a signal with a game that ignores SIGTERM, the stand-in labwc's end, `logout`, a labwc of another runtime folder, `restart`), no process left behind |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 175 s, no assertion changed |

**Step 4: 3.4, the black screen, the helper's `windows` event, the lid block** (`aresos-cover`, `aresos-shell`,
`aresos-desktop`, `labwc/rc.xml`).

- **The black screen itself.** `aresos-cover --black`: plain black, no text, no pointer, one borderless window on
  every output (`black_out()`: each window calls `fullscreen_on_monitor` for its own output, and an output plugged in
  later gets one too), app id `aresos.black`, ended by SIGTERM or `--limit`. `rc.xml` has a rule of its own for it
  (`ToggleAlwaysOnTop`, no `ToggleFullscreen`).
- **When (supervisor).** `go_black()` at the start of `request_stop()` for `shutdown`, `logout`, `restart`, and in
  `make_final()` when a shutdown or the session's signal joins a plain stop: only if `app_windows() == []`. With an app
  window open, no report or a dead helper the screens stay, and the stop's log says why. Never for a plain `stop`, for
  a `shutdown` that systemd says is none, or once labwc has ended.
- **Until.** `hide_black()` (SIGTERM now, SIGKILL after 2 s through the covers' `kill_covers`, never waited for):
  from `enter()` for every state but `STOPPING` and `STARTING` (a message window or the home must be seen; it runs
  before the window opens); from `finish_stop()` when the session goes on; from `on_windows()` for any report that is
  not a known zero and from `on_helper_exit()` (the lead's fix 4); from `on_labwc_gone()`; from `hide-cover`. After a
  `restart` whose startup cover was started it stays `BLACK_HANDOVER` (2 s) longer, below that cover. At a shutdown, or
  a logout that goes through, it stays: it ends with the supervisor (`Runner.end_children()`, die-with-parent) or by
  its own limit, `--limit 90` (`STOP_BUDGET + BLACK_EXTRA`).
- **The lid block.** `hold_lid()` at the start of every stop (also a plain `stop`, and a stop a replacement supervisor
  goes on with): the child `/usr/bin/systemd-inhibit --what=handle-lid-switch:sleep --who=AresOS --mode=block
  --why=… /usr/bin/sleep 90`, die-with-parent, never waited for. `release_lid()` when the stop ends and the session
  goes on. A start that fails, and a block that ends by itself with an error, are one log line each.
- **The helper.** `Windows.app_windows()` and `Helper.report_windows()`: the status pipe gets `{"event": "windows",
  "count": n, "names": [...]}` once at start and at each change. `aresos.black` is treated as the startup cover
  (`COVER_APP_IDS`): never an app, never covering, never minimized.
- `status` has `black` and `lid_block`.

| Module (step 4, run by name as above) | Result |
|---|---|
| `test_aresos_guardian.py` | 69 tests, OK (10 new: `BlackTest`) |
| `test_aresos_guardian_loop.py` | 20 tests, OK, 40 s, three runs in a row (3 new: a restart that goes black, holds the lid block and hands over to the startup cover; an app window that appears while the screens are black; a session that ends), no process left behind, no logind inhibitor taken |
| `test_aresos_cover.py` | 12 tests, OK, 11 s, three runs (3 new: the rule and `--black`'s arguments; in a private headless labwc with two outputs: black on every output above a window, never an app window for the helper's reader, SIGTERM; its own limit) |
| `test_aresos_shell_guardian.py` (new, the helper in-process) | 11 tests, OK |
| the other 13 `test_aresos_shell*.py` modules, one at a time | all OK: discovery 36, hardening 26, home 13, icons 43, launch_hints 13, protocol 21, shell 74, review_fixes 31, 16, 12 and 11, views 23, windows 33 |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 186 s, no assertion changed |

One existing assertion changed: `test_view_leaves_desktop_connection_readiness_window_rules_and_returns_alone`
(`test_aresos_shell_views.py`) expected the status pipe's only line to be `desktop_connected`; the helper's `windows`
report at its start now comes before it, and the test asserts exactly those two lines (a view still adds none).

**The `rc.xml` and `aresos-shell` lines step 4 changed** (for the lead's notice to `linux-aresos` and `linux-hub`;
line numbers as of this step's commit):

- `os/config/usr/share/aresos/labwc/rc.xml`, lines 41 to 43, added after the `aresos.cover` rule (which is unchanged,
  byte for byte): a two-line comment and
  `<windowRule identifier="aresos.black" serverDecoration="no"><action name="ToggleAlwaysOnTop" /></windowRule>`.
- `os/config/usr/libexec/aresos-shell`:
  - 62 to 68: the docstring's status-pipe section names the `windows` line.
  - 144 to 153: new constants `BLACK_APP_ID`, `COVER_APP_IDS`, `MESSAGE_WINDOW_APP_ID`, `WINDOW_NAMES`,
    `WINDOW_NAME_CHARS`.
  - 187: `PRIVATE_ENVIRONMENT` also lists `ARESOS_DESKTOP_LIFECYCLE` (decision 10; the helper never gets it, so
    nothing changes for an app).
  - 217, 218, 231, 234: `StatusPipe.__call__` returns `False` for a line the full pipe dropped, else `True` (`None`
    when reporting is off). Its callers ignored the result before.
  - 2660 and 2673: `Windows.covering()` leaves out `COVER_APP_IDS` (was: `STARTUP_COVER_APP_ID` alone).
  - 2676 to 2684: new `Windows.app_windows()`.
  - 3006 to 3008 and 3046, 3047: `Helper.__init__` keeps `windows_reported`, and reports once when window tracking
    is off.
  - 3807: `Helper.tick()` calls `report_windows()`.
  - 3818 to 3840: `windows_changed()` calls `report_windows()`; new `report_windows()` and `window_name()`.
  - 4371: `main()` writes `{"event": "windows", "count": null}` when the compositor is lost, before it exits.
  - Nothing in `aresos-shell/1.x` changes: no new operation, event or capability for the desktop or a view. The
    black screen takes the focus like any new window, so the mod hears `shell_focus` `background` (`other_window`)
    while it is up, and never `shell_covered` because of it.

**Step 5: section 4, package 48's leftovers** (`os/config/usr/libexec/aresos-desktop`). Nothing in this file deletes
a world folder, and one is moved in exactly one place.

- **4.2 One way to move a home.** `Supervisor.move_home(source, targets, proof)`:
  - refused while a stop runs, the session is ending, or a launch is alive, in hand-off or still with Prism
    (`home_busy()`);
  - takes the desktop lock itself (`take_desktop_lock()`: `flock`, exclusive, no waiting, as the wrapper takes it; an
    open or lock error is "unknown", never free) and holds it from the checks to the rename;
  - opens the worlds folder once; the folder must be a real folder, pass the caller's `proof` under the lock, and be
    the same folder (device and inode) by its path and through the descriptor before and after the checks;
  - renames with `rename_noreplace()`: `renameat2(RENAME_NOREPLACE)` through ctypes, inside that descriptor. A name
    that is taken is never replaced; for a dated target the next of `-1`, `-2`, … is tried. Never `os.rename`.
  - Its two callers: `move_unfinished()` (4.1) and `use_home()`.
- **`aresos-desktop use-home <folder>`** (socket op `use_home`): a folder named as HomeSwap names them
  (`AresHub-<date>`, `AresHub-new-<date>`) that passes `check_world` becomes `AresHub`, only while nothing has that
  name (a folder, a file or a link). Exit 0 only when it is the home now. It starts nothing: `retry` does.
- **4.1 The first home died while it was made.** `note_first_home()` (at each helper status line of a running game,
  and in `conclude()`): while a setup launch runs (`validate()` found no home at its authorization) and no home was
  ever ready, the optional key `first_home` in `desktop.json` gets `{launch, device, inode, seen}` once `AresHub` is a
  folder, written with `write_durable`. `validate()` answers `setup_unfinished` in place of `world_damaged` when the
  damaged `AresHub` is that folder and `hub_seen` is false (`unfinished_home()`); `refuse_start()` then enters `SETUP`
  with that reason: no latch, nothing started, also for a start from Prism by hand. `retry` on that window moves the
  folder to `AresHub-unfinished-<date>` and starts setup again. Every other damaged world latches `world_damaged` as
  before.
- **4.3 `world_missing` says where the home is.** `dated_home()`, `dated_homes()`, `newest_home()`,
  `found_homes()`, `found_homes_text()`: the window names the newest `AresHub-<date>` and the newest
  `AresHub-new-<date>` that pass the home checks, each with its `use-home` line. Nothing is moved. With neither, the
  text is the old one, byte for byte.
- **4.4 A dated home reported ready.** `ready()` checks a world when it becomes the ready one (the home as before; any
  other world if its name is one plain folder in the worlds folder). A world that is damaged, missing or outside is
  never declared ready. A sound one becomes the active world and sets `hub_seen`.
- **4.5 Leftovers.** `log_leftovers()` at each supervisor start: one line with the count and size of the
  `AresHub-new-<date>` folders. `status` has `leftovers` (their names, newest first). Nothing deletes them.

| Module (step 5, run by name as above) | Result |
|---|---|
| `test_aresos_guardian.py` | 94 tests, OK (25 new: `FirstHomeTest` 8, `UseHomeTest` 8, `MissingHomeTest` 3, `DatedHomeReadyTest` 3, `LeftoversTest` 2, one in `CommandTest`); the 24 of section 4 also with `TMPDIR` on the home's btrfs, so the real `renameat2` ran there and on tmpfs |
| `test_aresos_guardian_loop.py` | 21 tests, OK, 41 s (1 new: `use-home` through the real command and loop: no supervisor, a running game, `AresHub` there, then the move and `retry`), no process left behind |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 178 s; one assertion changed (below). Run before two last edits that touch only docstrings; `test_aresos_guardian.py` was run again after them |

One existing assertion changed: `test_creating_the_hub_finishes_setup` (`test_aresos_desktop.py`) reported a world
`SomeOtherDesktop` that is no folder and expected `IN_WORLD`, then reported `AresHub` without making it. With 4.4 the
first is never declared ready (`SETUP` stays), and the test now makes the hub on the disk before its report, as the
mod does; it still ends with `hub_seen` and the window closed.

**Step 6: the real game** (`reviews/25-guardian/rig/`; the evidence is `reviews/25-guardian/runs/*.json`). Nothing
under `os/` or `mod/` changed.

**The verdict: 2.5's close stands.** With the real Minecraft 26.2 and the worktree's AresOS mod, a confirmed flush
save, then SIGTERM through the watched pidfd, then Java's own exit leaves everything on the disk. SIGTERM alone does
too: Minecraft's own shutdown stops the integrated server, which saves once more, and Java ends with 143. So 25 does
not wait for a mod-side `prepare_stop`, and there is no PLAN-GAP from this step. 2.6 stays as written: no stop
certifies the closing save; this step shows, with the real game, that it saves.

- **The close alone** (`close-*`): no supervisor runs and nobody asks for a save. The rig sets a block that the disk
  does not hold, sends SIGTERM to its own game a millisecond later, and waits for Java's exit. After it the block is
  in the region file, `level.dat` and the player's data were written after the signal, and the status is 143.
- **The path** (`stop-*`): the real supervisor (`aresos-desktop`'s real loop under `env -i`) takes the rig's game by
  the adoption runtime file (`mode: hub`). The mod's hello is accepted, the helper's word makes the real home pass
  `check_world` (`IN_WORLD`). `aresos-desktop save` answers `Saved: AresHub is on the disk.`, and a block the disk did
  not hold before it is there after it. Then another block and `aresos-desktop stop`: exit 0, `Stopped: the home was
  saved first; Minecraft closed.`, the record `saved`, `sigterm`, `exited`, 143. Prism's stand-in was never started.
- **Reopened:** every launch first asks the reopened game itself for the blocks of the launch before (`reopened` in
  its file: the game's own answer, and the region file's).
- **First of all,** in every launch: `/proc/<game>/environ` has exactly one `XDG_RUNTIME_DIR`, the run's temporary
  folder, and the gate only where the run means it (`environment`). A game that fails this is asked nothing.

**The runs** (series `b`, one launch of the real game each; `reviews/25-guardian/runs/<run>.json`): the close alone 3 times, the path 3 times.

| Run | Before | What ran | After Java's exit | Java's status | Time |
|---|---|---|---|---|---|
| `close-1-b` | block 5 not on the disk | SIGTERM by the rig, 1 ms after the game's answer; no save asked | block 5 on the disk; `level.dat` written and the player's data written after the signal | 143 | 0.67 s from SIGTERM to exit |
| `stop-1-b` | block 7 not on the disk before `save`; block 8 not on the disk before `stop` | adopted, hello accepted, `IN_WORLD`; `save`: exit 0, 0.19 s, block 7 on the disk after it; `stop`: exit 0, record `saved`, `exited` | blocks 6, 7, 8 on the disk | 143 | `stop` 0.87 s as a command (+0.08 s: the save is confirmed (saved): Saved: AresHub is on the disk.; +0.08 s: SIGTERM sent to Java; ended after 0.75 s: confirmed, close exited) |
| `close-2-b` | block 10 not on the disk | SIGTERM by the rig, 1 ms after the game's answer; no save asked | block 10 on the disk; `level.dat` written and the player's data written after the signal | 143 | 0.74 s from SIGTERM to exit |
| `stop-2-b` | block 12 not on the disk before `save`; block 13 not on the disk before `stop` | adopted, hello accepted, `IN_WORLD`; `save`: exit 0, 0.22 s, block 12 on the disk after it; `stop`: exit 0, record `saved`, `exited` | blocks 11, 12, 13 on the disk | 143 | `stop` 1.03 s as a command (+0.11 s: the save is confirmed (saved): Saved: AresHub is on the disk.; +0.12 s: SIGTERM sent to Java; ended after 0.89 s: confirmed, close exited) |
| `close-3-b` | block 15 not on the disk | SIGTERM by the rig, 2 ms after the game's answer; no save asked | block 15 on the disk; `level.dat` written and the player's data written after the signal | 143 | 0.69 s from SIGTERM to exit |
| `stop-3-b` | block 17 not on the disk before `save`; block 18 not on the disk before `stop` | adopted, hello accepted, `IN_WORLD`; `save`: exit 0, 0.25 s, block 17 on the disk after it; `stop`: exit 0, record `saved`, `exited` | blocks 16, 17, 18 on the disk | 143 | `stop` 0.97 s as a command (+0.17 s: the save is confirmed (saved): Saved: AresHub is on the disk.; +0.17 s: SIGTERM sent to Java; ended after 0.86 s: confirmed, close exited) |
| `verify-b` | | reopened once more, quit by closing the window | | 0 | |

Reopened (15 blocks, each asked of the next launch's game and read from the region file; all there): `stop-1-b`: 4, 5; `close-2-b`: 6, 7, 8; `stop-2-b`: 9, 10; `close-3-b`: 11, 12, 13; `stop-3-b`: 14, 15; `verify-b`: 16, 17, 18.

**What was built** (all in `reviews/25-guardian/rig/`, a copy of `reviews/49b-arena-rerun/rig/` without its
measuring parts; a development aid, nothing ships):

- `run.sh` (the client-test lock, the memory and owner-game guards, package 47's GPU holder), `start.sh` (its own
  headless labwc), `inner.sh` (the restricted helper, the virtual keyboard, `gradlew --no-daemon runClient`),
  `lifecycle.sh`, `health.py`, `input.py`, `vinput.py`, `helper41.py`, `make-apps.py`, `retry.sh`, `jvm.gradle`:
  copied, with the names changed and the session's identity read from the run's private file.
- `check.sh` (one launch: `MODE=create|close|stop|verify`) and `check.py` (the check itself, and the public evidence).
- `java-wrapper.py`: stands in for Prism's wrapper. The game's JVM runs in a scope of its own; only its command line
  gets the run's `XDG_RUNTIME_DIR` and the gate; the wrapper holds the desktop lock as the real one does, stays Java's
  parent, and writes Java's real status with the real wrapper's own `end_report`, `write_exit` and `report_again`.
- `supervisor.py`: the real supervisor with stand-ins for Prism, the helper, the cover, the window and
  `systemd-inhibit`, as the loop test's harness has them.
- `probe/`: a data pack. `/trigger pkg25 set <n>` sets a glass block in the air above the home pad, `set <100 + n>`
  says whether it is there; `/trigger` needs no cheats, so the home keeps its commands off.
- `region.py`: reads one block from a save's region file, offline.
- `series.sh <tag> [first block]`: the home if there is none, then the close alone and the path in turn, three each,
  then one more reopening; started again with the same tag it goes on where it stopped. `summary.py <tag>`: the
  table below from the evidence, and exit 1 if anything in it is not as the check expects. `test_rig.py`: the rig's
  own checks without a game.

**Commands run:**

| Command | Result |
|---|---|
| `python3 -B reviews/25-guardian/rig/test_rig.py` | 4 tests, OK, 2 s: the region reader on a region file made there; with a stand-in game in a real, disposable user scope: the environment check and its two refusals, the close alone (143), the path (adopted, hello, `save`, `stop`: `saved`, `exited`, 143, nothing left behind) |
| `bash -n` on the rig's scripts | OK |
| `reviews/25-guardian/rig/series.sh a` | `create-a` made the home (the supervisor's `check_world`: ok). `close-1-a` and `stop-1-a` ran with one block per check and showed that the game had the lone block on the disk before anything was asked (decision 70); they are kept as they are. Stopped there. |
| `reviews/25-guardian/rig/series.sh b 4` | the runs in the table above; `summary.py b`: nothing odd, exit 0 |

Exit 75 (short of memory while another session's client test ran) came 11 times in all; each was waited out
for five minutes, never forced. No `os/tests` module was run: nothing under `os/` changed.

**Step 7: 3.1, the shutdown guard, and the VM checks.** Nothing of it ran on the laptop's own systemd: the unit
is only written here, and every test uses a stand-in `systemctl`.

- **The unit** `os/config/usr/lib/systemd/system/aresos-guardian.service`: `Type=oneshot`, `RemainAfterExit=yes`,
  `User=ares`, `Environment=XDG_RUNTIME_DIR=/run/user/1001`, `ExecStart=/usr/bin/true`,
  `ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown`, `TimeoutStopSec=85`, `WantedBy=graphical.target`.
  Enabled in `os/build.sh`.
- **Its order.** `After=greetd.service user@1001.service user-runtime-dir@1001.service` and
  `RequiresMountsFor=/var/home/ares` (the home's mount, whichever unit that is). The drop-in
  `session-.scope.d/50-aresos-guardian.conf` (`Before=aresos-guardian.service`) orders every session scope before
  it. systemd stops in reverse: the guard's stop ends before any of them begins to stop.
- **Armed first.** `Supervisor.guard_armed()` → `Runner.guard_active()` (`systemctl is-active
  aresos-guardian.service`, 2 s at most; only `active` counts; `activating` is asked again inside the same 2 s).
  Asked in `begin()` (before Prism is started) and in `on_jvm_start()` (every JVM). Not active: the window `guard`
  (`RECOVERY`, no latch, in `STICKY`), with systemd's word in it; `retry` asks again.
- **The guard's command** (`guard_command()`; `main()` sends `stop --reason shutdown` there, every other stop
  keeps `stop_command()` and its 70 s):
  1. No runtime folder: no session, exit 0, nothing asked.
  2. Ask the supervisor, `GUARD_REPLY_WAIT` 62 s for all of it. A reply that was recorded: its message, exit 0
     only for `ok`.
  3. No answer: the guard takes the desktop lock itself (`desktop_lock_state()` over `take_desktop_lock()`).
     Free: no game runs, exit 0 at once. Held or unknown: one recovery attempt, `GUARD_RECOVERY_WAIT` 10 s, asked
     again each second.
  4. Still no answer with the lock held or unknown, or a reply with `recorded: false`: the fallback record
     `~/.local/state/aresos/desktop-guard.json` (`Paths.guard_file`; `write_durable`, 0600; `schema`, `why`
     (`no_answer`, `unrecorded`), `lock` (`held`, `unknown`, `free`), `save`, `launch` from the runtime file,
     `written`), exit 1. It never signals anything.
- **The next start** (`apply_guard_fallback()`, in `start()` after `close_stale_stop()`, only when no game was
  adopted): latch `unsaved` with what the guard found, unless the supervisor's word is that the home was saved (its
  own stop record of that launch, or the `save` the guard passed on). Applied once: the file is removed after the
  latch is on the disk.
- **The game's scope** has `--property=TimeoutStopSec=15s` (`GAME_STOP_TIMEOUT`, `game_scope()`).
- **`os/ci/image-checks.sh`**: the guard is enabled (the link in `graphical.target.wants`), each of its lines, the
  drop-in's line, and the `aresos.black` rule in `rc.xml` (step 4's decision 52).
- **The VM checks** (run only in the lead's check build):
  - `os/ci/overlay/guardian.py` (the guest; action `guardian-arm` in `checks.py`), `os/ci/overlay/GuardianGame.java`
    (the stand-in game), `os/ci/guardian_host.py` (the host), and four places in `os/ci/vm.py` (bound: recorded
    with `rebind.py pending`, `os/manifest/ci/16/pending-rebind.json`). `.github/workflows/os-image.yml` is
    unchanged: vm.py's pass 1 is the brief's boot 1 (`save`), pass 2 is boot 2 (`hang`).
  - **`guardian-arm`**, after the existing checks and before the power key: the guard as systemd loaded it
    (`active`/`exited`, `enabled`, `1min 25s`, `User=ares`, its `ExecStop`, its `After` with the three units and
    the home's mount unit that `findmnt` names; the session scope's `Before` has the guard; no "ordering cycle"
    line in the boot's journal); `status` has `labwc: true`; the image's Java has `jdk.compiler`; a disposable
    home `AresHub` is seeded as ares (`seed_world()`: it passes `check_world`); the recovery terminal is ended;
    `retry` until the `killed` latch clears; the stand-in game is started through the real wrapper in the
    transient unit `aresos-ci-game.service` (as ares, `DefaultDependencies=no`); wait for `jvm_pid` and
    `lifecycle: true`; Prism is ended; wait for `windows == []`; the game scope's `TimeoutStopUSec` is `15s`
    (asserted), the session scope's is printed; the guard's `ActiveEnterTimestampMonotonic` is before the
    session's first `the game is starting` line. Then three watchers: `aresos-ci-guardian-probe` (as ares: twice a
    second labwc, the JVM, the wrapper, the socket by a `status` request, the home by a written and fsynced file,
    the units' states, the black window, the console; and one connection that asks `status` 64 times a tick from
    the moment the guard's stop begins and never reads), `aresos-ci-guardian-lid` (boot 1: a uinput lid that closes
    when the game writes its save marker, then logind's `LidClosed` and its list of AresOS's lid blocks),
    `aresos-ci-guardian-record` (`Before=aresos-guardian.service`, so its `ExecStop` runs after the guard's stop
    has ended: the stop record's allowlisted fields from `desktop.json`, whether Java is alive, whether a fallback
    record exists).
  - **The host**, after `system_powerdown`: waits for the game's `save_asked` line on the serial console, takes
    the screen until it is black (at most 0.1 % of the pixels brighter than 8; the frame before the key must not
    be black), in boot 2 presses Ctrl+Alt+F3 and takes the screen again; waits for the power-off inside
    85 + 15 + 20 s; then `guardian_host.check()` on `evidence/vm-pass-N/offline-boot.jsonl`:
    - both boots: power key < the guard's stop began < the save asked < the guard's stop ended; the session scope,
      `greetd.service`, `user@1001.service` and the home's mount began to stop only after it (systemd's own
      `Stopping …`/`Unmounting …` records); labwc gone only after it; every probe sample in between has labwc, the
      wrapper, the socket (answering, `stopping: true`), a writable home and the four units `active`; a black
      window and `black: true`; no sleep; no ordering cycle;
    - boot 1: the save answered at least 4.5 s after it was asked, then `closing` (SIGTERM), then the wrapper's
      exit with status 143, all before the guard's stop ended; the record says `saved`, `exited`, 143, closed,
      `shutdown`, no latch, no fallback record; the guard printed `Stopped: the home was saved first; Minecraft
      closed.`; the peer that never reads was dropped; the lid closed between asked and answered and logind saw it;
    - boot 2: no answer; `sigterm_ignored` 25 to 35 s after the save was asked; the guard's stop took 55 to 85 s;
      Java alive when it ended; the record says `overrun`, a save that is not `saved`, `sigterm`; the guard printed
      `Not a confirmed stop: the home could not be confirmed as saved first; …`; the wrapper ended 10 to 30 s after
      `user@1001.service` began to stop (the scope's 15 s); the probe saw `tty3`.
    The summary is `evidence/vm-pass-N/guardian.json`; the guest's facts are `guardian-arm-result.json`.

| Module (step 7, run by name as above) | Result |
|---|---|
| `test_aresos_guardian.py` | 106 tests, OK (12 new: `GuardTest`) |
| `test_aresos_guardian_loop.py` | 26 tests, OK, 63 s, twice (5 new: no game until the guard is active; the guard's command with nothing running and with a game; no supervisor while the game runs: the fallback record and `unsaved` at the next start; the check build's stand-in game as a real JVM, saving and ending with 143, and hanging). Run with `PATH=<a JDK 25>/bin:/usr/bin:/bin`; with the plain PATH the two JVM tests skip here (no Java on this laptop's PATH). No process left behind |
| `test_guardian_vm.py` (new: the VM proof's unit-level parts) | 7 tests, OK |
| `test_aresos_desktop.py` | 189 tests, OK (1 skipped), 182 s, on the final code (and once before the last edit, 184 s) |
| `test_control_vm.py`, `test_everyday_account.py`, `test_console_keymap.py` (they load or read `checks.py` and the overlay's `Containerfile`) | 62, 34 and 21 tests, OK |

Existing assertions changed: `game_scope()`'s exact command in `test_aresos_desktop.py` (two places: the new
property); the inventory of every `os.unlink` in `UseHomeTest.test_one_function_moves_a_world_folder_and_nothing_
deletes_one` (one more: the guard's fallback record, the supervisor's own small file); and the loop test of a game
that ignores SIGTERM now sets systemd's word through the harness's stand-in (`control/system`) instead of a script
of its own. `test_aresos_cover.py`, the `test_aresos_shell*.py` modules and the rig's `test_rig.py` were not touched
or run. After the tests `origin/main` was merged (7 commits, none in a file of this step).

**The hosted run** (`checks_only=true`, the whole `os/tests` suite, no VM): run **44458416374**, started on
`bda87419` (the step's last code commit) and not watched. It boots no VM and is no proof of the guard (the lead's
fix 7). Step 8 reads its result first: it is the first run of the whole suite with this step's changes, and the
first with a Java on the runner's `PATH` for the two stand-in game tests (they need 16 or newer, and skip
otherwise).

**New image files** (for the release diff): `/usr/lib/systemd/system/aresos-guardian.service`,
`/usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf`, the link
`/etc/systemd/system/graphical.target.wants/aresos-guardian.service`. New state file on his disk:
`~/.local/state/aresos/desktop-guard.json` (only after a shutdown with no answer; R28 never reads it).

**Step 8a: main merged, the image rule the check build stopped on, section 5's docs.** The lead's check build
(run **44533435611**, `check_build=build`) failed in "Throwaway image build and checks", before the VM, at the old
rule in `os/ci/image-checks.sh`: `grep -rlE 'aresos-desktop|prismlauncher'` over `/usr/lib/systemd/system` and
`/etc/systemd/system`, "A system unit starts the desktop". It matched the guard's own unit (its `ExecStop` and its
`Documentation=` line). Every image check before it had passed.

- **`origin/main` merged** (37 commits: 53c, 53d, 53f, 56, 311, 311b and handoffs; merge commit `df167952`). Two
  files conflicted; every other overlap merged by itself:
  - `os/config/usr/libexec/aresos-shell`, three hunks. **Constants:** 25's `BLACK_APP_ID`, `COVER_APP_IDS`,
    `MESSAGE_WINDOW_APP_ID`, `WINDOW_NAMES`, `WINDOW_NAME_CHARS` kept beside 53c's `LAPTOP_HOME_APP_ID`.
    **`Windows.covering()`:** leaves out both covers (25) and the laptop home (53c); its docstring names all three.
    **`Windows.app_windows()`** (no conflict, but the same question): the laptop home is left out of the `windows`
    count too, so it never keeps the screens from going black and never refuses a `logout` (decision 95). The module
    docstring's status-pipe section says so. Merged by themselves and unchanged: 53c's `view_focus` gate and
    foreground bookkeeping, 53d's `shell_search` with its SIGUSR1 handler first in `main()` (25's `windows` line
    when the compositor is lost stays in the `WaylandError` branch), 56's `focus_reported` and background
    `shell_focus` in `windows_changed()` (25's `report_windows()` stays its last call, after `search_landed()` and
    `report_covered()`).
  - `os/manifest/ci/16/pending-rebind.json`: both sides' `changes` rows kept (main's 311 and 311b, then 25's). The
    `files` list merged by itself; every bound file's bytes match its row (`os/ci/vm.py` is 25's, main did not
    change it).
  - Merged by themselves: `os/ci/image-checks.sh` (main's 311 labwc checks and 53f laptop-home check beside 25's
    guard and `aresos.black` checks), `os/tests/test_aresos_desktop.py` (main's labwc stages in the Containerfile
    test, 25's guard and scope changes), `os/tests/test_aresos_shell_views.py` (main's 53c tests beside step 4's
    two-line status assertion).
- **The image rule** (`os/ci/image-checks.sh`, the heredoc `SYSTEM_UNITS`; it replaces the grep). A Python check over
  the same two trees, run as root in the image:
  - it reads every file's `Exec*=` lines (continued lines joined and comment lines skipped, as systemd does);
    comments, `Documentation=` and every other key are not read;
  - any `Exec*=` line naming `aresos-desktop` or `prismlauncher` (the old rule's names and case) fails, in a unit
    or a drop-in, in either tree;
  - the one exception is `/usr/lib/systemd/system/aresos-guardian.service` by that exact path (a link to it, such as
    `graphical.target.wants/aresos-guardian.service`, is the same file and checked the same way): its `Exec*=`
    lines must be exactly `ExecStart=/usr/bin/true` and `ExecStop=/usr/libexec/aresos-desktop stop --reason
    shutdown`, each once, nothing else; the guard's path being a link fails;
  - a drop-in that systemd applies to the guard (`aresos-guardian.service.d`, `aresos-.service.d`, `service.d`, in
    either tree) must have no `Exec*=` line at all; other keys pass;
  - a copy of the guard anywhere else (such as `/etc/systemd/system/aresos-guardian.service`, which would override
    it) fails like any unit that names the desktop;
  - links to `/dev/null` (masks) and dangling links are skipped; links to folders are not followed (as `grep -r`).
  - The failure prints `A system unit starts the desktop or Prism:` and one line per finding (the file and its line,
    or what the guard runs against what it may run), then exits 1 with `SYSTEM_UNITS_FAILED`. The pass prints
    `SYSTEM_UNITS_OK …` and the `PASS` line `no system service runs the desktop: it starts inside the everyday
    session only; the shutdown guard only asks it to stop`.
- **Its tests:** `SystemUnitRuleTest` in `os/tests/test_guardian_vm.py` (6 new tests) cuts the heredoc out of
  `image-checks.sh` and runs it with `python3 -I -` against unit trees made in a temporary folder, as the image runs
  it: the image's tree as shipped (the real guard unit and its drop-in, the `wants` link, `service.d` with no
  `Exec`, a mask, a dangling link, a unit that names the desktop and Prism only in a comment, `Documentation=` and a
  `;` line) passes; eight changed guards fail (another stop, a start of the desktop, another start, one more `Exec`
  line after the stop, one before the start, the stop twice, no stop, a continued line that adds Prism); a copy at
  `/etc/systemd/system/aresos-guardian.service` fails; the guard as a link fails; a drop-in with an `Exec` line fails
  in each of the four folders that apply to the guard (and one without passes); five units that start the desktop or
  Prism fail (`ExecStart`, `ExecStart = …` with spaces, `ExecStartPre=-…aresos-desktop-java`, a `getty@.service.d`
  drop-in, a continued line with a `;` comment inside).
- **Proved by hand as well**, the rule cut out of the script into the scratchpad and run on three temporary trees:
  | Tree | The old grep | The new rule |
  |---|---|---|
  | `good`: the shipped guard and its `wants` link | fails (`A system unit starts the desktop`): the check build's failure | exit 0, `SYSTEM_UNITS_OK` |
  | `changed`: the guard's `ExecStop` made `aresos-desktop restart` | fails | exit 1: `…/lib/aresos-guardian.service: the shutdown guard runs exactly [...], but its Exec lines are [...]`, and the same for the `wants` link |
  | `desktop`: `etc/aresos-desktop.service` with `ExecStart=/usr/libexec/aresos-desktop` | fails | exit 1: `…/etc/aresos-desktop.service: ExecStart=/usr/libexec/aresos-desktop` |

  And read-only on this laptop's own trees (the running AresOS image, 612 files, no guard there): `python3 -I -
  /usr/lib/systemd/system /etc/systemd/system < rule.py` → exit 0, `SYSTEM_UNITS_OK` (the old grep also found
  nothing there). So no unit of the current base trips the new rule; its `service.d` holds only
  `10-timeout-abort.conf`, without an `Exec` line.
- **Section 5's docs:**
  - `docs/design/OS-BASE.md` B1: the `prepare_stop`/`save_complete` row says it is not built and why (2.6: a
    confirmed `save_world`, then SIGTERM; no stop certifies the closing save; confirmed or unsaved); the `save_world`
    row says both ends are built and gives the supervisor's acceptance rules (1.2 to 1.5) in place of "the
    supervisor's side waits for package 25".
  - B2: a **Built (package 25)** paragraph: `STOPPING`, the one routine and its deadline, what confirms a save,
    called off or `unsaved`, `overrun`, `stopped`, the admission block, the `unsaved` latch, and section 4 in two
    sentences.
  - B3: a **Built (package 25)** block: the guard (its order, armed first, its fallback, the game scope's 15 s, why
    not a delay lock), the black screen, the lid block, and what is not as B3 proposes (60 s, not 120 s; an app
    window open closes as before). The coordinator, its block inhibitor, "close your apps first", the battery and
    `request_power` stay proposals.
  - The supervisor's docstring: B3 in its design line; `STOPPING` in its states; planned stops never restart; the
    commands `save`, `stop`, `restart`, `logout`, `use-home`; `restart`, `logout`, the signals and labwc's end, the
    admission block and the `unsaved` latch; a paragraph on the guard.
  - Not touched: `os/owner-tools/`, `os/release/`, the install guides, `STATE.md`.

**The `aresos-shell` lines 25 changes, after the merge** (for the lead's notice; step 4's list above has the numbers
before it): 73 to 79 (the docstring's `windows` line); 155 to 164 (the constants); 210 (`PRIVATE_ENVIRONMENT`); 240,
241, 254, 257 (`StatusPipe`); 2699, 2700, 2714 (`covering()`); 2717 to 2725 (`app_windows()`); 3077 to 3079 and 3121,
3122 (`Helper.__init__`); 3926 (`tick()`); 3945 to 3967 (`windows_changed()`, `report_windows()`,
`window_name()`); 4685 (`main()`). `rc.xml`: lines 41 to 43, unchanged by the merge.

| Pattern (step 8a, each run alone as `env -i HOME=$HOME PATH=/usr/bin:/bin python3 -B -m unittest discover -s os/tests -p '<pattern>'`, on the final code) | Result |
|---|---|
| `test_aresos_desktop*.py` | 189 tests, OK (1 skipped), 177 s |
| `test_aresos_guardian*.py` (`test_aresos_guardian.py`, `test_aresos_guardian_loop.py`) | 132 tests, OK (2 skipped: the two stand-in JVM tests, no Java on that PATH), 58 s. `test_aresos_guardian_loop.py` once more with `PATH=<the local JDK 25>/bin:/usr/bin:/bin`: 26 tests, OK, nothing skipped, 62 s |
| `test_aresos_shell*.py` (all 15 modules, `test_aresos_shell_search.py` from main among them) | 407 tests, OK, 14 s |
| `test_aresos_laptop_home*.py` (main's two modules) | 54 tests, OK (3 skipped: two opt-in memory runs, one needs gtk4-layer-shell), 61 s |
| `test_guardian_vm.py` (the image rule's tests are here) | 13 tests, OK (6 new: `SystemUnitRuleTest`) |
| `test_console_keymap.py` (it cuts another heredoc out of `image-checks.sh`) | 21 tests, OK |

Existing assertions changed: `test_every_window_counts_but_the_desktops_the_covers_and_the_message_window`
(`test_aresos_shell_guardian.py`) also opens an `aresos.laptop-home` window and is renamed `…_and_the_laptop_home`;
`test_the_names_the_three_programs_share` also checks that the helper's `LAPTOP_HOME_APP_ID` is the laptop home
program's own `APP_ID`. Not run: the whole `os/tests` suite, `test_owner_update`, `test_inherited_homebrew`,
`test_sysusers`, and the rig (nothing under it changed). No GitHub run was started or watched.

## Left, in order

The lead's next `check_build=build` on step 8c must pass both boots before merge (lead's fix 7).
Check `guardian.json` in each pass for the two recovery services' completed stops after the guard. Boot 2 must
also record `tty3_seen` during the black stop. The lead owns the check build, final `REPORT.md` and PR.

## linux-aresos's read checklist (2026-11-19)

From the lead, for steps 7 and 8:

1. **The black window never outlives its stop.** A cancelled, failed or hung-past-bound stop removes it and the
   desktop returns. Steps 7 and 8 need tests for a hung save and a cancelled stop if any is missing, and the VM
   checks that a text console (Ctrl+Alt+F3) still switches behind it.
2. **The lid inhibitor in the VM** is taken from the supervisor's own context, not a terminal (polkit judges by
   session). Its result is logged, and a refusal never fails the stop. Step 4 built the logging; step 7 checks it.
3. **`windows` names** are app names, never window titles (already so; keep titles out of every log).
4. **`rc.xml`:** step 7 checks whether `os/ci/image-checks.sh` pins anything in `rc.xml`. The merge must keep 21b's
   key bindings and 23c's `Super_L` keybind; the lead coordinates the order.

**Step 7's answers:**

1. Tests: a refused save, an overrun and Java's own end were there (`BlackTest`, step 4). Added: a save that hangs
   (`GuardTest.test_a_save_that_hangs_takes_the_black_screen_away_when_the_stop_is_called_off`, `restart` and
   `logout`: at the save deadline the stop is called off, the black screen and the lid block end, the window
   shows, the game runs on). The VM presses Ctrl+Alt+F3 behind the black screen in boot 2 and requires the probe
   to see `tty3`.
2. The lid block is taken by the supervisor in the session (never by the check). The VM reads the supervisor's
   `lid_block` and, in boot 1, logind's own list. A block that logind does not list is printed as `REPORTED, NOT
   BLOCKING` and never fails the check or the stop; the lid event itself, and that nothing slept, are asserted.
3. Unchanged: names only. The VM's evidence takes the count of windows, never a name or a title.
4. `os/ci/image-checks.sh` pins no hash of `rc.xml`. It pins: the exact lines of the `aresos-desktop` rule and
   the `aresos.cover` rule (and now `aresos.black`); the brightness, volume and mute bindings' commands;
   `W-C-Escape` (exactly one binding with its two actions, in order); `theme/name`, `theme/titlebar/layout`, the
   window switcher's `style`; and every absolute command path in the file must be in its list of startup commands.
   A new keybind such as 23c's `Super_L` breaks none of these unless it runs a command outside that list.

## Decisions taken where the brief left room

1. **The active world, and how much of 4.4 is in.** 1.3 defines the active world through 4.4's check, which is step
   5. Built now: `check_world(paths, lock, name=None)` takes a folder name, and `ready()` calls
   `note_ready_world()`, which makes a reported world the active one only if it is one plain path component inside
   the worlds folder and passes the home checks. Not built (step 5): a damaged or outside world is still *declared
   ready* as before, and a dated home does not set `hub_seen`. A reported world that fails the check leaves the
   active world unchanged, so a save there ends `wrong_world`, never `saved`.
2. **A request nobody waits for is given up.** When every caller of the request in flight has reached its deadline,
   the slot is freed and the waiting request goes out. The late answer no longer matches an id in flight and is
   logged and dropped. Without this a hung save would hold the slot for ever. The mod joins or queues the extra
   request itself.
3. **An answer with a wrong or unknown id is dropped** and the request stays in flight until its real answer or its
   callers' deadlines. Ids must be JSON integers: `true`, `1.0` and `"1"` do not match.
4. **`no_channel` is answered at once**, not held until a hello arrives. Step 2's "ask again each second" does the
   waiting.
5. **A replaced or closed connection.** The request in flight on it is `lost`. A waiting request goes out on the new
   connection when a newer hello replaced the old one, and is `no_channel` when there is none.
6. **`invalid` and `wrong_world`.** `ok:true` with no `world` object or an `id` that is no text is `invalid`. A named
   world that is not the active one, `desktop` anything but `true`, or an active world that changed since the request
   went out is `wrong_world`. `ok:false` with a reason outside the mod's four is `invalid`.
7. **`--reason`** (`shutdown`, `backup`, `update`, `manual`; default `manual`) on the command line, for `save` now and
   `stop` in step 2. The socket op answers `bad_reason` for anything else and asks the game nothing.
8. **Every reply is non-blocking**, the wrapper's too. A wrapper reads its reply at once, so nothing changes for it.
9. **Save ids count per supervisor process.** A replacement supervisor starts at 1 again; its connection is new too.
10. **`aresos-shell` is untouched.** Its own `PRIVATE_ENVIRONMENT` does not list the gate; the helper never gets it
    from the supervisor. Step 4 changes that file anyway and can add the name.
11. **How the loop tests keep the machine rules.** The supervisor is a process of its own under `env -i` with exactly
    `HOME`, a temporary `XDG_RUNTIME_DIR`, `PATH` and the `LABWC_PID` of a stand-in. The stand-ins read their paths
    from a file beside them, so no test variable rides in the environment. A process is signalled only if its
    `/proc/<pid>/environ` names the test's runtime folder.

Step 2:

12. **A closed record stays in `desktop.json`** (`open: false`, with `save`, `close`, `status`, `ended`) as the last
    stop's outcome until the next stop replaces it, so the VM can read "confirmed and exited" offline. Only an open
    record names a launch.
13. **"Clearly not stopping"** is `initializing`, `starting`, `running`, `degraded` or `maintenance`: systemd answers
    `stopping` before any of them. `stopping` is yes; anything else, an error or no answer in 2 s stays a shutdown.
14. **The admission block is bound to the instance and to the session's labwc** (`LABWC_PID` from the supervisor's own
    environment, with its start ticks; only looked at). The runtime folder, and the instance in it, can outlive a
    session; by the instance alone an old block would keep the next session's desktop from ever starting. Without a
    live `LABWC_PID` it is bound to the instance alone. A block that cannot be read is no block.
15. **Every stop asks its save with reason `shutdown`** (the game is about to be closed).
16. **Only `no_channel`, `no_world` and `server_stopping` are asked again.** `lost`, `timeout`, `invalid`,
    `wrong_world`, `not_desktop_world` and `error` are not confirmed at once. The next ask goes out only if a whole
    second still fits before the save deadline, so with the real numbers a save phase gives up after 29 s.
17. **Java gone before the save was confirmed** is `stopped` with the latch `unsaved`, for every kind. The one
    exception is the wrapper's own word that Java never ran (a failed start): nothing to save.
18. **A stop that could not be recorded answers `ok: false`, `recorded: false`**, also when it was saved and exited
    (the lead's fix 1: the guard then takes its fallback path).
19. **"Nothing is running" needs a free desktop lock too.** With the lock held by a game this supervisor cannot see,
    a stop that can be called off is; a shutdown writes a record with `launch: null`, answers `unsaved`, `failed`,
    and the next start latches `unsaved`.
20. **A plain stop with nothing running** calls off a pending backoff restart and shows `quit`, unless a message
    window already shows something else. It writes no record.
21. **The close is `exited` by the status alone (143).** Java gone but the lock still held at the deadline is
    `overrun`.
22. **A stop asked for after an overrun is a new stop**: a new 60 s and a new record (a second SIGTERM at most).
23. **A `save` that joined** hears the stop's last save result when the stop ends (`no_channel` if none was asked).
24. **The texts of `save_failed`, `stuck` and `unsaved` exist now**, because step 2 enters them; step 3 owns the
    windows' final texts and `desktop-view.bashrc`.
25. **`retry` on `stuck` or `save_failed` with the game alive** clears the window, as for every other window.
26. **The game scope's result is not asked for a stopped launch**: `scope_result()` can block up to 10 s.
27. **R28's key list is frozen from this branch's `Persisted` without `stop`** (`R28_KEYS`, `r28_load` in the test).
    It was not compared with R28's image: no tag of it is in this checkout. **Confirmed by the lead (2026-11-19):**
    the list matches main's `Persisted` keys, and main is what R28 is cut from today. Step 3 added no persisted key.

Step 3:

28. **The session's end is never asked about.** `end_session()` skips `systemctl is-system-running`: a signal or
    labwc's end cannot be called off (2.2), whatever systemd says. It always writes the admission block, so SIGTERM
    to the supervisor by hand ends this session's desktop until the next login (the keeper ends with exit 0, as
    before).
29. **`STOP_EXIT_RESERVE` 3 s.** With a signal, labwc's end, or a logout that waits for labwc, the wait for Java (or
    labwc) ends at 57 s, so the supervisor's own exit fits inside the 60 s (2.1). A `stop --reason shutdown` from the
    guard keeps the whole 60 s: the supervisor does not exit after it. The reply's text still says "60 seconds".
30. **A signal after an overrun exits at once.** If the open record names the launch that is still there, with
    SIGTERM sent and `overrun`, nothing more is waited for (2.7). Decision 22 stands for commands.
31. **labwc "gone" is no such process, or one that has exited.** A `LABWC_PID` whose number another process took
    reads as "not watched", never as gone.
32. **Without a watched labwc `logout` is refused before anything is stopped** (`error: no_session`), instead of
    stopping the game and then reporting that labwc stays.
33. **The `windows` event** is `{"event": "windows", "count": n, "names": [...]}`. A count that is no JSON integer
    from 0 up makes the count unknown (the helper says so when it lost track). Names are optional (64 at most; a
    missing one reads "an app without a name"). It is read whether or not a game runs. The count is unknown until
    the helper that runs now has reported, and again when it exits. "Fresh" means the last report of the running
    helper: there is no age limit, because reports come only at changes.
34. **A refused logout** answers `result: refused` with `error` (`apps_open`, `apps_unknown`, `no_session`) and
    `windows`; no record, no block. The logout phase is logged but not written into `desktop.json` (the launch's
    record is closed by then). A stop that logged out answers with `kind: shutdown` (the ending session made it
    final) and `logout: exited` (labwc's pidfd fired) or `ending` (the session's signal came first).
35. **A `restart` or `logout` that joins a running stop** hears that stop's reply; nothing is restarted or logged
    out (2.8: nothing starts a second stop).
36. **`restart` starts again only when the game is gone and no latch is set.** A latch, also `unsaved`, shows its
    window instead: `retry` stays the only way past a latch. With nothing running and a start already on its way
    (Prism up, no Java yet) it starts no second Prism (`restart: starting`). An unknown window count starts below
    the app in front, without the cover. Exit 0 needs confirmed, `exited` or nothing running, and the new start.
37. **Three windows for a stop that was called off:** `save_failed`, `save_failed_restart`, `save_failed_logout`
    (the first sentence says what was not done; the rest is the same). All are in `STICKY`.
38. **The `helper` window offers `restart`** in place of "retry (after closing Minecraft)".
39. **Only a logout's admission block is lifted.** The block file's `kind` decides; a logout's block that a
    shutdown joins is rewritten as a shutdown's. Step 2 would have lifted a shutdown's block when a logout was
    tried after it.
40. **The exit's cleanup is shared.** At the supervisor's exit the helper has 5 s at most (as before), but the
    window and the covers share that wait instead of adding 5 s and 2 s of their own. `stop_helper()` and
    `close_view()` are unchanged for use during a session.

Step 4:

41. **Black comes only at a stop's start** (or when a shutdown joins a plain stop). An app that closes during the
    stop does not bring it, and a replacement supervisor that goes on with a stop does not go black: the first one's
    black screen died with it, and no helper has reported to the new one.
42. **Black also with nothing running.** A shutdown or logout from a recovery window goes black the same way; a
    `restart` with nothing running shows black for a moment and then its startup cover.
43. **The restart's handover is a fixed 2 s** (`BLACK_HANDOVER`) after the startup cover was started, not a signal
    that the cover is on the screen: one timed item instead of a pipe from the cover. If the cover needs longer, the
    desktop shows for a moment. It ends sooner when the home is ready or a window shows, and at once when the new
    start has no startup cover.
44. **At a shutdown the lid block stays, as the black screen does**, until the supervisor exits or its own limit
    (the child's `sleep 90`); the brief says "for the length of every stop". logind looks at a closed lid again as
    soon as a block is released, and a shutdown that did not go through logind could then suspend in the middle of
    the teardown. For `stop`, `restart`, a stop that is called off and a logout that does not go through it ends with
    the stop. **Confirmed by the lead (2026-11-19):** the lid block stays with the black screen until the supervisor
    exits at a shutdown or at a logout that goes through.
45. **Unknown takes the black away too.** A `windows` report with no count, and the helper's exit, end the black
    screen as an app window does (unknown counts as open). In a teardown the helper can die a moment before labwc;
    then the black screen ends that moment earlier.
46. **Which windows count** (`Windows.app_windows()`): every toplevel the compositor has described (its first `done`)
    except the desktop's (and its dialogs), `aresos.cover`, `aresos.black` and the message window `aresos.desktop`.
    Minimized ones count, windows nobody owns count (Prism's own window, the recovery terminal). A toplevel that is
    not described yet never counts: it could be the black screen itself, and counting that would take it down.
47. **Names** are the program's name from the catalogue, else the window's app id; printable characters only, 40
    characters, at most 8 names, sorted. `count` is always the full number.
48. **A dropped report is written again.** The status pipe drops a line when it is full, and no heartbeat repeats
    this one, so `StatusPipe` says when it dropped a line and `tick()` (every 0.5 s) writes it again.
49. **The lid block's stderr goes to the supervisor's** (the journal), so logind's own refusal can be read there.
    Released with SIGTERM, SIGKILL 2 s later if it is still there (the covers' mechanism).
50. **The black screen hides the pointer** (`set_cursor_from_name('none')`), and follows outputs that come and go.
51. **`hide-cover` (Super+Ctrl+Escape) ends the black screen too.** The recovery terminal it opens counts as an app
    window anyway, once the helper says so.
52. **No image check was added** for the new rule or `--black` (`os/ci/image-checks.sh` is CI's; step 7).

Step 5:

53. **`use-home` goes through the running supervisor only.** It alone knows that no launch is alive, in hand-off or
    still with Prism. With no supervisor the command moves nothing and says so (in a session the keeper keeps one
    running).
54. **`use-home` takes a name, never a path**: exactly HomeSwap's two dated forms, with the `-1`, `-2` suffix. A
    trailing `/` from the shell's completion is dropped. `AresHub-unfinished-<date>` and every other name are refused;
    he can still rename a folder himself.
55. **`use-home` changes no state**: it clears no latch, sets no `hub_seen` and starts nothing. Its reply ends with
    `Type retry.`
56. **"No launch alive and none in hand-off" is read widely** (`home_busy()`): also no stop running, the session not
    ending, no Prism that is still starting a game, and a game whose end is not accounted for yet counts as alive.
57. **4.1 takes two retries in the same session.** The launch ends as today (`setup_crashed`, `setup_closed`,
    `killed`, …). The next start (his `retry`, or the next session) shows `setup_unfinished`; only `retry` on that
    window moves the folder, because he has read there what it does. If the folder is no longer the remembered one by
    then, nothing is moved and the start decides anew.
58. **`setup_unfinished` is no latch and no kept disposition**: each start works it out again from the record and
    the disk.
59. **What "saw it appear" means.** The launch is a setup launch by the supervisor's own word at its authorization.
    A replacement supervisor that adopted that launch goes on looking, and one that accounts for a setup launch that
    ended while no supervisor ran looks once at that accounting (the runtime file names it as setup). After a reboot
    the runtime file is gone, and only a record written before counts. **For the reviewer:** the narrower reading
    counts only what one supervisor process saw itself.
60. **The record ends early on purpose**: when a home is seen ready, when a start finds the home sound (damage that
    comes later is `world_damaged` as ever, also when the helper never reported), and when `retry` has moved the
    folder. `retry` and `forget-hub` otherwise keep it. If another folder takes the name during the same launch, the
    record follows it.
61. **`AresHub-unfinished-<date>`** has HomeSwap's date pattern (local time, milliseconds; `-1`, `-2`, … up to 99
    when taken). It matches neither dated form: never offered by `world_missing`, never taken by `use-home`, never a
    leftover.
62. **A world that is not declared ready (4.4) gets no latch and no window.** The next start opens the home, which
    this world is not, and a latch would block that start with a text about AresHub. One error line per launch and
    world; the state goes from `IN_WORLD` to `STARTING`; the active world stays, so a save there is `wrong_world`. A
    folder that is not there counts like one outside. Any sound world other than the home sets `hub_seen`, with a
    dated name or not.
63. **A world is checked when it becomes the ready one**, never at every heartbeat. That now also checks the home when
    he comes back to it straight from another world, which was skipped before.
64. **"Newest" in 4.3 is the date in the name**, then the suffix; never a file time. At most 16 folders of each kind
    are read (`HOMES_CHECKED`). The text is worked out when the window opens and at each `status`.
65. **The leftovers' size is bounded**: 32 folders and 20,000 files each are measured, beyond that the line says "at
    least". `status` lists at most 64 names.
66. **`desktop-view.bashrc` is unchanged**: `aresos-desktop` is on the message window's PATH (the `/usr/bin` link),
    as `forget-hub` already relies on.
67. **A failed fsync of the worlds folder after the rename is one log line**; the reply says moved, because it is.

Step 6:

68. **The rig's java wrapper sets the gate and the runtime folder, not `inner.sh`** (the brief names `inner.sh`).
    Gradle and its `systemd-run --user` need the session's runtime folder, so the wrapper sets both for the JVM
    alone (`systemd-run --scope --setenv`). The game gets the run's `XDG_RUNTIME_DIR` in every mode, also without
    the gate, so no launch of this rig can dial the session's supervisor.
69. **A block is set by a data pack on the host's `/trigger`,** typed into chat by the rig's virtual keyboard: no
    cheats, so the home stays as the create flow makes it. It is a glass block in the air above the pad (x 1 to 14,
    y 90, z 2 to 5), not one placed by hand; the chunk changes the same way.
70. **Two blocks for each check.** The game writes a changed chunk to its region file within a tick by itself, but
    the same chunk at most once in ten seconds (seen in `close-1-a` and `stop-1-a`, not read in its code). So each
    check sets a first block and then at once the block it is about: only a save brings that one to the disk, and
    the evidence says it was not there before.
71. **"On the disk" is read twice:** offline from the region file (`region.py`), and by the reopened game.
72. **Three of each.** The brief asks for the close alone three times and the path once; the lead's handoff for the
    stop three times. Both run three times, in turn.
73. **`exited` rests on Java's real status, reported the real way:** the rig's wrapper is Java's parent and uses the
    real wrapper's functions for the exit record and the `jvm_exited` report. The real wrapper cannot start the game
    here: it starts only through a supervisor that started Prism.
74. **The supervisor's helper is a stand-in** that reports `AresHub` ready once the rig has read "joined the game"
    in the game's log; the supervisor then checks the real home itself (4.4). The game talks to the rig's own
    restricted helper, as in package 49b.
75. **The home is made by the real game** (a session's first start with no `AresHub`), in the test supervisor's
    worlds folder as a real folder. `mod/run/saves` is a link to that worlds folder, as the instance's
    `minecraft/saves` is in the image; `series.sh` removes the link when it ends.
76. **`series.sh` waits for the laptop's game lock** (taken and let go at once) before each try. While another
    session's game runs, its memory is missing and every try would be refused; exit 75 is still retried after five
    minutes, six times at most.
77. **The rig's settings:** 1280x720 at 60 Hz, distances 8 and 5, heap 1024 MiB, `MemoryHigh` 2560M, the NVIDIA
    holder as package 49b.
78. **The launch's id stays out of the evidence** (`launch <id>` in the stop's phases), with the nonce, the
    environment and every path.

Step 7:

79. **`TimeoutStopSec=85`** (the lead's fix 1; 3.1 says 75). `WantedBy=graphical.target`, as
    `aresos-console-keymap.service`: the guard is ordered after greetd, which belongs to that target, and
    `multi-user.target` would be one more unit ordered after it. `ExecStart=/usr/bin/true` is spelled out. The home's
    mount is named by `RequiresMountsFor=/var/home/ares`, not by a unit name: it is `var-home.mount` on an installed
    laptop and may be `var.mount` or the root in the VM. It also means that unmounting the home stops the guard first.
80. **Armed first is asked twice per start**: in `begin()`, so no Prism opens for a start that would be refused,
    and in `on_jvm_start()` for every JVM (after the "already running" check, so a refused second wrapper changes
    nothing). A guard that goes away while the game runs stops nothing; only the next start is refused.
81. **`activating` is asked again** each 0.1 s inside the same 2 s (a login in the first moment after boot);
    every other word, an error and no answer are "not active" at once.
82. **JUDGMENT-CALL: with no answer the guard looks at the lock first**, and exits 0 at once when it is free. The
    brief's order is ten seconds of asking again, then the lock. That would add ten seconds to every shutdown with
    no supervisor (after a logout, from a console, from the greeter), and the owner asked for no visible lag (board
    #379). A free lock is the same positive evidence before the ten seconds as after them; with the lock held or
    unknown the recovery attempt runs as the brief says. Changing it back is one condition in `guard_command()`.
83. **No runtime folder is "no session"**: exit 0 without asking. The folder goes after the user's last process,
    and the guard is ordered before `user-runtime-dir@1001.service` stops. Without this rule the lock could not even
    be opened there, which would read "unknown" and leave a fallback record at every shutdown from the greeter.
84. **A reply with `recorded: false` is not asked again** (decision 22: that would be a new stop). The fallback
    record is written unless the reply is `confirmed` and the lock is free; it carries the reply's `save`, and a
    `saved` or `nothing` there keeps the next start from latching.
85. **The fallback latch** overrides another latch, as `close_record()` does, and clears a pending backoff restart.
    A record that cannot be read latches too (it exists, so the guard had no answer). If the latch cannot be
    written, the record stays for the next start. A supervisor that adopts the game leaves the record alone.
86. **A launch the fallback names is not made `stopped`.** After a reboot its runtime file is gone, so nothing
    counts it; a replacement supervisor in the same session accounts for it as before this step.
87. **No test asks the laptop's systemd about the guard.** The loop harness always points `SYSTEMCTL` at a
    stand-in (`control/guard`, `control/system`); `test_aresos_desktop.py`'s loops use `systemctl_stand_in()`; the
    fake runners have `guard`.
88. **The stand-in game is one Java file run by the pinned Java itself** (`java GuardianGame.java`), if the
    image's Java has `jdk.compiler`; `guardian-arm` asserts that first and says what to do if not (build the class
    into the overlay). It says only `GUARDIAN_GAME <what> [id=n|mode=…]`.
89. **The wrapper runs in a transient system unit** as ares with no default dependencies, so neither the check
    service's stop nor the shutdown's first transaction ends it; the JVM itself sits in the real game scope under
    `user@1001.service`, where the wrapper puts it.
90. **The stop record reaches the host through the journal**: a check-only unit ordered before the guard reads
    `desktop.json` in its own stop, after the guard's stop ended, and the journal is read offline. The disk image's
    file is not read directly: `offline_journal.py`'s second reader restores journal paths only.
91. **The lead's fix 5, "each fixture answered it"**: boot 2's game never answers by design. Asserted: both were
    asked; boot 1's answered after its 5 s.
92. **Ctrl+Alt+F3 is pressed in boot 2**, where the screen stays black for 30 s, not in boot 1's 5 s beside the
    lid and the peer.
93. **`image-checks.sh` greps the unit's lines** and runs no `systemd-analyze verify`: that container has no
    systemd, and the VM's boot shows whether there is a cycle.
94. **`checks.py` imports `guardian` inside its action**, not at its top: package 18c's control layer and
    `test_control_vm.py` carry `checks.py` with only `channel.py` and `console_keymap.py` beside it, and a top-level
    import broke that test here.

Step 8a:

95. **JUDGMENT-CALL (light; for the lead and `linux-hub`): the laptop home is no app window.** 53c's
    `aresos.laptop-home` window has no owner, so without a rule it would have counted like Prism's own window: the
    screens would never go black while it shows, and `logout` would be refused with "an app is still open
    (aresos.laptop-home)". It is part of the desktop (as `covering()`, `active()` and `unowned_windows()` already
    treat it on main), so `app_windows()` leaves it out: a shutdown with only the laptop home and the world shows
    black, and `logout` goes through. It is inert until 23c starts it, so nothing changes in the image today.
    Changing it back is one name in `app_windows()` and one in its test.
96. **The image rule's reach.** The same two trees as the old grep, and the same names, case-sensitive. "Executes"
    means an `Exec*=` key (any `Exec` key, so also `ExecCondition`, `ExecReload` and `ExecSearchPath`, which is
    stricter than needed). A drop-in "that applies to the guard" is one in a folder systemd reads for it: its own,
    `aresos-.service.d` and `service.d`; one with an `Exec*=` line fails even if it names nothing of ours, because it
    would change what runs at every shutdown. A link is judged by the file it points to.
97. **The tests sit in `test_guardian_vm.py`** (the guard's CI-side parts), not in a module of their own; they run
    the heredoc exactly as the image does (`python3 -I -` with the two folders), as `test_labwc_stage.py` and
    `test_console_keymap.py` run theirs.

## Package 25 report draft

### Done

- The desktop supervisor and wrapper authenticate the game's lifecycle connection, confirm a flush-save for the
  active home and record the outcome before closing Java. Stop, restart, logout and session-end share the same
  deadline. Recovery can identify an unfinished first home and offer a checked, no-overwrite rename.
- The shutdown guard asks the running supervisor to save before systemd tears down the session. The shell reports
  app windows. The cover, labwc rule and lid inhibitor let the shutdown run behind black when the desktop is alone.
  The message window provides `restart`. OS-BASE B1–B3 and the supervisor's help describe these behaviors.
- **New release-image paths** are `/usr/lib/systemd/system/aresos-guardian.service`,
  `/usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf` and the enablement link
  `/etc/systemd/system/graphical.target.wants/aresos-guardian.service`. Existing files changed in place are
  `aresos-desktop`, `aresos-desktop-java`, `aresos-shell` and `aresos-cover` under `/usr/libexec`, plus
  `/usr/share/aresos/desktop-view.bashrc` and `/usr/share/aresos/labwc/rc.xml`. At runtime the supervisor
  adds optional keys to `desktop.json`, can write `~/.local/state/aresos/desktop-guard.json` after a guard
  failure and uses `$XDG_RUNTIME_DIR/aresos/desktop-stopping.json` to keep admission closed during teardown.
- **Step 8b changes only the verification path.** The fixture holds open a dedicated virtio port from startup.
  It writes `ready`, `saving` upon receiving the request, and, on boot 1, `answering` before sending the reply.
  The host checks readiness before the key and accepts the black frame only inside that window. A camera error
  fails the check and the stopped guest's journal is still extracted. The journal must show the fixture's request,
  the matching answer on boot 1, Java's exit, the guard's result and teardown in order. Boot 2 must still show
  the request, silence from the save handler, ignored SIGTERM and a recorded overrun. The image check build now
  invokes both passes on fresh overlays. All fixture and camera code lives under `os/ci`.
- **Step 8c keeps Ctrl+Alt+F3 available during the save.** The guard wants polkit at startup and is ordered
  after both `polkit.service` and the image's enabled `getty@tty3.service`. Reverse stop order keeps VT
  authorization and the login prompt available until the guard returns. A polkit startup failure still allows
  the save guard to arm. The guest checks both units are active before the key. On both boots the host checks
  PID 1's stop starts and successful completions in the powered-off guest's journal. On boot 2 it also requires
  the host's keypress and a guest sample of tty3 while the guard is deactivating, the supervisor is stopping and
  its black window is present. The change adds no release-image path or owner-facing text.

### Verified

**Run 44594035922, attempt 2, on `bb7bc420`.** Times below are seconds after the power key. Journal and probe
times use the guest's monotonic clock. Frame, key injection and elapsed power-off times are host measurements.

| Observation | Boot 1, five-second save | Boot 2, hung game |
| --- | ---: | ---: |
| Guard stop began | 0.043 | 0.043 |
| Fixture received save | 0.557 | 0.561 |
| Black frame captured | 0.63 | 0.63 |
| Fixture answered save | 5.561 | No answer |
| Guard stop ended (duration) | 6.097 (6.054) | 60.558 (60.515) |
| Session scope / greetd / user manager began stopping | 6.103 / 6.105 / 6.319 | 60.561 / 60.564 / 60.837 |
| Probe first saw labwc gone | 6.332 | 60.834 |
| Java exited | 5.889 (143) | 75.912 (137) |
| `var.mount` began stopping | No journal entry | No journal entry |
| Guest powered off | 7.4 | 76.8 |

- **Boot 1 passed the step 8b save check.** The fixture answered request 1 and the record read after the guard
  said `saved`, `exited`, status 143, with no fallback or latch. The silent peer was dropped. The lid closed
  during the save and the VM stayed awake. The probe reported `lid_block_held=false` and logind listed no AresOS
  inhibitor. Both boots passed the ordinary pre-shutdown Ctrl+Alt+F3 check (`recovery-result.json`, tty3 active,
  agetty on `/dev/tty3`, login PAM checked). Boot 1 sends no Ctrl+Alt+F3 during the black save.
- **Boot 2 lost the recovery console during shutdown.** In `vm-pass-2/offline-boot.txt` lines 4629–4636,
  logind received `Seat.SwitchTo` and polkit authorized `org.freedesktop.login1.chvt` before shutdown.
  After the power key, PID 1 stopped tty3's getty at +0.445 s and polkit at +0.554 s (lines 5954–5972 and
  5995–6015). The fixture received the save at line 6022. The host recorded a black frame and a Ctrl+Alt+F3 at
  about +0.65 s in `guardian-watch.json`. Lines 6026–6038 show that same switch reaching logind. D-Bus could
  not reactivate polkit during teardown and logind returned `Permission denied` at +0.834 s. Logind itself
  began stopping at +75.949 s (line 6641). The probe read tty1 50 times and tty63 15 times after the power
  key, with zero tty3 samples. The black and tty3-labelled PNGs have identical SHA-256 hashes.
- **The hung-game deadline and record held.** The fixture ignored SIGTERM at +30.545 s. Java was alive when
  the guard ended and exited 15.075 s after the user manager began stopping. The persistent record said
  `save=timeout` (unsaved) and `close=overrun`. The guest powered itself off inside the 120 s bound.
- Replaying the saved journals, camera cues and host measurements under `env -i` with `python3 -B` reproduced
  `GUARDIAN_VM_PASSED (save)` and the missing-console failure using the checker from `bb7bc420`. The step 8c
  checker rejected both original journals with `polkit.service began to stop before the guard's stop ended`.
  Boot 1 also lost getty and polkit early, at +0.451 and +0.547 s. The replays wrote to worktree scratch.

**Step 8c ordering check.** Before editing the shipped unit, staged the proposed unit in worktree scratch.
An initial verify using the laptop's unit search path found no cycle but exited 1 because the laptop lacked
`/usr/libexec/aresos-desktop`. A private root contained the vendor units, repo units, the guard and getty
enablement links, and the real repo stop executable. Ran the following with systemd 259.9 on the candidate,
then again on the shipped unit with the image's greetd alias and console-keymap enablement link.

```sh
SYSTEMD_LOG_LEVEL=debug systemd-analyze --system --man=no --generators=no --root="$PWD/.work/8c/root" \
    verify graphical.target aresos-guardian.service polkit.service getty@tty3.service systemd-poweroff.service poweroff.target
```

Both private-root runs exited 0. Neither log contained an ordering cycle. Both showed the guard's `After`
edges to polkit and getty, and each service's default `Conflicts=shutdown.target` and `Before=shutdown.target`.
`systemd-poweroff.service` follows `shutdown.target`, and `poweroff.target` follows `systemd-poweroff.service`.
Thus the guard finishes first, both services stop, and only then can systemd power off.

**Step 8c local tests.** Ran each module in its own process, one at a time. `test_path` was `/usr/bin:/bin`,
with the local JDK 25's `bin` prepended for the guardian loop.

```sh
env -i HOME="$PWD/.work/8c/home" TMPDIR="$PWD/.work/8c/tmp" PATH="$test_path" \
    python3 -B -m unittest discover -s os/tests -p "$module.py"
```

| Module | Tests | Seconds | Result |
| --- | ---: | ---: | --- |
| `test_aresos_desktop` | 189 | 206.711 | OK (1 skipped, real user-manager scope) |
| `test_aresos_guardian` | 106 | 5.602 | OK |
| `test_aresos_guardian_loop` | 26 | 59.464 | OK, including both Java fixtures |
| `test_guardian_vm` | 19 | 0.499 | OK |
| `test_console_keymap` | 21 | 0.018 | OK |
| `test_checkout_sources` | 8 | 0.876 | OK |

Before the fix, the first run of the updated `test_guardian_vm` reported 17 failures counting subtests. The old
checker accepted early service teardown and tty3 samples at or after the end of the guard. The final tests
also reject missing stop completions and a tty3 sample without the black window. `bash -n os/ci/image-checks.sh`,
in-memory compilation of both changed VM Python files and `git diff --check` passed.
`find .work -type f -size +500000000c -print` printed nothing.

**Run 44587459044 at `5bdcd2fd` showed (b), a failure in the host's observation. Whether the guard saved that
particular boot is undecidable from the retained artifact.**

- The image checks passed. `guardian-arm-result.json` records the guard active and enabled, its 85-second timeout,
  the four required ordering dependencies, `session-1.scope` ordered before the guard, both scope limits at 15 s,
  and an accepted fixture hello with an empty app-window list. `prepare-poweroff-result.json` records return code
  0 and a persistent system journal for that boot. All pixels in the 1280×800 pre-key `last-vm-frame.png`
  exceeded the host's brightness threshold of 8.
- `vm-pass-1/serial.log` lines 1394–1396 contain `ARESOS_JOURNAL_READY` (151.829197 s), `ARESOS_POWER_KEY_ARMED`
  (151.831350 s) and the follower's last journal record, a sync request. Line 1397 switches mid-terminal escape
  to a status line for the **recorder** stopping. Lines 1399–1401 report the session and user manager stopping.
  There is no forwarded fixture request, answer or guard result. Line 1559 is `reboot: Power down`.
  `qmp-events.json` records a guest-requested shutdown 7.152308 s after POWERDOWN. Elapsed time alone cannot
  establish a five-second save.
- In that revision `os/ci/vm.py` took the serial byte offset **before** the power key (lines 152–155).
  `guardian_host.watch` raised on QEMU exit when it could not find the substring in those serial bytes
  (lines 45–49). That unwound `vm.py` at line 157, before the offline read at line 166. The artifact contains
  neither the persistent journal export nor `guardian.json`. A missing line on that console could produce the
  reported assertion even when the fixture answered. The guard's own journal, fixture events and durable stop
  record from the next boot decide the save question.
- Replayed `git show 5bdcd2fd:os/ci/guardian_host.py` under `env -i` with `python3 -B`, the archived
  `serial.log` and a stopped QEMU stand-in. Starting at byte 0 and at byte 128727 (the arming token) both
  raised `the VM powered off before the game was asked to save`. The entire file contains zero
  `GUARDIAN_GAME save_asked` markers.
- The OOM was the earlier pressure check. Serial lines 1374–1375 identify PID 3088, `python3`, in
  `aresos-ci-pressure.scope`. `shortcut-result.json` records that same PID, 5312 MiB allocated and exit 137.
  The subsequent arm cleared the latch and found the live fixture connected. The OOM victim was the pressure source.
- Earlier hosted `checks_only` run 44458416374 succeeded on `bda87419` (regressions and ways-back model).
  Step 6's headless real-game rig placed blocks, read their region file and reopened the home. Three SIGTERM-only
  closes exited 143 in 0.67–0.74 s. In three supervisor stops the save took 0.08–0.17 s and the stop finished
  in 0.75–0.89 s. All 15 blocks checked on reopening were present. The rig commands and per-launch receipts are
  recorded above under step 6.

Step 8b ran one test module per process from the worktree with this command. `test_path` was `/usr/bin:/bin` or
the local JDK 25's `bin` prepended to it. Every supervisor in the loop suite used its own runtime and stand-ins.

```sh
env -i HOME="$PWD/.work/8b/home" TMPDIR="$PWD/.work/8b/tmp" PATH="$test_path" \
    python3 -B -m unittest discover -s os/tests -p "$module.py"
```

| Module | Result |
| --- | --- |
| `test_aresos_desktop` | 189 tests in 207.301 s and 203.775 s, OK both times (1 skipped, the real user-manager scope test) |
| `test_aresos_guardian` | 106 tests in 5.536 s, OK |
| `test_aresos_guardian_loop` | 26 tests in 59.410 s and 60.580 s, OK both times, including both Java fixtures with the guard's shutdown command |
| `test_guardian_vm` | 17 tests in 0.470 s and 0.489 s, OK both times, including silent serial, missing cue, late frame, wrong answer ID and wiring for both check-build passes |
| `test_journal_ready` | 6 tests in 0.001 s, OK |
| `test_console_keymap` | 21 tests in 0.019 s, OK |
| `test_checkout_sources` | 8 tests in 0.856 s, OK |

The loop exercised the real socket, wrapper and stand-in JVM. The saving JVM answered and closed with 143.
The hanging JVM received the request, ignored SIGTERM and was still alive at `overrun`. The host tests use
synthetic journals. `bash -n os/ci/check-build.sh` and `git diff --check` exited 0. Python compiled
`vm.py`, `guardian_host.py` and the guest's `guardian.py` in memory. The binding refresh command below printed
`pending: 10 bound files differ from the active bindings, 0 removed`. The worktree has no file over 500 MB in
`.work/`.

```sh
python3 -B reviews/27-first-update-release/rebind.py pending '25 step 8b: time VM screenshots from the fixture port and retain the offline journal after a missed frame'
```

### Not verified

The corrected image still needs both hosted boots. Run 44594035922 supplied black frames for both, but its
boot 2 never selected tty3. The next check build must show tty3 during the hung stop and both services stopping
after the guard on both boots. Boot 1's lid-inhibitor observation also remains to be rechecked.
Human checks remain for lid-close on the physical laptop,
scaled or mixed outputs, the laptop home and search at shutdown, and restoring a dated home from the real message
window. The real-game measurements cover a small flat development world.

### JUDGMENT-CALL

- **Decision 82.** When the supervisor cannot answer, the guard immediately tries to take the desktop lock. A
  free lock lets a shutdown from the greeter finish without the ten-second recovery wait. A held or unreadable
  lock still gets the retry and fallback. Waiting before checking would add ten seconds even with no writer.
  Moving the condition in `guard_command()` would change this choice.
- **Decision 95 (step 8a).** Both `covering()` and `app_windows()` exclude the laptop home. It is a desktop
  surface. Counting it as an app would keep the screens lit and refuse logout even with all apps closed.
  Changing this needs the helper's window filters and their tests. Step 8b adds no owner-facing behavior.
- Step 8c adds no new JUDGMENT-CALL. It restores the existing tty3 recovery behavior and keeps the guard's
  85 s limit, the supervisor's deadline and the 120 s VM power-off bound.

### PLAN-GAP

The check-build entry point selected pass 1 only, though acceptance requires both shutdown scenarios before merge.
It now runs pass 2 before printing `CHECK_BUILD_VM_PASSED`. For the real-game check, JVM logging ended at
SIGTERM. Step 6 verified the closing save by reading the newly written block and player data from disk and
reopening the world.

### Known limits

- A power cut, a forced power-off or a shutdown that skips unit stops can bypass the save. A confirmed flush
  covers work through the request. Later ticks and Minecraft's own closing save have no separate acknowledgement.
- Loading, switching home or sitting at the title screen can use the 30-second save allowance and end
  `unsaved`. Unexpected loss of labwc can take the display away before a save finishes. The supervisor records
  the result and leaves a hung JVM to systemd during teardown. If the state disk cannot be written, even the
  fallback can fail.
- A shutdown with apps open keeps them visible and lets normal teardown close them. A terminal counts as an app,
  so a logout typed there is refused. An unknown window count also keeps the screens visible and prevents
  logout. The world can still play sound behind black until Java exits.
- Before Prism hands off Java, a plain stop can find no writer and a later launch can still start. Shutdown
  blocks that hand-off. R28 ignores a newer fallback record after rollback. A supervisor that understands the
  record applies it on a later start.
- An unfinished first home is recognized by device and inode. Inode reuse could cause a different damaged
  folder to be moved aside on retry. Filesystems without no-overwrite rename support refuse the move.
  A damaged or missing world reported ready is logged and stays unready. A hub launch can show slow-start
  after 120 s. Dated-home lookup checks the 16 newest candidates of each kind.
- The image check inspects Exec directives in the two shipped system-unit trees. An indirect launch hidden in a
  differently named script is outside that check.

### Open questions

Does the final check build establish both shutdown orders, including tty3 during the hung stop, and the recorded
outcomes inside their time limits? The release requires that result.

### Exact new texts for the owner

The following are the package's window and command texts. Angle brackets mark substituted values. Recovery
windows begin with `AresOS: recovery` and a blank line. Step 8b adds only test diagnostics.

`aresos-desktop save` prints one of the following lines.

- `Saved: AresHub is on the disk.`
- `Not saved: no home is open in Minecraft right now (it is loading, switching homes or closing).`
- `Not saved: the world open in Minecraft is not an AresOS home.`
- `Not saved: Minecraft is closing the world right now.`
- `Not saved: Minecraft could not write AresHub to the disk; its log says why.`
- `Not saved: Minecraft saved <name>, which is not the home AresHub.`
- `Not saved: the home changed from <a> to <b> while it was saved.`
- `Not saved: Minecraft did not answer in time.`
- `Not saved: the connection to Minecraft closed before it answered.`
- `Not saved: Minecraft is not running, or has not connected to AresOS yet.`
- `Not saved: Minecraft's answer could not be used (<why>).`
- `Not saved: the AresOS desktop supervisor did not answer (<error>).`

The invalid-answer detail is `the answer names no world` or `the answer is neither a save nor a known refusal`.

Step 2, the windows (`<why>` is one of the `Not saved: …` lines above, or one of the lines below):

- `save_failed`: `Minecraft was not stopped, because your home could not be confirmed as saved first.` / `<why>` /
  `Minecraft keeps running and nothing is lost.` / `Type  retry  and press Enter to close this window.`
- `stuck`: `Minecraft was asked to close, but it is still running after 60 seconds.` / `AresOS stopped waiting. It
  never ends Minecraft by force and starts no second one meanwhile.` / `Once Minecraft has closed, type  retry  and
  press enter to try again.`
- `unsaved`: `The last time Minecraft was stopped, AresOS could not confirm that your home was saved first.` /
  `<why>` / `What you built in the last minutes before that stop may be missing.` / `Your home opens as it is on the
  disk.` / `Type  retry  and press Enter to open it.`
- More `<why>` lines: `The stop could not be recorded on the disk.`, `Not saved: Minecraft could not be asked in
  time.`, `Not saved: the stop ran out of time before the home was saved.`, `Not saved: a Minecraft that AresOS
  cannot see holds the desktop lock.`, `Minecraft ended before your home was confirmed as saved.`, `The stop ran
  out of its 60 seconds before Minecraft was asked to close.`

Step 2, the `stop` command and `retry`:

- `Stopped: the home was saved first; Minecraft closed.` (or `there was nothing to save`)
- `Nothing to stop: Minecraft is not running.`
- `Not stopped: Minecraft keeps running. <why>`
- `Not a confirmed stop: <the home was saved first | there was nothing to save | the home could not be confirmed as
  saved first>; <Minecraft closed | Minecraft ended, but not by closing in its own orderly way | Minecraft did not
  close within 60 seconds, so AresOS stopped waiting (it never ends Minecraft by force)>. <why>`, with ` The stop
  could not be recorded on the disk.` after it when it could not.
- `Not stopped: the AresOS desktop supervisor did not answer (<error>).`
- `retry`: `AresOS is stopping Minecraft right now. Type retry again when that is done.` and `AresOS is shutting
  down or logging out, so nothing is started any more.`
- The wrapper's refusal: `AresOS is stopping, so Minecraft is not started now.` `status`: `AresOS is stopping
  Minecraft.`

Step 3, the windows (the body is `save_failed`'s; `<why>` as above):

- `save_failed_restart`: `Minecraft was not restarted, because your home could not be confirmed as saved first.` …
- `save_failed_logout`: `AresOS did not log out, because your home could not be confirmed as saved first.` …
- `helper`, last line: `Type  restart  and press Enter to save your home and start both again.`
- The message window has a second word, `restart`.

Step 3, `restart` (`<stop>` is one of step 2's `Stopped: …`, `Nothing to stop: …` or `Not a confirmed stop: …` lines):

- `<stop> Minecraft is starting again.`
- `<stop> Minecraft is already starting.`
- `<stop> Minecraft was not started again; the AresOS window says why.`
- `<stop> Minecraft is not started again.`
- `Not restarted: Minecraft keeps running. <why>`
- `Not restarted: the AresOS desktop supervisor did not answer (<error>).`

Step 3, `logout`:

- `Logged out: the home was saved first; Minecraft closed.` (or `there was nothing to save`)
- `Logged out: Minecraft was not running.`
- `Not logged out: an app is still open (Mail). Close it first; nothing was stopped.`
- `Not logged out: 2 apps are still open (Mail, Files). Close them first; nothing was stopped.`
- `Not logged out: AresOS cannot tell whether an app is still open (its app helper has not reported). Nothing was
  stopped.`
- `Not logged out: this AresOS desktop watches no session of its own that it could end. Nothing was stopped.`
- `Not logged out: Minecraft keeps running. <why>`
- `<stop> Not logged out: an app is open now (Mail).`
- `<stop> Not logged out: 2 apps are open now (Mail, Files).`
- `<stop> Not logged out: AresOS can no longer tell whether an app is open.`
- `<stop> Not logged out: the session could not be asked to end.`
- `<stop> Not logged out: the session did not end within the stop's 60 seconds.`
- `<stop> Not logged out.` (the stop was not confirmed, or Minecraft did not close in its own way)
- `Not logged out: the AresOS desktop supervisor did not answer (<error>).`
- A reason on `restart` or `logout`: `only a stop has a reason: shutdown, or none`

Step 4: `hide-cover` answers `The black screen is gone.` (nobody sees it: a key binding runs it). `systemd-inhibit
--list` shows the lid block as `AresOS`, `AresOS is saving your home before Minecraft stops`. No window text changed.

Step 5, the windows:

- `setup_unfinished` (state `SETUP`, no latch):
  `AresOS: your first home was not finished` / (blank) / `Minecraft stopped while it was making your home, so this
  folder is only half made:` / `  ~/.local/share/aresos/worlds/AresHub` / `  (<what the check found>)` / (blank) /
  `Type  retry  and press Enter: AresOS moves that folder aside, as` / `AresHub-unfinished-<date> beside it (nothing
  is deleted), and makes your home again.`
- `world_missing`, between its first two lines and its last two, when a folder was found:
  `In the same folder AresOS found (it moves nothing by itself):` / (blank) /
  `The newest home under a dated name that passes its checks, most likely the home you had:` / `  <AresHub-date>` /
  `To make it your home again (the folder is renamed, nothing else changes):` /
  `  aresos-desktop use-home <AresHub-date>` / `then  retry` / (blank) /
  `A new home that was still being made, and is complete:` / `  <AresHub-new-date>` /
  `To make that one your home instead:` (alone: `To make it your home:`) /
  `  aresos-desktop use-home <AresHub-new-date>` / `then  retry`.
  Its next line then reads `Or put the folder back (from a backup), then type  retry  and press enter to try again.`

Step 5, `use-home` (each refusal begins `Not moved: `):

- `<folder> is your home AresHub now (the folder was renamed; nothing was deleted). Type retry.`
- `use-home takes the name of a dated home in ~/.local/share/aresos/worlds: AresHub-<date> or AresHub-new-<date>.`
- `AresHub exists. use-home only fills the place of a missing home and never replaces one.`
- `There is no folder <folder> in ~/.local/share/aresos/worlds.`
- `<folder> is not a folder.`
- `<folder> does not pass AresOS's checks of a home (<what the check found>).`
- `Minecraft is running. Stop it first (aresos-desktop stop), then try again.`
- `Minecraft is starting right now. Try again once it runs or has closed.`
- `AresOS is stopping Minecraft right now. Try again when that is done.`
- `AresOS is shutting down or logging out.`
- `A Minecraft that AresOS cannot see holds the desktop lock. Close it first.`
- `AresOS cannot tell whether Minecraft is running (the desktop lock: <error>).`
- `<folder> changed while it was checked.` / `AresHub exists already.` / `The folder could not be moved (<error>).`
- `the AresOS desktop supervisor did not answer (<error>).`
- The command's own usage error: `use-home takes one folder name, and no other command takes one`.

Step 5, `retry` on `setup_unfinished`: `Moved the unfinished home to AresHub-unfinished-<date> (nothing was
deleted). State: SETUP`, or `The unfinished home was not moved: <one of the refusals above> Nothing is changed. Type
retry to try again.` The move can also give `AresHub is no longer the folder that was left unfinished.`,
`AresHub no longer reads as unfinished.`, `A home is one folder inside the worlds folder.` or
`Every name it could get is taken.` The wrapper's refusal there is `Your first home was not finished; the AresOS
window says what to do.`

Step 7:

- `guard` (state `RECOVERY`, no latch): `Minecraft is not started yet. The part of AresOS that saves your home when
  the laptop shuts down` / `is not running (aresos-guardian.service: <systemd's word>), and without it a shutdown
  could cut a save short.` / (blank) / `Type  retry  and press Enter to try again.` / `If this window comes back,
  restart the laptop.`
- The wrapper's refusal there: `AresOS could not save your home at a shutdown right now, so Minecraft is not
  started; the AresOS window says more.`
- `unsaved`, three more `<why>` lines: `The AresOS desktop supervisor did not answer when the laptop shut down, and
  Minecraft was still running.` / `The AresOS desktop supervisor did not answer when the laptop shut down, and
  AresOS could not tell whether Minecraft was still running.` / (existing)
  `The stop could not be recorded on the disk.`
- The guard's command (the journal only; nobody sees it): `Nothing to stop: no AresOS session is running.`,
  `Nothing to stop: the AresOS desktop supervisor did not answer (<error>), and no Minecraft holds the desktop
  lock.`, `Not a confirmed stop: the AresOS desktop supervisor did not answer (<error>), and Minecraft is still
  running.` (or `nobody can tell whether Minecraft is still running (<why>).`), followed by `The next start of
  AresOS says so.` or `That could not be recorded either (<error>).`

## Verification notes from steps 1–8a

- **Step 8a image rule.** The next check build, 44587459044, passed the rule and the subsequent image checks.
  Boot 1 armed the guard. The shutdown evidence ends as described in the report draft.
- **Known limits of the image rule** (low harm: it is a tripwire for a mistake in the repo, not a guard against an
  attacker with root): it reads `/usr/lib/systemd/system` and `/etc/systemd/system` only, as the old grep did, not
  `/run/systemd`, `/usr/local/lib/systemd/system`, `/etc/systemd/system.control`, user units or generators; a key
  spelled other than `Exec…` (systemd ignores those anyway) and a desktop started through a script of another name
  are not seen.
- **The merge, not run together yet:** the black screen with 53c's laptop home on a second output (the home is not
  started in the image before 23c), and 53d's search over the world open at the moment a stop goes black (the black
  window takes the focus like any new window, so the world hears `shell_focus` `background`; what the search does
  then is 53d's, unchanged). Both helper suites pass on the merged file; nothing ran them in one compositor.

- **Step 7, for step 8: what never ran before the check build.** The unit under a real systemd (its order, a
  cycle, `User=ares`, `RequiresMountsFor`); `systemctl is-active` asked from the session; the real
  `systemd-inhibit`; the image's Java running a single file; the uinput lid; the black window over the startup
  cover in a real labwc; the journal carrying the game's lines. Each has its own assertion with a message; read
  `evidence/vm-pass-N/guardian-arm-result.json` (the guest's facts, or its traceback), `guardian.json` (the times,
  written before the assertions run), `guardian-black.png`, `guardian-tty3.png`, `last-vm-frame.png` and
  `offline-boot.txt`.
- **Where the check build is most likely to stop first**, in the order it would:
  1. `desktop_session` (the existing `shortcut` step) expects `SETUP` at the first start. If the guard is not active
     when the supervisor first asks, it finds `RECOVERY`/`guard` instead: then the unit failed to start
     (`systemctl status aresos-guardian` in the journal: `User=`, the mount) or the order at boot is not what
     decision 81 assumes.
  2. `jdk.compiler` missing in `java-25-openjdk-headless`: build `GuardianGame.class` into the overlay (the
     brief's second way) and start it with `-cp`.
  3. `retry` does not clear `killed` within 240 s (memory pressure after the pressure step).
  4. `windows` never becomes `[]`: something else in the VM's session counts as an app window; the assertion
     prints the names.
  5. The frame before the power key is black, or the frame during the save is not: the startup cover (`retry` shows
     it) should be up before, and `aresos.black` above it during. If black is below the cover, that is a real
     finding about two always-on-top windows, not about the check.
  6. `the game scope's 15 s`: `systemd-run --user --scope --property=TimeoutStopSec=15s` was never run on a real
     user manager here.
  7. Boot 1's order. If a unit "began to stop before the guard's stop ended", `guardian.json` has every time.
  8. The lid: `logind_lid_closed` must be `b true` (the device is made as `os/tests/power-events.py` makes its
     own). The lid block is only reported.
  9. Boot 2's bounds (55 to 85 s for the guard, 10 to 30 s from the user manager's stop to the wrapper's end).
- **The VM step's time.** `Boot QEMU and assert session, policy and recovery` has 20 minutes for both passes. This
  step adds about a minute of `retry` waiting and 15 s to each pass, and boot 2's shutdown takes about 80 s more.
  Its limit is in the workflow, a bound file, which this step did not change.
- **Not proven by the VM as built:** plymouth's shutdown screen (it is ordered after greetd's stop, so after the
  guard); a real lid with a real `HandleLidSwitch` other than `ignore`; a shutdown with an app window open (the
  black screen stays away; not exercised); the fallback record (no supervisor at a shutdown: the loop test stands
  for it); `use-home` in the image (step 5's note).
- **Other rigs and tries.** A supervisor from this branch on a machine without the unit shows `guard` and starts
  nothing: every rig or try that lets a wrapper ask a real supervisor needs a stand-in `SYSTEMCTL` that answers
  `active` (as the loop harness has). Step 6's rig adopts its game and never asks; `test_rig.py` was not run again.
  **For the lead:** `linux-hub`'s tries (`hub-try`, `~/AresOS-try`) meet this once 25 is on main.
- **A rollback to R28** leaves `desktop-guard.json` unread (R28 knows no such file); R29's next start applies it.
- **The loop harness, step 7:** `start(wait=False)` returns without waiting for the home; `control/guard` and
  `control/system` hold the stand-in systemd's words; `fixture(mode, **numbers)` runs the Java stand-in in place
  of the Python one (needs a Java 16 or newer on `PATH`, or the pinned one).
- **Step 6, what the game does by itself.** A changed chunk is in its region file within a tick, but the same chunk
  at most once in ten seconds. So up to ten seconds of building in a chunk are in memory only; the flush save and
  the closing save are what bring them to the disk. That is what the stop routine's save is for, and it works.
- **Step 6, the log has no server-stop lines.** The brief asks for them. The development client's log ends at
  SIGTERM (its logging stops with the JVM's shutdown): no "Stopping server", no "Saving players". The `All chunks
  are saved` lines in the `stop-*` files come from the mod's flush save, before the signal. That the server stopped
  and saved is on the disk instead: the block, `level.dat` and the player's data written after SIGTERM, status 143.
  Whether Prism's game logs the lines is for the VM to show, if it matters.
- **Step 6, the times** are of a small flat home (the rig's 40 test apps, distances 8 and 5) on the laptop: SIGTERM
  to Java's exit 0.67 to 0.74 s; `save` as a command 0.19 to 0.25 s; in a `stop` the save was confirmed 0.08 to
  0.17 s after its start, SIGTERM went out in the same moment, and the stop ended after 0.75 to 0.89 s (0.87 to
  1.03 s as a command). `STOP_BUDGET` and the other numbers are unchanged. A big or old world, and the Nether home, were not timed.
- **Step 6, what the rig is not.** Loom's development client started by Gradle with Java 25 from the home folder:
  not Prism's instance, its production jar or its log settings; the same mod sources and the same Minecraft. The
  real wrapper did not start the game. No black screen, no real helper and no lost focus (the VM's boot 1). "On the
  disk" means read back from the region file: nothing here shows an fsync or a power cut. Not tried: SIGTERM while
  the world loads, while the game is paused, or with a save in flight; a game that ignores SIGTERM (the loop test
  and the VM's boot 2 stand for that).
- **For step 7.** 2.5 stands: build 3.1 on it. The VM's stand-in JVM should end with 143 after SIGTERM, as the real
  game does. To run the check again: `reviews/25-guardian/rig/series.sh <tag> <first block>` (the home in
  `.work/pkg25` has blocks 1 to 18 set: take 19, or remove `.work/pkg25` for a new home); one launch is
  `reviews/25-guardian/rig/run.sh <name> MODE=…` (`check.sh`'s head says how). `.work/pkg25` (ignored, a few
  MB; nothing in `.work/` is over 500 MB) holds the home and each run's raw logs. The report lists the rig under Verified; nothing of it ships.
- **Step 5, where a world folder can move.** `rename_noreplace()` has one caller, `move_home()`, and that has two
  (`move_unfinished()`, `use_home()`); `UseHomeTest.test_one_function_moves_a_world_folder_and_nothing_deletes_one`
  reads the file's syntax tree for that and lists every other rename, replace, unlink and rmtree in the file (the
  instance's staging copy, `reset-instance`, the supervisor's own small files). A new one fails that test.
- **`renameat2` is glibc's own function, called through ctypes.** A C library without it, or a filesystem that does
  not know `RENAME_NOREPLACE` (it answers `EINVAL`), means the move is refused; there is no fallback to `os.rename`.
  Run here on tmpfs and on the home's btrfs. Not run in the image: step 7's VM could try one `use-home`.
- **Device and inode are all that 4.1 remembers.** If he deletes the half-made folder and another damaged folder gets
  its name and, by reuse, its inode number while no home was ever ready, `retry` moves that one aside (never
  deleted). A known limit for the report.
- **A damaged or missing world that the mod reports ready shows no window** (decision 62): the game goes on, the
  supervisor's state stays `STARTING`, and a hub launch that was never ready shows `slow_start` after 120 s. A known
  limit for the report.
- **For step 6 (the rig).** With 4.4 a world the helper reports ready is declared ready only if it is a sound home at
  `$HOME/.local/share/aresos/worlds/<name>` of the test supervisor's `HOME`. And 1.3 still wants `world_saved` to
  name the active world: without a helper that is the locked world, `AresHub`. So the rig's world has to be (or be
  linked as a real folder, not a symlink: `check_world` refuses a link) `AresHub` in that worlds folder. Give the
  adoption runtime file `mode: hub`: with `setup` and no home ever ready, the supervisor would remember the rig's
  world as a first home (harmless while it is sound, but not what the rig shows).
- **For step 7 (the VM).** `status` has a new key, `leftovers` (folder names): add it to the evidence allowlist only
  if a check needs it. `desktop.json` has a new optional key, `first_home`, with a device and an inode number and no
  path. The disposable world the fixture seeds must be a sound home named `AresHub` (the lead's fix 5), or the stop
  ends `wrong_world`.
- **`take_desktop_lock(paths)`** is there for step 7's guard command (the lead's fix 1: the guard takes the lock
  itself, and an error is "unknown"): it returns a descriptor, `None` while the lock is held, and raises `OSError`
  when nobody can tell.
- **Not verified:** the mod's side of a first home that dies (which files exist when); the tests stand for it with a
  home whose completion record, level or marker is missing. And the real `use-home` typed in the real message
  window.

- **The real `systemd-inhibit` was never run** (the machine rules). Its command line runs first in the VM (step 7):
  the check should see AresOS's block in `systemd-inhibit --list` during the save, and no `the lid block ended by
  itself` in the journal. It needs polkit's `org.freedesktop.login1.inhibit-handle-lid-switch` and
  `inhibit-block-sleep` for the session's user (the defaults allow a local session).
- **`logind.conf.d/90-aresos.conf` already ignores the lid** (`HandleLidSwitch=ignore`), so the block is a second line
  of defence today; it matters once that policy changes.
- **The black screen takes the keyboard focus from the game**, as any new window does. The helper never calls it
  covering, so the mod does not pause the world for it; whether Minecraft's own pause on lost focus changes the save's
  answer is for the VM's boot 1 to show ("the screen is black; the save was answered"). Step 6's rig has no black
  screen.
- **Not verified together:** the real supervisor, the real helper and the real cover in one compositor. Verified in
  parts: the real cover with the helper's real window reader in a private headless labwc with two outputs
  (`test_aresos_cover.py`, `BlackTest`); the supervisor with stand-ins for the cover and `systemd-inhibit`
  (`test_aresos_guardian_loop.py`); the helper's report read by the supervisor's `on_windows()`
  (`test_aresos_shell_guardian.py`). Real hardware with two screens or a scaled screen: not tried.
- **Behind the black screen the game's world keeps its sounds and music until the game exits**, a few seconds at a
  shutdown. The mod silences the home only on `shell_covered`, and the black window is deliberately not "covering"
  (that would arm the uncover rule). `linux-hub` agrees it is low harm (the lead, 2026-11-19). A possible follow-up
  is a quiet-only signal for the black window. A known limit for the report.
- **A `logout` typed into a terminal is refused**: that terminal is an app window (3.4's definition). A session with
  no helper (a latch at its start) never goes black and cannot `logout`. Known limits for the report.
- **Where step 4's code hooks in**, for whoever changes the stop routine: `request_stop()` (start), `make_final()`,
  `finish_stop()` (the one place that releases the lid block and decides the black screen after a stop),
  `resume_stop()` (lid block only), `enter()` (never a window or the home behind black).
- **The loop harness, step 4:** the stand-ins `cover` and `inhibit` note `start <pid> <arguments>` and `end <pid>` in
  `control/covers` and `control/inhibits` (`self.noted()`, `self.up()`); the harness always points
  `desktop.SYSTEMD_INHIBIT` at the stand-in, so no loop test can take a real inhibitor. `StopRunner` (state machine)
  has `blacks`, `black_up`, `black_stops`, `black_error`, the same four for `lid_`, and `behind_black`.
- **For step 2: where a save's callback runs.** `done(SaveResult)` can run inside `conclude()` (a launch's end closes
  the channel first, before the accounting is saved), inside `tick()` (a deadline), or before `request_save()`
  returns (`no_channel`). It must only note the result. Start, stop or account for a launch from `pending()`.
- **For step 2: the mod's reconnect backoff** (0.5 s doubling to 10 s; it starts over only after a connection that
  held 10 s). After a supervisor restart the adopted game's hello can be up to 10 s away, so `no_channel` is normal
  for a replacement supervisor's first seconds. The wrapper reports `jvm_started` long before the mod loads, so in
  the real game the first hello is normally accepted; the stand-in game connects earlier and shows the refused-then-
  accepted path.
- **Not verified on a real session: that the real labwc passes `labwc_problem()`** (labwc exports `LABWC_PID` to its
  autostart, and its own environment has `XDG_RUNTIME_DIR`). If it does not, the log says why and `logout` is
  refused; nothing else changes. Step 7's VM check should read `status` and expect `labwc: true`.
- **A session with no helper cannot log out through `logout`** (a latch at the session's start means no launch and
  no helper, so the count stays unknown). A known limit for the report.
- **Signals in tests.** `watch_signals()` runs only in `supervise()` (the main thread); the in-thread loops of
  `test_aresos_desktop.py` still stop through `loop.stopping`. A test that starts a supervisor process and sends it
  SIGTERM now gets the stop routine: the loop harness's cleanup first makes the stand-in game save and close.
- **The loop harness, step 3:** `start(keeper=True)` runs the keeper (`desktop.SELF` is `bin/self`);
  `start(labwc_runtime=<folder>)` gives the stand-in labwc another runtime folder; the file `control/windows` holds
  the stand-in helper's `windows` event (`self.windows('Mail')` writes it and waits) and `control/quiet` silences
  the helper; set `STOP_EXIT_RESERVE` together with a small `STOP_BUDGET`; the cleanup ends every process whose own
  environment names the test's runtime folder.
- **What shows after a stop is decided only in `finish_stop()` and `settle_stopped()`.** While a stop runs, or the
  state is `STOPPING`, or a sticky window shows, `held()` is true and `ready()`, the start timeout and a helper
  failure change no state.
- **"Due now" is never `self.clock()`.** `tick()` reads the clock first; a later reading is not due, and the loop
  then spins until the deadline. The loop test found exactly that; `stop_due()` returns `stop.started` for "at
  once", and one test runs a stop on a clock that moves between two readings.
- **A stop while Prism has not handed the game over** finds nothing running and ends at once. After a plain stop
  Prism may still start the game a moment later (admitted like a start by hand); after a shutdown the block
  refuses it. A known limit for the report.
- **An unwritable state folder**: the record's writes are caught (`record_stop()`); `settle()` and `latch()` after
  the stop still raise as before, and `finish_stop()` logs that.
- **The stop's times with the stand-in game were not measured** beyond "the command answers in well under a second";
  the report's numbers come from the real game (step 6) and the VM.
- **The loop harness, more:** the file `control/ignore-term` makes the stand-in game ignore SIGTERM;
  `start(SYSTEMCTL=<a script that prints stopping>)` gives systemd's word; `self.games()` counts every game ever
  started; `STOP_BUDGET` and `STOP_SAVE_WAIT` can be set through `start()`.
- **`SAVE_WAIT` is read when `request_save()` is called**, so a test can change it; `request()`'s default timeout is
  bound when the function is defined.
- **The loop test's harness** (`test_aresos_guardian_loop.py`): `start(**numbers)` sets module numbers such as
  `SAVE_WAIT` or `BACKOFF` in the supervisor's process; the file `control/save-mode` says what the stand-in game
  answers (`saved`, `renamed`, `hang`, or a refusal); the game ends with 143 on SIGTERM. The stand-in `labwc` is a
  process of that name with the test's runtime folder in its environment, as 3.2 will require. The harness calls
  `supervise()` directly: a test of the keeper has to point `desktop.SELF` at the harness.
- **Running the tests.** Run them under `env -i` as above, so nothing of the session reaches a test. `-B` keeps
  Python from writing `__pycache__` into `os/config/usr/libexec`.
- **Not verified here:** the real mod against this end (step 6), and anything in the VM (step 7). OS-BASE B1 still
  says the supervisor's side waits for package 25 (section 5 is step 8).
