# 19-review-fixes-21: holds sized by real work; replay uses its own hold; exports admitted; late duplicates reported

**Goal:** close security review 13 (`reviews/19-mail/SECURITY-REVIEW-13.md`, head `53a2d391`; read it first). It found
no approval bypass, and replay sent once from three calls. Four blocking points remain, all about recovery, plus one
should-fix. Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-20` still apply where this brief
doesn't change them; where in doubt, their "If unsure" rule decides.

## The bar for this and the next review (lead decision, 2026-11-08)

Record this in `REPORT.md` as the lead's decision (not the owner's), and say it in the relevant tool descriptions:

- Cancel applies only to a reserved operation: prepared, never submitted. Such an operation expires within 15
  minutes, and submitting it still asks the owner. A cancel that fails on a full disk is an availability problem, not
  a safety one.
- No ledger can hold disk space against the other programs on the laptop (Claude's own file writes, downloads),
  because they share the filesystem.
- What the service guarantees on a full or nearly full disk is that it **fails closed**: no send, delete or
  unsubscribe runs without its approval, twice, or differently; nothing is reported as done when it isn't; no record
  is lost or corrupted; and it says plainly that the disk is full.
- Reservations protect cancel and restore confirmation against the service's own writes only; beyond that they are
  best effort.
- On a normal disk, nothing may refuse without cause.

## What to build

1. **The restore hold is sized by the actual work** (review finding 3; a real bug at any disk size, since the hold grows
   with retained history). `storage.py` (around line 328) charges every retained operation, including unchanged
   completed ones. Charge only the operations that need reconstruction. Tests: the review's case (100 retained
   operations, a backup, one metadata write, then a restore with 8 MiB free) needs roughly zero hold for zero
   reconstructions, and confirmation succeeds; 10,000 retained operations on a normal disk restore and confirm with a
   hold that matches the operations actually reconstructed.

2. **Replay of an interrupted write uses its own reservation** (review finding 2; double counting). A cancel
   interrupted at `sqlite_prepared` replays on restart from the hold it already had, not as additional work on top of
   it. Test the review's case: free space equal to the floor plus that hold, a crash at `sqlite_prepared`, and the
   restart serves `operation_status` and finishes the cancel. Check the other reserved writes (restore confirmation,
   repair settlement) replay the same way and test one of them.

3. **Caller exports go through the ledger** (review finding 1). `files.py` (around line 128) writes the Downloads file
   without admission. The Downloads write and the private export blob are admitted as ordinary work before writing.
   `ENOSPC` (or any write error) from the filesystem is reported cleanly as a full disk, with nothing half-written left
   behind (no partial Downloads file, no orphaned blob). The report states the limit from the bar above: other
   programs on the laptop can still use the space. Tests: the review's case (pending approval, 12 MiB free, a 5 MiB
   uncached attachment save) is refused before writing, or succeeds with cancel still working; an injected `ENOSPC`
   during the Downloads write and during the blob write leaves nothing behind and reports the full disk.

4. **Late Sent duplicates are reported whenever they're seen** (review finding 4). Every evidence read of a Sent-copy
   stage (`mail_operation_status`, repair, settlement) counts copies by Message-ID in Sent and reports a duplicate
   warning when there is more than one, through the result and the existing bounded notice path (once per detection,
   not a growing stream of notices). Nothing is deleted. Test the review's case: settled `failed` after 901 seconds, a
   successful retry, then the original APPEND lands; the next `operation_status` shows the warning and a notice exists.

5. **Pending results are streamed** (should-fix, do it now). `engine.py` (around line 54) builds every pending
   description before cutting the page. Stream pagination and cursor calculation so only the returned page's
   descriptions are built. Test with 10,000 unknown operations: the page is correct, the cursor works, and peak memory
   stays under a fixed bound independent of the count.

6. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-13.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 21" section: the lead's bar (above), each finding, what changed, the files changed and why, the
   tests by name. Update tool descriptions where the bar changes what Claude should expect (cancel on a full disk, the
   export limit). Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code or tests (both
   workflows, both passes) and the statement that any later commit changes only files under `reviews/`; in the PR
   body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Brief 18's tests under `control/tests/` change only by additions or where the
new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `53a2d391` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Fail closed and say the disk is full; never report done when it isn't; never refuse on a normal disk without cause.

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
  test_restore_batches`, plus your new plain-Python tests. Aim for one push with the code and tests and one with the
  report. Don't start extra manual workflow runs. For the second pass on the final head, rerun the same pull-request
  run with `gh run rerun <id>`; never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: ledger accounting, replay and evidence reads, on code it wrote.
