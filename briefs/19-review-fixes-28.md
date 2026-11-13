# 19-review-fixes-28: reopen a check before reading; archive only closed checks; filing recovery uses the evidence it has

**Goal:** close security review 20 (`reviews/19-mail/SECURITY-REVIEW-20.md`, head `8724c0b6`; read it first), judged
against the lead's refined disk bar (round 25). One blocking point remains, narrower again; there is no bypass, and the
approval-test fixture change, the startup set and the sweep's per-operation assertion all held. Approved by the lead on
2026-11-09. Briefs 19 and `19-review-fixes` to `-27` still apply where this brief doesn't change them; where in doubt,
their "If unsure" rule decides.

**Not this round:** the owner approved R1–R3 as its own package (19b) after Mail merges; its brief is separate. Don't
start any of it here. This round stays narrow.

## What to build

1. **Reopen before you read** (review blocking point; `mail/adapter.py` around line 723, `archive.py` around line 22).
   This extends round 27's rule, which already refuses a new check's live read when its registration can't commit, to
   reopening a clean check.
   - Any evidence read that could change a committed check result first commits the check as open. If that commit
     fails, the read doesn't happen, and the response says "not yet checked" plus the storage error. No count is shown
     that isn't recorded.
   - Archive eligibility requires every warning-producing check of the operation (every row of round 27's inventory C:
     duplicate Sent copies, MOVE/COPY role drift and destination evidence, RENAME role drift, location-scan
     completeness, setup qualification) to be closed with a committed result and no unacknowledged warning. Check that
     `archive.py` enforces this for every check kind, not only duplicates, and test each kind.
   - Test the review's sequence: a clean send, two matching copies, admission refused during `operation_status`, a crash
     (volatile state discarded), healthy admission, then `control_archive` with a cutoff covering the operation before
     any pending read. The operation is not archived away, and a pending read then shows the duplicate warning. Also:
     the refused `operation_status` itself shows "not yet checked" and the storage error, not a count.

2. **Filing recovery uses the evidence it has** (should-fix, do it now; `mail/filing.py` around line 161). Don't require
   the whole special-folder map to resolve. Report the role drift and the locations that can be observed, and leave only
   the genuinely unavailable parts "not yet checked". Test the review's case: an interrupted MOVE where Target resolves
   as Trash and Drafts' role is missing; recovery reports the Trash drift and the observed locations, and marks only the
   Drafts part unresolved.

3. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-20.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 28" section: each finding, what changed, the archive eligibility rule per check kind, the files
   changed and why, the tests by name. Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code
   or tests (all workflows, both passes) and the statement that any later commit changes only files under `reviews/`;
   in the PR body, the runs on the final head.

## Out of scope

Everything else, including R1–R3 (package 19b) and a fresh hunt for other issues. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/` other than
`control-mail.yml` (sweep sharding only, `timeout-minutes: 45` kept). Brief 18's tests under `control/tests/` change
only by additions or where the rule forces it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `8724c0b6` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Commit "open" before reading; never show a count that isn't recorded; never archive an operation with an open check or
an unacknowledged warning; report what can be observed and mark only the rest unresolved.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and the base tests you ran in round 27, plus your new plain-Python tests. Run the real-server tests whose fixtures you
  touch locally where they can run without containers, or reason through them carefully before pushing (round 27's
  first push failed seven of them). Aim for one push with the code and tests and one with the report. Don't start extra
  manual workflow runs. For the second pass on the final head, rerun the same pull-request run with `gh run rerun <id>`;
  never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a narrow check-ordering and archive-eligibility fix, on code it wrote.
