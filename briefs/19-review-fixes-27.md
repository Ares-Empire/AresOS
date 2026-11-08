# 19-review-fixes-27: a check that can warn stays open until its result is committed

**Goal:** close security review 19 (`reviews/19-mail/SECURITY-REVIEW-19.md`, head `ce73b0f3`; read it first), judged
against the lead's refined disk bar (round 25). One blocking point remains, down from three; there is no bypass, and
round 26's inventories A and B held. Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-26`
still apply where this brief doesn't change them; where in doubt, their "If unsure" rule decides.

**Not this round:** brief 26b's rules R1–R3 as a whole are not this PR's; the lead has asked the owner whether to build
them as their own package after Mail. Don't start them. This round applies one narrow rule from them, to round 26's
inventory C only.

## The rule (lead decision, round 27; record it in `REPORT.md` as the lead's)

**A check that can produce an owner warning stays open until its result, clean or warning, is committed.** Recovery and
the pending view treat an open check as unresolved. They rerun it with live, read-only evidence when they can, and show
it as "not yet checked" when they can't. Losing the warning's write therefore leaves the check open instead of silently
closed, and nobody has to rediscover the operation.

## What to build

1. **The duplicate-copy check stays open until committed** (review blocking point; `mail/adapter.py` around line 707).
   A send or APPEND counts as `done` for the action, but its Sent-copy check (the count of copies with that Message-ID)
   stays open until a committed result exists, clean or a duplicate warning. Commit the open state with the action's own
   records (before or together with marking the action done), so a failed warning write leaves it open.
   - Recovery and `control_pending` (and `mail_filing_notices` where it lists Mail warnings) treat an open check as
     unresolved: they rerun it with a live, read-only Sent search when they can and commit the result; when they can't
     (server unreachable, storage refused), they show it as "not yet checked" for that operation.
   - Test the review's case: a completed send, two matching Sent copies, admission refused for `mail_sent_copy_check`
     during `operation_status`. Then, without calling `operation_status` again, after space returns, and separately
     after a restart, `control_pending` or `mail_filing_notices` shows the duplicate warning for that operation.
   - Normal use stays quiet: a clean check committed right after a send shows nothing extra, in `control_pending` and
     in the notices.

2. **Inventory C again, under this rule.** List every check whose result can be an owner warning: duplicate Sent copies,
   filing role drift (move, copy, rename), incomplete location scans, and anything else you find. Give each its open
   state (where it is committed, when it closes) and how recovery and the pending view resolve it (live rerun, or "not
   yet checked"), as a table in `REPORT.md`. Close any other entry the same way and test it.

3. **Recovery notices only for what was unfinished at startup** (should-fix, do it now; `storage.py` around line 540).
   Capture the set of intents actually unfinished when the service started, instead of classifying by row creation
   time. Test the review's case: prepare a send, restart while it is only `reserved`, then submit before expiry; it
   finishes `done` with no "unfinished" notice. A send actually left `submitting` at startup still gets its notice.

4. **The sweep must not mask a loss** (should-fix, do it now; `mail_tests/test_review23_sweep.py` around line 431).
   After a restart and after space returns, assert the affected operation's own warning by operation id, before any
   further live evidence read such as `operation_status`; "some notice exists" is not enough. Test the assertion
   function itself: the old assertion would have passed on review 19's case, the new one fails on it.

5. **Stop condition.** If the rule turns out to need R1–R3's larger pieces (a new committed projection of owner state, a
   rebuilt sweep oracle from server event logs), stop: write in `REPORT.md` what and roughly how big, commit and push
   that note, and end the run with it as your final message. Don't build it.

6. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-19.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 27" section: the lead's rule, the new inventory C table (check, open state, how recovery and
   pending resolve it, test), the should-fixes, the files changed and why, the tests by name. Run IDs as before: in
   `REPORT.md`, the runs of the last commit that changes code or tests (all workflows, both passes) and the statement
   that any later commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including R1–R3 beyond this rule and a fresh hunt for other issues. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/` other than
`control-mail.yml` (sweep sharding only, `timeout-minutes: 45` kept). Brief 18's tests under `control/tests/` change
only by additions or where the rule forces it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `ce73b0f3` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Leave the check open rather than closing it without a committed result; rerun it read-only when possible, otherwise
say "not yet checked".

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and the base tests you ran in round 26, plus your new plain-Python tests. Aim for one push with the code and tests and
  one with the report. Don't start extra manual workflow runs. For the second pass on the final head, rerun the same
  pull-request run with `gh run rerun <id>`; never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a narrow recovery rule with an inventory, on code it wrote.
