# 19-review-fixes-20: one space ledger for every write; restore keeps repair identity; settle an APPEND only when it can't land

**Goal:** close security review 12 (`reviews/19-mail/SECURITY-REVIEW-12.md`, head `d5a0b24a`; read it first), judged
under the owner's decision 24. It found no approval bypass and no second SMTP delivery. Four blocking points remain,
all about recovery staying possible, plus one should-fix. Three of the blocking points are one class: some writer
forgot a floor, or the floors disagree. Rounds 18 and 19 each closed one path and the next path stayed open, so this
round **fixes the class by construction**. Approved by the lead on 2026-11-08. None of this removes a feature. Briefs
19 and `19-review-fixes` to `-19` still apply where this brief doesn't change them; where in doubt, their "If unsure"
rule decides.

## What to build

1. **One space ledger for every write** (review blocking points 1 and 2, and the class behind round 19's).
   - Every durable write goes through one admission function: ordinary calls, repairs, repair settlement, archive,
     restore, restore confirmation, the journal index build, expiry and anything else that writes. No writer has its
     own floor.
   - Space for each recovery right is reserved explicitly, in the ledger, at the moment the right comes into being, and
     released when the right ends:
     - a pending approval holds the space for its cancel record;
     - a pending restore holds the space for its confirmation;
     - an unresolved repair holds the space for its settlement record.
   - No write may take free space below the sum of all held reservations plus one fixed safety floor. A reserved write
     (the cancel, the confirmation, the settlement) uses only its own reservation and needs nothing else.
   - This replaces round 19's separate 64/20/16/4 MiB floors with one consistent rule; remove those floors.
   - **If the index build can't be admitted, the service still starts.** Asking actions refuse with `storage_limit` and
     say why; cancel, restore, restore confirmation and `operation_status` keep working by streaming the journal.
   - Tests replay the review's three sequences, and cancel still works after each:
     - an index rebuild starting at 30 MiB free (2,000 records based on a real delete approval);
     - about 2,150 repeated archives starting at 20 MiB free, with a pending approval;
     - round 19's 38 uncertain repairs.
     Plus: the service starts and serves cancel and status when the index build is refused; reservations are released
     when their right ends (approval sent, expired or cancelled; restore confirmed; repair settled).

2. **Restore keeps repair identity** (review blocking point 3). The permanent evidence carries each repair's
   `repair_of` and `stage`, so a restored unknown repair is found and reused after a restore, like any other. Where
   that relationship can't be recovered (older evidence without it), refuse new repairs for that send's stages, with a
   status that says why, rather than allocating another. Test: the review's sequence (finish SMTP with a failed Sent
   stage, back up, create an unknown repair, restore that backup and confirm, repair again) ends with one unresolved
   repair.

3. **An empty search settles an APPEND only once the old attempt can't still land** (review blocking point 4).
   - An unknown Sent-copy repair can settle to `failed` only when its attempt ended at least a fixed quiet period ago
     (15 minutes unless you find a documented reason for another value; say which and why) and the search runs on a
     fresh IMAP connection.
   - Before that, it stays `unknown`, and the reply says when to try again.
   - After every APPEND of a Sent copy, a read-only count of copies with that Message-ID in Sent reports a warning (in
     the result and through the existing bounded notice path) if there is more than one. Never delete automatically.
   - Test: the review's late-completing APPEND sequence ends with one Sent copy, or with the duplicate warning, never a
     silent duplicate; a settlement attempted inside the quiet period stays `unknown` and names the time.

4. **Restore writes in bounded batches** (should-fix, do it now). `storage.py` (around line 339) collects all missing
   operations into one dictionary and one journal record. Write reconstructed operations in bounded batches with a
   bounded record size, so journal verification memory stays flat. Test with 1,000 and 10,000 restored operations:
   peak verification memory stays under the same fixed bound.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-12.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 20" section: each finding, what changed, the ledger rule in plain words, the files changed and
   why, the tests by name. If the 15-minute wait is worth one owner-section line, add it (it applies only to a rare
   uncertain Sent-copy repair). Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code or
   tests (both workflows, both passes) and the statement that any later commit changes only files under `reviews/`;
   in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where the
ledger replaces a removed floor; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `d5a0b24a` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted (tests of the removed separate floors are replaced by ledger tests covering the same
  guarantees; name each).
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Every write asks the one ledger; a recovery right's space is held from the moment the right exists; uncertainty about
an earlier APPEND stays uncertainty until time or evidence rules it out.

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
  test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming`,
  plus your new plain-Python tests. Aim for one push with the code and tests and one with the report. Don't start
  extra manual workflow runs. For the second pass on the final head, rerun the same pull-request run with
  `gh run rerun <id>`; never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a storage-admission redesign and recovery semantics, on code it wrote.
