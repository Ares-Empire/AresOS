# 18e: Control service fixes: progress and report

Builder: Claude agent, Opus 5.5 (step 1). Branch `pkg/18e-service-fixes`, PR #69 (draft until CI is green).
A Claude builder can't create `REPORT.md`: this file is the report.

## Done

All six items, in the brief's order (item 6's process-chain check first).

| Item | What the code does now | Files |
|---|---|---|
| 6, check | The interactive boundary suite records, per case, the process chain of the testapp MCP server and of every managed hook (pid, start time, command), and asserts that each Stop hook has the MCP server's parent among its four nearest ancestors. Kept as a real test: item 6 depends on it, and a Claude Code update could break it silently. | `control/boundary/process_chain.py` (new), `interactive_suite.py`, `mcp-fixture.py`, `notification-fixture.py`, `test_interactive.py` |
| 1 | `Client.connect` tries a failing connect (`ENOENT`, `ECONNREFUSED`) again for up to 3 s in 0.1 s steps, a fresh socket each time. Then, or on any other connect failure, it raises `ServiceUnavailable`, code **`service_unavailable`**: "The AresOS tool service is not running; nothing was sent. Try again later." (other errors: "could not be reached (<reason>); nothing was sent ..."). A connection lost after connecting keeps `UnknownRequest` / `transport_error`. The proxy returns `service_unavailable` without its follow-up pending read (it would wait 3 s again). | `protocol.py`, `proxy.py` |
| 2 | `aresos admin …` with a non-root effective uid answers `permission_denied` "Admin commands need sudo: run sudo aresos admin <app> <action> (same options)." before any socket or password prompt. | `cli.py` |
| 3 | `serve()` selects with `Daemon.timeout(refresh_at)`: the Chrome maintenance time (60 s, also the longest sleep), `Engine.next_deadline()` (earliest open reservation's `expires`, or now + 1 s while deferred owner notices wait to be written; `None` when nothing is timed), and 0.1 s only while a loosening Chrome confirmation waits. A deadline that can't be read gives 1 s. 5 ms margin so it wakes after a wall-clock deadline, not before. | `daemon.py`, `engine.py` |
| 4 | `[Unit]` gains one comment line, `StartLimitIntervalSec=30` and `StartLimitBurst=5`: with `RestartSec=2` the sixth start (refused) comes within about 15 s; one crash still restarts. | `packaging/aresos-toold.service`, `tests/test_unit.py` |
| 5 | The refusal is built from the policy's folders, relative to the home, sorted: "Path is outside the allowed folders; choose ~/Documents or ~/Downloads." | `files.py` |
| 6 | `usage.py` (new). The MCP proxy's `note_use` calls `usage.mark()` before a result that names an operation reaches the session: a non-read action whose `data` holds an `operation_id` or `approval` key, or an `unknown` outcome. The mark is `/run/user/<uid>/aresos-control/used/<ppid>-<start>` (folders 0700, file 0600, every step `O_NOFOLLOW`, owner and mode checked). The Stop hook, on `service_unavailable` or `transport_error`, calls `usage.used()`: walks its ancestors from its parent, four levels, never PID 1; a mark (or anything unreadable) blocks once with "AresOS tools are not running. If you prepared or sent something with them in this session, its outcome is unknown: tell the owner, and don't repeat it."; no mark prints nothing, exit 0. `stop_hook_active` still guards; `UserPromptSubmit` and the service-up path are unchanged. | `usage.py`, `proxy.py`, `hooks.py` |

Docs: `control/README.md` ("Process and request contract": start-up gap, admin hint, idle loop, start limit; "Caller
file policy": the refusal; "Hooks": quiet unless used). `KNOWN-LIMITS.md`: there is only
`reviews/20-chrome/KNOWN-LIMITS.md`, and none of its limits change.

Tests changed beyond the new ones (no assertion weakened):
- `test_review22_protocol.py`: the 30 s timeout pin now checks the socket the client creates
  (`factory.return_value.settimeout`), since each connect try uses a fresh socket; the timeout policy it pins is the same.
- `chrome_tests/test_unit.py`: the second byte-for-byte pin of the unit gains the same three `[Unit]` lines.
- `test_strict_json.py`: the admin-input case patches `geteuid` to 0, so it tests input parsing on any runner (CI runs as root).

## Item 6: the process chains (read/run: boundary run 43668437092, Claude Code 2.1.319)

Case `normal-yes` (`terminal/interactive/normal-yes/process-chains.json`), pid / ppid / start / command:

```
MCP server:  43  24  12305  /usr/bin/python3 -I /opt/aresos-control/mcp-fixture.py testapp
             24  22  12258  /usr/local/bin/claude --permission-mode default INTERACTIVE_OWNER_TURN_1
             22  21  12258  sh -c /usr/local/bin/claude ...                   (tmux's shell)
             21   1  12257  tmux -S /tmp/claude/interactive.sock new-session ...
Stop hook:   94  93  12448  /usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py hook Stop
             93  24  12448  /bin/sh -c /usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S .../launch.py hook Stop
             24  22  12258  /usr/local/bin/claude ...                          (the same process: pid 24, start 12258)
```

The MCP server's parent is Claude Code itself; the Stop hook runs under `/bin/sh -c` (dash keeps the shell), so Claude
Code is its level 2. The same in all 17 cases, both permission modes and the DAA cases' second process
(`INTERACTIVE_CASE_PASS` lines, `process_chains`). The real proxy starts as `/usr/bin/env -i … python3 …`; `env`
execs, so its parent is the same. The hook command line is the real managed one (only `launch.py` is the stand-in).

**Real managed hooks in the container: not possible.** The boundary image installs the hook stand-in and no service
(B1's design). Instead the stand-ins run the real `usage` code: the MCP stand-in calls `usage.mark()` on each tool
call (as `note_use` does for an operation), the hook stand-in records `usage.used()` from its place in the real
process tree, and each case asserts that a Stop hook finds a mark exactly when a tool call arrived (quiet in the
denied cases). Result: see "Runs". The whole hook path (`hooks.main` → client → unreachable → notice or silence) is
unit-tested with fakes; under the real systemd it is 18c's VM pass.

## Idle numbers (item 3)

Measured as 18c change 14: voluntary + nonvoluntary context switches of all the service's threads over 60 s, idle, in
the base CI container (`test_integration.Integration.test_idle_service_wakes_at_most_once_a_second`, asserts ≤ 1/s).

| | Run | Switches in 60 s | Per second | Threads |
|---|---|---|---|---|
| Before (0.1 s loop; items 1, 2, 4, 5 in) | 43668906122 | 597 | 9.95 | 1 |
| After (deadline loop) | 43669664617 | 1 | 0.02 | 1 |

## Runs

| Run | Workflow | Commit | Result |
|---|---|---|---|
| 43668437092 | Control boundary (dispatch) | 05c740cf | green: process chains recorded and pinned, 17 cases |
| 43668906122 | Control base (dispatch) | 0d27e8d2 (before item 3) | failed as expected: idle 9.95/s; also the `test_review22` timeout pin (pin updated in eaf3eaab) |
| 43669664617 | Control base (PR) | 386e14ea | idle 0.02/s; **23 integration tests timed out in tearDown**: SIGTERM no longer woke the minute-long select (PEP 475 restarts it). Fixed: `Daemon.stop()` writes to a wake-up pipe in the selector (checked on the laptop: real SIGTERM ends `serve()` at once) |
| 43669664632 | Control boundary (PR) | 386e14ea | **green**: chains pinned, and the real `usage` code under Claude Code: `stop_used` true exactly in the 7 cases with a tool call; DAA `[true, true, false]` (its new session, denied, stays quiet) |
| 43670639975 / 43670639979 / 43670639991 / 43670640000 / 43670639999 | base / boundary / Mail / Chrome polkit / Chrome qualification | 4705a4ea | **all green**; base: 339 tests, idle 1 switch in 60 s (0.02/s), "Control base suite PASS" |
| 43670639964 | Control Chrome | 4705a4ea | **latency (plain) and latency (audit) green** (gate unchanged); fixtures and python-shards (0) failed only on `chrome_tests/test_unit.py`, a second copy of the unit pin I had missed. Updated in the next commit |
| see the PR | all six control workflows | final commit | running at hand-off; the lead checks them |

Lesson for the next step: every push to the PR, even of this file, restarts all six control workflows (the
`pull_request` path filter looks at the whole PR diff) and cancels the running ones.

## Verified

- **run** (laptop, `PYTHONPATH=.. python3 -m unittest …` in `control/tests`): `test_service_fixes` 25 tests OK
  (items 1, 2, 3, 6), `test_files.Files.test_outside_refusal…` OK, `test_unit` 2 OK, `test_review22_protocol` OK,
  `test_strict_json.StrictJSON` OK; `control/boundary`: `test_interactive.ProcessChains` 3 OK. The new tests fail on
  today's code (the modules or names they import don't exist, the texts and the unit differ, the idle loop measures
  9.95/s in run 43668906122).
- **run**: the laptop's other failures in `test_strict_json`, `test_ingress_bounds`, `test_boundary_exact`,
  `test_review_fixes_16` are the same set on the base commit 75cdbb41 (no `/etc/claude-code`, not root); CI runs
  them as root in the container.
- **read**: 18c PROGRESS "Findings for the lead" 2a/2b/2c and "Check 6 in numbers" (`origin/pkg/18c-image`).

## For 18c's next VM pass (under systemd): assertions to hand on

1. **Check 6, never used:** a session that only reads (or calls nothing of ours); `systemctl stop aresos-toold`; one
   turn: no text of ours on screen, model requests 2 (no extra, no Stop continuation), hook exit 0 with empty stdout.
   His own Stop hook runs once, on the first attempt.
2. **Check 6, used:** a session that calls a preparing tool (`testapp_prepare_send` or `mail_prepare_send`, result with
   an approval): `/run/user/<uid>/aresos-control/used/<claude pid>-<start>` exists (file 0600, both folders 0700, owner
   `<uid>`; `<start>` = field 22 of `/proc/<claude pid>/stat`). Stop the service; one turn: exactly one "Stop hook
   error: AresOS tools are not running. If you prepared or sent something …" and one extra model request (the
   continuation), never "operation_status" or "Service connection lost". It repeats once per turn while the service is
   down (see JUDGMENT-CALL 5). After logout the mark is gone. Precondition: `/run/user/<uid>` must exist (a real login
   or lingering); without it no mark can be written and the session stays quiet.
3. **Start-up gap:** `systemctl restart aresos-toold; aresos control pending` at once: `ok: true` (no
   `transport_error`). With the service stopped: `error.code == "service_unavailable"`, message contains "not running"
   and "nothing was sent", after about 3 s.
4. **Failed state without `Restart=no`:** drop-in `ExecStartPre=/usr/bin/false` only; within 20 s of `systemctl
   start`: `ActiveState=failed`, `Result=start-limit-hit` (or `exit-code` on the last start), `NRestarts` ≤ 5; then
   `systemctl reset-failed` before the next check.
5. **Admin hint:** as the owner, `aresos admin control log`: exit 1, `error.code == "permission_denied"`, message
   "Admin commands need sudo: run sudo aresos admin control log (same options).", no password prompt.
6. **Refusal:** the outside-folder refusal reads "choose ~/Documents or ~/Downloads." (no Desktop).
7. **Idle:** change 14 over 60 s: at most 60 switches (expect a handful), 1 thread.
8. The unit pin in 18c's image check needs the three new `[Unit]` lines (comment, `StartLimitIntervalSec=30`,
   `StartLimitBurst=5`) when 18c merges main.

