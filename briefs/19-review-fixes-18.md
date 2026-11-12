# 19-review-fixes-18: repairs are idempotent, restore always has room, the journal has a lifecycle

**Goal:** close security review 10 (`reviews/19-mail/SECURITY-REVIEW-10.md`, head `eead1eb5`; read it first). It used
the owner's new bar (decision 24: AresOS is normal Claude Code plus our tools; the tools must be safe in themselves
and no worse than normal Claude Code; a tricked Claude going around them from the terminal is accepted as normal-OS
risk). No prompt-path bypass, credential leak or destructive free action was found; approvals, replay and prepare
reuse held. One blocking finding and two should-fixes remain; fix all of them in this round. Approved by the lead on
2026-11-08. Briefs 19 and `19-review-fixes` to `-17` still apply where this brief doesn't change them; where in doubt,
their "If unsure" rule decides.

## What to build

1. **Repairs are idempotent and can't lock out recovery** (blocking). `mail_operation_repair` with
   `stage="sent_copy"` on an already completed send (`engine.py` around line 174) creates a new operation and three
   journal transactions every time, although nothing needs repairing, and these consume the recovery reserve. The
   review completed one send, kept another approval pending and repeated that repair: cancel then returned
   `storage_limit`; after restoring the backup from just before the last repair, restore confirmation returned
   `storage_limit` and archive returned `restore_required`, so no recovery command could proceed.
   - A repair of a stage that is already complete returns its existing result and writes nothing (no new operation,
     no journal transaction, no audit growth beyond what a read writes).
   - An ineligible repair (wrong action, missing DATA acceptance, unknown stage, stage not failed) is refused before
     anything is recorded.
   - Restore confirmation, and whatever a restore needs to finish (the archive step it unblocks, if that is part of the
     path), gets its own capacity that no ordinary tool call can consume, repairs included. Free work and repairs stop
     at their own limits first; restore confirmation always has room.
   - Regressions: the review's exact sequence ends with cancel and restore confirmation working; a repeated repair of a
     completed stage writes nothing (journal, SQLite and audit sizes unchanged); restore confirmation succeeds with
     ordinary capacity exhausted.

2. **The independent journal has a supported lifecycle** (should-fix, do it now). The independent journal
   (`storage.py` around line 208) counts toward the same 1 GiB limit and archiving never shrinks it, so once it nears
   832 MiB, archiving can't free space. Provide a lifecycle that keeps the restore and replay guarantees, for example:
   closed journal segments exported with the owner's archive file, with a hash anchor kept so restore detection and
   replay still verify; or separate capacity accounting for the journal. Say which you chose and why, and what the
   owner runs (the existing owner-only archive step, extended). Test that the cycle frees space, that a restore of an
   older store is still detected and refused until the owner confirms, and that replay still refuses old ids.

3. **Remove the remote-settings cache check** (should-fix, do it now). Under decision 24 it goes anyway, and today
   `boundary.py` (around line 81) makes the service user traverse `~/.claude`, so a private home directory gives
   `boundary_not_installed` even with no cache. Remove the `~/.claude/remote-settings.json` check from the service, and
   remove the subscription-only login restriction round 17 added to brief 18b's harness launcher
   (`control/boundary/launch.py`), restoring its earlier behaviour. Keep the managed drop-in checks and everything else
   from round 17; slimming the managed settings to the ask rules is a separate follow-up after merge, not this round.
   Update the round-17 report text and tests that relied on these two checks, naming each change.

4. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-10.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 18" section: each finding, what changed, the files changed and why, the tests by name. Update
   the owner-section archive line if what the owner runs changes. Run IDs as before: in `REPORT.md`, the runs of the
   last commit that changes code or tests (both workflows, both passes) and the statement that any later commit
   changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and the managed-settings slimming. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`. Change brief 18b's
`control/boundary/` only as point 3 says. Brief 18's tests under `control/tests/` change only by additions or where
the new rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `eead1eb5` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted beyond the round-17 expectations point 3 removes (named in the report).
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Write nothing for a repair that has nothing to repair; keep restore's room separate from everything else; never drop
a guarantee that lets restore and replay be verified.

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
  test_ingress_bounds test_journal_closed test_policy_sources test_archive`, plus your new plain-Python tests. Aim for
  one push with the code and tests and one with the report. For the second pass on the final head, rerun the same run
  with `gh run rerun <id>`; never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (point 1, point 2, point 3).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: storage and recovery semantics, on code it wrote.
