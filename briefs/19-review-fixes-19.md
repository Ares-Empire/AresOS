# 19-review-fixes-19: one unresolved repair per stage; cancel always has room; the journal streams

**Goal:** close security review 11 (`reviews/19-mail/SECURITY-REVIEW-11.md`, head `88c83ef7`; read it first), judged
under the owner's decision 24 (the tools must be safe in themselves). Completed-stage idempotence, the restore
exemption, separate journal accounting and the removals all held; no bypass or leak was found. One blocking finding
and one should-fix remain; fix both in this round. Approved by the lead on 2026-11-08. Briefs 19 and
`19-review-fixes` to `-18` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule
decides.

## What to build

1. **Recovery traffic can't eat recovery** (blocking). Every eligible repair allocates a new operation
   (`engine.py` around line 184). If IMAP drops, the repair is `unknown`, the original stage stays `failed` and
   eligible, and archive keeps unresolved records: 38 attempts gave 38 unknown repairs, archives couldn't reclaim
   them, and cancel returned `storage_limit`.
   - At most one unresolved repair per stage: while a repair of a stage is `unknown` (or still running), a new repair
     request for that stage re-checks that repair's evidence first and returns it, instead of allocating another
     operation.
   - A safe resolution path for an unknown repair: re-check the evidence (the Sent copy by its Message-ID, the
     answered flag) read-only and settle the repair to `done` (evidence found) or `failed` (evidence absent and the
     check itself succeeded); a `failed` repair makes the stage eligible again. An inconclusive check (the server
     still unreachable) leaves it `unknown` and writes nothing new. Decide whether this runs inside the repeated
     repair call, through `mail_operation_status`, or as its own read-then-settle action, and say why.
   - Cancellation gets its own reserve, like restore confirmation, that repairs and every other call can't use.
   - Regressions: the review's 38-attempt sequence ends with one unresolved repair and cancel working; one unresolved
     repair per stage under repeated calls; an unknown repair settles to `done` when the Sent copy is found and to
     `failed` (stage eligible again) when the check proves it absent; cancel succeeds with all other capacity used.

2. **The journal isn't held in memory** (should-fix, do it now). `storage.py` (around line 105) loads every historical
   record into `self.events`, about 32–45 KB of objects per small send sequence, 1.2–1.7 GB a year at 100 sends a
   day. Keep the disk record forever, as decided, but stream its verification at start and keep only a bounded index
   in memory: what replay refusal and restore detection need (for example the hash chain head, operation ids and
   their hashes or states, the generation). Nothing that needs the whole history in memory remains.
   - Test that memory stays bounded across many operations (for example peak or retained size measured with
     `tracemalloc` over thousands of synthetic events stays under a fixed bound, independent of the event count), that
     start-up verification still detects a corrupted or truncated journal, and that restore detection and replay
     refusal still work after a restart with a large journal.

3. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-11.md` (already committed) to the review links in `REPORT.md`. Add
   a "Review fixes, round 19" section: each finding, what changed, the files changed and why, the tests by name. Run
   IDs as before: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes)
   and the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on the final
   head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where
the new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `88c83ef7` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Reuse rather than allocate; settle only on proof; keep cancel's room separate from everything else; never drop what
restore detection and replay refusal need.

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
  test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity`, plus your new
  plain-Python tests. Aim for one push with the code and tests and one with the report. Don't start extra manual
  workflow runs. For the second pass on the final head, rerun the same pull-request run with `gh run rerun <id>`;
  never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (point 1, then point 2).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: recovery semantics and a streaming journal, on code it wrote.
