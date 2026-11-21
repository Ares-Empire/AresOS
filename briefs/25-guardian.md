# 25: the guardian saves the world before every planned stop

Board #357; the owner's answer is board #379; brief (lead fills). OS package: `os/` and `docs/design/OS-BASE.md`,
nothing under `mod/`. Led by `linux-laptop-home`; worktree `~/AresOS-25-guardian`, branch `pkg/25-guardian`.
Revision 2 (2026-11-19), after the two brief reviews in `reviews/25-guardian/BRIEF-REVIEW-1-*.md`.

**Builder:** a Claude agent on Fable 5.2, one fresh agent per step. This code stands between the owner's world and
every shutdown: high-stakes data safety, where a second round costs more than the model.
**Review:** a fresh Codex `gpt-6.2-astra` `high`, read-only, with one focused data-safety pass (Acceptance).
`linux-aresos` reads the `os/` diff before merge. Rides R29 at the earliest.

## Why

Today nothing saves the home before it is stopped, and nothing checks what reached the disk.

- **Shutdown or restart:** systemd signals labwc and the supervisor together. The game loses its display and most
  likely dies on the spot (package 40 measured it as an X11 window; which backend GLFW picks is not verified), or
  is killed with its launcher a moment later (`die_with_parent`). What he built since Minecraft's last own save
  can be gone.
