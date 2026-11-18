# 25: the guardian saves the world before every planned stop

Board #357, brief (lead fills). OS package: `os/` and `docs/design/OS-BASE.md`, nothing under `mod/`. Led by
`linux-laptop-home`; worktree `~/AresOS-25-guardian`, branch `pkg/25-guardian`.

**Builder:** a Claude agent on Fable 5.2, one fresh agent per step. This code stands between the owner's world and
every shutdown: high-stakes data safety, where a second round costs more than the model.
**Review:** a fresh Codex `gpt-6.2-astra` `high`, read-only, with one focused data-safety pass (Acceptance).
`linux-aresos` reads the `os/` diff before merge. Rides R29 at the earliest.

## Why

Today nothing saves the home before it is stopped, and nothing checks what reached the disk.

- **Shutdown or restart:** systemd signals labwc and the supervisor together. The game runs through XWayland,
  loses its display and most likely dies on the spot, or is killed with its launcher a moment later
  (`die_with_parent`). What he built since Minecraft's last own save can be gone.
- **The next start** calls that end a crash (three in a row latch recovery) or a memory kill with a minute's
  wait: a wrong message for his own shutdown (package 23's known limit 4).
- **The supervisor** notices SIGTERM up to 30 s late, then leaves the game running. It cannot stop or restart the
  game, and the mod's lifecycle channel (package 46) has no other end.
- **Package 48's leftovers:** a half-made first home reads as "damaged, restore from a backup"; a home under a
  dated name opens unchecked; `world_missing` does not say where the home is.

After 25: before the system or the supervisor ends the game on purpose, the world is flush-saved, the answer is
checked, the game closes, and the supervisor waits for Java's real exit and the lock, inside a fixed budget. A
planned stop never counts as a crash or a kill. A save that cannot be confirmed is never called clean: the stop
is called off where it can be, and the next start says so where it cannot.

## Read first

`AGENTS.md`. `docs/design/OS-BASE.md` B1 (the `save_world` and `prepare_stop` rows), B2, and B3 (only its
"shutdown ordering guard" is this package). All of `os/config/usr/libexec/aresos-desktop` and its wrapper
`aresos-desktop-java`. Read only: `mod/src/main/java/dev/aresos/shell/LifecycleClient.java`, its test,
`FakeSupervisor`, `HomeSwap.java`; the reports of packages 46 ("Contract readings", the measured times), 48 ("For
linux-aresos") and 23 (JUDGMENT-CALL 10, known limit 4). `os/tests/test_aresos_desktop.py`; the check build's VM:
`os/ci/vm.py`, `os/ci/overlay/checks.py`.

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
- **1.3 Asking for a save.** `{"op":"save_world","id":n,"reason":…}`, ids counting up, reason `shutdown`,
  `backup`, `update` or `manual`. At most one request in flight and one waiting: a caller that arrives while one
  is in flight gets one follow-up request, sent when the first is answered, and later callers join it. Each
  caller has its own deadline on the supervisor's clock (`pending()`). A caller's result is exactly one of:
  - `saved`: `ok:true`, the right `id`, `world` is `{"id": <the locked world>, "desktop": true}`; keep `ms`.
  - `other_world`: the same for a desktop world under another name (`AresHub-<date>`, see 4.3). A stop accepts it
    (that world did reach the disk); `save` reports it as not saved and names it.
  - `refused`, with the mod's reason: `no_world`, `not_desktop_world`, `server_stopping` or `error`.
  - `timeout` (a late answer is logged and dropped), `lost` (the connection closed first), `no_channel` (no
    accepted hello), `invalid` (anything else, such as `ok:true` without a world).
- **1.4 `save` for other callers** (package 26's backups, tests, him): socket op `save` and `aresos-desktop save`,
  deadline 60 s. The reply comes when the result is in, so the loop learns to answer a peer later. Exit 0 only
  for `saved`.

### 2. One stop routine (state `STOPPING`; no message window while it runs)

- **2.1 The budget.** `STOP_BUDGET = 60` s from the stop's start until Java is gone and the desktop lock is free.
  The save gets at most `SAVE_DEADLINE = 30` s of it, never more than what is left; the close gets the rest.
  Every stop logs one line: the save's wait and `ms`, the close's time, the total. These are starting values (46
  measured saves of 0.02 to 0.7 s): report what the VM and the real game took and whether they should change.
- **2.2 The record first.** Before the save is asked, write a stop record into `desktop.json` (which launch, why,
  when, whether a world was ready in this launch) and keep it true at each phase. Fsync the file and the folder,
  as the wrapper does for its exit record: the power may go seconds later. The file stays schema 1 with optional
  keys, so R28's supervisor still reads it after `previous`.
- **2.3 The save, then what.** Stops that can be called off: `restart`, `logout`, `stop`. Stops that cannot:
  `shutdown` and the session ending. A launch that was in a world but has no accepted hello waits for one up to
  10 s (the mod's longest backoff) before `no_channel`.

  | Save result | Can be called off | Cannot |
  |---|---|---|
  | `saved`, `other_world` | close | close |
  | `no_world`, `not_desktop_world`; `no_channel` when no world was ready in this launch | close | close |
  | `server_stopping` (the game is closing by itself) | ask again each second; `timeout` at the deadline | the same |
  | `error`, `timeout`, `lost`, `invalid`; `no_channel` after a world was ready | call it off: the game keeps running, window `save_failed` | close anyway, latch `unsaved` |

- **2.4 The close.** SIGTERM to Java through the pidfd the supervisor already watches: never a PID from a file,
  never through the wrapper, never SIGKILL. Minecraft's own shutdown hook stops the integrated server, which saves
  once more and lets go of the world. Then wait for the real exit (the pidfd) and for `jvm_lock_held()` to be
  false. B1's `prepare_stop` message is not built: the mod has no such op, the system's teardown ends the game by
  SIGTERM too, and after a confirmed flush save the close can lose only the ticks in between. While `STOPPING`
  no JVM is authorized, no backoff restart fires, and a launch still in hand-off is waited for and then closed.
- **2.5 Accounting.** A launch that ends while a stop record names it is `stopped`: never counted, never restarted
  by backoff, never latched `killed`, whatever status Java ended with (143 is the expected one). That is decided
  from the supervisor's own record, never from who sent a signal (JUDGMENT-CALL 10 stands). The stop is clean only
  if the save was confirmed or nothing was open, Java left inside the budget, and not by SIGKILL. A stop that was
  called off closes its record, and the launch runs on as before; after an overrun the record keeps naming the
  launch, so its later end is still `stopped`.
- **2.6 Overrun.** Java is still there when the budget ends: the supervisor stops waiting, records it, and never
  kills. `restart` and `stop`: window `stuck` (still running; saved first or not), and no second game while the
  lock is held. `logout`: no logout. `shutdown` and a session ending: exit; the system's teardown ends Java.
- **2.7 The next start.** A stop record still open at start-up (the laptop went off, the supervisor died) is
  closed as unclean; a restarted supervisor never resumes a stop, it adopts a game that still runs. `unsaved` (a
  world was ready and its save was not confirmed) is a latch like the others: the next start shows a window that
  says the world could not be saved last time and why, and `retry` clears it. A session that is ending persists
  it without opening a window.

### 3. Who calls it

- **3.1 The laptop shuts down or restarts: an ordering guard (OS-BASE B3).** A system unit
  `aresos-guardian.service` (oneshot, `RemainAfterExit=yes`, `User=ares`, `XDG_RUNTIME_DIR=/run/user/1001`,
  `ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown`, `TimeoutStopSec=75`), enabled in `os/build.sh`
  and ordered so that its stop has finished before `greetd.service`, `user@1001.service` or any session scope (a
  drop-in beside `session-.scope.d/50-aresos-recovery.conf`) begins to stop: labwc and the game are still up
  while the world is saved and the game closes. No supervisor running: exit 0 at once. Chosen over a logind delay
  lock: it covers every orderly shutdown whoever asked for it and needs no D-Bus in the supervisor. It must not
  create an ordering cycle at boot. If unit ordering cannot give this order in the VM, leave the guard out, finish
  the rest and say so first in the report. If the session is still up 120 s after a `shutdown` stop (the shutdown
  was called off), show the `quit` window.
- **3.2 The session ends under the supervisor.** SIGTERM, SIGHUP and SIGINT are noticed within a second
  (`signal.set_wakeup_fd` on a pipe in the selector; today `select` sleeps up to 30 s) and run the stop routine
  before the supervisor exits; the keeper waits for it. A signal during a save or a stop turns it into one that
  cannot be called off; it never starts a second save and never abandons one. Also watch labwc itself
  (`LABWC_PID`, by pidfd, checked to be labwc): when it ends, the session is over, and nothing of the old session
  may outlive it by more than the budget.
- **3.3 Commands** (socket ops and `aresos-desktop` words; the reply comes when the stop has ended, and the
  command waits `STOP_BUDGET + 10` s): `stop [--reason shutdown|manual]` (exit 0 for clean or nothing running;
  after `manual` the `quit` window), `restart` (stop, then `begin(cover=COVER_AGAIN)`; also a word in the message
  window, `desktop-view.bashrc`), `logout` (stop, and only if clean `labwc --exit`). `retry` stays as it is: it
  never stops a running game.

### 4. Package 48's leftovers

- **4.1 The first home died while it was made.** Remember in `desktop.json` that a setup launch started with no
  `AresHub`; forget it when the hub is first seen. If the world then reads damaged, `hub_seen` is false and that
  mark is set: `SETUP` with reason `setup_unfinished` instead of the `world_damaged` latch, and `retry` renames
  the folder to `AresHub-unfinished-<date>` (inside the worlds folder, refused if the name exists, nothing
  deleted) and starts setup again. Every other damaged world stays exactly as today.
- **4.2 `world_missing` says where the home is.** It names the newest `AresHub-<date>` that passes the home
  checks, and an `AresHub-new-<date>` that does, with the `mv` line that puts it back. Nothing is renamed for him.
  The prefixes and the date pattern equal `HomeSwap`'s; a test reads the Java constants.
- **4.3 A dated home reported ready** (`ready()`, about lines 1427 to 1446). `check_world` takes the folder name.
  A world other than the locked one is checked the same way if it is a plain folder inside the worlds folder,
  and is never declared ready when damaged or outside. It sets `hub_seen` too, so a missing `AresHub` afterwards
  reads `world_missing`, never a silent new setup beside his old home.
- **4.4 `AresHub-new-<date>` leftovers.** Nothing is deleted: one may be the home he just made. One log line at
  start with their count and size, and `status` lists them.

### 5. Docs

`OS-BASE.md` B1 (`save_world`: both ends built; `prepare_stop` as built in 2.4), B2 (`STOPPING`, `stopped`,
`unsaved`), B3 (the guard is built; the coordinator stays a proposal). The supervisor's docstring. Never
`os/owner-tools/`, `os/release/`, the install guides or `STATE.md`.

## Steps

One fresh agent per step, about 250k tokens. Each ends with its tests green by module name, a commit (trailer
`Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`), a push, and `reviews/25-guardian/PROGRESS.md` true:
done, left in order, what the code does not show.

1. Section 1.
2. Section 2, with 3.3's `stop` op and command to drive it.
3. 3.2, 3.3's `restart` and `logout`, and the windows' texts.
4. 3.1 with its image wiring and the VM check. Push, start `gh workflow run "OS image" --ref pkg/25-guardian -f
   check_build=build`, write the run ID into `PROGRESS.md`, stop.
5. Sections 4 and 5, the real game once, the report, the pull request. Look at step 4's run once
   (`gh run view <id>`; never a watch, never a loop) and fix what its new checks show. If this step runs short,
   the real game becomes a step 6: say so in `PROGRESS.md`.

## Acceptance

- **`os/tests/test_aresos_guardian.py`** (new; the state machine with `FakeRunner`): every rule of sections 1, 2
  and 4. Among them: each way a hello is refused, a second hello, an adopted game; five callers on one request in
  flight and one waiting; a late answer; `ok:true` with a wrong `id`; every row of 2.3's table for both kinds of
  stop; 143, 0, SIGKILL and no report at all after a stop are `stopped`, and three stops in a row never latch; an
  open record at start-up; `unsaved` survives a reboot; `desktop.json` keeps `schema` 1 and every key R28's
  `Persisted.load` reads; the guard's `TimeoutStopSec` is at least `STOP_BUDGET + 10`, and its drop-in and enable
  line exist.
- **`os/tests/test_aresos_guardian_loop.py`** (new; the real loop, the real wrapper, a stand-in game process).
  Failure injection: a save that hangs, one that answers `error`, one that answers `no_world`, a world that
  changed its name, SIGTERM in the middle of a save, a game that ignores SIGTERM (never killed, no second game,
  and on `shutdown` the supervisor exits at the budget). SIGTERM to an idle loop begins the stop within 1 s and
  the keeper waits. A stand-in for labwc (a process of the test's, named `labwc` and given as `LABWC_PID`; the
  hosted runner has no labwc) ends: the supervisor and the keeper end inside the budget.
- `test_aresos_desktop.py` and `test_aresos_cover.py` still pass, by name, with the hand-off model unchanged.
- **The VM** (the check build; `os/ci/vm.py` is a bound file: after changing it run
  `python3 reviews/27-first-update-release/rebind.py pending "25: …"` and commit the list). A stand-in game that
  is a real JVM (the pinned Java through the real wrapper, speaking the lifecycle channel, so the PID check sees
  it; a single-file Java program if the image's Java runs one, else a class built into the check overlay) runs
  when the power key is pressed. Start it so that the check service's own stop cannot reach it, as
  `prepare-poweroff` starts its journal follower. The journal's monotonic times show: the guard's stop began, the
  save was answered, Java exited, and only then did labwc, the session scope and greetd begin to stop. The stop
  record is clean; power-off stays inside `vm.py`'s 120 s; no "ordering cycle" line at boot; the stop limits of
  the guard, the session scope and `user@1001.service` are each at least `STOP_BUDGET + 10` s (raise one in the
  drop-in if not).
- **The real game, once,** headless and under the client-test lock (start from `reviews/49b-arena-rerun/rig/`;
  never Prism, never his instance). The adoption path lets the real supervisor take a game it did not start (a
  runtime file naming the rig game's PID, start ticks and nonce). With the gate set: the hello is accepted, `save`
  answers, then `stop`. Report the log's server-stop lines, Java's exit status and time to exit, and that a block
  placed just before the request is in the reopened world. If SIGTERM does not close the world cleanly, keep the
  design (the save is confirmed first) and write it under PLAN-GAP: a mod-side `prepare_stop` would be
  `linux-hub`'s package. If the rig cannot do this, say so under Not verified.
- Merge `origin/main` before the last push. After it: `gh workflow run "OS image" --ref pkg/25-guardian -f
  checks_only=true`, and the check build again if `os/config` or `os/ci` changed since step 4's. Push, then stop:
  never watch CI.
- The report (AGENTS.md format) goes into `PROGRESS.md`; the lead commits it as `REPORT.md`. It has the measured
  times, the exact new texts, the new image files for the release diff, the Known limits and every JUDGMENT-CALL.
  Open the pull request "Package 25: the guardian saves the world before every planned stop". Never merge.
- **The reviewer's data-safety pass** looks for: a stop called clean without a checked `world_saved`; a signal to
  anything but the watched pidfd, or any kill; a second game while the lock is held; a world folder renamed or
  deleted outside 4.1; a hello or an answer trusted without its PID, nonce or `id`; the guard holding a shutdown
  past its limit.

## The safety bar (decision 24; the owner restated it 2026-11-18)

Real harm gets fixed: a lost or damaged world, a stop called clean that was not, anything hard to undo. Low-harm
edge cases are not built around; they go under Known limits in the report. That list starts with these: a power
cut or a forced power-off is not a planned stop; a shutdown that skips unit stops (`--force`) skips the guard; a
stop during New home drops the home being made (the old one is saved and closed first); a normal world open in
the desktop instance is closed by the game alone, unconfirmed; when labwc dies under the game, 25 can only record
it (`unsaved`); the supervisor never kills a hung game; other apps' unsaved work is untouched (OS-BASE B3).

## Questions for the owner (the lead asks; build the recommendation, each is one constant or one branch)

1. **How long may a shutdown wait when the game hangs?** Normally the save adds a few seconds. Recommended: at
   most 60 s, then the laptop goes off anyway and the next start says the world could not be saved.
2. **After a stop without a confirmed save,** the next start shows one window that says so and waits for `retry`
   (recommended: he should know before he builds on), or it opens the home at once and only logs it.
3. **`restart` when the save fails:** the game keeps running and a window says why (recommended), or it restarts
   anyway.
4. **A first home that was never finished:** `retry` moves the unfinished folder aside and makes the home again
   (recommended), instead of today's "damaged, restore from a backup".
5. **Leftover `AresHub-new-<date>` folders:** 25 deletes nothing (recommended); cleaning waits for backups (26).
6. **Words and texts:** `restart` in the message window; `aresos-desktop save` and `logout` in a terminal; the
   texts of `unsaved`, `save_failed`, `stuck`, `setup_unfinished` and `world_missing`'s new lines (in the report).

## Machine rules

- **Never the owner's session:** no window in it, no input to it (`wayland-0`). Never his `.minecraft`, Lunar
  Client, `~/AresOS-try`, his Prism data, his worlds or his `~/.local/state/aresos`.
- **Never the live supervisor.** Every test and rig run sets its own `HOME` and `XDG_RUNTIME_DIR` (temporary
  folders). An `aresos-desktop stop`, `restart`, `logout`, `save` or `retry` with the session's
  `XDG_RUNTIME_DIR` would reach his running game.
- **No real shutdown, restart or logout of the laptop:** no `systemctl poweroff` or `reboot`, no `loginctl`, no
  `labwc --exit` outside a headless compositor you started, no system unit installed or started. The guard runs
  only in the hosted VM.
- Headless only. A game only through the rig or `mod/dev/client-test.sh`, which take the client-test lock; exit 75
  means wait five minutes and try again, never `--force`. Stop only processes you started, by PID.
- `os/tests`: the modules you touch, by name, one at a time; never the whole folder, never `test_owner_update`.
  The repo is public: made-up names only, and the pre-push privacy check is never bypassed (`--no-verify`).

## Out of scope

Package 26 (backups; it will call `save`). Package 23c (the view token, the laptop home, `search`, the screens):
it changes the same file, so keep your code in functions of its own and do not reshape `Loop.handle`,
`save_runtime` or `PRIVATE_ENVIRONMENT` beyond what you need. Package 53. OS-BASE B3's power coordinator: block
inhibitors, "close your apps first", the lid, the battery, `request_power`. A mod-side `prepare_stop`, and
anything under `mod/`. The owner tools and the `aresos` command. A shutdown button in the hub.

**CI timing (the lead, 2026-11-19):** the R28 release cut has CI first from Thu 2026-11-19 12:00 until `linux-aresos` says it is through. Start the `check_build=build` run only after that; until then, run the `checks_only=true` run alone and say in PROGRESS.md that the check build waits.

## The owner's answer (board #379, 2026-11-19)

Asked: "Shutdown saves your world first: a few seconds normally, at most 60 s if the game hangs. If a save could not
be confirmed, the next start shows one window and waits for you. OK?" He answered: "Yes but no visible 60s shutdown
lag. Let's put a black screen and do it in the background? Because once I press shutdown I close the lid and leave
right away". So, on top of the recommendations above, which he accepted:
- **No visible wait at shutdown.** The moment a shutdown starts, every screen goes black: turn the outputs off, or
  cover them with a plain black surface, whichever is reliable in the VM. No text, no progress. The save and the stop
  run behind it, and the machine powers off by itself when they are done or the budget runs out.
- **Closing the lid must not stop the save.** While the stop routine runs, it holds a logind block on the lid switch
  and on sleep (`handle-lid-switch:sleep`, mode `block`), so a lid closed right after pressing shutdown does not
  suspend the laptop mid-save. It releases the block when it ends. Test in the VM: a lid event during the save does
  not suspend, and the machine still powers off.
- Logout and restart behave the same way (the screen black while it saves), so there is one behaviour to learn.
