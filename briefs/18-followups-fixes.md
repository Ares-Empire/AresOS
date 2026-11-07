# 18-followups-fixes: fence each write in the separate record before the main log

**Goal:** fix the one blocking finding in `reviews/18-control-base/REVIEW-3.md` (fresh `gpt-6.1-sol` re-check of
head `a9c0cbd`) on the same branch, with tests that fail before the fix and pass after it. Nothing else changes.

## Background (read first)

- `briefs/18-followups.md` (change 3, the small separate record, and what must still hold) and
  `reviews/18-control-base/REVIEW-3.md`, finding 3.
- `control/aresos_control/storage.py` (`write`, recovery in `__init__`, `confirm_restore`),
  `control/tests/test_crashes.py`, `control/tests/test_record.py`, and the Follow-ups section of
  `reviews/18-control-base/REPORT.md`.

## The problem

`Store.write` commits the full event to SQLite (`sqlite_prepared`) before appending its entry to the separate
record. A kill -9 there, followed by restoring an older SQLite backup before the service restarts, makes that
operation vanish from both: no `restore_required`, no entry, no `unknown`. The separate record exists precisely
so that a restored main log can't hide an operation, so the record must never be behind the main log. The crash
tests didn't catch it because they restart straight after the kill, which copies the prepared event into the record.

## What to fix

1. **The record entry is durable first.** Each write appends and syncs its compact entry in the separate record
   before anything of that write is committed to SQLite. Message bodies and app data still go only to SQLite and
   the blob store (change 3 of `briefs/18-followups.md` stands).
2. **Recovery never guesses and never drops.** When the record holds an entry whose full event is missing from
   SQLite (a crash between the two, with or without a restore), the operations it names must not vanish: require
   the owner's `restore_confirm` as for any older log, and list them `unknown` with their short descriptions. Only
   if you can prove from durable state alone that a case is an ordinary crash with nothing irreversible after it
   may you recover it without the owner; then say exactly how in the report, and test it. If unsure, fail closed.
3. **Tests that copy the backup first.** For every write boundary (`journal_appended`, `sqlite_prepared`,
   `sqlite_committed`, `journal_committed`, and any new one) in reservation, submission, stage, outcome, repair and
   restore writes: kill -9 there, restore the preceding SQLite backup **before the first restart**, then restart.
   The operation must be either `restore_required` and listed `unknown` after confirmation, or present with an
   honest state; never gone, never sent twice. Keep the existing restart-straight-away crash tests too.

Then add a short "Follow-up fix" section to `reviews/18-control-base/REPORT.md`: the change, its tests, the
failing-then-passing runs, and what an ordinary crash in the new window now costs the owner (for example a
`sudo aresos admin control restore_confirm` after a power loss in that moment). Update `control/README.md` where it
describes the write order. Don't rewrite the rest of the report, and don't edit the `REVIEW*.md` files.

## Out of scope

Everything else, including the other judgment calls. Ideas or further findings go in the report as **PLAN-GAP** or
**JUDGMENT-CALL**, not into the code. Same out-of-scope list as `briefs/18-control-base.md` (`os/`, `mod/`,
`docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`,
`docs/control/FEATURES.md`).

## Acceptance

- The new backup-before-restart tests fail on `a9c0cbd` and pass after the fix; say in the report that you saw them
  fail.
- All existing tests still pass; none weakened, skipped or deleted. If an existing assertion has to change because
  the behaviour changed on purpose, say which and why.
- The workflow passes twice on the final head (push and pull-request runs both count).
- No secrets, real addresses or account names.

## If unsure

Take the option that keeps a send from happening twice or without its approval, and keeps every outcome honest.
Say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/18-control-base`. Commit in small steps and push this branch; draft
  PR #6 already exists, so don't open another. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 6 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a careful change to the write order and recovery, with crash tests.
