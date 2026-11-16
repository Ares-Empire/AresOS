# 18e review 1

Reviewer: fresh Claude agent (not the builder), Opus 5.5, 2026-11-16. Head `13e9e1e4`, range `c746075d...13e9e1e4`
(PR #69). Ran locally (laptop, no containers):
- `PYTHONPATH=control:control/tests python3 -m unittest control.tests.test_service_fixes`: 35 tests, 34 OK. The one
  error is `test_an_mcp_session_started_without_the_service_gets_its_tools`, because `mcp_types` isn't installed
  on the laptop. CI installs the SDK.
- `control.tests.test_unit`, `control.tests.test_review22_protocol`,
  `control.tests.test_files.Files.test_outside_refusal_names_the_configured_folders_in_a_stable_order` and
  `control.chrome_tests.test_unit`: 10 OK. In `control/boundary`, `test_interactive.ProcessChains`: 3 OK.
- A scratch probe outside the repo (finding 1): `Daemon.serve()` with a reservation past its expiry, whose expiry
  write raises.
- `git merge-tree c746075d HEAD origin/main` (the old three-argument form, which only prints) to look for the
  clash with `b04c7e77`.
CI: I took the lead's word that it is green on `13e9e1e4` and didn't re-query it.

## What was checked

- The brief, `AGENTS.md`, `PROGRESS.md` and the whole diff.
- Items 1 to 6, and the proxy's start without the service (item 7).
- `Client.connect`/`connection`. A retry happens only before a byte is sent, and a lost connection still gives
  `UnknownRequest`/`transport_error`. No request can be sent twice.
- The admin hint. `argparse` keeps `--input` out of the echoed words.
- The refusal text. The roots are guaranteed to be under the home.
- The unit's start limit: the sixth failing start comes at about 10 s, and one crash still restarts.
- The deadline loop against `_expire`, `flush_notices`, `Store.write`'s fence, Chrome maintenance and the
  confirmation poll. The wake-up pipe and SIGTERM.
- `usage.py`: `O_NOFOLLOW` at every step, owner and mode checks, the start-time key, fail-closed reads.
- The `.told` life cycle.
- The real launch chains (`settings/user-mcp.json`: `env` execs, so the proxy's parent is Claude Code;
  `managed-hooks.json`).
- The fallback catalogue: it is the same `tools_for(app)` the service returns, and the owner-only filter runs
  twice. The tests, and whether they exercise their claims.

**Clash with `b04c7e77` (restore lock):** none hidden.
- The merge has one textual conflict in `engine.py`: the module constants (`NOTICE_RETRY` and
  `LOCKED_PENDING`/`LOCKED_NOTICES`). Keep both.
- `next_deadline()` returns `None` while `store.locked`, the same as `_expire()` and `flush_notices()`.
- PR #80 changes only how pending and notices are shown under the lock, not when the lock is set or lifted.
- The lift (`control_restore_confirm`) is a request, so the loop works out the next deadline again right after it.

## Findings

1. **should-fix: the deadline loop busy-spins when an expiry keeps failing**
   (`control/aresos_control/daemon.py:150-159`, `engine.py:224-235`).
   - What happens: `_expire()` raises before the write fence on a reservation past its expiry, with an error that
     isn't a storage refusal (a `ValueError` from `json_value`, `sqlite3.OperationalError` "database is locked", a
     malformed op). The reservation stays `reserved`. `write_failed` stays false, and no notice is deferred.
     `next_deadline()` then returns a time in the past, so `timeout()` returns `0.0` on every pass. The loop spins
     at full CPU and logs "Background maintenance failed" once per pass, until a restart. The same error comes back
     after the restart.
   - Probe:
     - With a `ValueError` and with `sqlite3.OperationalError`: 200 passes in 0.017 s, every select timeout `0.0`.
     - With `Refused('storage_limit')`: a 1.005 s cadence, because the deferred notice turns into the 1 s retry.
     - The old loop kept such failures at 10 passes a second.
   - Fix: never sleep less than a floor (the old 0.1 s) for a deadline that is already due when `timeout()` runs.
     Or note in `serve()` that `expire()` raised, and wait `UNKNOWN_DEADLINE` then. Add a test where the expiry
     write raises: no two `0.0` timeouts in a row.
   - Minor, same place: while deferred notices exist, `next_deadline()` returns `now + 1` even when a reservation
     expires sooner. That can mark it `failed` up to 1 s late (submission still checks expiry itself). Fix: take
     the `min` of the two.

