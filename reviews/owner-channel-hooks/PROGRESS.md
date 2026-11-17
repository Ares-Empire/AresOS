# Owner channel test: the hooks find the session's mark (progress)

Branch `fix/owner-channel-hooks`, off `main` at `1beddbc5` (after #91). Builder: Claude agent (Opus), for the lead.

## What was wrong

`control/tests/test_owner_state_channels.py`,
`OwnerStateChannels.test_paged_committed_pending_through_every_installed_channel`, failed at line 109: after
`self.mark_session()`, `hook Stop` launched as the owner printed nothing, so `json.loads` raised "Expecting value"
(runs 43893138937 and 43919136534, job `ledger`, branch `briefs/20-restore-lock-followups`, before #91).

The cause is that the test process was the container's **PID 1**:
- The ledger job runs `docker run … bash -c 'source control/ci/setup.sh; python3 control/ci/base.py --optional'`.
  bash execs the last command of a `-c` string in place (checked with bash 5.3 here: the Python child got bash's own
  PID), and docker's command is PID 1 without `--init`.
- `mark_session()` has a child mark its parent, the test process, so the mark was `1-<start>`. `usage.mark` writes it.
- A hook's session is its nearest ancestor that isn't a shell, "within four levels and never PID 1"
  (`usage._session`: `if pid <= 1: break`). The hook's chain was `python3 <- sh <- PID 1` (before #91: `python3 <- PID
  1`), so the walk found no session, `usage.used()` said no, and the hook stayed quiet, exactly as it should for a
  session that never used the tools.

The run 43945576041 confirmed it on post-#91 code: with the new precondition (below) and no `--init`, it failed with
"the hooks this test launches would not find its session's mark (test process pid 1; …)".

Not the other candidates: `setUp` makes `/run/user/<owner uid>` the owner's, 0700, and the marker creates the 0700
folders itself. A refused folder would have counted as a mark before #91 (`used()` then said yes on anything
unreadable), so that run's hook would have printed, not stayed quiet.

## Harness, not product

A real session can't hit this. On the laptop PID 1 is systemd and Claude Code is a child of the owner's terminal
(under `systemd --user`), so it is never PID 1, and the walk's "never PID 1" never hides it. The real chain is pinned by
the boundary suite with real Claude Code 2.1.319: `python3 <- sh <- sh <- claude` for both hooks (#91's PROGRESS, run
43889464982). The same `mark_session()` hook tests pass in Control base, where `control/ci/test.sh` runs `base.py`
with a command after it, so bash forks and the test process has an ordinary PID: run 43901887887 (#91's head),
`test_malformed_hook_input_gives_explicit_failure_feedback` and `test_stop_hook_installation_failures_are_quiet` ok.

## Why it went unseen

Only the dispatched workflow `control-owner-oracle.yml` runs this test (`control/ci/base.py --optional`), and only its
ledger job runs it that way. A full run takes about 2.5 hours, so it is dispatched rarely. The failure also pointed at
the hook's output (an empty reply) rather than at the test process's PID.

## What changed

1. `.github/workflows/control-owner-oracle.yml`, job `ledger`: `docker run --init`, with a comment saying why. The
   test process now gets an ordinary PID under docker's init, as on the laptop.
2. `control/tests/test_integration.py`, `mark_session()`: the marker child now prints `usage.used()` after marking,
   and the harness asserts it. `used()` from the marker resolves the same process a hook's walk reaches over its
   shells, so a mark the hooks won't find fails right there, naming the test process's PID, instead of as an empty
   hook reply later. What the tests check is unchanged.
3. The same workflow gets a `workflow_dispatch` boolean input `ledger_only` (default false). When true, the
   `alterations`, `sweep` and `onboarding` jobs are skipped (`if: ${{ !inputs.ledger_only }}`). The default runs
   every job as before.

## Verified

- Run 43945576041 (ledger only, `1ceee40a`: the precondition, no `--init`): ledger failed with "test process pid 1".
  The other three jobs were skipped, so `ledger_only` works.
- Run 43947829901 (ledger only, `c697961b`, with `--init`): success. Both optional tests ok, among them
  `test_paged_committed_pending_through_every_installed_channel`; the other three jobs skipped.
- Locally (laptop, Python 3.14, not root), from `control/tests` with `PYTHONPATH=control`:
  - `test_stop_hook`: 8 tests, OK.
  - `test_service_fixes`: 56 tests, 1 error, `test_an_mcp_session_started_without_the_service_gets_its_tools`:
    `ModuleNotFoundError: No module named 'mcp_types'` (no MCP SDK installed on the laptop). Not touched by this
    change: neither module imports `test_integration`.
  - `python3 control/generate.py --check`: "Generated artifacts match definitions" (nothing generated was touched).
  - A simulation in a scratch runtime folder: a child marks its parent and `usage.used()` there says true, and a hook
    stand-in below `/bin/sh -c` says true for the same mark.
- Not run locally: `test_integration` and `test_owner_state_channels` (root, an installed launcher). CI runs them.

## CI

- Owner oracle, ledger only: run 43947829901, success (ledger green; alterations, sweep, onboarding skipped).
- PR checks: see the pull request.

## Judgment calls

JUDGMENT-CALL: the fix is the environment (`--init`) plus a loud precondition in `mark_session()`, not a stand-in
session process. A stand-in (a long-lived process the harness would start, which then starts both the marker and
every hook) would free the harness from the runner's PID, but it would rework `launch()` for every hook test and the
direct launch in `test_stop_hook_installation_failures_are_quiet`, for a case that only arises when the test runner
itself is PID 1, which no real session is. Changing it later stays within the harness.

JUDGMENT-CALL: product code unchanged. `usage.mark` still writes a mark for a PID 1 parent that no hook ever reads.
That is harmless on the laptop, where Claude Code is never PID 1. Refusing PID 1 in `mark` would make the two sides
agree; it is a product change, so it is left for the lead.

JUDGMENT-CALL: `control-base.yml` keeps its `docker run` without `--init`. `control/ci/test.sh` runs a command after
`base.py`, so bash forks; if that ever changes, the new precondition names the cause.

## The lead (2026-11-16)

- **Review 1: SAFE** (three optional nits).
- **`usage.mark` for a PID 1 parent stays as it is.** On the laptop, Claude Code is never PID 1. A mark no hook reads
  is harmless, and refusing it would be a product change for no owner-visible gain.
- **Nits 1 and 2 go to the queue** (item 16, with the idle-loop flake): name the hook's own path in `mark_session`'s
  message, and give Control base `--init` or a comment where `test.sh`'s `printf` keeps the test process off PID 1.
  Nit 3: the laptop's chain ends at konsole under system PID 1, not `systemd --user`. The conclusion stands.
- Merge after Control Mail, Control Chrome and Chrome qualification are green on 756775c2. This commit changes only
  `reviews/`.
