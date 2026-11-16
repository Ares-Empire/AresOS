# Review 1: PR #91, the Stop hook never exits 2; quiet for sessions that never used the tools

Reviewer: a fresh Claude agent on Fable 5.2 (security and package review in one), not the builder. 2026-11-16.
Read-only: nothing in the worktree was changed except this file. Mutations and prototypes ran in a scratch copy.

Range: `a46ffe44..829ec9a3` (`git diff $(git merge-base origin/main HEAD)...HEAD`), branch `fix/stop-hook-quiet`.

Verdict: **SAFE.** Nothing blocking: the generated `Stop` command never ended with exit 2 or an error in any case I
tried (note 4a is Claude Code's own shell failing before the command starts), and no path is worse than on `main`.
Two should-fix findings: both are judgment calls the builder raised (2
and 1), and both exist on `main` today in a wider form. Should-fix 1 stays open as a small fix for a next round, on
this branch or after it; my advice on each is below.

## What I ran

- `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions". The prompt hook's
  generated entry is identical to `a46ffe44` in both JSON files; only the `Stop` command differs, timeout still 15.
- `PYTHONPATH=control:control/tests python3 -m unittest test_stop_hook test_ingress_bounds test_strict_json`: 19 tests,
  16 pass. `test_service_fixes test_slim_policy`: 64 tests, 62 pass. The 5 that fail need `/etc/claude-code` or the
  vendored MCP SDK, and fail the same way on `a46ffe44` (checked in a scratch copy of that commit).
  `control/boundary`: `test_interactive`, 14 pass.
- The generated `Stop` command through `/bin/sh -c` (here bash 5.3.9) with stand-in launchers of my own:
  - launcher missing; exit 1 and exit 2 after a complete decision; partial JSON then a crash; a complete decision and
    then SIGKILL, SIGSEGV, SIGTERM or `os._exit(2)`; a `SystemExit` string; a syntax error; stdout closed by the
    launcher. Each gave exit 0, no stdout, no stderr.
  - a launcher that succeeds: output passed on exactly at 128 KiB, 1.5 MiB (the largest `display_json` gives) and
    6 MiB; backslashes, `%s`, a leading `-n`, quotes, `$HOME`, backticks and `$(id)` unchanged; trailing newlines
    removed, inner ones kept; 8 MiB and empty stdin reach the launcher.
  - a hostile environment for the outer shell (`PATH`, `IFS`, `BASH_ENV`, `ENV`, `PYTHONPATH`, `PYTHONHOME`,
    `PYTHONSTARTUP`, exported functions named `printf`, `env` and `if`, `SHELLOPTS`), a working directory full of
    planted `json.py`/`os.py`/`sitecustomize.py`, a deleted working directory, a closed stdout: nothing of it reached
    the inner command; always exit 0. One exception is note 4a.
- The same command with the worktree's real `hooks.main` and the real `usage` walk behind it (marks under a scratch
  runtime folder, a stand-in socket service):
  - never used (no marks folder, or a folder without this session's mark): 140 runs over a service that holds work,
    answers nonsense, never answers or is down, with a valid input and 15 bad ones (empty, not JSON, cut short, an
    array, another event, renamed fields, wrong type, an escaped lone surrogate, 70 levels deep, a repeated key, `NaN`,
    a 30-digit integer, invalid UTF-8, a BOM, 7 MiB), with `usage.used()` raising and with a config lacking
    `act_socket`. Every run: exit 0, no stdout, no stderr, and the service never saw a connection.
  - used: results under check 2.
- The unmodified generated commands on this laptop, where nothing is installed (so: launcher missing), and the
  worktree's `launch.py` under the guard (`protected()` fails): exit 0, nothing, for both events.
- 16 mutations of my own in a scratch copy: 12 killed, 4 survive (nit 3).
- Claude Code's side, read from the installed 2.1.325 client's bundled source (the pin is 2.1.319; CI covers that
  one): exit 2 blocks, any other non-zero exit is a non-blocking error, a timeout is "cancelled", stdout on exit 0 is
  trimmed and parsed when it starts with `{`, and the cap on consecutive blocked stops is 8
  (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`), counted from zero again after every tool call. This is a reading of bundled
  code, not a run of the client.
- Greps for the old behaviour over `control/`, `os/`, `docs/`, `briefs/` and PR #58's branch (`pkg/18c-image`,
  `69943d65`).
