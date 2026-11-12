# 19-review-fixes-25: bounded responses that always carry the error and warnings; admission never latches; cleanup never replaces the first error

**Goal:** close security review 17 (`reviews/19-mail/SECURITY-REVIEW-17.md`, head `de1098d7`; read it first). Again
there is no approval, replay, credential or free-action bypass. Three blocking points and one should-fix remain.
Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-24` still apply where this brief doesn't
change them; where in doubt, their "If unsure" rule decides. The branch head is `c9210c35` (the lead's one-line
Mail-job timeout change on top of `de1098d7`); build on it.

## The refined disk bar (lead decision, 2026-11-08)

Record this in `REPORT.md` as the lead's decision, next to round 21's bar. On a full or failing disk, only these are
blocking:

- an approval bypass;
- a second or different delivery, APPEND or delete;
- a false `done`;
- a lost or corrupted committed record;
- a lost warning the owner must learn (filing, duplicates);
- a refusal that persists on a healthy disk.

The exact storage wording under multiple faults is should-fix: any of disk full, quota or I/O counts as the plain
message. Review 18 is judged against this.

## What to build

1. **Bounded responses that always carry the error and the warnings** (review finding 1). `mail/filing.py` (around line
   321) attaches every observed location without paging, and the shared result layer adds them after the size check:
   a 20,000-character Message-ID and 350 identical copies produced a 7.1 MB response, over the 6 MiB socket limit, and
   the caller got neither the disk-full error nor the warning.
   - Observations are paged, with a count and a cursor (reuse round 11's filing-location pages where they fit).
   - The result layer checks the size after adding observations and always reserves room for the storage error and
     every owner warning, cutting observations (never warnings or the error) to fit, with the count and cursor saying
     what was cut.
   - Tests: the review's case (20,000-character Message-ID, 350 copies, destination becomes Trash, `ENOSPC` on the
     post-MOVE write) returns disk full, the warning and a paged list, under the socket limit; every response in the
     sweep and the suites is validated through the real serialization and transport size limit, in the central harness
     (round 23's schema check is the place).

2. **Admission refusals never latch** (review finding 2). `engine.py` (around line 119) sets `write_failed` for every
   storage refusal, including ledger admission checks that come before any write, so after space returns the service
   keeps refusing until a restart. Only a write that may have started a transaction sets `write_failed`. An admission
   refusal returns `storage_limit` with its warning and leaves no latch; the next call after space returns works
   without a restart. Test the review's case: background blob expiry hits admission, space returns, then a composition
   and the next expiry both work.

3. **Cleanup never replaces the first error** (review finding 3). `blobs.py` (around line 128) unlinks the temporary file
   in `finally`, and an `EIO` there replaces the original `ENOSPC`. Use one helper for every `finally`-cleanup path
   (blobs, exports, passwords, journal truncation, index rebuild, anything else): the primary storage error stays, and
   a cleanup failure is added beside it as a note. Test: `ENOSPC` on the outgoing-wire write, then `EIO` on the unlink,
   gives disk full plus the cleanup note; one more cleanup path tested the same way.

4. **Sweep assertions tightened** (should-fix, in scope).
   - Completion is asserted against every requested target: a two-message delete with only one MOVE can never pass as
     `done`. Add the review's probe (two-message deletion, `MOVE:1`, UID 2 remaining) as a test of the assertion
     function itself, which must fail it.
   - Add archive compaction to the flows.
   - Add a persistent-exhaustion mode: every write fails from point k on (not just one), for each k.
   - Add primary-plus-cleanup pairs: `ENOSPC` on the primary write, `EIO` on each cleanup point that follows.
   - Print the counts as before, including for the new modes.

5. **CI time.** Keep each Mail job under about 30 minutes on a normal runner. If the sweep grows past that, split it into
   its own parallel job in `.github/workflows/control-mail.yml` (same container setup, the sweep's tests only, its own
   artifact), with the remaining Mail and base tests in the existing job. You may change that workflow for this and
   nothing else; keep both jobs' `timeout-minutes: 45`. Say the measured durations in the report.

6. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-17.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 25" section: the refined bar (above), each finding, what changed, the files changed and why, the
   sweep's new modes and counts, the CI layout and durations, the tests by name. Run IDs as before: in `REPORT.md`, the
   runs of the last commit that changes code or tests (both workflows, both passes) and the statement that any later
   commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/` other than `control-mail.yml` as point 5 allows. Brief 18's tests under
`control/tests/` change only by additions or where the new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `de1098d7` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Keep the error and every warning in the response and cut observations instead; latch only on a write that may have
started; let the first error win and add cleanup failures beside it.

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
  test_review23_results test_review24_exports`, plus your new plain-Python tests (including as much of the sweep as
  runs without containers). If you change the workflow, check its YAML locally before pushing. Aim for one push with
  the code and tests and one with the report. Don't start extra manual workflow runs. For the second pass on the final
  head, rerun the same pull-request run with `gh run rerun <id>`; never push again just to get another run. Keep it to
  about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: response bounds, latch semantics and sweep modes, on code it wrote.
