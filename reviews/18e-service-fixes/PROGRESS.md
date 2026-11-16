# 18e: Control service fixes: progress and report

Builder: Claude agent, Opus 5.5 (step 1); fix round with the lead's decisions of 2026-11-15 (JUDGMENT-CALLs 2 and 5,
and the proxy's start without the service from 18c's VM run): Claude agent, Opus 5.5. Branch `pkg/18e-service-fixes`, PR #69 (draft until CI is green).
A Claude builder can't create `REPORT.md`: this file is the report.

## Fix round 1 (2026-11-16, Claude agent on Opus 5.5)

From `REVIEW-1.md` (CHANGES-NEEDED, findings 1 to 7), `SECURITY-REVIEW-1.md` (SAFE; known limits 1 to 4 and the
hardening note) and the lead's items 9 and 10 (from #58's security review, F1 and K2). Tests are in
`control/tests/test_service_fixes.py` unless named otherwise; line numbers are at commit `6094865e`.

**Merge.** `origin/main` merged (`2e131f54`). One conflict, `control/aresos_control/engine.py`'s module constants
(`NOTICE_RETRY` against `LOCKED_PENDING`/`LOCKED_NOTICES` from `b04c7e77`): both kept. Re-checked: `next_deadline()`
returns `None` while `store.locked` (`engine.py:260`), as `_expire()` and `flush_notices()` do; the lock is lifted only
by `Store` at `storage.py:942`, inside the `control_restore_confirm` request, and `serve()` runs `expire()` and works
out the next deadline again at the top of the pass after every request. Main's Repo privacy pattern
(`.github/workflows/repo-privacy.yml`) run over the merged tree and over this round's added lines: no match.

