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