- CI on `829ec9a3` (`gh pr checks 91`):
  - Control base, run 43889464942: success, 377 tests, with `test_stop_hook` (6) and the four hook cases of
    `test_integration`, `test_stop_hook_installation_failures_are_quiet` among them.
  - Control boundary, run 43889464982: success, real Claude Code 2.1.319 under dash. `normal-yes`: the first stop is
    the held-work block, the continuation's stop `{}`, one continuation. `normal-no`: `""`, none. Chains for both
    hooks: `python3 <- sh <- sh <- claude`, so Claude Code sits at level 3 of the 4 the walk allows.
  - Repo privacy: success.
  - Still running when I finished (15:21 UTC), none failed so far: Control Mail (run 43889465120, 6 of 12 jobs
    done), Control Chrome (43889465068, 5 of 26), Chrome qualification (43889465011, 6 of 31). Mail's `containers`
    jobs run the whole base suite again before the mail tests (`control/ci/mail/run.sh:32`); shards 1, 2 and 3 have
    passed, so the hook tests are green there too. These runs are not covered by this review until they finish.

## The five checks

1. **A session that never used the tools.** Launcher missing, `protected()` refusal, unreadable or malformed
   configuration, invalid or oversized stdin, a changed event shape, `usage.used()` raising, a client error: all give
   exit 0 with no output. I found no way to exit 2 or to show an error through the generated command. A timeout is
   Claude Code's "cancelled", never a block, and nothing on this path waits (the service is never contacted). The one
   way such a session is still blocked is should-fix 2: marks that exist but can't be read.
2. **A session that used the tools.**
   - Held work blocks once: the block, then `{}` when `stop_hook_active` is true. The reason text is unchanged:
     `output()` is untouched, my run matched it byte for byte, and `test_stop_hook.py:179-182` pins it. PR #58's check
     6 looks for `AresOS held/unfinished work` and for the "not running" sentence, and times the managed commands
     through `/bin/sh -c` from an unmarked caller expecting exit 0 and empty stdout. All of that holds.
   - The outage notice comes once: block, quiet, quiet; after the service answered once, the next outage tells again;
     never while `stop_hook_active` is true.
   - A failure gives one JSON block and nothing on stderr, and is quiet on the continuation, whenever the input
     parses. It does not hold for input the strict decoder refuses: should-fix 1.
3. **The wrapper.** Quoting is right: the outer shell sees one single-quoted script, and the two interpolated words
   are fixed. `env -i` leaves `PATH` and `LANG` only; every program is named by absolute path and `printf`/`exit` are
   builtins. Output is exact (above). Output of a launcher that ends non-zero is never printed. Timeout 15 unchanged
   and pinned. What a session controls: its stdin (not parsed unless marked, then strict), its own marks (by design),
   and Claude Code's own outer shell (note 4a).
4. **Other dependents of exit 2.** None left. The boundary fixture now runs the real hook code; the Mail and Chrome
   suites never call the hooks; `os/ci/control/` exists only on PR #58's branch and is compatible (check 2);
   `os/tests/test_control_image.py:151` there asserts only that the command contains `launch.py hook `. Docs: nits 1.
5. **Tests.** The claims are exercised: `ManagedCommand` runs the generated string, `Hook` runs `hooks.main`, the
   integration test shows the marked session hearing before and after each quiet failure, and the boundary case would
   time out if the stand-in failed to import. Gaps: nit 3.

