# 19-review-fixes-26b: owner-visible state is read from the journal, not kept beside it

**Goal:** an amendment to round 26 from the lead (2026-11-08). Review 18's findings 2 and 3, and earlier the lost
duplicate counts (round 21) and the lost observations (round 23), share one cause: owner-visible state is kept beside
the journal, in memory or a cache, instead of being read from it. Close that class with one rule rather than more
paths. Round 26's item 1 (bounded responses) and item 4 (should-fixes) stay as built; this round makes round 26's
items 2 and 3 instances of the rule below. Briefs 19 and `19-review-fixes` to `-26` still apply where this brief
doesn't change them; where in doubt, their "If unsure" rule decides.

## The rule (lead decision, round 26; record it in `REPORT.md` as the lead's)

- **R1.** Every fact the owner must learn is computed when it is read: pending items, filing and duplicate warnings,
  notices, refusals and their reasons, admission state. It comes from the committed journal plus live checks such as
  current free space. Nothing the owner must learn lives only in memory or in a cache that outlives its cause. Memory
  may hold extra detail (observation pages, a held warning's exact wording), but never the only copy of a warning.
- **R2.** Whatever is needed to warn is committed before the remote action. The intent record, written before MOVE,
  COPY, RENAME, send, APPEND, delete or unsubscribe, carries enough to derive the owner's warning if the outcome never
  gets recorded: message, source, destination, the role at preparation, recipients. An intent left `started` is itself
  a warning, until resolved.
- **R3.** A refusal is a function of current state and is recomputed on every call. Only the transaction latch persists
  (a journal write that may have started), and recovery clears it. Index admission, ledger admission and blob admission
  are rechecked each time.

## What to build

1. **First, the note (before any code).** Under the round-26 section of `reviews/19-mail/REPORT.md`, write a short note
   (about one page): an inventory of every owner-visible fact (pending items, each warning and notice kind, each
   refusal and its reason, admission states, anything else), its current source (journal, SQLite state, memory, cache),
   and its source under R1–R3. Commit it on its own.

2. **Stop condition.** If R1–R3 need a migration that changes the format of records already committed (the journal or
   the independent record), or are otherwise clearly bigger than one round, **stop after the note**: add a PLAN-GAP to
   the note saying what would have to change and roughly how big (files, records, migration, tests), commit and push the
   note, and end the run with that as your final message. Don't build it. Adding new fields to records written from now
   on, with old records read compatibly, is not a migration of committed records and doesn't trigger the stop.

3. **Then implement R1–R3.**
   - Owner-visible facts are derived on read from committed records plus live checks. `deferred_notices` (and any other
     in-memory or cached owner state the note finds) may stay only as extra wording on top of a committed source, never
     as the only copy.
   - Intent records written before each remote action carry what R2 lists. An intent left `started` produces a warning
     in `control_pending` and the app's notices until resolved (this replaces or subsumes round 26's recovery notices).
   - Every refusal is recomputed per call; only the transaction latch persists, and recovery clears it.

4. **The sweep checks the rule once, not path by path.**
   - After every fault point, plus a restart or space restored, the owner-visible warnings equal those derived
     independently from the test servers' own logs (what was moved where, what was sent, appended, deleted or
     unsubscribed, and the roles at the time).
   - No refusal remains on a healthy disk without a restart.
   - Keep the per-flow counts in the log, and keep each Mail job under about 30 minutes (the sweep's shards may change in
     `control-mail.yml` for that only, with `timeout-minutes: 45` kept).

5. **Report.** The note (point 1) plus a "Review fixes, round 26b" section: what changed, the files changed and why, how
   the sweep checks the rule, the tests by name. Update round 26's tables where an entry's closure is now the rule. Run
   IDs as before: in `REPORT.md`, the runs of the last commit that changes code or tests (all workflows, both passes) and
   the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/` other than `control-mail.yml` as point 4 allows. Brief 18's tests under
`control/tests/` change only by additions or where the rule forces it; name each change and keep its assertions.

## Acceptance

- The note exists and lists every owner-visible fact with its source under R1–R3.
- Either the stop condition applies (note and PLAN-GAP pushed, nothing built), or R1–R3 are implemented with tests that
  would fail on round 26's head and pass now, and the sweep checks the rule as point 4 says. No earlier test is weakened,
  skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Derive it from what is committed and what is live; commit what is needed to warn before acting; recompute refusals.
If the change would rewrite committed records, stop and say so.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and the base tests you ran in round 26, plus your new plain-Python tests (including as much of the sweep as runs
  without containers). Aim for one push with the code and tests and one with the report. Don't start extra manual
  workflow runs. For the second pass on the final head, rerun the same pull-request run with `gh run rerun <id>`; never
  push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (the note first).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a state-derivation rule across the base and Mail, on code it wrote.