## JUDGMENT-CALLs

1. **Error code `service_unavailable`.** Matches the hooks' existing `service_unavailable` pending flag. Connect
   failures that are not retried (permission, a path under a file, a connect timeout) get the same code with "could not
   be reached (<reason>); nothing was sent": nothing was sent there either. Rejected: a second code for those.
2. **The 3 s wait reaches the hooks too** (the brief says every caller). While the service is down, every prompt
   (`UserPromptSubmit`) and every turn end (`Stop`) waits about 3 s before going quiet. Rejected for now: hooks without
   the wait (a one-line change: a `connect_wait` for the hook's client), which would make a start-up-gap Stop look
   like "not running". The owner may prefer quick prompts while the service is broken.
3. **MCP instructions unchanged.** `COMMON_INSTRUCTIONS` doesn't mention `service_unavailable`: changing it changes the
   generated instruction files and 18c's pins of them. The message says what to do ("Try again later").
4. **What marks a session:** a non-read action whose result `data` names an `operation_id` or `approval`, or an
   `unknown` outcome. Reads never mark (also `operation_status`, `control_pending`), and other sessions' work in
   `pending` doesn't either. A missing marks folder is a clear "no" (otherwise every unused session would get the
   notice); any other read error counts as marked. A mark that can't be written is skipped: that session then stays
   quiet; the tool result still names its operation.
