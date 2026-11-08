# 19-review-fixes-22: short writes never corrupt the journal; observed duplicates are always returned

**Goal:** close security review 14 (`reviews/19-mail/SECURITY-REVIEW-14.md`, head `99280cd0`; read it first), judged
against the lead's fail-closed disk bar from round 21 (recorded in `REPORT.md`). No approval bypass or replay path was
found, and three approved submissions gave one arrival. Two blocking points break the fail-closed bar, plus one
should-fix. Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-21` still apply where this brief
doesn't change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Short writes never corrupt the journal** (blocking). `storage.py` (around line 406) ignores the byte count of the
   unbuffered journal write: a commit-marker write that accepts only 13 bytes returns `ok=true`, clears the failure
   latch, and leaves a journal that startup rejects as `evidence_corrupt` even after space returns. A short event write
   followed by `ENOSPC` reports "Mail transport failed".
   - Every journal write checks the byte count and loops until complete, or fails. A failed or short write truncates
     the journal back to its last complete record (and syncs) and returns a plain disk-full error, never `ok=true`.
   - The failure latch stays set until a write succeeds in full.
   - Startup safely drops an interrupted tail: a final record without its commit marker, from a write that was never
     acknowledged. It still rejects real corruption in the middle or in a committed record.
   - Storage errors (`ENOSPC`, `EDQUOT`, `EIO`, and short writes) are classified explicitly as storage errors with a
     plain message, and are never reported as "Mail transport failed" or another transport error.
   - Tests: a commit-marker write that accepts 13 bytes makes prepare fail with disk-full, and after space returns the
     service starts and continues; a short event write followed by `ENOSPC` gives the disk-full message; a torn tail at
     startup is recovered; a corrupt committed record is still rejected; the latch stays set after a short write until
     a full write succeeds.

2. **Observed duplicates are returned even when recording them fails** (blocking). In `mail/adapter.py` (around line
   730), when the evidence read found the Sent copies but persisting the duplicate warning fails, `mail_operation_status`
   returns only a generic "Live evidence unavailable". In `mail_operation_status`, repair and settlement, return the
   copy list and the duplicate warning that were observed, together with the disk-full error, for any storage exception
   while recording (not only selected `Refused` ones). Test the review's case: two Sent copies with the Message-ID plus
   `ENOSPC` on the warning write; the result shows both copies, the warning and the disk-full error. Repair and
   settlement behave the same way.

3. **One timeout policy for every changing request** (should-fix, do it now). `protocol.py` (around line 51) extends
   the reply window only for `method=call`; save acknowledgements, uploads, downloads and account setup keep ten
   seconds. Apply one policy to every request that can change state. A reply that arrives after the client's timeout
   is reported to the caller as `unknown` with the operation or request to check, never as a failure that invites a
   retry. Test the review's case: a save acknowledgement held 11 seconds at `sqlite_prepared` is not reported as a
   failure; the caller is told the outcome is unknown and how to check it, and the committed result is visible
   afterwards. One more test for an upload or account-setup request.

4. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-14.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 22" section: each finding, what changed, the files changed and why, the tests by name. Run IDs
   as before: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes) and
   the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on the final
   head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where the
new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `99280cd0` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Fail closed: a write that didn't complete is undone and reported as a full disk; what was observed is returned; a reply
that may have been committed is `unknown`, never a failure.

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
  test_restore_batches test_review21_pending test_review21_storage`, plus your new plain-Python tests. Aim for one push
  with the code and tests and one with the report. Don't start extra manual workflow runs. For the second pass on the
  final head, rerun the same pull-request run with `gh run rerun <id>`; never push again just to get another run. Keep
  it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: journal write integrity and error classification, on code it wrote.
