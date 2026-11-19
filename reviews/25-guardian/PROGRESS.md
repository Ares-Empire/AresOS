# Package 25, the guardian: progress

Updated after **step 3** (2026-11-19). Builder: a Claude agent on Fable 5.2, one fresh agent per step.
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

## Left, in order

4. 3.4: the black screen, the helper's `windows` event, the lid block.
5. Section 4.
6. The real game.
7. 3.1 and the VM checks.
8. The check build's findings, section 5 (docs), the report, the pull request.

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

**New texts** (the `save` command prints them; for the report's list):

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
- `<stop> Not logged out: AresOS can no longer tell whether an app is open.`
- `<stop> Not logged out: the session could not be asked to end.`
- `<stop> Not logged out: the session did not end within the stop's 60 seconds.`
- `<stop> Not logged out.` (the stop was not confirmed, or Minecraft did not close in its own way)
- `Not logged out: the AresOS desktop supervisor did not answer (<error>).`
- A reason on `restart` or `logout`: `only a stop has a reason: shutdown, or none`

## What the code does not show

- **For step 2: where a save's callback runs.** `done(SaveResult)` can run inside `conclude()` (a launch's end closes
  the channel first, before the accounting is saved), inside `tick()` (a deadline), or before `request_save()`
  returns (`no_channel`). It must only note the result. Start, stop or account for a launch from `pending()`.
- **For step 2: the mod's reconnect backoff** (0.5 s doubling to 10 s; it starts over only after a connection that
  held 10 s). After a supervisor restart the adopted game's hello can be up to 10 s away, so `no_channel` is normal
  for a replacement supervisor's first seconds. The wrapper reports `jvm_started` long before the mod loads, so in
  the real game the first hello is normally accepted; the stand-in game connects earlier and shows the refused-then-
  accepted path.
- **For step 4: the real helper sends no `windows` event yet**, so every `logout` in a real session is refused
  (`apps_unknown`) and every `restart` starts below the app in front, until `aresos-shell` reports the count. The
  format is decision 33; when tracking is lost the helper should send `"count": null`. Which windows count is 3.4's
  (a terminal he types `logout` into is an app window unless the helper says otherwise).
- **For step 4: where the black screen belongs.** Its start: `request_stop()` for `shutdown`, `logout`, `restart`
  when `app_windows() == []`. A window that appears: `on_windows()`. Its end: `finish_stop()` (called off, failed,
  overrun, `no_logout()`), `start_again()` once the startup cover is up, `on_labwc_gone()`. The black cover and the
  `systemd-inhibit` child belong in `Runner.end_children()`'s list, which is the only cleanup at the supervisor's
  exit.
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
  failure change no state. Step 4's black screen belongs to the same two places.
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