- **The next start** calls that end a crash (three in a row latch recovery) or a memory kill with a minute's
  wait: a wrong message for his own shutdown (package 23's known limit 4).
- **The supervisor** notices SIGTERM up to 30 s late, then leaves the game running. It cannot stop or restart the
  game, and the mod's lifecycle channel (package 46) has no other end.
- **Package 48's leftovers:** a half-made first home reads as "damaged, restore from a backup"; a home under a
  dated name opens unchecked; `world_missing` does not say which dated folder holds the home.

After 25: before the system or the supervisor ends the game on purpose, the world is flush-saved and the answer
checked; then the game closes and the supervisor waits for Java's real exit and the lock, all inside one deadline.
A planned stop never counts as a crash or a kill. A stop without a confirmed save is never passed off as one: it
is called off where it can be, and the next start says so where it cannot.

## Decided

- **The owner (board #379).** Asked whether a shutdown may save first (a few seconds, at most 60 s if the game
  hangs) and whether an unconfirmed save may show one window at the next start: "Yes but no visible 60s shutdown
  lag. Let's put a black screen and do it in the background? Because once I press shutdown I close the lid and
  leave right away". So the screens go black while a stop saves, a closed lid never interrupts it, and logout and
  restart look the same (3.4).
- **The lead.** Black only once nothing needs his attention: while an app window is open he sees his apps, never
  black (OS-BASE B3). A `restart` whose save fails leaves the game running and says why. A first home that was
  never finished is moved aside. This package deletes nothing. The exact new texts go into the report for the
  owner. A guard the VM cannot prove blocks the release. The lead starts the check build, never the builder.

## Read first

`AGENTS.md`. `docs/design/OS-BASE.md` B1 (the `save_world` and `prepare_stop` rows), B2 and B3. All of
`os/config/usr/libexec/aresos-desktop`, its wrapper `aresos-desktop-java` and `aresos-cover`; in `aresos-shell` the
status pipe and `Windows`. Read only: `mod/src/main/java/dev/aresos/shell/LifecycleClient.java` and its test,
`FakeSupervisor`, `mod/src/client/java/dev/aresos/client/WorldSaves.java` (when each refusal is given),
`HomeSwap.java`; the reports of packages 46 ("Contract readings"), 48 ("For linux-aresos") and 23 (JUDGMENT-CALL
10, known limit 4). `os/tests/test_aresos_desktop.py`; the check build's VM: `os/ci/vm.py`,
`os/ci/overlay/checks.py`. Both brief reviews.

## Build

### 1. The lifecycle channel, the supervisor's end (OS-BASE B1, as package 46 built the mod's)

- **1.1 The gate.** `game_environment()` adds `ARESOS_DESKTOP_LIFECYCLE=1`. The wrapper allows it (`SUPPLIED`) and
  drops an inherited one (`DROPPED`). Prism, the helper, its apps and the message windows never get it.
- **1.2 `lifecycle_hello`** on `desktop.sock` is accepted only if all hold: the peer's uid is ours; its PID is the
  current launch's JVM as the wrapper reported it (`jvm_started`), alive with the same start ticks; `instance` is
  this session's; `nonce` is the launch's (`hmac.compare_digest`); `major` is 1; `capabilities` has `save_world`.
  Accepted: no reply (the mod expects none), one log line. Refused: one log line (never the nonce) and the
  connection closes; the mod tries again, which also covers a hello before `jvm_started`. One peer per launch; a
  newer accepted hello replaces the older. After the hello only `world_saved` is read; anything else is dropped.
  `status` says whether a hello is accepted (a boolean).
- **1.3 What counts as saved.** The **active world** of a launch is the folder the helper last reported ready and
  `check_world` passed (4.4), or the locked world while none was reported, so a dead helper never stops saving. A
  request is `{"op":"save_world","id":n,"reason":…}`, ids counting up, reason `shutdown`, `backup`, `update` or
  `manual`. Its result is `saved` only if all hold: `ok:true`; the request's `id`; it came on the connection the
  request went out on; `world` is `{"id": <the active world>, "desktop": true}`; the active world did not change
  in between. Everything else is not a save: `wrong_world`, `refused` (the mod's `no_world`, `not_desktop_world`,
  `server_stopping` or `error`), `timeout` (a late answer is logged and dropped), `lost` (the connection closed
  first), `no_channel` (no accepted hello), `invalid`.
- **1.4 One in flight, one waiting.** A caller that arrives while a request is in flight gets one follow-up
  request, sent when the first is answered; later callers join it. Each caller has its own deadline on the
  supervisor's clock (`pending()`).
- **1.5 `save` for other callers** (package 26's backups, tests, him): socket op `save` and `aresos-desktop save`,
  60 s. The reply comes when the result is in and names the world; exit 0 only for `saved`. No reply may block the
  loop: a peer that does not take its line at once is dropped (today `reply()` waits up to 2 s for each). A
  command has one deadline for all of it, connecting and waiting included: 70 s for `save`, `stop`, `restart` and
  `logout` (today `request()` gives every socket step 10 s).

### 2. One stop routine (state `STOPPING`; no message window while it runs)

- **2.1 One deadline.** `STOP_BUDGET = 60` s, absolute, from the first request or signal of a stop to its end. A
  save already in flight, the save, the close, the replies, the cleanup and a logout all fit inside it, and
  nothing that joins the stop extends it. The save phase gets at most 30 s. Cleanup never waits without a limit:
  a helper, window or cover still there 1 s after SIGKILL is left to the system (today `stop_helper`, `close_view`
  and `end_covers` wait for ever). Every stop logs its phases with their times, to `desktop.log` and to the
  journal. The numbers are starting values: package 46's samples (0.02 to 0.7 s) predate its save-failure
  accounting, so report what the VM and the real game took.
- **2.2 Two kinds.** A stop that can be called off: `restart`, `logout`, `stop`. One that cannot: `shutdown` and
  the session ending (3.2). A `shutdown` asked for while systemd clearly says the system is not stopping
  (`systemctl is-system-running`, 2 s at most) is a plain `stop`; with no clear answer it stays a `shutdown`.
- **2.3 The record first.** Before the save is asked, write a stop record into `desktop.json` (launch, kind, the
  wall-clock start) and keep it true at each phase; fsync the file and the folder, as the wrapper does for its
  exit record. It closes when the stop is called off, which is possible only before SIGTERM is sent (the launch
  then runs on as an ordinary one), or when the launch it names has ended. Until then it names the launch: after
  an overrun and across a supervisor restart too. If it cannot be written, a stop that can be called off is; one
  that cannot goes on, and its reply says so. The file stays schema 1 with optional keys (R28 reads it after
  `previous`).
- **2.4 The save.** In this order:
  - **Nothing to save**, only on positive evidence: no Java is alive and none is in hand-off, or the worlds folder
    holds no folder at all. Then go to the close.
  - **`saved`** (1.3): go to the close.
  - **`no_world`, `server_stopping`, no accepted hello yet:** ask again each second until the save deadline. A
    game that is loading, switching homes, closing by itself or reconnecting gets there by itself. None of them
    ever means "nothing to save", for an adopted game either.
  - **Anything else, and the deadline:** the save is not confirmed. A stop that can be called off is called off:
    the game keeps running, window `save_failed`. One that cannot closes anyway and is recorded as `unsaved`.
- **2.5 The close.** SIGTERM to Java through the pidfd the supervisor already watches: never a PID from a file,
  never through the wrapper, never SIGKILL. Minecraft's own shutdown hook stops the integrated server, which saves
  once more and lets go of the world. Then wait for the real exit (the pidfd) and for `jvm_lock_held()` to be
  false. The close is `exited` (status 143, inside the deadline), `failed` (any other status, a kill, no report)
  or `overrun`.
- **2.6 What a stop may claim.** `saved` is the mod's word that everything up to the request is on the disk. What
  the game writes after it (the ticks until SIGTERM, its own closing save) no stop certifies; step 6 shows once,
  with the real game, that the SIGTERM close saves. So no stop is called clean. A stop is **confirmed** (saved, or
  nothing to save) or **unsaved**, and its close is reported beside it. B1's `prepare_stop` and `save_complete`
  stay unbuilt: the mod has no such op, and the system's own teardown ends the game by SIGTERM too.
- **2.7 Accounting and overrun.** A launch that ends while a stop record names it is `stopped`: never counted,
  never restarted by backoff, never latched `killed`, whatever its status, also when a replacement supervisor
  adopted it. That is decided from the supervisor's own record, never from who sent a signal (JUDGMENT-CALL 10
  stands). At the deadline with Java still there: the supervisor stops waiting, records `overrun` and never kills.
  `restart` and `stop`: window `stuck`, and no second game while the lock is held. `logout`: no logout. A stop
  that cannot be called off ends there: the supervisor answers, exits when the session's signal comes, and the
  system's teardown ends Java.
- **2.8 While it runs.** No JVM is authorized, no backoff restart fires, `retry` answers that AresOS is stopping,
  and a launch in hand-off is waited for and then closed. That holds until the stop is called off, `restart`
  starts the game again, or the session ends. A supervisor that replaces this one finds the open record and
  adopts the game: a stop that can be called off and had not sent SIGTERM is called off; any other goes on inside
  what is left of the deadline (by the record's start), and a `restart` or `logout` cut this way ends at the
  `quit` window. An op that arrives during a stop joins it: nothing starts a second stop or a second save, every
  caller gets its reply when the stop ends, `save` gets the stop's save result, and `stop --reason shutdown` or a
  signal makes it one that cannot be called off.
- **2.9 The next start.** A record still open whose launch is gone is closed: the launch is `stopped`, and if its
  save was not confirmed the latch `unsaved` is set. `unsaved` is a latch like the others: a window says the world
  could not be confirmed as saved last time and why, the home opens as it is on the disk, and `retry` clears it.
  A session that is ending persists it without opening a window. `save_failed`, `stuck` and `guard` (3.1) are not
  latches, but they stay until `retry` or the session's end: a heartbeat must not close them, as `ready()` would
  today. A stop with nothing running writes no record.

### 3. Who calls it

- **3.1 The laptop shuts down or restarts: the ordering guard (OS-BASE B3).** A system unit
  `aresos-guardian.service`: oneshot, `RemainAfterExit=yes`, `User=ares`, `XDG_RUNTIME_DIR=/run/user/1001`,
  `ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown`, `TimeoutStopSec=75`, enabled in `os/build.sh`. It
  is ordered after `greetd.service`, `user@1001.service`, `user-runtime-dir@1001.service` and the home's mount,
  and a drop-in beside `session-.scope.d/50-aresos-recovery.conf` orders every session scope before it. So at
  shutdown its stop ends before any of them begins to stop: labwc, Prism's wrapper, the socket and the disk are
  still there while the world is saved. Chosen over a logind delay lock: it covers every orderly shutdown whoever
  asked for it and needs no D-Bus in the supervisor. It must not create an ordering cycle at boot.
  - **Armed first.** No JVM is authorized unless the guard is active (`systemctl is-active`, 2 s at most).
    Otherwise window `guard`; `retry` asks again.
  - **No supervisor answers** (no socket, refused, or no reply inside the command's deadline): try again each
    second for 10 s (the keeper starts a new supervisor after 2 s). Then, if the desktop lock is free, nothing is
    running: exit 0. If it is held, a game may be writing: write a fallback record (a file of its own in the state
    folder, fsynced, naming the launch from the runtime file) and exit 1. The command never signals anything. The
    next supervisor applies the fallback once: `unsaved` for that launch, unless its own record says `saved`.
  - **The real wait.** Normally a few seconds. At worst the command gives up after 70 s and the guard after 75 s;
    a game that ignores SIGTERM is then ended by systemd's own limit for the game scope (90 s by default; the VM
    prints it), so about 165 s to power-off. It is behind black until the guard ends (3.4).
  - **Other ends of a session** (labwc killed, `loginctl terminate-session`, greetd restarted) stop no system
    unit, so the guard does not run: 3.2 does what it can and records the truth. The supported logout is 3.3's.
- **3.2 The session ends under the supervisor.** SIGTERM, SIGHUP and SIGINT are noticed within a second
  (`signal.set_wakeup_fd` on a pipe in the selector; today `select` sleeps up to 30 s) and run the stop routine
  before the supervisor exits; the keeper waits for it. The supervisor also watches labwc by pidfd. It takes
  `LABWC_PID` only from its own environment and uses it only if that process is named labwc, has our uid and has
  this supervisor's `XDG_RUNTIME_DIR` in its environment: a supervisor on a private runtime folder can then never
  touch the session's labwc; with a `LABWC_PID` that fails this check it watches nothing and logs that once.
  When labwc ends the session is over, and nothing of the old session outlives it by more than the deadline; a
  supervisor started after its labwc ended stops what it adopts and exits.
- **3.3 Commands** (socket ops and `aresos-desktop` words; exit 0 only for a confirmed stop whose close `exited`,
  or when nothing is running):
  - `stop [--reason shutdown]`: after a plain stop the `quit` window.
  - `restart`: stop, then start again: with no app window open as `retry` does (the startup cover), otherwise as
    an automatic restart does (below the app in front). Also a word in the message window (`desktop-view.bashrc`).
  - `logout`: refused while an app window is open or the helper has not said (3.4): it names them and stops
    nothing. Otherwise stop; if confirmed and `exited`, SIGTERM to labwc through the pidfd of 3.2 (never `labwc
    --exit`, which signals whatever `LABWC_PID` says), and wait for its exit inside the deadline. If labwc stays,
    the reply says so and the `quit` window shows.
  - `retry` stays as it is: it never stops a running game.
- **3.4 The black screen and the lid (board #379).**
  - **When.** A `shutdown`, `logout` or `restart` goes black at its start if the helper's last report says no app
    window is open. With an app window open, or no report, the screens stay as they are: he sees his apps. The
    helper reports the count on its status pipe (event `windows`, at each change, as `apps_running` is coalesced):
    every window but the desktop's, the covers' and the supervisor's message window, minimized ones included.
  - **How.** `aresos-cover --black`: plain black, no text, one fullscreen window on every output, app id
    `aresos.black`, kept on top by a window rule of its own in `rc.xml` (no `ToggleFullscreen`: each window asks
    for its output itself). The helper treats it as the startup cover: never an app, never covering, never
    minimized. A surface, not outputs switched off: switching them off rearranges windows under a game that is
    saving, and only a child with die-with-parent restores the display when the supervisor dies. labwc, the game
    and the save run on behind it.
  - **Until.** It ends when the stop is called off, fails or overruns (the window must be seen), when `restart`'s
    startup cover is up, when labwc ends, or by its own limit (`STOP_BUDGET + 30` s). At a shutdown it stays until
    the session is torn down.
  - **The lid.** For the length of every stop the supervisor holds a logind block on `handle-lid-switch:sleep`
    (a `systemd-inhibit` child with die-with-parent). It is started and never waited for, so it cannot delay the
    stop; a failure is one log line. The static policy in `logind.conf.d` stays as it is.

### 4. Package 48's leftovers

- **4.1 The first home died while it was made.** While a setup launch that started with no `AresHub` runs,
  remember in `desktop.json` the folder once it appears (device and inode; looked for at each heartbeat and at
  the launch's end). At a later start, if `hub_seen` is false and `AresHub` is that same folder and reads damaged:
  `SETUP` with reason `setup_unfinished` instead of the `world_damaged` latch, and `retry` moves it to
  `AresHub-unfinished-<date>` and starts setup again. Every other damaged world stays exactly as today, also a
  half-made one the supervisor never saw appear.
- **4.2 One way to move a home.** Only while no launch is alive and none is in hand-off, holding the desktop lock
  (`flock`, as the wrapper takes it) from the checks to the rename, with `renameat2(RENAME_NOREPLACE)` through
  ctypes, never `os.rename`. 4.1 uses it, and so does a new command `aresos-desktop use-home <folder>`, which
  makes a dated folder that passes the home checks the home, only while no `AresHub` exists.
- **4.3 `world_missing` says where the home is.** It names the newest `AresHub-<date>` that passes the home
  checks, and an `AresHub-new-<date>` that does, with the `use-home` line. Nothing is moved for him. The prefixes
  and the date pattern equal `HomeSwap`'s, its `-1`, `-2` suffix included; a test reads the Java constants.
- **4.4 A dated home reported ready** (`ready()`, about lines 1427 to 1446). `check_world` takes the folder name.
  A world other than the locked one is checked the same way if it is a plain folder inside the worlds folder, and
  is never declared ready when damaged or outside. It becomes the active world (1.3) and sets `hub_seen`, so a
  missing `AresHub` afterwards reads `world_missing`, never a silent new setup beside his old home.
- **4.5 `AresHub-new-<date>` leftovers.** Never deleted: one may be the home he just made. One log line at start
  with their count and size, and `status` lists them.

### 5. Docs

`OS-BASE.md` B1 (`save_world`: both ends built; `prepare_stop` as 2.6 leaves it), B2 (`STOPPING`, `stopped`,
`unsaved`), B3 (the guard, the black screen and the lid block are built; the coordinator stays a proposal). The
supervisor's docstring. Never `os/owner-tools/`, `os/release/`, the install guides or `STATE.md`.

## Steps

One fresh agent per step, about 250k tokens. Each ends with its tests green by module name, a commit (trailer
`Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`), a push, and `reviews/25-guardian/PROGRESS.md` true:
done, left in order, what the code does not show.

1. Section 1.
2. Section 2, with 3.3's `stop` to drive it.
3. 3.2 and 3.3: the signal wake-up, labwc, `restart`, `logout`, the windows' texts.
4. 3.4: the black screen, the helper's `windows` event, the lid block. Name the `rc.xml` and `aresos-shell` lines
   you changed in `PROGRESS.md`: the lead gives notice to `linux-aresos` and `linux-hub`.
5. Section 4.
6. The real game (Acceptance). It decides whether 2.5's close stands, so it comes before the guard.
7. 3.1 and the VM checks. Push, start one `gh workflow run "OS image" --ref pkg/25-guardian -f checks_only=true`,
   and stop: never watch it, never start a check build. The lead starts the check build once `linux-aresos` says
   R28 is through.
8. Started by the lead with the finished check build's run ID: fix what its new checks show, section 5, the
   report, the pull request.

## Acceptance

- **`os/tests/test_aresos_guardian.py`** (new; the state machine with `FakeRunner`): every rule of sections 1, 2
  and 4. Among them: each way a hello is refused; five callers on one request in flight and one waiting; a late
  answer; a reply with a wrong `id`, a wrong world, from an older connection, or after the active world changed;
  2.4 for both kinds of stop while loading, after an adoption, with a dead helper, during New home, and for
  `server_stopping` followed by `no_world`; a record that cannot be written; 143, 0, SIGKILL and no report after
  a stop are `stopped`, also for a replacement supervisor in a teardown, and three stops in a row never latch; an
  op and a signal that join a stop; a stalled peer; the guard not active; the command's fallback record; the
  windows that must survive a heartbeat; a `labwc` with another runtime folder is never signalled; `logout` with
  an app window open; `desktop.json` with the new keys read through R28's frozen key list; 4.1 to 4.5.
- **`os/tests/test_aresos_guardian_loop.py`** (new; the real loop, the real wrapper, a stand-in game process).
  Failure injection: a save that hangs, one that answers `error`, one that answers `no_world`, a world that
  changed its name, SIGTERM in the middle of a save, a game that ignores SIGTERM (never killed, no second game,
  and a stop that cannot be called off exits at the deadline). SIGTERM to an idle loop begins the stop within 1 s
  and the keeper waits. A stand-in for labwc (a process of the test's, named `labwc`) ends: the supervisor and the
  keeper end inside the deadline.
- `test_aresos_desktop.py`, `test_aresos_cover.py` and the `test_aresos_shell*.py` modules you touch still pass,
  by name, with the hand-off model unchanged.
- **The real game (step 6), a condition for merging.** Headless, under the client-test lock, on a copy of
  `reviews/49b-arena-rerun/rig/` in `reviews/25-guardian/rig/`; never Prism, never his instance.
  - Only the game's own command line in `inner.sh` gets the gate, `XDG_RUNTIME_DIR` set to the test supervisor's
    temporary runtime folder, the instance and nonce its adoption runtime file names, and an absolute
    `WAYLAND_DISPLAY` if it needs one. Before the first `save`, check that `/proc/<game>/environ` has that
    `XDG_RUNTIME_DIR`: with the session's, the mod would dial his live supervisor.
  - The close alone, three times: place a block, send SIGTERM to the rig's own game, reopen the world: the block
    is there. Report the log's server-stop lines, the exit status and the time to exit.
  - The path, once: the adoption path lets the real supervisor take the rig's game; the hello is accepted, `save`
    answers `saved`, `stop` ends confirmed and `exited`.
  - If SIGTERM does not close the world soundly, or the rig cannot show it, stop and say so first: the package
    does not merge on an unverified close. A mod-side `prepare_stop` is then `linux-hub`'s package, and 25 waits.
- **The VM (the lead's check build), a condition for the release.** `os/ci/vm.py` is a bound file: after changing
  it run `python3 reviews/27-first-update-release/rebind.py pending "25: …"` and commit the list. The stand-in
  game is a real JVM (the pinned Java through the real wrapper, speaking the lifecycle channel; a single-file Java
  program if the image's Java runs one, else a class built into the check overlay), started so that the check
  service's own stop cannot reach it. The shortcut step leaves the supervisor latched `killed`: clear it with
  `retry` (it answers after a minute without memory pressure) and wait until `status` shows the game with an
  accepted hello. Evidence holds allowlisted fields only: never an environment, a runtime file, a nonce or a token.
  - **Boot 1, the power key with a save that takes 5 s,** a peer that never reads, a lid event during the save,
    and no app window open (Prism's own window counts as one: end it first). By the journal's monotonic times:
    the guard's stop began; the screen is black (pixels); the save was answered; Java exited; the guard's stop
    ended; only then did labwc, the session scope, greetd, `user@1001.service` and the home's mount begin to stop.
    During the save a probe saw all of them, the game's wrapper and the socket alive and the home writable.
    Nothing suspended. Read offline, the record says confirmed and `exited`. Power-off stays inside `vm.py`'s
    120 s. At boot: no "ordering cycle" line, and the guard active before the session's first JVM was authorized.
    The stop limits of the session and game scopes are printed.
  - **Boot 2, a game that never answers and ignores SIGTERM.** The guard ends at its limit, the machine powers off
    by itself inside 3.1's worst case, and the record says `unsaved` and `overrun`.
- Merge `origin/main` before step 7's and step 8's last push. Step 8 ends as step 7 does: one `checks_only=true`
  run, then stop.
- The report (AGENTS.md format) goes into `PROGRESS.md`; the lead commits it as `REPORT.md`. It has the measured
  times, the exact new texts for the owner, the new image files for the release diff, the Known limits and every
  JUDGMENT-CALL. Open the pull request "Package 25: the guardian saves the world before every planned stop". Never
  merge.
- **The reviewer's data-safety pass** looks for: a stop reported as confirmed without a `saved` that passes 1.3 or
  2.4's positive evidence; a signal to Java or labwc other than SIGTERM through its watched pidfd; a second game
  while the lock is held or a stop runs; a world folder moved outside 4.2 or deleted anywhere; a hello or an
  answer trusted without its PID, nonce, connection or `id`; anything that can outlast the one deadline.

## The safety bar (decision 24; the owner restated it 2026-11-18)

Real harm gets fixed: a lost or damaged world, a stop passed off as saved, anything hard to undo. Low-harm edge
cases are not built around; they go under Known limits in the report. That list starts with these: a power cut or
a forced power-off is not a planned stop; a shutdown that skips unit stops (`--force`) skips the guard; no stop
certifies the game's own closing save (2.6); a shutdown while the game is loading or at its title screen waits up
to 30 s and can still end `unsaved`; when labwc dies under the game, 25 can only record it; the supervisor never
kills a hung game; a shutdown with an app open closes that app as it does today (B3's "close your apps first" is
not built), but never behind black.

## Machine rules

- **Never the owner's session:** no window in it, no input to it (`wayland-0`). Never his `.minecraft`, Lunar
  Client, `~/AresOS-try`, his Prism data, his worlds or his `~/.local/state/aresos`.
- **Never the live supervisor or his labwc.** Every supervisor a test, a rig or a try by hand starts runs under
  `env -i` with `HOME`, a temporary `XDG_RUNTIME_DIR`, `PATH` and the `LABWC_PID` of a stand-in it started; never
  with the shell's `DISPLAY`, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS` or `LABWC_PID`. The supervisor hands
  its whole environment on and ends labwc at a logout: with the shell's, a test would end his session. An
  `aresos-desktop` command with the session's `XDG_RUNTIME_DIR` would reach his running game.
- **No real shutdown, restart or logout of the laptop:** no `systemctl poweroff` or `reboot`, no `loginctl`, no
  `labwc --exit`, no system unit installed or started. The guard runs only in the hosted VM.
- Headless only. A game only through the rig or `mod/dev/client-test.sh`, which take the client-test lock; exit 75
  means wait five minutes and try again, never `--force`. Stop only processes you started, by PID.
- `os/tests`: the modules you touch, by name, one at a time; never the whole folder, never `test_owner_update`.
  The repo is public: made-up names only, and the pre-push privacy check is never bypassed (`--no-verify`).

## Out of scope

Package 26 (backups; it will call `save`). Package 23c (the view token, the laptop home, `search`, the screens):
it changes the same file, so keep your code in functions of its own and do not reshape `Loop.handle`,
`save_runtime` or `PRIVATE_ENVIRONMENT` beyond what you need; a `restart` keeps the session's instance and, once
23c is on main, its view token, which never reaches the game or any evidence. Package 53. OS-BASE B3's power
coordinator: block inhibitors on shutdown, "close your apps first", the battery, `request_power`. A mod-side
`prepare_stop` or close acknowledgement (the follow-up that would certify the close; `linux-hub`'s), and anything
under `mod/`. The owner tools and the `aresos` command. A shutdown button in the hub.

**The lead's call on the worst case (2026-11-19):** the game's scope gets `TimeoutStopSec=15s` (one property in
`game_scope()`), so a game that ignores SIGTERM after the guard has ended does not keep a closed laptop on for
systemd's default 90 s. The VM prints the effective limit.

## The lead's fixes after the recheck (2026-11-19, `reviews/25-guardian/BRIEF-RECHECK-1-codex.md`)

These override anything above that disagrees.
1. **Time budget with room for the fallback.**
   - The supervisor's stop keeps its one 60 s deadline.
   - The guard's command waits at most 62 s for the supervisor's reply, then makes at most one 10 s recovery attempt,
     then writes its fallback record.
   - The guard unit's `TimeoutStopSec` is **85 s**, so the fallback always has time.
   - An explicit failure to write the stop record takes the same fallback path as no answer.
   - **"No writer" needs positive evidence:** the desktop lock is opened and taken with `flock` by the guard itself.
     An open or lock error counts as "unknown", never as free, so the fallback record is written and the command
     exits 1.
   - The worst case to power-off is then 85 s plus the game scope's 15 s, all behind the black screen.
2. **Launch admission stays closed for the whole teardown.** When a stop of kind `shutdown` or `logout` begins, the
   supervisor writes a session-bound admission block in its runtime folder. It is written before the launch record
   can close. It holds for any later or replacement supervisor until the session ends, and it is written also for a
   logout with no game running. No launch, `retry` or hand-off is admitted while it exists.
3. **A logout with no game running still logs out.** With positive evidence that no writer exists, `logout` goes on
   to signal labwc through the watched pidfd and checks that it exited within the deadline. "Nothing to save" is
   never a reason to skip the logout itself.
4. **The app check is fresh at the moment it matters.**
   - The helper's window count is invalidated when tracking is lost or the helper dies; unknown counts as open.
   - An app window that appears during the stop removes the black screen at once.
   - `logout` requires a fresh count of zero immediately before it signals labwc, not only at the start.
5. **The VM fixture really saves.** Seed a disposable world folder before each boot, so the stop takes the save path,
   and assert from the evidence that each fixture received the save request and answered it.
6. **The hung-shutdown gate is consistent.**
   - The VM asserts the game scope's effective `TimeoutStopSec` is 15 s.
   - Boot 2's power-off bound is 85 s + 15 s + 20 s of margin.
7. **The release proof is on the final code.** If step 8 changes the guard, the stop routine or the VM check after the
   lead's check build, the step ends by asking the lead for a new check build on its final commit. That build must
   pass before merge. A `checks_only` run boots no VM and does not count as this proof.
