# 18d main merge, fixes round 4: the guard test must not swallow its own assertions

**Goal:** fix the one FIX finding of the package review of round 3 (`reviews/18d-base-slim/PACKAGE-REVIEW-6.md`, on
`f9bce2ad`) and record what its known limit asks for. The security review of round 3 (`SECURITY-REVIEW-5.md`) found
no FIX. The briefs of rounds 1 to 3 (`briefs/18d-main-merge-fixes*.md`) still apply. Test code only; nothing else
changes.

## What to fix

1. **The guard test swallows its own positive assertions (finding 1).** In the guard's own test
   (`control/mail_tests/test_review23_sweep.py`, around line 711), the expected rejection probes and the positive
   assertions share one latched guard. After a rejection, the guard's exit replaces a later assertion failure with
   `AmbientRead`, which the outer `assertRaises` accepts. The reviewer reproduced it: with `time.localtime` patched to
   return an invalid empty tuple, the explicit-calendar assertion (around line 738) should fail, but the test prints
   OK. Fix it:
   - Run every positive assertion in its own fresh guard scope that holds no intentional rejection, and each expected
     rejection in its own scope, so a rejection can never stand in for a failed assertion.
   - Add a regression that breaks each explicit conversion the test claims to allow (for example `time.localtime`
     with an argument, `time.strftime` with a tuple, any other explicit form it checks) and shows the test then
     fails.
   - Check the other guard and mutation tests from rounds 2 and 3 for the same pattern (a latched rejection that could
     replace a later failure inside one `assertRaises`) and fix any you find the same way; say which you checked.
2. **Known limit to record (finding 2).** From Mail run `43175779056` on `f9bce2ad` (attempt 1, as far as it ran) and
   the final head's two attempts, record per-flow discovered points and single, persistent and cleanup-pair counts
   against the baseline (6,642 points; 6,302 single, 6,302 persistent and 15,915 cleanup-pair cases on Linux), and
   every required Mail job's duration against its 35-minute limit.

## Tests and runs

- Locally: `python3 control/generate.py --check`, the guard tests with each new regression, and the focused sweep
  tests the change touches, as far as macOS allows.
- On GitHub, on the final head: Control base, Control Mail and Control boundary **twice each** (the pull-request run,
  then `gh run rerun <id>`; never a new push for the second pass). Both Mail attempts must pass every job. No oracle
  run.
- Any push restarts all three workflows and cancels older runs: commit locally (this brief and the review commit are
  local too) and push once, when everything is done and green locally.
- Budget: about six executions.

## Report

Add a section "Main merge fixes, round 4" to `reviews/18d-base-slim/REPORT.md`: the fix, the regressions and their
results, the tests checked for the same pattern, the count table and the job durations. Record the final run IDs and
attempts in the PR #25 description.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. The draft PR #25 exists. Never merge anything, never push
  to `main`, never force-push.
- Don't edit the design or plan files, `README.md`, `STATE.md`, `HANDOFF.md`, anything under `os/`, `mod/`,
  `docs/INSTALL*`, `docs/EMERGENCY.md`, `reviews/19b-owner-state/`, `reviews/19-mail/`, the review files the
  reviewers wrote (`reviews/18d-base-slim/*REVIEW*.md`, `SECURITY.md`), or production code under
  `control/aresos_control/`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a small, exact fix in the harness it built in rounds 1 to 3.
