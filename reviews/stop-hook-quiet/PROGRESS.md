# Stop hook: never exit 2, quiet unless used (progress)

Branch `fix/stop-hook-quiet`, off `main` at `a46ffe44`. Builder: Claude agent (Opus), for the lead (linux-tools).

## Why

Control's managed hooks run in every Claude Code session on the laptop. Claude Code reads a `Stop` hook's exit code 2
as "don't stop" (stderr goes to Claude) and any other non-zero exit as a visible hook error. Before this change:

- `hooks.main` read and validated the event *before* asking `usage.used()`, and every exception ended in
  `raise SystemExit(2)`. A hook bug, a changed event shape or a bad install blocked the stop of every session once per
  turn end, including sessions that never used the tools (against the owner's #254, "quiet unless used").
- The managed `Stop` command ran Python bare, so `launch.py`'s own errors (`protected()`, configuration, arguments) came
  out as exit 1, and `python3` itself exits 2 when it can't open `launch.py`.

## What changed

1. **`control/aresos_control/hooks.py`.** `main` asks `usage.used()` first, before reading or parsing anything. It reads
   only the process tree and the marks. A session that never used the tools gets nothing and never connects. Its input
   isn't parsed, so nothing in it and no failure on it can reach the session. The input is still read to the end
   (`read_input`), so Claude Code's pipe never breaks. That also holds past the 6 MiB bound: a used session keeps the
   first `WIRE_LIMIT + 1` bytes and drops the rest. If `usage.used()` raises, the hook is quiet (why: below). In a
   session that used the tools, a failure is now a JSON decision, `{"decision":"block","reason":"AresOS hook failed;
   inspect pending work before continuing: …"}` with exit 0 (`failed()`, plain `json`). It is not given again while
   `stop_hook_active` is true. The process never exits 2. Held work, the outage notice and the prompt hook are unchanged.
2. **`control/aresos_control/boundary_policy.py`.** One template, `hook_command(event, variable)`, now builds both managed
   commands, so `Stop` gets the prompt hook's shell guard:
   `/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /bin/sh -c 'if decision=$(/usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py hook Stop 2>/dev/null); then printf "%s" "$decision"; fi; exit 0'`,
   timeout 15. The `UserPromptSubmit` command is byte-for-byte unchanged (checked). Regenerated `managed-hooks.json` and
   `managed-settings.draft.json`; `generate.py --check` passes.
3. **Docs.** `control/README.md` (Hooks: the order, the guard, the failure decision, what an unparseable input does),
   `control/settings/managed-settings.draft.comments.md` (the `hooks.Stop` row), `control/boundary/README.md` (the hook
   stand-in and the held-work cases), and a comment in `control/launch.py`. `docs/design/CONTROL.md` doesn't describe
   exit codes or the command. Under `control/` and `docs/`, the grep for `hook Stop|SystemExit(2)|exit code 2|exit 2`
   now finds only the generated command and unrelated `os/` scripts.

**Why quiet when `usage.used()` raises.** `used()` already counts marks or processes it can't read as a mark, so only a
bug in it can raise, and that bug would hit every session the same way. Blocking every session's stop for our own bug
is exactly what #254 rules out. Quiet costs little. The held work stays in the service, every tool result still
carries `pending` (a session that uses the tools again sees it at its next call), `aresos control pending` lists it,
and it expires without running. So quiet loses at most one turn-end reminder, in a session that did use the tools.

## Tests

New file `control/tests/test_stop_hook.py`:
- `ManagedCommand`: the generated `Stop` and `UserPromptSubmit` commands, run through `/bin/sh -c` as Claude Code runs
  them, with a stand-in launcher path. The command exits 0 with no stdout and no stderr when the launcher is missing,
  exits 1 (after printing a decision), exits 2 (with or without a decision), crashes, prints 16 KiB of binary garbage
  to stderr, or is killed. A launcher that succeeds is passed on exactly: its JSON, its argv `hook <event>`, and the
  whole stdin, 1 MiB included. The `Stop` command string and timeout are pinned.
- `Hook` (`hooks.main`): a session that never used the tools, or whose `usage.used()` raises, gets no output, no
  stderr and no `SystemExit`, the client is never called, and the input is read to the end. Checked for invalid JSON,
  not an object, the wrong event, a wrong type, a repeated field, an oversized input (6 MiB + 70 KB), a raising
  client, a client that can't be built and an unexpected reply, for both events. A used session gets exactly one JSON
  line `{"decision":"block","reason":"AresOS hook failed; …"}` for each of those, and nothing for the ones that parse
  when `stop_hook_active` is true. `UserPromptSubmit` stays quiet. The held-work reason is pinned word for word (brief
  18c's VM test in #58 looks for it), with `{}` under `stop_hook_active`. The outage notice is unchanged. Unused
  sessions hear neither.

Updated, where they pinned exit 2: `test_ingress_bounds` (raw bounds, schema types, the continuation guard) and
`test_strict_json` (repeated fields) now patch a used session and expect the JSON decision. In `test_integration` (CI
only, root), the malformed-input test is now unmarked = quiet and marked = decision, always exit 0 and empty stderr. New:
`test_stop_hook_installation_failures_are_quiet`. A marked session with held work hears of it; with bad configuration,
a `protected()` refusal or a missing launcher it gets `(0, "", "")`; afterwards it hears again.

Boundary suite (CI only, real Claude Code 2.1.319). Before this change no interactive case blocked a stop: the hook
stand-in always printed `{}`. Now `notification-fixture.py` runs the real `hooks.main` behind the real managed command,
with a stand-in service that answers `control_pending` from `/home/assistant/held-work.json`, and it logs each `Stop`
output in order. The supervisor holds work for two cases:
- `normal-yes` (the send ran, so the session used the tools). The first stop is blocked once with the held-work
  decision. The model's single continuation carries the operation id. The continuation's stop prints `{}`.
- `normal-no` (never used). Every stop is quiet and there is no continuation.

`check_held_stops` is unit-tested in `test_interactive.HeldStops`, which the Dockerfile build runs. The process-chain
pin (`process_chain.check`) now also covers `Stop`'s new chain under the guard (the prompt hook's shape).

### Mutations (each undone afterwards; `git status` clean)

| Mutation | Result |
|---|---|
| M1 `Stop` command back to bare Python | killed (10 failures) |
| M2 guard without `2>/dev/null` | killed (11) |
| M3 guard prints the launcher's stdout even on failure | killed (5) |
| M4b the old order: usage asked only after parsing | killed (15) |
| M5 the old failure path: stderr + `SystemExit(2)` | killed (2 failures, 29 errors) |
| M6 an exception from `usage.used()` not caught | killed (18) |
| M7 an exception from `usage.used()` counts as used | killed (10) |
| M8 no drain past the bound | killed (5) |
| M9 an unused session doesn't read its input | killed (36) |
| M10 the failure path ignores `stop_hook_active` | killed (7) |
| M11 the held-work reason text changed | killed (1) |
| M12 a used session's failure stays quiet | killed (31) |
| M13 the held-stop check skips the continuation's stop | killed (2) |
| M14 the held-stop check accepts `{}` from an unused session | killed (1) |

A script applied each mutation alone, ran the tests named for it and restored the file from git. M4 (the old gate
added after parsing while the new one stays) survived as an equivalent mutant: the early gate still decides.

### Local results (laptop, Python 3.14, not root, no `/etc/claude-code`)

- `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions".
- `test_stop_hook` (6), `test_ingress_bounds`, `test_strict_json`, `test_service_fixes`, `test_slim_policy`,
  `test_unit`, `test_policy_sources`: 90 tests. The only failures are the same 10 that fail on `main` here (no
  `/etc/claude-code`, no vendor MCP binary, not root). Checked by running the same set on `a46ffe44`.
- `control/boundary`: `test_interactive` (14) and `test_native` (11) pass.
- I scanned the modules the stand-in now imports (the hooks chain) for syntax newer than the boundary image's Python
  3.11 (PEP 701 f-strings): none found.
- Not run here: `test_integration`, `test_owner_state_channels` (root and an installed launcher) and the boundary
  container suites. CI runs them.

## CI

Round 0, on `829ec9a3`:
- Control base, run 43889464942: success. 377 tests, with `test_stop_hook` and the four hook cases of
  `test_integration`, including `test_stop_hook_installation_failures_are_quiet`.
- Control boundary, run 43889464982: success, real Claude Code 2.1.319 under dash.
  - `normal-yes`: `held_stops` is the held-work block, then `{}`, with one continuation.
  - `normal-no`: `[""]`, no continuation.
  - Both hooks' chains are now `python3 <- sh <- sh <- claude`, so Claude Code sits at level 3 of the walk's 4.
- Repo privacy, run 43889464924: success.
- Control Mail 43889465120, Control Chrome 43889465068 and Chrome qualification 43889465011 hadn't finished when fix
  round 1 was pushed. No job had failed: Mail 9 of 12 done, Chrome 5 of 26, qualification 8 of 31, its
  `native-precedence` (the boundary image with the new stand-in) among the passed ones.

Fix round 1: see below.

## JUDGMENT-CALLs for the lead (round 0; the lead's answers are in fix round 1)

1. **`usage.used()` still counts unreadable marks or processes as used.** That was 18e's reviewed choice, kept here.
   When marks can't be read, every session, including ones that never used the tools, hears of held work once per
   stop and of an outage once per outage. Those are deliberate JSON decisions, not failures, but it is a case where
   an unused session is affected. "Whatever fails" would argue for quiet there too: a one-line flip in `used()` (and
   `notice()`), the README and two or three tests. My advice: flip it in a small follow-up if you agree. Not done
   here, because it reverses a reviewed decision outside this brief.
2. **Input that can't be parsed, in a used session, blocks every stop.** With no `stop_hook_active` to read, it blocks
   up to Claude Code's own limit, as the README already said for exit 2. Only a changed Claude Code input format or a
   final message over 6 MiB gets there, and the latter's continuation is short and parses, which ends it. Kept.
3. **A broken installation is now silent at `Stop` in every session**, including ones that used the tools. Before, it
   was a visible exit-1 hook error. This is the brief's decision 3. It still shows: the MCP proxies fail and the
   `aresos` CLI refuses.
4. **The interactive boundary suite's hook stand-in now runs the real hook code.** That goes beyond "make sure a case
   still shows": no case did before. It is the only end-to-end proof that Claude Code 2.1.319 honours a JSON block
   through the new guard. Cost: `normal-yes` gets one more model round trip.

## Fix round 1 (review 1, Fable: SAFE; the lead took both should-fixes into this PR)

`REVIEW-1.md` is committed unchanged (`21a0944a`); the fixes are in `edde349d`.

1. **Should-fix 1 (my JC2): input the strict decoder refuses no longer blocks every stop.** The review's input carries
   an escaped lone surrogate in `background_tasks`, a field the hook never reads, and it stays the same across turns.
   Claude Code's cap of 8 blocked stops starts again after each tool call, so before this fix the block was unbounded.
   Now `hooks.first_stop(event, raw)` gives the failure block only when the input readably says `stop_hook_active` is
   false. It reads the strictly parsed event, or else the same bytes parsed leniently for that one field
   (`json.loads` of `raw.decode('utf-8-sig', errors='replace')`). True, missing, not a boolean, or unreadable even
   leniently (input cut at the 6 MiB bound, truncated JSON, not an object): quiet. Held work and the outage notice are
   unchanged.
2. **Should-fix 2 (my JC1), the lead's decision reversing 18e.** `usage.used()` and `usage.notice()` count a marks
   folder or process they can't read as **unmarked**, so every session stays quiet when usage can't be read. Why, in
   the lead's words: these hooks run in every session on the laptop, the owner's rule #254 is quiet unless used, and
   the flip costs only a missed reminder in a used session while its marks are broken. Held work stays held, and shows
   at the next tool call and in the CLI. A `.told` file that can't be written or read still tells: the session's mark
   was read, so it is known to have used the tools. Recorded in `usage.py`'s docstring, the README (marks paragraph
   and a new known limit), and `hooks.py`'s comment on a raising `used()`.
3. **Nits.**
   - The stale sentences are fixed: `usage.py`'s docstring and the README now say both managed commands add a shell.
     The README's "pipe never breaks" now says it holds while the hook's code runs (review note 4c).
   - The CI placeholder above is filled.
   - Each of the review's four surviving mutations now has a test. `test_input_that_cannot_be_read_is_quiet` covers
     an unused session's read that raises. The `oversized by whitespace` case covers a valid object padded past
     6 MiB, which is still refused and never read as a request. `test_the_failure_reason_is_bounded_and_shows_hidden_characters`
     covers `shortened` and `visible`.

Tests changed:
- `test_stop_hook.Hook.failures` carries a `told` expectation for each case. It has new cases for the review's lone
  surrogate, invalid UTF-8, `stop_hook_active` missing or not a boolean, and oversized by whitespace. Every case is
  quiet under `stop_hook_active: true`.
- `test_ingress_bounds` (raw bounds, schema types, guard) and `test_strict_json` now put `"stop_hook_active":false`
  in their inputs where they expect the block.
  - The raw-bounds `bytes` case (cut at the bound) is quiet.
  - Its `depth` case (1200 levels) may go either way, because lenient parsing depends on Python's recursion limit:
    3.14 reads it.
- `test_integration.test_malformed_hook_input_gives_explicit_failure_feedback` adds the review's surrogate input,
  once with false (told) and once with true (quiet).
- `test_service_fixes`:
  - `test_unreadable_marks_or_processes_count_as_unmarked`, `test_unreadable_marks_never_tell_and_record_nothing`
    (both renamed);
  - the link and FIFO tests now expect `False`.

Mutations, round 1 (same method; `git status` clean afterwards):

| Mutation | Result |
|---|---|
| R1 no lenient read: unparsed input blocks (round 0's rule) | killed (20) |
| R2 input unreadable even leniently blocks | killed (4) |
| R3 a missing `stop_hook_active` counts as false | killed (2) |
| R4 lenient decode without `errors='replace'` | killed (1) |
| R5 lenient decode keeps a BOM | killed (1) |
| R6 `used()`: an unreadable session counts as used (18e) | killed (2) |
| R7 `used()`: an unreadable folder counts as used (18e) | killed (2) |
| R8 `notice()`: an unreadable session tells (18e) | killed (2) |
| R9 `notice()`: an unreadable folder tells (18e) | killed (1) |
| N1 (review) no `try` around an unused session's read | killed (4) |
| N2 (review) `read(WIRE_LIMIT)` instead of `+ 1` | killed (2) |
| N3 (review) failure reason not `shortened` | killed (1) |
| N4 (review) failure reason not `visible` | killed (1) |

Local, round 1: `generate.py --check` passes. Running `test_stop_hook` (8), `test_ingress_bounds`, `test_strict_json`,
`test_service_fixes`, `test_slim_policy`, `test_unit`, `test_policy_sources` and `test_operations` gives 109 tests. The
failures are main's environmental set here (no `/etc/claude-code`, vendor or root). The boundary
`test_interactive` (14) and `test_native` (11) pass.

CI, round 1, on `962d5abe`:
- Control base, run 43896881674: success.
- Control boundary, run 43896881526: success, `CONTROL_INTERACTIVE_ASK_PASS cases=17`.
- Repo privacy, run 43896881565: success.
- Control Mail 43896881336, Control Chrome 43896881453 and Chrome qualification 43896881196 were still queued, or had
  passed only their first jobs, when the recheck fix below was pushed. No job had failed. I cancelled round 0's Chrome
  and qualification runs once round 1 superseded them, so the new ones weren't queued behind them.

## Recheck 1 (Fable: SAFE, one test-only should-fix)

The recheck is appended to `REVIEW-1.md` and committed unchanged (`211131d0`). The tests are in the next commit.
- **Should-fix: the link test now tells a followed read from a refused one.** Since the flip, a read that followed
  the link into an empty folder gave the same "unused" as a refused read. `test_a_link_where_the_folder_should_be_is_never_followed`
  now plants this session's valid mark where each link leads (`elsewhere/used/20-500`, then `elsewhere/20-500`), and
  expects `used()` and `notice()` to be false. It then shows that the same mark in the real folder is found.
  Mutation L1 (reads open the folders without `O_NOFOLLOW`, writes keep it): killed.
- **Nit 1:** `stop_hook_active` 0 and `null` are now failure cases that must stay quiet. F1 (`== False`) is killed,
  and so is F2 (present and falsy).
- **Nit 2:** new `test_a_link_where_the_mark_should_be_is_no_mark`, a link at this session's mark name to another
  session's real mark. L2 (`_plain` following links) is killed.
- **Nit 3:** the "less one" above is gone. **Nit 4:** the PR description now gives round 1's rules. **Nit 5:** the
  README's known limit says which damage silences every session and which silences one; its last sentence names the
  held work.
- Local: `test_stop_hook` (8) and `test_service_fixes.QuietUnlessUsed` (27) pass.

CI on the recheck commit: run IDs in the report to the lead.
