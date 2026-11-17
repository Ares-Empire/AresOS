# PR #96 review 1: owner channel test marks the session its hooks resolve

Reviewer: fresh Claude agent (Opus), not the builder. Head `756775c2` (base `1beddbc5`, current `origin/main`).
Read-only review; no containers, root, rpm-ostree/bootc/ostree or `os/tests/test_owner_*` were run.

## What I checked

1. **Root cause.**
   - Read `usage.py` (`_session`, `parent`, `mark`, `used`), `hooks.py` (`main` asks `usage.used()` first and, when it
     says no, prints nothing), `launch.py` (the hook runs in process, with no extra fork), `managed-hooks.json`
     (`env -i … /bin/sh -c 'if decision=$(python3 … launch.py hook Stop) …'`) and `control/ci/base.py`.
   - `_session` stops at `pid <= 1` (usage.py:143). `mark` writes `<ppid>-<start>` for any parent, PID 1 included
     (usage.py:160-167). So a test process that is PID 1 gets a mark that no walk ever reads, and `used()` says no.
   - bash 5.3 here: `bash -c 'echo $$; source /dev/null; set -euo pipefail; python3 …'` gives Python bash's own PID
     (exec'd in place). With a command after it, Python gets a new PID. So the ledger job's
     `bash -c '…; python3 control/ci/base.py --optional'` made the test process the container's PID 1. In
     `control/ci/test.sh`, used by Control base, a `printf` follows `base.py`, so bash forks there.
   - Logs:
     - 43945576041 (no `--init`, with the new precondition): `AssertionError: … (test process pid 1; …)`, raised by
       `mark_session` at test_integration.py:123.
     - 43919136534 (before the PR): `JSONDecodeError` at test_owner_state_channels.py:109, the empty hook reply.
     - 43947829901 (`--init`): both optional tests `ok`, `OK`.
   - History fits the cause. `pid <= 1` came in with 117440e9 and `mark_session` in the channel test with 139a9696.
     Both are in accf2eb0 (failing) and neither is in 96bb1a03, the last green full run (43738332693).
   - **Harness, not product.** This session's own chain on the laptop is
     `bash <- claude (3353) <- bash <- konsole <- systemd (PID 1)`. Claude Code is an ordinary PID, and the hook walk
     stops at the first process that isn't a shell, which is Claude Code, before it could reach PID 1. Toolbox and
     distrobox share the host's PID namespace, so they don't change that.
2. **Does `used()` in the marking child resolve the same session as a hook?**
   - `run_user` runs `[sys.executable, "-c", …]` with `preexec_fn`, so it forks and execs directly. Its parent is the
     test process, and `used()` checks the test process at walk level 1.
   - `launch` runs the managed command, also a direct child. `env` execs; `sh` runs the `$(…)` Python, which the
     shell execs. The hook's parent is `sh`, and the walk reaches the test process at level 2, well within 4.
   - Same uid (`identity(OWNER)`), same `/run/user/<uid>` and same `/proc`. Neither side reads the environment.
   - In CI the installed `usage.py` is a copy of the same tree (`setup.sh:13`).
   - Independent simulation in scratch: a Python "test process" marks itself through a child, then runs the real
     `managed-hooks.json` Stop command with a stand-in that prints `usage.used()`. Marked: the child says true and
     the hook says true (its parent is the `sh`). Unmarked: both say false.
   - Control base on the PR's merge commit (run 43949391406, job 133587521337): all four `mark_session` tests in
     `Integration` pass with the new assert, and 380 tests ran (`Control base suite PASS`). The assert doesn't
     false-fail when the test process is an ordinary PID.
   - Where the two sides can differ is finding 1 below. The hook tests' positive assertions still catch that case.
3. **`--init` side effects and test counts.**
   - `base.py --optional` selects exactly the two `OPTIONAL` tests, and this PR leaves the selection unchanged.
   - Ledger test counts: 96bb1a03 ran 2 (both ok), accf2eb0 ran 2 (1 error), 1ceee40a ran 2 (1 failure) and c697961b
     ran 2 (both ok).
   - `test_every_pinned_gap_belongs_to_an_executed_suite` is static (AST and JSON). The channel test's daemon is the
     test process's child, so `terminate()` doesn't depend on PID 1.
   - With tini the test process loses PID 1's ignored-default signals, and orphans are reaped by tini instead of
     piling up as zombies. Nothing in either test relies on either behaviour.
   - Tini passes on the child's exit code, so `pipefail` and `tee` still fail the step.
   - The `os.kill(os.getpid(), …)` workers in `control/tests` are not part of this job.
4. **Workflow.**
   - YAML parses. The only trigger is `workflow_dispatch`, and the boolean input defaults to false.
   - The three jobs get `if: ${{ !inputs.ledger_only }}`, and `ledger` has none. On a default dispatch the condition
     is true. No job has `needs:`, so the implicit `success()` is true as before. The default dispatch therefore runs
     every job exactly as before.
   - Run 43947829901 shows `ledger` success and `sweep`, `onboarding` and `alterations` skipped.
   - Nothing in the repo downloads these artifacts (grep for the artifact names and `gh run download`).
   - Not a finding, already true before this PR: `concurrency` is per ref with `cancel-in-progress: false`. A quick
     ledger-only dispatch on a branch with a full run in progress waits behind it. A second pending dispatch replaces
     the first.
5. **Local runs** (laptop, Python 3.14, not root, `PYTHONPATH=..` from `control/tests`):
   - `test_stop_hook`: 8 tests, OK.
   - `test_service_fixes.QuietUnlessUsed`: 27 tests, OK.
   - `test_integration.py` parses.
   - Nothing that calls `mark_session` can run without root: `Integration` and `OwnerStateChannels` chown, write
     `/etc/aresos-control` and make `/run/user/<uid>`. CI covers them (Control base above and ledger run
     43947829901).

## Findings

1. NIT. `control/tests/test_integration.py:117-118` and `:123-124`: the docstring says a mark "the hooks won't find
   fails here". That holds only while every process between the test process and the hook is a shell, within four
   levels. The precondition checks the end of the hook's walk (the test process), not the path to it. A non-shell
   wrapper added to the managed command (a forking `timeout`, say) or deeper nesting would pass the precondition, and
   the hooks would still miss. The hook tests' positive assertions catch that later, as before this PR. The failure
   message also always blames PID 1, though it prints the PID, so the reader can tell. Optional: say "when the test
   process itself can't be a hook's session (PID 1)", or give the init hint only when `os.getpid() == 1`.
2. NIT. `control/ci/test.sh:6-7` and `.github/workflows/control-base.yml:24`: Control base avoids the same PID-1 exec
   only because a `printf` follows `base.py`, which isn't obvious. A tidy-up that drops or moves that line would bring
   the problem back in the workflow that gates every control PR. The builder decided this as a judgment call. The new
   precondition would name the cause, so the cost is low. A one-line comment in `test.sh`, or `--init` there as well,
   would close it for good. Optional.
3. NIT. `reviews/owner-channel-hooks/PROGRESS.md:31-32` says Claude Code is a child of the terminal "under
   `systemd --user`". On the laptop now the chain is `claude <- bash <- konsole <- systemd (PID 1)`. The conclusion
   still holds: Claude Code itself is never PID 1, and the walk stops at it. Only the wording is off.

No BLOCKER or FIX. The root cause is proven by run 43945576041's message and agrees with the code and the bash
behaviour. The fix is confined to the test harness and the optional workflow. Default dispatch behaviour is
unchanged, and no test was weakened: the precondition can only add a failure.

SAFE