## Findings

### Blocking

None.

### Should-fix 1: input the strict decoder refuses blocks every stop of a used session (security: **fix**, small)

`control/aresos_control/hooks.py:129-137`, `control/README.md:380-382`, PROGRESS judgment call 2.

The continuation guard reads `stop_hook_active` only from the strictly parsed event. When the decoder refuses the
input, `event` is `None` and the failure block is printed at every stop.

Steps (run through the generated command, real `hooks.main`): a marked session, the service up, nothing pending. The
input is `{"hook_event_name":"Stop","stop_hook_active":true,"last_assistant_message":"reply 2",
"background_tasks":[{"type":"shell","description":"build \ud83d"}],"session_crons":[]}`: an escaped lone surrogate,
which `common.json_value` refuses, in a field the hook never reads. Four stops in a row, `stop_hook_active` false and
then three times true, with a new `last_assistant_message` each time, each returned
`{"decision":"block","reason":"AresOS hook failed; inspect pending work before continuing: …"}`. The same input
without the surrogate gave `{}` twice.

Why Claude Code's cap doesn't end it: the reason tells Claude to inspect pending work, which is a tool call, and the
count of consecutive blocked stops starts again at zero after every tool call while `stop_hook_active` stays true
(2.1.325; `reviews/hook-input-fields/REVIEW-1.md` finding 3 read the same). So "up to Claude Code's own limit"
(`README.md:382`) is a bound only for a Claude that answers without tools. It ends when Claude stops calling tools
(then 8 more rounds) or the owner interrupts.

What makes it last: content that stays the same across continuations. A lone surrogate in
`background_tasks[].description` or `.command` or in `session_crons[].prompt` (2.1.325's own schema text says each is
cut at 1000 characters; I did not confirm that the cut can split a pair), or a later Claude Code field the decoder
refuses. Not `last_assistant_message`: it changes with each continuation, as the builder says.

On `main` the same loop runs through exit 2 in every session; this PR confines it to sessions that used the tools.
That is why it doesn't block the merge.

Fix: when the strict decoder refused the input, read `stop_hook_active` once more with plain `json.loads` on the kept
bytes, inside a `try`, only to stay quiet when it is `true`. I tried it in a scratch copy: the four stops above give
block, quiet, quiet, quiet; the first stop stays loud; no existing test expectation changes. Add one test with such
an input, and correct `README.md:380-382`. On the earlier decision (hook-input-fields review 1 kept this path loud):
it rested on the cap as the bound. The cap doesn't bind here, and a second, third and fourth identical block tell
Claude nothing new, so I'd bound it.

### Should-fix 2: marks that can't be read count as "used" in every session (security: **known limit**; a follow-up is fine)

`control/aresos_control/usage.py:187-188` (`used`), `:204-205` and `:209-210` (`notice`),
`control/aresos_control/hooks.py:8`, `control/README.md:364-365` and `:375-376`, PROGRESS judgment call 1.

`hooks.main` is quiet when `usage.used()` raises, but `used()` itself answers `True` for anything it can't read, so
that case never raises.

Steps: a marks folder exists (some session used the tools in this login) and has a group or other bit
(`chmod 755 /run/user/<uid>/aresos-control`), or an ancestor's `/proc/<pid>/stat` can't be read, or the open fails for
lack of descriptors. A session that never used the tools then gets the held-work block once per turn end (I ran this
one: folder 0755, unmarked caller, held work, block), the outage notice at every stop while the service is down
(`notice()` answers `True` too), and the failure block on bad input.

It needs a damaged marks folder or exhausted resources: only the proxy creates these folders (0700), and nothing else
in the shipped code uses the path. So it is no reason to hold this PR.