2. **should-fix: a proxy left without its Claude Code process marks the subreaper, and every session there counts
   as used** (`control/aresos_control/usage.py:119-128`, `proxy.py:192-201` and `:227`).
   - What happens: `mark()` reads `os.getppid()` when the result arrives. If Claude Code dies without signalling
     its MCP children (OOM kill, crash, SIGKILL) while an operation-naming call is in flight, the SDK lets the call
     finish after stdin closes. The proxy has been re-parented by then, to `systemd --user` (a child subreaper) in a
     desktop login. `note_use` then marks that process.
   - Why it matters: a Claude Code session in a terminal tab or in tmux has `systemd --user` within four levels,
     because Fedora's `sh -c` execs its single command, so the hook's parent is Claude Code. From then until
     logout, every such session counts as used and gets the notice at the next outage. That is the opposite of
     "quiet unless used", and nothing shows it.
   - Fix: record the parent's pid and start time once, when `serve()` starts. In `note_use`, mark that identity,
     and skip the mark when `os.getppid()` has changed (the session is gone). Add a unit test with a changed ppid.

3. **nit: the ancestor walk doesn't stop at the session's own Claude Code** (`usage.py:106-116`).
   - What happens: a Claude Code started from another session's Bash tool (`claude -p …`) has the parent session
     within four levels. If the parent is marked, the child that never used the tools gets the notice. Its `.told`
     is then written under the parent's key, so the parent, which did use them, stays quiet for that outage.
   - This follows the brief's "up to four levels". It is a gap in the plan, for the lead to decide.
   - Options: document it, or stop the walk at the first ancestor whose comm/exe is Claude Code.

4. **nit: new use doesn't re-arm the notice** (`usage.py:119-128`).
   - Only a hook that reaches the service removes `.told`. Example: a turn whose `UserPromptSubmit` fell in an
     outage, then prepared or sent through the proxy once the service was back, then hit a second outage before
     `Stop`. That turn stays quiet.
   - Fix: `mark()` also unlinks `<key>.told`, so a new operation re-arms it.

5. **nit: every connect failure becomes `service_unavailable`, including a configuration error**
   (`protocol.py:79`, `proxy.py:22-29`).
   - What happens: EACCES, ENOTDIR and connect timeouts get "…could not be reached (<reason>)… Try again later".
     The proxy then starts on its fallback catalogue instead of failing visibly. A marked session's `Stop` says
     "AresOS tools are not running". A permission or path problem looks like a passing outage.
   - The same notice also follows a 10 s read timeout on a busy service (`transport_error`). That one is as the
     brief asks.
   - Fix: fall back to the own catalogue, and say "try again later", only for `NOT_LISTENING`. Keep failing at
     start for other errors.

6. **nit: "nothing was sent" after a step already reached the service** (`proxy.py:65`, `:117` with `:124-128`).
   - What happens: in `file_save` and `mail attachment_save`, the service can stop between the download (file
     already written by `files.save`) and the `saved` report. The tool result then says "nothing was sent. Try
     again later." and drops `saved`. The `unknown` branch keeps it.
   - Fix: after an earlier step of the same call has reached the service, keep `saved` in the result and use a
     message that says what was done.

7. **nit: tests that don't test what they say.**
   - `control/tests/test_service_fixes.py:295`: the store has no `operation` attribute, so the exact
     `deadline == expires` check never runs. With only one reservation, "earliest" isn't exercised either. Use
     `store.get('op:' + id)['expires']` and two reservations.
   - `control/boundary/test_interactive.py:204`: `ProcessChains` comes after `if __name__ == '__main__':
     unittest.main()`, so running the file directly skips it, and no CI job runs this file. Move the main block to
     the end.
   - `process_chain.check` records `UserPromptSubmit` chains but doesn't assert them, though `reached()` relies on
     them. Under dash the chain is exactly four levels.
   - The `note_use` call inside `call_tool` is covered only by reading the code.

CHANGES-NEEDED
