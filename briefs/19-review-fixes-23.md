# 19-review-fixes-23: observations survive persistence failures, everywhere; the first storage error wins; a fault-injection sweep proves it

**Goal:** close security review 15 (`reviews/19-mail/SECURITY-REVIEW-15.md`, head `2be76104`; read it first), judged
against the lead's fail-closed disk bar (round 21, in `REPORT.md`). No bypass, credential exposure or second delivery
was found. The two blocking points are round 22's class on paths round 22 didn't reach, so this round **closes the
class, not the two cases**, and proves it with a sweep that covers new write points automatically. Approved by the lead
on 2026-11-08. Briefs 19 and `19-review-fixes` to `-22` still apply where this brief doesn't change them; where in
doubt, their "If unsure" rule decides.

## What to build

1. **One rule for every path: observations survive a persistence failure.**
   - Every result is built from what the service observed (copies found, duplicate warnings, stage outcomes, remote
     answers), and only then is persistence attempted.
   - A persistence failure adds the storage error to the result but never removes an observed fact.
   - Apply this in one place that every execution, repair, status and settlement path goes through (for example the
     stage-recording and result-building layer in `engine.py` and the Mail adapter's evidence calls), not per path.
     The review's case: `mail_sent_copy_check` (`mail/adapter.py` around line 866), during a repair and during a send:
     two matching Sent copies plus `ENOSPC` on that check's journal write must return both copies and the duplicate
     warning with the disk-full error.

2. **The first storage error is kept to the end.**
   - The typed storage error (`ENOSPC`, `EDQUOT`, `EIO`, short write) propagates through execution and outcome
     handling. A later failure-latch refusal never replaces it with "A journal transaction did not finish"; at most it
     is added after it.
   - The review's case (`engine.py` around line 183): an approved send where `submitting` commits, then `ENOSPC` on the
     first stage record. The result says disk full, the submission stays non-repeatable, and after space returns a
     restart recovers it to the correct outcome (`unknown` or what the evidence proves), never a second SMTP `DATA`.

3. **A fault-injection sweep as the test for both.**
   - For each flow (send, Sent-copy repair, delete to Trash and for good, unsubscribe, `mail_operation_status`, repair
     settlement, cancel, restore confirmation), run the flow once per durable write point, with `ENOSPC` injected at
     that point.
   - Each run asserts: the result says the disk is full; nothing observed is missing (copies, duplicate warning, stage
     outcome); never `ok=true` for a write that didn't land; no second delivery, APPEND or delete; and after space
     returns, a restart recovers and `mail_operation_status` is correct.
   - The test enumerates the write points itself by wrapping the storage layer (count the durable writes a flow makes
     in a clean run, then fail each in turn), so a new write point is covered automatically. Print the number of write
     points per flow in the log, and fail the test if a flow reports zero.
   - Keep it fast enough for CI (synthetic servers or in-memory substitutes where the flow allows; real container
     servers where it matters for the observation, as in earlier rounds).

4. **Every response matches its advertised schema** (should-fix, do it now). `mail/definitions.py` (around line 104)
   advertises only `operation` and `original` for repaired responses, which now include `evidence`. Add `evidence` (and
   anything else responses carry) to the advertised output schemas, and validate every response in the Mail and base
   suites against its advertised schema, centrally in the test harness (the shared call helpers), so no response can
   drift from its schema again. Regenerate the artifacts.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-15.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 23" section: the rule from point 1 in plain words, where it lives, the sweep (flows and write
   points counted), the files changed and why, the tests by name. Run IDs as before: in `REPORT.md`, the runs of the last
   commit that changes code or tests (both workflows, both passes) and the statement that any later commit changes only
   files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where the
central schema validation forces it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `2be76104` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Observe first, persist second, and never let a persistence failure erase an observation or replace the first storage
error.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest
  test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact
  test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming
  test_restore_batches test_review21_pending test_review21_storage test_review22_protocol test_review22_storage`, plus
  your new plain-Python tests (including as much of the sweep as runs without containers). Aim for one push with the
  code and tests and one with the report. Don't start extra manual workflow runs. For the second pass on the final
  head, rerun the same pull-request run with `gh run rerun <id>`; never push again just to get another run. Keep it to
  about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a cross-cutting result/persistence rule and a fault-injection sweep, on code it wrote.