| Finding | Outcome | What changed | Pinned by |
|---|---|---|---|
| R1 #1, security hardening note: idle loop spins on a failing expiry | fixed | `daemon.py:29`, `:158-159`: a deadline already due when the loop sleeps waits `OVERDUE_RETRY` (0.1 s, the old cadence), never 0; a future one still wakes 5 ms after it. `engine.py:252-266`: while notices are deferred, a reservation expiring sooner than the 1 s retry wakes the loop at its own time; one already overdue (it failed with the notices' write) is tried again with them, each second | `test_an_expiry_that_keeps_failing_never_spins` (`ValueError` and `sqlite3.OperationalError` from the expiry write: five passes 0.1 s apart, still reserved, then expired once the write works; old code: five 0.0 s), `test_only_a_deadline_already_due_waits_the_floor`, `test_deferred_notices_never_delay_an_earlier_reservation` |
| R1 #2: a re-parented proxy marks the subreaper | fixed | `usage.py:51` `parent()`; `proxy.py:226-230` reads it once when `serve()` starts; `usage.py:148-167` `mark(session)` marks only while `os.getppid()` is that pid and its start time is unchanged, else raises `ParentChanged`; `proxy.py:203-218` `note_use` logs one warning line ("AresOS tools: session not marked, …") and marks nothing | `test_the_proxy_marks_only_while_its_parent_is_the_same_process` (fake `/proc`: re-parented to pid 7, one log record, no folder made; same pid with another start time refused; the real parent marked) |
| R1 #3, security known limit 1: the walk passes the session's own Claude Code | fixed (lead's decision) | `usage.py:30` `SHELLS`, `:130-145` `_session`: the session is the hook's nearest ancestor whose process name isn't a shell; only its mark counts. Four levels and never PID 1 stay the outer bounds | `test_a_nested_claude_is_a_session_of_its_own` (B's hook doesn't find A's mark or use up A's `.told`), `test_a_wrapper_that_isnt_a_shell_hides_the_mark`, `test_four_levels_and_never_pid_1`, `test_unmarked_sessions_stay_quiet`; boundary: `test_interactive.ProcessChains.test_the_session_is_the_nearest_process_that_isnt_a_shell` |
| R1 #4: a new use doesn't re-arm the notice | fixed | `usage.py:162-166`: `mark()` also unlinks `<key>.told` (a missing one is fine; any other failure raises after the mark is made, and `note_use` swallows it) | `test_a_new_use_re_arms_the_notice` |
| R1 #5, security known limit 3: every connect failure is `service_unavailable` | fixed | `protocol.py:20-23`, `:53-71` `NotConnected` (was `ServiceUnavailable`): `ENOENT`/`ECONNREFUSED` → `service_unavailable` (retried 3 s, "not running … Try again later"); `EAGAIN`/`ETIMEDOUT`/a connect timeout → `service_busy` ("busy … Try again later", not retried); anything else (`EACCES`, `ENOTDIR`, `ELOOP`, …) → `setup_error` ("could not connect to their service (<reason>): their setup looks wrong. Nothing was sent; tell the owner.", no "try again"). `proxy.py:31-34`: the fallback catalogue only for `service_unavailable`. `hooks.py:27-32`, `:82-83`: the Stop notice is the constant `NOT_RUNNING` for `service_unavailable` and the constant `NOT_REACHED` ("AresOS tools could not be reached. …", same advice) for the other three codes and `transport_error` | `test_a_broken_setup_is_not_retried_and_says_so_without_try_again` (real `ENOTDIR`, `ELOOP`, and `EACCES` when not root), `test_a_busy_service_is_not_retried_and_says_try_again_later` (a real full listen queue gives `EAGAIN`; a `TimeoutError`), `test_stop_hook_is_quiet_unless_used` (each cause gives its constant) |
| R1 #6, security known limit 4: a saved file reported as "nothing was sent" | fixed | `proxy.py:134-144` `report_saved` (shared by `file_save` and `mail_attachment_save`, which both repeated the same lines): a `NotConnected` on the `saved` report returns `data.saved` with the constant `SAVED_UNREPORTED` ("The file was saved (see data.saved), but the AresOS tool service could not be reached to record that. Don't save it again.") | `FixRoundProxy.test_a_file_saved_before_the_service_stopped_keeps_its_path` (both tools; the file is on disk, the result keeps its path, no "nothing was sent", no "Try again") |
| Security known limit 2: a FIFO at a mark or `.told` name blocks | fixed | `usage.py:108-117` `_create`: `O_NONBLOCK`, then anything that isn't a regular file is refused. `proxy.py:209-211`: `names_operation` runs inside `note_use`'s `try` | `test_a_fifo_at_a_mark_or_told_name_never_blocks` (real FIFOs in a temp folder, each call in a thread with a 2 s limit: `mark`, `note_use`, `used`, `notice`; with a reader on the FIFO the open succeeds and it is still refused) |
| R1 #7: tests that didn't test | fixed | exact expiry with two reservations (`store.get('op:' + id)['expires']`, the later-made one expiring first); `ProcessChains` moved above `__main__` (`test_interactive.py:200`); `process_chain.py:76-97` asserts each Stop **and** UserPromptSubmit hook's session (by `usage`'s rule) is an MCP server's parent, and that prompt chains were recorded; `call_tool` → `note_use` | `test_next_deadline_is_none_idle_and_the_earliest_open_reservation_otherwise`; `ProcessChains` (4 tests; running the file directly now runs 13 tests, before 9); `FixRoundProxy.test_call_tool_marks_the_session_read_at_start` (`serve()` with stand-in SDK modules: the parent read at start is marked once, for the operation-naming result only) |
| Lead's item 9 (#58 F1): pending reminders reach every session | fixed | `hooks.py:59-61`: a session without a mark (as `usage.used()`) returns before connecting: no reminder, no notice, no connection. `hooks.py:34-35`, `:48`: the Stop reason ends with the constant `REMINDER` " Don't complete, cancel, resend or acknowledge this work on your own: tell the owner what is waiting, and let him decide." (was "Resolve, cancel reserved work, or report uncertain outcomes to the owner before ending.") | `test_an_unmarked_session_never_hears_of_pending_work` (both hooks, `Client` never made), `test_a_marked_session_still_gets_the_reminder_in_the_new_words` (wording pinned), `test_the_hooks_follow_the_real_marks` (real `usage` on a fake `/proc`). Integration (CI, root): `/run/user/<owner>` made in `setUp`; the MCP test asserts the real proxy marked its parent (the test process) before its hook blocks; `mark_session()` for the hook tests that prepare over the socket (`test_integration.py`, `test_owner_state_channels.py`) |
| Lead's item 10 (#58 K2): `permission_denied` blocks every turn | fixed | `hooks.py:68-70`: `permission_denied` from the status call means nothing for this session: no output, both hooks | `test_permission_denied_means_nothing_for_this_session` |

Tests changed beyond the new ones (no assertion weakened): `test_ingress_bounds` (two hook tests) and the existing
hook tests in `test_service_fixes` now say their session used the tools (`usage.used` patched to `True`), since only
such a session reads pending work; `test_four_levels_and_never_pid_1`, `test_unmarked_sessions_stay_quiet` and
`test_unreadable_marks_or_processes_count_as_marked` use shells between the hook and its session, as the new rule
needs; the old "other connect errors" test became the `setup_error` test.

