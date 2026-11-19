# Package 25, the guardian: progress

Updated after **step 1** (2026-11-19). Builder: a Claude agent on Fable 5.2, one fresh agent per step.
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

## Left, in order

2. Section 2, with 3.3's `stop` to drive it.
3. 3.2 and 3.3: the signal wake-up, labwc, `restart`, `logout`, the windows' texts.
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

## What the code does not show

- **For step 2: where a save's callback runs.** `done(SaveResult)` can run inside `conclude()` (a launch's end closes
  the channel first, before the accounting is saved), inside `tick()` (a deadline), or before `request_save()`
  returns (`no_channel`). It must only note the result. Start, stop or account for a launch from `pending()`.
- **For step 2: the mod's reconnect backoff** (0.5 s doubling to 10 s; it starts over only after a connection that
  held 10 s). After a supervisor restart the adopted game's hello can be up to 10 s away, so `no_channel` is normal
  for a replacement supervisor's first seconds. The wrapper reports `jvm_started` long before the mod loads, so in
  the real game the first hello is normally accepted; the stand-in game connects earlier and shows the refused-then-
  accepted path.
- **A planned SIGTERM is still a crash.** Nothing of section 2 exists: a game ended by SIGTERM (143) is counted and
  restarted after the backoff, `Loop.close()` still waits without a limit, and signals are still noticed late.
- **`desktop.json` has no new keys yet**, so the test through R28's frozen key list is step 2's.
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