5. **Notice once per turn, not once per session.** While the service is down a marked session gets the notice at
   every turn end (blocked once per turn by `stop_hook_active`). Once per session would need a second file ("told").
6. **Start limit 30 s / 5 starts,** with one comment line in the unit. The owner's manual `systemctl start` after a
   start-limit failure needs `systemctl reset-failed` first (README says so).
7. **Idle loop:** 60 s (the existing maintenance period) is the longest sleep, so a suspend or clock change delays a
   wall-clock expiry by at most a minute; submission checks the expiry itself. Deferred notices retry every second.
   Retention's day-long limits run on the periodic passes. SIGTERM wakes the sleep through a pipe (`Daemon.stop()`).

## PLAN-GAPs

1. The interactive container can't run the real managed hooks (stand-in, no service): covered by the real `usage`
   code in the stand-ins plus unit tests; the full path is for 18c's VM.
2. The brief's "one clear notice" vs "block once": built as once per turn (JUDGMENT-CALL 5).

## Left, in order

1. CI on the final commit: all six control workflows green, especially base (the SIGTERM fix; idle ≤ 1/s) and
   Chrome's latency gate (item 3 touches the loop that serves Chrome; the 525 ms hold must stay). If the latency
   gate moves: stop and report (brief).
2. Then mark PR #69 ready; the fresh review; the lead hands section "For 18c's next VM pass" to 18c.
3. The last step deletes this file after the lead has committed its text as the report.

What the code doesn't show: the wake-up pipe exists only because the loop now sleeps long (SIGTERM ignored for up to
a minute otherwise); `Engine.next_deadline` must stay cheap (it runs before every select); the boundary suite's
`process_chain.py` is a kept pin, not a diagnostic.