**How the Claude Code process is identified.** Structurally, not by name: the hook's session is the first process
from the hook's parent up whose name (`/proc/<pid>/stat` field 2) is not in `SHELLS` (`sh`, `bash`, `dash`, `zsh`,
`ksh`, `mksh`, `fish`, `busybox`, `env`), within four levels, never PID 1. Run 43680998223 recorded the chains this
relies on, in all 17 cases: Stop `python3 ← sh ← claude`, UserPromptSubmit `python3 ← sh ← sh ← claude` (the managed
prompt command's own `/bin/sh -c` and its `$(…)` subshell), MCP server `python3 ← claude`. On Fedora, bash as `sh`
execs a single command, so the hook's parent can be Claude Code itself; that works the same. The boundary pin now
fails if anything but shells stands between Claude Code and either hook. Checked on the laptop against the real
process tree as well (scratch probe: a child marks its parent; a hook under `sh -c` and under `$(…)` finds it; a
non-shell process in between is its own, unmarked session).

**JUDGMENT-CALLs (fix round 1).**
1. **Three connect codes, not two.** The lead's list names "not listening" (`service_unavailable`) and setup errors
   (`EACCES`, `ENOTDIR`, `ELOOP`, "setup looks wrong", no try again). A full queue (`EAGAIN`) or a connect timeout is
   neither: the service runs and is busy, so "setup looks wrong" would be false and "try again later" is the right
   advice. It gets its own code, `service_busy`. Like `setup_error` it stops a proxy at start (the fallback catalogue
   is for `service_unavailable` only, as the lead said); a busy service's 10 s read timeout already stopped a proxy at
   start before (`transport_error`). The hook treats both as unreachable ("could not be reached", once per outage,
   quiet unless used). This replaces the first round's JUDGMENT-CALL 1.
2. **A setup error is quiet unless used, too.** `setup_error` joins `UNREACHABLE` in the hook, so only a marked session
   hears "could not be reached" (once per outage). Otherwise a broken setup would block every turn of every session,
   which "quiet unless used" ended.
3. **A wrapper is the safer reading.** A process other than a shell between Claude Code and a hook (a `timeout`,
   `nice`, any wrapper that doesn't exec) is taken as the session: it has no mark, so the hook stays quiet and gives no
   reminder. None is in the managed commands today (the boundary pin would fail first). The mark side is not walked:
   the proxy marks its direct parent, which the managed launch (`env` execs) makes Claude Code; a non-exec wrapper
   there would mark the wrapper, and that session would stay quiet.
4. **`acknowledge` in the reminder.** The lead's wording names complete, cancel and resend; #58's finding was also
   about acknowledging outcome notices the owner never saw, so the constant says "complete, cancel, resend or
   acknowledge".
5. **The gate goes before the connection.** An unmarked session's hooks don't connect at all (the lead: "gets nothing
   and costs nothing"). A marked session's hooks behave as before, including `reached()`. Marks that can't be read
   still count as marked, so the reminders show then, as before the gate.

**Known limits that remain.**
1. **Per session, not per operation** (lead's item 9 d). The service doesn't record which session made an operation:
   requests on `act.sock` carry the owner's uid and nothing about the session. So a session that used the tools also
   gets reminders and notices about other sessions' work, with the new wording telling it to leave that work to the
   owner. Scoping would need a session identity sent with every request and kept in the operation record.
2. **`/clear` keeps the mark.** It starts a new conversation in the same Claude Code process, so the new conversation
   inherits the old one's mark (and its reminders and notice). The process is all the hooks can see.
3. **`--resume` / `--continue` start unmarked.** A conversation continued in a new Claude Code process is a new
   session: until it uses the tools again, it gets no reminders of the work its earlier process prepared. That work
   still expires in the service; the owner sees it with `aresos control pending`.
4. **A session that used only reads** (or nothing of ours) is never told about an outage or pending work, by design
   (brief item 6).
5. **The process name is the process's own.** A process of the owner can name itself `sh`, or plant or remove marks:
   the accepted level of CONTROL.md section 7 (it could call the service directly). A wrong name only adds or removes
   an informational notice or reminder.

**For 18c's next VM pass**, in addition to the list below: check 2's notice text is unchanged for a stopped service
("AresOS tools are not running. …"). Item 9's VM check (an unmarked session with another session's pending work: no
reminder, model requests 2) goes to #58's fix round, per the lead.

**Local checks** (laptop, `PYTHONPATH=.:tests python3 -m unittest …` in `control/`): `test_service_fixes` 50 tests,
49 OK; the one error is `test_an_mcp_session_started_without_the_service_gets_its_tools` (no MCP SDK on the laptop).
`test_unit` 2 OK, `test_review22_protocol` 6 OK, `chrome_tests.test_unit` 1 OK, `chrome_tests.test_restore_lock` 5 OK,
`mail_tests.test_review26_results` 8 OK, `generate.py --check` OK. `test_ingress_bounds` 8, 7 OK: the error is its real
MCP binary case (no SDK). `test_files` 12, 11 OK; `test_strict_json` 5, 3 OK; `test_operations` 17, all 18 failures
(subtests) `boundary_not_installed`: these need `/etc/claude-code` (environment, as before). `control/boundary`:
`python3 -m unittest test_native test_interactive` 24 OK (as the image build runs them); `python3 test_interactive.py`
13 OK. `test_integration` and `test_owner_state_channels` need root: CI only.

**CI.** Which job runs the boundary's offline tests: the Control boundary workflow's image build
(`control/boundary/Dockerfile:15`, `python3 -m unittest -v test_native test_interactive`); run 43680998223's log shows
the three `ProcessChains` tests passing there. So no workflow change was needed. Runs on this round: see "Runs (fix
round 1)" below.

## Done

All six items, in the brief's order (item 6's process-chain check first).

| Item | What the code does now | Files |
|---|---|---|
| 6, check | The interactive boundary suite records, per case, the process chain of the testapp MCP server and of every managed hook (pid, start time, command), and asserts that each Stop hook has the MCP server's parent among its four nearest ancestors. Kept as a real test: item 6 depends on it, and a Claude Code update could break it silently. | `control/boundary/process_chain.py` (new), `interactive_suite.py`, `mcp-fixture.py`, `notification-fixture.py`, `test_interactive.py` |
| 1 | `Client.connect` tries a failing connect (`ENOENT`, `ECONNREFUSED`) again for up to 3 s in 0.1 s steps, a fresh socket each time (MCP proxies and CLI; the hooks make one attempt with `Client(…, connect_wait=0)`, lead's decision). Then, or on any other connect failure, it raises `ServiceUnavailable`, code **`service_unavailable`**: "The AresOS tool service is not running; nothing was sent. Try again later." (other errors: "could not be reached (<reason>); nothing was sent ..."). A connection lost after connecting keeps `UnknownRequest` / `transport_error`. The proxy returns `service_unavailable` without its follow-up pending read (it would wait 3 s again). | `protocol.py`, `proxy.py` |
| 2 | `aresos admin …` with a non-root effective uid answers `permission_denied` "Admin commands need sudo: run sudo aresos admin <app> <action> (same options)." before any socket or password prompt. | `cli.py` |
| 3 | `serve()` selects with `Daemon.timeout(refresh_at)`: the Chrome maintenance time (60 s, also the longest sleep), `Engine.next_deadline()` (earliest open reservation's `expires`, or now + 1 s while deferred owner notices wait to be written; `None` when nothing is timed), and 0.1 s only while a loosening Chrome confirmation waits. A deadline that can't be read gives 1 s. 5 ms margin so it wakes after a wall-clock deadline, not before. | `daemon.py`, `engine.py` |
| 4 | `[Unit]` gains one comment line, `StartLimitIntervalSec=30` and `StartLimitBurst=5`: with `RestartSec=2` the sixth start (refused) comes within about 15 s; one crash still restarts. | `packaging/aresos-toold.service`, `tests/test_unit.py` |
| 5 | The refusal is built from the policy's folders, relative to the home, sorted: "Path is outside the allowed folders; choose ~/Documents or ~/Downloads." | `files.py` |
| 6 | `usage.py` (new). The MCP proxy's `note_use` calls `usage.mark()` before a result that names an operation reaches the session: a non-read action whose `data` holds an `operation_id` or `approval` key, or an `unknown` outcome. The mark is `/run/user/<uid>/aresos-control/used/<ppid>-<start>` (folders 0700, file 0600, every step `O_NOFOLLOW`, owner and mode checked). The Stop hook, on `service_unavailable` or `transport_error`, calls `usage.notice()`, which looks as `usage.used()` does: walks its ancestors from its parent, four levels, never PID 1; a mark (or anything unreadable) blocks once with "AresOS tools are not running. If you prepared or sent something with them in this session, its outcome is unknown: tell the owner, and don't repeat it."; no mark prints nothing, exit 0. Once per outage (lead's decision): `usage.notice()` gives the notice only while the session's `<pid>-<start>.told` (beside the mark, 0600, `O_NOFOLLOW`) is missing and creates it; a hook that reaches the service calls `usage.reached()`, which removes it. `stop_hook_active` still guards (checked before anything is recorded); `UserPromptSubmit` stays silent on failure. | `usage.py`, `proxy.py`, `hooks.py` |

| 7 (lead, from 18c's VM run) | A proxy started while the service is down no longer dies: `Proxy.tools()` asks the service as before (with the 3 s wait) and, on `service_unavailable` only, offers its own `tools_for(app)` (a JSON copy, the same owner-only filter). Calls then answer `service_unavailable` until the service is up; the service still checks every call. A catalogue the service returns wins; any other failure still stops the proxy. | `proxy.py` |

Docs: `control/README.md` ("Process and request contract": start-up gap, proxy start without the service, admin hint, idle loop, start limit; "Caller
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
| see the PR | all six control workflows | 7fc97459 | green (lead) |
| 43679206934 / 43679206942 / 43679206919 / 43679206932 / 43679206924 / 43679206941 | all six control workflows | 023fd050 (hooks connect once; one notice per outage) | superseded by the next push (Chrome polkit had passed) |
| see the PR | all six control workflows | fix round with item 7 | reported to the lead at hand-off |

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
- **run** (fix round, laptop, `PYTHONPATH=control:control/tests python3 -m unittest control.tests.test_service_fixes`):
  32 tests OK. New: the hooks (both events, a missing socket and a stale one) end in under 0.5 s with the real client
  and the 3 s default in place, while the proxy still waits; `connect_wait=0` makes one attempt (no sleep); one
  notice per outage at the `usage` level and through `hooks.main` (first stop tells, later stops and a lost connection
  stay quiet, a reply to `Stop` or `UserPromptSubmit` re-arms it, the continuation guard records nothing), a `.told`
  file that can't be written or read still tells, a link or folder at its name is never followed, unreadable marks
  tell at every stop. Against the previous `hooks.py` the hook timing test measures 3.0 s (fails).
- **run** (item 7, laptop, with the locked SDK installed into a scratch folder by `pip --target` as CI does, nothing
  system-wide): `test_service_fixes` 35 tests OK, `test_ingress_bounds` 8 OK (its MCP stdio case included),
  `generate.py --check` OK. New: the proxy with no service lists `tools_for('testapp')` (no owner-only tool), a call
  answers `service_unavailable`, a service that appears then gets the next call; a served catalogue wins (owner-only
  entries still filtered), other failures still raise; and a real MCP stdio session (the SDK server, `proxy.main`)
  started with no service initializes, lists the tools, gets `service_unavailable`, then reaches a service that
  appeared. Against the previous `proxy.py` the MCP case fails ("Raw MCP proxy exited"). `test_approval_questions`
  fails 5 cases on the laptop, the same 5 on 7fc97459 (environment).

## For 18c's next VM pass (under systemd): assertions to hand on

1. **Check 6, never used:** a session that only reads (or calls nothing of ours); `systemctl stop aresos-toold`; one
   turn: no text of ours on screen, model requests 2 (no extra, no Stop continuation), hook exit 0 with empty stdout.
   His own Stop hook runs once, on the first attempt.
2. **Check 6, used:** a session that calls a preparing tool (`testapp_prepare_send` or `mail_prepare_send`, result with
   an approval): `/run/user/<uid>/aresos-control/used/<claude pid>-<start>` exists (file 0600, both folders 0700, owner
   `<uid>`; `<start>` = field 22 of `/proc/<claude pid>/stat`). Stop the service; one turn: exactly one "Stop hook
   error: AresOS tools are not running. If you prepared or sent something …" and one extra model request (the
   continuation), never "operation_status" or "Service connection lost". After logout the mark (and any `.told`) is
   gone. Precondition: `/run/user/<uid>` must exist (a real login
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
9. **One notice per outage:** in the used session of check 2, with the service still stopped, two or three more turns:
   no further notice and no extra model request (`/run/user/<uid>/aresos-control/used/<claude pid>-<start>.told`
   exists, empty, 0600). Then `systemctl start aresos-toold` and one turn (its hooks reach the service; the `.told` file
   is gone), `systemctl stop aresos-toold` and one turn: exactly one notice again.
10. **Hooks don't wait:** with the service stopped, each `UserPromptSubmit` and `Stop` hook of a session ends at once
   (well under a second, not the CLI's 3 s; time `launch.py hook Stop` with the managed command and an input).
11. **A session started with the service down gets the tools:** `systemctl stop aresos-toold`; start a new Claude
   Code session (its MCP servers start and stay up, `/mcp` lists them connected); a tool call answers
   `service_unavailable`; `systemctl start aresos-toold`; in the same session, without a restart, a tool call (say
   `testapp_list`) succeeds.

## JUDGMENT-CALLs

1. **Error code `service_unavailable`.** Matches the hooks' existing `service_unavailable` pending flag. *Superseded
   in fix round 1 (review 1 #5, the lead): other connect failures now get `service_busy` or `setup_error`.*
2. **Hooks connect once (lead's decision, 2026-11-15).** The builder had let the 3 s wait reach the hooks (the brief
   says every caller), so every prompt and turn end waited about 3 s while the service was down. The lead decided the
   hooks make one attempt: `Client(path, connect_wait=0)` (one parameter, no second code path; `None` keeps
   `CONNECT_WAIT`). The 3 s wait stays for the MCP proxies and the CLI, which cover the seconds after boot. Accepted:
   a hook during the start-up gap sees "not running" (a marked session then gets the notice once, and the next hook
   that reaches the service re-arms it).
3. **MCP instructions unchanged.** `COMMON_INSTRUCTIONS` doesn't mention `service_unavailable`: changing it changes the
   generated instruction files and 18c's pins of them. The message says what to do ("Try again later").
4. **What marks a session:** a non-read action whose result `data` names an `operation_id` or `approval`, or an
   `unknown` outcome. Reads never mark (also `operation_status`, `control_pending`), and other sessions' work in
   `pending` doesn't either. A missing marks folder is a clear "no" (otherwise every unused session would get the
   notice); any other read error counts as marked. A mark that can't be written is skipped: that session then stays
   quiet; the tool result still names its operation.
5. **One notice per outage (lead's decision, 2026-11-15).** The builder had given the notice at every turn end. Now
   `Stop`, giving it, writes `<pid>-<start>.told` beside the session's mark (same folder, 0600, `O_NOFOLLOW`); while it
   exists later stops stay quiet. The next hook that reaches the service (any reply, `Stop` or `UserPromptSubmit`)
   removes it, so a later outage notices again. A `.told` file that can't be written still notices (better twice than
   never); one that can't be read, or isn't a plain file, counts as not given; marks that can't be read notice at every
   stop (no session key to record). A `.told` file that can't be removed (not seen in practice: the folder is private)
   would keep that session's next outage quiet.
6. **Start limit 30 s / 5 starts,** with one comment line in the unit. The owner's manual `systemctl start` after a
   start-limit failure needs `systemctl reset-failed` first (README says so).
7. **Idle loop:** 60 s (the existing maintenance period) is the longest sleep, so a suspend or clock change delays a
   wall-clock expiry by at most a minute; submission checks the expiry itself. Deferred notices retry every second.
   Retention's day-long limits run on the periodic passes. SIGTERM wakes the sleep through a pipe (`Daemon.stop()`).

## PLAN-GAPs

1. The interactive container can't run the real managed hooks (stand-in, no service): covered by the real `usage`
   code in the stand-ins plus unit tests; the full path is for 18c's VM.
2. The brief's "one clear notice" vs "block once": the lead decided once per outage (JUDGMENT-CALL 5).

## Left, in order

1. CI on the final commit: all six control workflows green, especially base (the SIGTERM fix; idle ≤ 1/s) and
   Chrome's latency gate (item 3 touches the loop that serves Chrome; the 525 ms hold must stay). If the latency
   gate moves: stop and report (brief).
2. Then mark PR #69 ready; the fresh review; the lead hands section "For 18c's next VM pass" to 18c.
3. The last step deletes this file after the lead has committed its text as the report.

What the code doesn't show: the wake-up pipe exists only because the loop now sleeps long (SIGTERM ignored for up to
a minute otherwise); `Engine.next_deadline` must stay cheap (it runs before every select); the boundary suite's
`process_chain.py` is a kept pin, not a diagnostic.