Fix: the builder's advice, which I share: `used()` and `notice()` answer `False` when the marks or the process tree
can't be read, with the README lines and two or three tests. 18e chose "assume a mark" so that an outage isn't hidden
from a session that did send something. This PR's own reasoning for `used()` raising (the work stays held, every tool
result carries it, it expires unrun) holds here just as well, and #254 asks for quiet. Until then, `hooks.py:8`
shouldn't say "whatever fails".

### Nits

1. **Stale sentences.** `control/aresos_control/usage.py:7` and `control/README.md:355` still say that only the
   `UserPromptSubmit` command adds a shell of its own. Both commands do now.
2. **`reviews/stop-hook-quiet/PROGRESS.md:113`:** "CI: (Filled in after the runs.)" is still the placeholder.
3. **Mutations that survive** (none changes what a session sees today):
   - `hooks.py:93-96`, the `try`/`except` around `read_input()` for an unused session removed: all tests pass. The
     shell guard would still make the command quiet; `hooks.main` alone isn't held to it.
   - `hooks.py:70`, `read(WIRE_LIMIT)` instead of `WIRE_LIMIT + 1`: all pass. An input that is a valid object followed
     by whitespace past 6 MiB would then be accepted; no test has an oversized input whose first 6 MiB parse.
   - `hooks.py:78`, `shortened` or `visible` removed from the failure reason: all pass.
4. **Notes, no change asked.**
   a. The outer `/bin/sh -c` is Claude Code's, before `env -i`. With `POSIXLY_CORRECT=1` and an exported function
      named `exit` (`BASH_FUNC_exit%%`) in Claude Code's own environment, bash as `sh` ends with status 2 before the
      command starts ("`exit': is a special builtin"). That holds for any hook command, the old one included, needs
      the owner's own start environment (2.1.325 starts managed hooks without the repository settings' `env`), and no
      command string can prevent it.
   b. In a used session a slow service can take the hook past its 15 s (connect up to 10 s, then a read up to 10 s).
      Claude Code then cancels the hook: shown as cancelled, not a block. As on `main`. A service that accepts and
      never answers took 10.1 s here and gave the "could not be reached" notice.
   c. A failure before the hook's Python code runs leaves stdin unread; "Claude Code's pipe never breaks"
      (`control/README.md:305`) holds for `hooks.main` only. For an input over the pipe's 64 KiB, Claude Code's write then
      fails. As I read 2.1.325 it drops a write error that arrives after the input was queued, and the prompt hook's
      guard has behaved this way since it was added, but I did not run the real client against a missing launcher. If
      it ever shows as a hook error, `else cat >/dev/null` in the guard drains the input.

SAFE

## Recheck of 962d5abe

Reviewer: a fresh Claude agent on Fable 5.2, 2026-11-16: not the builder, and a new context after review 1.
Read-only: nothing in the worktree was changed except this section. Mutations, stand-ins and prototypes ran in
scratch copies of `control/` at `962d5abe`, `829ec9a3` and `a46ffe44`. The test modules also ran in the worktree, as
the lead's command has it; `git status` is clean afterwards.

Range: `829ec9a3..962d5abe`. The fix is `edde349d`; `21a0944a` adds this file and `962d5abe` updates PROGRESS.

Verdict: **SAFE.** Both should-fixes are closed in the code, and I found no input or state that brings either back.
The nits are closed except PROGRESS's CI line for this round. One new should-fix, in a test only: the fix round took
the read side out of the link test (the code is right; I ran it). It is three lines and no reason to hold the merge.

### What I ran

