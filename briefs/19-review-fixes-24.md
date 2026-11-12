# 19-review-fixes-24: filing, background work and exports join the shared rule; the sweep covers what it claims

**Goal:** close security review 16 (`reviews/19-mail/SECURITY-REVIEW-16.md`, head `dd8ea4f6`; read it first), judged
against the lead's fail-closed disk bar (round 21, in `REPORT.md`). No approval, credential or replay bypass was found.
The three blocking points are round 23's class in paths outside the shared result layer and outside the sweep:
filing, background expiry and exports. The sweep's gaps are why they slipped through, so its should-fix is in scope
now. Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-23` still apply where this brief doesn't
change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Filing goes through the shared result layer** (blocking). In `mail/filing.py` (around line 286), MOVE succeeds,
   the destination gains the Trash role, then `ENOSPC` on the post-MOVE journal write returns only `storage_limit`, with
   no observations or warning, and the retained intent has `destination: null`.
   - The observed COPYUID destination, the changed role and the filing-policy warning ("the special folders changed …
     now in <folder>, which is now Trash") are returned together with the storage error, through round 23's shared
     result layer (free moves, copies and renames alike).
   - When the intent or notice can't be persisted, the warning still reaches the owner's notice path: kept in memory and
     shown in following results and `aresos log` until it can be stored or the service restarts, and written as soon as
     a write succeeds. The promised disclosure is never lost silently.
   - Test the review's case: MOVE succeeds, the destination gains `\Trash`, then `ENOSPC` on the post-MOVE write; the
     result shows the exact destination, the role and the warning with the disk-full error, and the warning appears in
     the next Mail result and in `control_log`; after space returns it is stored.

2. **The failure latch keeps the original cause** (blocking). `daemon.py` (around line 42) swallows a storage error
   raised in background work, and `engine.py` (around line 493) clears the stored diagnosis on the next request, so
   later refusals only say "A journal transaction did not finish".
   - A storage error in background work (expiry, maintenance, retention) is kept with the latch, never swallowed.
   - Every later refusal names the original cause (disk full, quota or I/O) until a write succeeds in full.
   - Background errors are logged (service log) and reach the owner's notice path.
   - Test: `ENOSPC` during `Engine.expire()`, then a change request whose refusal names disk full; after a successful
     write the latch clears.

3. **Exports keep the storage error next to the rollback result** (blocking). In `files.py` (around line 159),
   `ENOSPC` on the directory fsync after the destination was published returns `file_refused` describing the rollback,
   without disk full. Return disk full together with what the rollback did. Test the review's case.

4. **The sweep covers what it claims.**
   - **Write mechanisms:** inject at the OS level, covering the journal, the journal index connection, SQLite's
     statement and internal writes (through a VFS shim, or by failing the underlying file writes SQLite makes), and file
     create, write, link, rename, truncate and fsync for blobs, exports and passwords.
   - **Flows:** add caller exports (`mail_attachment_save`, `testapp` `file_save`), password storage (account add),
     filing (free moves, copies and renames), background expiry and maintenance, and the index build, to round 23's
     flows.
   - **Restart:** run the restart with a failure injected as well, not only clean, and then a clean restart after that.
   - **Recovery assertions are independent.** Compare the recovered state with expected outcomes computed
     independently of the recovered database: which remote actions were attempted (from the fixtures' own logs: SMTP
     DATA, APPEND, MOVE, EXPUNGE, HTTPS POST), and that each stays non-repeatable. A recovery that reports `reserved`
     for an operation whose remote action was attempted fails the test; it is never skipped.
   - Print the per-flow and per-mechanism write-point counts as before, and fail if any flow or mechanism reports zero.
   - Keep it within the CI time budget; say in the report how long it takes.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-16.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 24" section: each finding, what changed, the files changed and why, the sweep's flows,
   mechanisms and counts, how recovery is checked independently, the tests by name. Run IDs as before: in `REPORT.md`,
   the runs of the last commit that changes code or tests (both workflows, both passes) and the statement that any later
   commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where the
new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `dd8ea4f6` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Observe first, persist second; keep the first storage error with the latch; never lose a promised warning; check
recovery against what actually happened remotely, not against what the recovered database says.

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
  test_restore_batches test_review21_pending test_review21_storage test_review22_protocol test_review22_storage
  test_review23_results`, plus your new plain-Python tests (including as much of the sweep as runs without
  containers). Aim for one push with the code and tests and one with the report. Don't start extra manual workflow
  runs. For the second pass on the final head, rerun the same pull-request run with `gh run rerun <id>`; never push
  again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: extending the shared rule and an OS-level fault-injection sweep, on code it wrote.
