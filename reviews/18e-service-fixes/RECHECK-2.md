# 18e recheck 2 (fix round 1)

Reviewer: fresh Claude agent (not the builder, the fix-round builder or the first reviewers), Opus 5.5, 2026-11-16.
Package and security together. Head `6d645b19` (PR #69); fix round `3f39e3c7..6d645b19`, read without main's own
changes except where they meet this branch (merge `2e131f54`, restore lock `b04c7e77`).

Ran on the laptop (no containers, nothing written to the worktree but ignored caches):
- `control/`: `PYTHONPATH=.:tests:<locked MCP SDK in a scratch folder> python3 -m unittest tests.test_service_fixes
  tests.test_ingress_bounds`: 58 OK (the MCP stdio cases included). `tests.test_unit tests.test_review22_protocol
  chrome_tests.test_unit`, `chrome_tests.test_restore_lock`, `mail_tests.test_review26_results`: all OK.
  `generate.py --check`: match.
- `control/boundary`: `python3 -m unittest test_interactive.ProcessChains` 4 OK; `python3 test_interactive.py` 13 OK.
- 16 mutations on a scratch copy of `control/` (list below).
- Real re-parenting probe: a child reads `usage.parent()`, its parent exits, the child calls `usage.mark()`:
  `ParentChanged`, no file written.
- A probe of the largest approval through `bound_result`: the service refuses an approval over 16 KiB, so a result
  that names an operation always keeps its `data` and marks.

## Findings of round 1: closed?

| Finding | Closed | Checked by |
|---|---|---|
| R1 #1, hardening note: spin on a failing expiry | yes | `daemon.py:158-159` waits 0.1 s for a deadline already due; `engine.py:261-266` takes the earliest of a future reservation and the 1 s notice retry. Mutations `spin` and `notice_delay` fail 4 and 1 tests |
| R1 #2: re-parented proxy marks the subreaper | yes | `proxy.py:226-230` reads the parent once; `usage.py:157-158` refuses a changed ppid or start time. Mutations (no check / pid only) fail; real probe gives `ParentChanged` |
| R1 #3, S KL1: nested `claude -p` takes the parent's notice | yes (lead's decision) | `usage.py:130-145`. Mutation back to "nearest marked ancestor" fails 4 tests; the boundary pin with the old rule fails `test_the_session_is_the_nearest_process_that_isnt_a_shell` |
| R1 #4: new use doesn't re-arm | yes | `usage.py:162-166`; mutation fails `test_a_new_use_re_arms_the_notice` |
| R1 #5, S KL3: every connect failure is "not running" | yes | `protocol.py:53-71`, `hooks.py:27-32`, `:82-83`, `proxy.py:31-34`. Mutations `busy_as_setup`, `reached_text` fail. The proxy-at-start half is unpinned (nit 1) |
| R1 #6, S KL4: saved file said "nothing was sent" | yes | `proxy.py:134-144`; mutation fails both apps |
| S KL2: FIFO blocks | yes | `usage.py:108-116` (`O_NONBLOCK`, then `S_ISREG`); `names_operation` inside the `try` (`proxy.py:209-211`). Mutations `no_nonblock`, `no_isreg`, `names_outside_try` fail |
| R1 #7: tests that didn't test | yes | exact expiry with two reservations; `ProcessChains` above `__main__` (13 run directly); prompt chains asserted (`process_chain.py:85-97`); `call_tool` → `note_use` (`no_note_use` mutation fails) |
| Lead's item 9: usage gate and new wording | yes, as asked | `hooks.py:59-61` returns before any connection; `REMINDER` at `:34-35`, `:48`. Mutation `no_gate` fails 9 tests; integration marks the session where it expects a reminder |
| Lead's item 10: `permission_denied` gives nothing | yes | `hooks.py:68-70`; mutation fails the Stop case (UserPromptSubmit returned on any error before) |

Mutations: 15 of 16 are caught. The one that survives is `fallback_any` (nit 1).

## Judgment calls

1. **Three codes.** Sound. Linux AF_UNIX with a timeout gives `EAGAIN` at once on a full queue, so `service_busy` is
   real and true. A busy service stops a proxy at start, as a busy service's read timeout already did. With
   `listen(16)` that needs 17 waiting connections.
2. **`setup_error` quiet unless used.** Sound. A broken setup shows where it belongs: the proxy fails at start in
   `/mcp`.
3. **The nearest ancestor that isn't a shell is the session; a wrapper hides the mark.** Sound for the chains
   recorded on 2.1.319 (Stop `python3 ← sh ← claude`, prompt `python3 ← sh ← sh ← claude`, MCP `python3 ← claude`).
   Fedora's `/bin/sh` shows as `sh`, and the pin now covers both hooks.
   - The cost: it fails quiet. Before item 9 only outage notices depended on the chain. Now the pending reminders do
     too. A future Claude Code that runs hooks or MCP servers through anything other than a shell silences both, in
     every session, with no sign. The pin sees only the version CI runs, and nothing in the image pins the laptop's
     Claude Code (known limit A).
   - The other reading, "unknown wrapper = marked", would bring back #58 F1's cost for every session. So I agree with
     the choice; it needs a line in the limits list.
4. **"acknowledge" in the reminder.** Sound: #58 F1 named acknowledging notices the owner never saw.
5. **Gate before the connection; unreadable marks count as marked.** Sound.
   - An unmarked session reaches the "unreadable" branch only if a folder's owner or mode is wrong, something other
     than a plain file sits at its key, or `/proc` can't be read. All of these need the owner's own processes to
     tamper; the hook's ancestors are alive while it runs.
   - Then every such session gets the reminders: loud, as before the gate. That is the right side to fail on.

**The gate, asked directly.**
- **Can an unmarked session still be blocked or charged?** Only through JC5's unreadable states, or Stop input that
  isn't valid JSON (exit 2, which comes before the gate and is unchanged). The second doesn't happen with
  Claude Code's own input. `used()` never raises. Otherwise: no connection, no output, exit 0.
- **Can a session that used the tools miss a reminder about its own held work?** Yes, and every case fails quiet.
  Each is bounded by expiry and `aresos control pending`:
  - its mark was never written: no `/run/user/<uid>`, or a parent that couldn't be read at start;
  - `--resume` in a new process (listed);
  - the chain change of JC3 (known limit A);
  - work done in a nested `claude -p` or through the `aresos` CLI from a Bash tool (known limit B).

## New problems the fixes could bring

- **Connect codes and texts.** All three are accurate, and none points at `operation_status`. `strerror` is the only
  variable part. Paths: `ENOENT`/`ECONNREFUSED` → retried, then `service_unavailable`; `EAGAIN` → `service_busy`;
  `EACCES`/`ENOTDIR`/`ELOOP` → `setup_error`. A too-long path has no errno and gives `setup_error (OSError)`, which
  is fine. One new edge: nit 3.
- **Parent check and PID reuse.** Once the parent dies, `getppid()` returns the subreaper, which was alive (an
  ancestor) when the parent was read, so it can't equal the recorded pid. The start-time check covers the rest.
  If the parent dies after the check, the mark goes under the old `<pid>-<start>`, which no new process can match.
  If it dies before `parent()` runs, the proxy's stdin is already at EOF, so no call can arrive to mark anything.
- **`O_NONBLOCK` create.** It has no effect on a regular file. A FIFO gives `ENXIO` without a reader, and is refused
  by `S_ISREG` with one. A folder at the name gives `EISDIR`, a socket `ENXIO`, a link `ELOOP`. In `mark()` each
  ends in `note_use`'s `except`. In `notice()` each gives the notice. Nothing blocks.
- **The restore lock (`b04c7e77`) and the idle loop.**
  - The merge resolution keeps both constant blocks (`engine.py:24-32`).
  - While the lock holds, `next_deadline()` returns `None`, the same as `_expire()`, so the loop sleeps at most until
    maintenance (60 s). Nothing can expire then, and the poll still runs at 0.1 s while a Chrome confirmation waits.
  - The lock is set only when the `Store` opens. It is lifted only inside `control_restore_confirm`, a request, so
    the next pass runs `expire()` first and then works out the deadline fresh.
  - An overdue reservation whose expiry then fails waits 0.1 s, never 0.
  - A side effect of item 9: after a reboot, no session hears `restore_required` from the hooks (known limit C).

## Findings

No blocking findings, and no security **fix** findings.

**Nits (package):**
1. **The start-up rule "fallback catalogue only for `service_unavailable`" is not pinned.**
   - Where: `control/aresos_control/proxy.py:31-34`; the test at `control/tests/test_service_fixes.py:230`.
   - Why: with the check removed (every `NotConnected` gets the fallback), all tests pass. The README and JC1 say
     that a busy service or a setup error stops the proxy at start.
   - Fix: add `NotConnected(BlockingIOError(EAGAIN))` and `NotConnected(PermissionError(EACCES))` to that test's
     "still stop" list.
2. **One integration case now passes vacuously.**
   - Where: `control/tests/test_integration.py:591-594`, the last case of
     `test_prompt_hook_installation_and_service_failures_are_quiet`.
   - Why: that test never marks its session, so with the service stopped the prompt hook returns at the gate.
     "Service down, UserPromptSubmit quiet" is no longer exercised through the real launcher.
   - Fix: call `self.mark_session()` before that case. Optionally add a Stop with the service down, expecting
     exactly the `NOT_RUNNING` notice.
3. **A start-up race can now kill a proxy for a whole session.**
   - Where: `control/aresos_control/daemon.py:58-63` with `UMask=0077`
     (`control/packaging/aresos-toold.service:14`).
   - Why: between `bind()` and `chmod(0o666)` the new `act.sock` is 0700. An owner connect in those microseconds
     gets `EACCES`, which is now `setup_error`: not retried, no fallback catalogue, and the proxy dies at start. In
     the first round it got the fallback. The window is microseconds against 0.1 s retries, so this is rare.
   - Fix (daemon): bind under a temporary name, `chmod`, `listen`, then `rename` into place. That also closes the
     `ECONNREFUSED` window. A `umask(0o111)` around `bind` would do as well.

**Known limits** (security; low harm; each fails quiet or is bounded by expiry). Worth adding to the fix round's
"Known limits that remain" (`reviews/18e-service-fixes/PROGRESS.md`) and the README's Hooks section:

- **A. A Claude Code update can silence every session.** Where: `control/aresos_control/usage.py:130-145`,
  `proxy.py:228`.
  - What happens: if Claude Code puts a process other than a shell between itself and the hooks, or between itself
    and the MCP servers, every session stays quiet: no pending reminders and no outage notices.
  - Why nobody sees it: the boundary pin runs only on the Claude Code version CI uses.
  - Harm: the owner isn't reminded of held work; it still expires.
  - Fix later: re-run the interactive boundary suite whenever the laptop's Claude Code changes version.
- **B. Work started outside the session's own MCP proxies is reminded to nobody.** Where:
  `control/aresos_control/hooks.py:59-61`.
  - What happens: a nested `claude -p` session is its own session, and the `aresos` CLI run from a Bash tool marks
    nothing. Work prepared in either reaches no session's reminders, unless the parent session used the tools
    itself.
  - Before item 9 every session heard of such work.
  - Harm: low; it expires, and `aresos control pending` lists it.
- **C. A restore lock after a reboot reaches no session through the hooks.**
  - What happens: marks live on a tmpfs, so they are gone after a reboot, and nothing marks a session during the
    lock. So no session hears `restore_required` from the hooks.
  - Harm: low. Any tool call's result says `restore_required`, and the instructions say to stop and ask the owner.
- **D. The rest of #58 F1's wording.** Where: `control/aresos_control/definitions.py:52`, `hooks.py:44`.
  - What happens: every tool result carries all sessions' `pending`. The MCP instructions, in every session, still
    say "Every result includes pending items; resolve or report them before finishing". `operation_cancel` and
    `notice_ack` are free.
  - So a session that used any tool, reads included, is still invited to cancel another session's reservation or
    to acknowledge a notice the owner never saw. The per-prompt context says "inspect status" without the new
    `REMINDER`.
  - The gate removed the breadth F1 was about (every session, every turn), so this is low harm.
  - Fix: one sentence ("report them to the owner; don't complete, cancel, resend or acknowledge another session's
    work on your own") and the same `REMINDER` on the prompt context. That changes the generated instruction files
    that 18c pins, so the lead routes it, probably with #58's fix round.

For 18c when it merges this: its VM sessions that expect "AresOS held/unfinished work" must first use a tool (a mark);
an unmarked session now gets nothing (`os/ci/control/actions.py` `REMINDER` on `pkg/18c-image`).

## CI

- `gh pr checks 69`: "no checks reported". The head `6d645b19` is a `[skip ci]` commit, and it and `6c614617`
  change only `PROGRESS.md`. The code head is `6c614617`; its runs:
  - **Green:** Control base (43829438763), Control boundary (43829438766), Control Mail (43829438960), Control Chrome
    polkit (43829438759), Repo privacy (43829438873).
  - **Control Chrome (43829438753), still running:** 22 jobs green, among them `python-shards` 0-3, `package`,
    `native-precedence` and **`latency (audit)`**. `fixtures (policy, word-1)` is running; three are queued,
    **`latency (plain)`** among them.
  - **Control Chrome qualification (43829438758), still running:** 17 green; `qualification-pairs` 2 running, 12
    queued.
  - None has failed so far.
- Item 3 touches the loop that serves Chrome, so `latency (plain)` must still pass before merge. This round changed
  only the overdue branch.

SAFE