- `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions". The fix round
  touches no generated file, and not `boundary_policy.py`, `launch.py` or `control/boundary/`.
- `PYTHONPATH=control:control/tests python3 -m unittest test_stop_hook test_ingress_bounds test_strict_json`: 21 tests,
  18 pass. `test_service_fixes test_slim_policy`: 64 tests, 62 pass. PROGRESS's eight modules: 109 tests. What fails
  needs `/etc/claude-code`, the vendored MCP SDK or root, and is the same set as for the seven of those modules that
  exist on `a46ffe44` (run in scratch copies of both). `control/boundary`: `test_interactive` and `test_native`, 25 pass.
- The generated `Stop` and `UserPromptSubmit` commands through `/bin/sh -c` (bash 5.3.9, Python 3.14.8), with a
  stand-in launcher of my own behind them: the real `hooks.main`, the real `usage` walk over the real `/proc` with its
  marks under a scratch runtime folder, and the real `Client` against a stand-in socket service. The harness process
  is the session, so its mark is a file named for it.
  - For check 1: 53 inputs, each as four stops in a row (`stop_hook_active` false, then true three times), over a
    service with nothing pending, a service that holds work, and no service: 636 runs.
  - For check 2: 18 kinds of damage to the marks or the process tree, for a session with a mark and for one without
    (another session's mark beside it), over a service that holds work, no service and a service that answers
    nonsense, with a valid `Stop` twice, review 1's input and a prompt: 432 runs.
  - A session with readable marks, and one that never used the tools: about 40 checks of what each hears.
  - The same launcher without the shell guard, 12 runs, to see the exit code and stderr the guard would hide.
  - The unmodified commands on this laptop (nothing installed): exit 0, nothing, for both events.
- A fuzz of `hooks.main` in a session that used the tools, with five service stand-ins: 60,000 damaged copies of a
  continuation's input and 60,000 of a first stop's, from four base inputs (valid, review 1's, raw surrogate bytes,
  the wrong event with `NaN`).
- Mutations in scratch copies: 27 on `962d5abe` (24 killed, 3 survive: two are nit 1, one is note c), and 7 on the
  read side of `usage.py`, each on `829ec9a3` and on `962d5abe` (the should-fix and nit 2).
- CI on `962d5abe` (`gh pr checks 91`, last read at 15:54 UTC):
  - Control base, run 43896881674: success, 379 tests, with `test_stop_hook` (8),
    `test_malformed_hook_input_gives_explicit_failure_feedback` (the surrogate input, told and quiet) and
    `test_stop_hook_installation_failures_are_quiet` among them.
  - Control boundary, run 43896881526: success, real Claude Code 2.1.319. `normal-yes`: the held-work block, then
    `{}`. `normal-no`: `[""]`. Chains `python3 <- sh <- sh <- claude` for both hooks.
  - Repo privacy, run 43896881565: success.
  - Not finished, none failed: Control Mail (43896881336, queued), Control Chrome (43896881453, 5 of 26 jobs done),
    Chrome qualification (43896881196, not started). Mail's `containers` jobs run the base suite once more; the Chrome
    suites never call the hooks. These three are not covered by this recheck until they finish.

### The four checks

1. **Should-fix 1: closed.** `hooks.first_stop` (`hooks.py:76-89`, used at `:149`) gives the failure block only for
   input that says `stop_hook_active` is false, read strictly or, failing that, with plain `json` from the same bytes.
   - Review 1's input: block, quiet, quiet, quiet, in all three service states.
   - No failure block came at a continuation: not in the 636 runs, and not for 60,000 damaged continuation inputs.
     Each of the 8,061 failure blocks in the fuzz came for bytes that plain `json` reads as an object whose
     `stop_hook_active` is `false`.
   - Told at the first stop only: escaped lone surrogates (high, low, in a key), raw surrogate bytes, invalid UTF-8,
     a UTF-8 sequence cut before a quote, `NaN`, `1e400`, a 30-digit integer, 70 and 1200 levels deep (Python 3.14
     reads 1200 leniently), a BOM, repeated fields, 6 MiB + 1 of valid JSON, a valid object padded past 6 MiB with
     spaces, a wrong, unknown or non-string event name.
   - Quiet at every stop: truncated (in a string, right after the flag, before it), a string over 6 MiB with the flag
     before or after it, 6 MiB of leading spaces, an array, an array holding the object, `null`, a number, a string,
     empty, whitespace, a 5000-digit integer, 200,000 levels deep, 3 MiB of `[`, two BOMs, UTF-16, the flag as `0`,
     `1`, a string or `null`, the flag missing or only nested, trailing garbage, two objects, a raw newline or NUL in
     a string, single quotes, a trailing comma, `False`.
   - Every run: exit 0, no stderr. Valid input is unchanged: `{}`; the held-work block, then `{}`; the notice once.
   - Cost of the second read: at most 0.35 s more on 6 MiB, no higher peak memory. The slowest input I found (6 MiB
     of empty objects after a surrogate) took 4.8 s, 4.5 s of it the strict read as on `829ec9a3`; the timeout is 15.
     6 MiB of `[` or of `{"a":` ends cleanly without the guard (exit 0, no stderr).
   - The real client sends the field this guard reads: in the boundary run above, the continuation's stop is `{}`.
2. **Should-fix 2: closed.** `usage.used` (`usage.py:176-193`) and `usage.notice` (`:196-228`) answer no for
   anything they can't read.
   - All 432 runs: exit 0, no stdout, no stderr, and the service never saw a connection. The damage: the marks
     folder 0755, 0770, 0701, 0000, 0300 or 0400; `aresos-control` 0750; `used` or `aresos-control` a link to a
     folder that holds the session's mark; `used` a plain file; the session's mark a folder, a link to another mark, a
     dangling link, a FIFO or a socket; no runtime folder; no descriptor left; a `/proc` without the processes.
     Without the guard, the three I ran that way (0755, no descriptor, the `/proc` without the processes) return
     with exit 0 and an empty stderr: the quiet is a clean return, not a crash the guard hid.
   - A session that never used the tools: I found no path left on which it hears anything. With readable marks and
     another session's mark beside it: quiet for held work, an outage, a nonsense answer, bad input and a prompt; no
     connection; nothing written into the marks folder.
   - A session that used the tools, with readable marks, lost nothing. Held work: the block (it names the operation
     and ends with the owner sentence), `{}` at the continuation, the block again at the next turn end, the context
     on a prompt. An outage: nothing at a continuation and no `.told` written; then the notice once, quiet twice, a
     quiet prompt; after the service answered once, the next outage tells again; a `.told` that can't be written
     tells at every stop. A nonsense answer: the failure block once. `permission_denied`: quiet. With the marks folder
     at 0755 it is quiet, and back at 0700 it hears again.
   - What the reversal costs is recorded truthfully. One addition: nothing mends a damaged folder (the proxy skips a
     mark it can't write, without a sign), so "while its marks are broken" lasts until logout or until someone
     removes the folder.
3. **Nits.**
   - Stale sentences: closed. `usage.py:7` and `control/README.md:356` name both commands, `hooks.py:8`'s "whatever
     fails" now holds, and "the pipe never breaks" is limited to while the hook's code runs. A grep over `control/`
     and `docs/` found no sentence that still states an old rule (unreadable marks as a mark, the notice at every
     stop for them, unparsed input blocking up to Claude Code's limit).
   - PROGRESS's CI lines: round 0 is filled and right (runs 43889464942, 43889464982 and 43889464924 are success on
     `829ec9a3`). Round 1's line (`PROGRESS.md:212`) is still a pointer: nit 3.
   - The four surviving mutations: closed, each killed by a test now. No `try` around an unused session's read:
     `test_input_that_cannot_be_read_is_quiet`. `read(WIRE_LIMIT)`: the "oversized by whitespace" case. `shortened`
     or `visible` removed: `test_the_failure_reason_is_bounded_and_shows_hidden_characters`. PROGRESS's R1 to R9 are
     killed here too.
4. **What the fix round broke.** In the code: nothing I could find. In the tests: one lost its claim (the should-fix
   below). The others still exercise theirs. The cases that expect the block now carry `"stop_hook_active":false` and
   assert the block. The cases that now expect quiet would be told under round 0's rule (mutations R1 to R3 fail
   them), so they are not empty. The unreadable cases in `test_service_fixes` assert `True` around the damage: `used`
   before it and after the repair, `notice` after the repair. Only the 1200-level case of `test_ingress_bounds`
   accepts both outcomes, and says why.

### Findings

#### Blocking

None.

#### Should-fix: the link test no longer shows that reads never follow a link (test only, small)

`control/tests/test_service_fixes.py:543-558`, `test_a_link_where_the_folder_should_be_is_never_followed`.

The folder behind the link is empty. Before this round `used()` had to answer `True` there (refused, so "as if
marked"), which a read that followed the link could not. Now it has to answer `False`, and a read that follows the link
into the empty folder answers `False` too. The write side is still held (`mark()` raises, the folder stays empty).

Shown by a mutation: `_open_folder` without `O_NOFOLLOW` for reads only (`usage.py:86`). On `829ec9a3` this test
kills it; on `962d5abe` none of the 63 tests of `test_service_fixes` and `test_stop_hook` notices it.

The code itself is right: through the generated command, a session whose mark sits in a folder that `used` or
`aresos-control` links to stayed quiet (check 2).

Fix, tried in a scratch copy: after the write-side assertions, put the session's mark where the link leads
(`elsewhere/used/20-500` in the first half, removed again; `elsewhere/20-500` in the second), then assert
`used()` is `False`. The test passes on the real code and fails on the mutant.

#### Nits

1. **A flag that is falsy but not a boolean isn't pinned.** `first_stop` with `== False`, or with "present and
   falsy", passes every test: `test_stop_hook.py:128` uses `'no'`, and `test_ingress_bounds.py:95-96` use `1` and
   `'true'`, all truthy. The code is right (`0` and `null` were quiet in my runs). If it regressed, a later Claude
   Code that sent `null` or `0` there would block every stop again. Add `0` and `None` to the "not a boolean" case.
2. **A link where a mark should be.** `_plain` with `follow_symlinks=True` (`usage.py:127`) passes every test, on
   `829ec9a3` as well. Under the old rule both readings gave "marked"; now they differ, so a test can hold it: a link
   at the session's mark name that points to another session's mark is no mark. The code refuses it (check 2). The
   two owner checks (`usage.py:89`, `:101`) have no test on either commit; not this round's.
3. **`reviews/stop-hook-quiet/PROGRESS.md:212`:** fill in round 1's runs (above). `:209` says the local failures are
   main's set "less one"; in my scratch copies the set is the same as on `a46ffe44`.
4. **The pull request's description** still gives round 0's rule ("not again while `stop_hook_active` is true") and
   doesn't mention that unreadable marks now count as unused. It becomes the public record of the merge.
5. **`control/README.md:400-403`:** "every session, used or not" holds for a damaged folder; a link or folder where
   one mark should be, or one unreadable process, silences that session only. "Its held work" has no owner in the
   sentence.

#### Notes, no change asked

a. Held work and the outage notice still take a missing `stop_hook_active` as a first stop, as on `main`; only the
   failure block needs a readable `false`. The fuzz shows it: 131 blocks for valid input whose flag was renamed
   away, all of them held work or the notice, none a failure block. The notice is bounded by `.told`. Held work
   would block each stop of a session that used the tools if a later Claude Code dropped the field, while the work
   is held.
b. A repeated flag is read as its last value by the lenient read: `true` then `false` in one object gives the
   failure block at each stop. Claude Code's own JSON writer can't produce a repeated field.
c. The third surviving mutation lets the lenient read accept raw control characters in strings. Such input is quiet
   today and would be told once; both are bounded.
d. One expectation of mine was wrong, not the code: a plain file at the socket's path gives "not running"
   (`ECONNREFUSED`), not "could not be reached". Unchanged from `main`.

SAFE
