# 19-review-fixes-10: no automatic undo after a role race

**Goal:** close security re-review 3 (`reviews/19-mail/SECURITY-REVIEW-3.md`, head `5c93fbe0`; read it first). Round
9's automatic undo is itself a non-atomic action with the same race: it can move mail into a folder that just became
Trash or into a replaced source folder, and the copy undo can expunge the last surviving copy. Remove the undo
entirely: after a race, nothing is moved back and nothing is deleted; the owner is told exactly where the messages
are. Separators, blob origin, `operation_status` and whitespace are confirmed closed. Approved by the lead on
2026-11-07. Briefs 19 and `19-review-fixes` to `-9` still apply where this brief doesn't change them; where in doubt,
their "If unsure" rule decides.

The branch now contains `main` (merged by the lead at `5c93fbe0`). Build on the current head.

## What to build

1. **After a move or copy, check, report, and touch nothing** (re-review finding 1). Keep round 9's checks before
   the action, the audit-log intent and the post-check. Remove every automatic undo (the `UID MOVE` back and the copy
   `UID EXPUNGE` in `control/aresos_control/mail/filing.py` and anything calling them).
   - If the post-check finds that a role changed, or that the target now holds a protected role (Trash, Drafts, or an
     optional role whose rules forbid the change), the service does nothing destructive and moves nothing back. The
     result is `partial` (the existing outcome name; never `done`). It names the exact current location of every
     message, using the new UIDs from the server's `COPYUID` answer, and says in plain words: "The special folders
     changed while Claude was moving these messages. Nothing was deleted. They are now in <folder>, which is now
     <role>. Check them in your mail program." For a copy: "… while Claude was copying these messages. Nothing was
     deleted. The copies are now in <folder>, which is now <role>; the originals stayed in <source>. Check them in your
     mail program."
   - Claude sees that text in the result, and the owner gets the same text as a notice: it shows in every following
     Mail result and in the owner's `aresos log` until acknowledged (use the base's existing notice mechanism and
     `mail_notice_ack`).

2. **A copy never expunges anything** (re-review finding 2). A copy that landed in a protected folder stays there and
   is reported as in point 1. Cleaning it up is an ordinary `mail_delete`, which asks the owner.

3. **Residual, as a JUDGMENT-CALL in the report:** if a role moves to the target and back between the `MOVE` and the
   post-check, the result can be `done` with the messages in the intended target. That target is not a protected
   folder at the end, so nothing is lost. Say so in plain words in the round-10 section and in "For the owner:
   decisions before merge", replacing round 9's undo judgment call.

4. **Should-fix: the outcome is always recorded.** `locations()` also catches `Uncertain` (connection loss), keeps the
   observations collected so far with `scan_complete=false`, and the final outcome is always persisted. The audit
   intent never stays `started`.

5. **Tests**, through the real adapter path with the scripted IMAP frontend:
   - The re-review's three reproductions: Trash reassigned to the now-empty source after the `MOVE`; the source folder
     replaced before the old undo point; the original of a `COPY` removed by another client before the post-check.
     Each ends `partial` with every message preserved (checked on the server, nothing expunged, nothing moved back),
     its location reported exactly, the plain-words text in the result and in the owner's notice, and zero approval
     operations used.
   - The race points of round 9's tests (Trash, Drafts, Archive; before the `MOVE` and between the `COPY` and the
     post-check) now expect this outcome instead of an undo; change only those expectations, name each in the report
     and keep every other assertion.
   - Connection loss during the location scan: the outcome is persisted with `scan_complete=false` and the
     observations so far; the intent is not left `started`.
   - Ordinary moves and copies with stable roles still end `done`.

6. **Report.** Link `reviews/19-mail/SECURITY-REVIEW-3.md` from `REPORT.md` next to the other review files. Add a short
   "Review fixes, round 10" section: each finding, what changed, the tests that prove it by name, the changed earlier
   expectations. Update "For the owner: decisions before merge" and the PR body to match, in plain words. Run IDs: in
   `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes) and the statement
   that any later commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
`control/tests/`, and the workflow files under `.github/`.

## Acceptance

- Each point has regression tests that would fail on `5c93fbe0` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted beyond the undo expectations point 5 changes.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Leave the mail where it is and tell the owner. Never move or delete to recover. Take the option that keeps a mail
from being sent twice, sent without its approval, or moved into Trash, out of Drafts or deleted without approval, and
say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Every push to the PR starts the Mail,
  base and boundary workflows (they run on the pull request only). Before each push, run locally everything that
  doesn't need containers (Docker isn't available on this Mac): `python3 control/generate.py --check`, a syntax check
  of every `control/**/*.py`, and the plain-Python test classes (`unittest.TestCase` subclasses that need no mail
  server, for example in `control/mail_tests/test_review_fixes_*.py` and `test_dkim.py`, and your new ones). Batch
  your commits into as few pushes as you can, ideally one for the code and tests and one for the report. For the
  second pass on the final head, rerun the same run with `gh run rerun <id>`; never push again just to get another
  run. Keep it to about 6 workflow runs in all.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: removing a recovery path safely, with race tests on code it wrote.
