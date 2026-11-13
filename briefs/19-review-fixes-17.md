# 19-review-fixes-17: every managed policy source is checked; recovery never runs out of room

**Goal:** close security review 9 (`reviews/19-mail/SECURITY-REVIEW-9.md`, head `9278b000`; read it first).
Everything else held (all 52 policy mutations refused, ancestors, MIME limits, exceptions, caps, no approval bypass).
One blocking finding and one should-fix remain; fix both in this round. Approved by the lead on 2026-11-08. Briefs 19
and `19-review-fixes` to `-16` still apply where this brief doesn't change them; where in doubt, their "If unsure"
rule decides.

## What to build

1. **Every managed policy source is checked** (blocking). Claude Code merges `/etc/claude-code/managed-settings.d/*.json`
   after the main managed file. Those drop-ins are managed policy, so `--setting-sources ''` and
   `allowManagedPermissionRulesOnly` don't exclude them, and `boundary.py` (around line 71) never looks at them. The
   review kept both checked files exactly as generated, added `managed-settings.d/99-open.json` with an
   `excludedCommands` entry and a Bash allow rule for `aresos *`, and `Boundary.require()` passed; the CLI then sent
   mail with no prompt. A `managed-settings.d` symlink to an allowed Documents folder would also let a saved
   attachment become policy.
   - First read the current Claude Code documentation end to end (code.claude.com: managed settings, settings,
     server-managed settings if documented) and list in `REPORT.md` every policy source Claude Code reads on Linux:
     the main file, drop-ins, managed MCP, any server-managed or remote policy, and any other path. Mark claims
     **read** with the page and date.
   - Check every one of them. For now, refuse with `boundary_not_installed` unless `managed-settings.d` is absent, or
     is a real root-owned directory (not a symlink, not writable by group or others) with no entries at all. Any
     symlink anywhere in the managed paths refuses. Any other policy source found in the documentation is either
     checked the same way (absent, or exactly as generated) or explained in the report as not applicable on this
     system, with the reason.
   - If server-managed or remote policy exists for this account type, say in the report how it is excluded or
     checked (and test it if it is a local file or setting).
   - Write one design-ready sentence in the report: decision 22 will later add vetted additions, possibly as
     drop-ins; then the check must compute the merged policy in Claude Code's documented order and compare it with
     the generated policy plus the vetted additions. Don't build that now.
   - Regressions: the review's drop-in refuses (naming it); a symlinked `managed-settings.d` refuses; a symlinked parent
     of the main file refuses; an empty real `managed-settings.d` passes; a non-empty one (any file, also a non-JSON
     file) refuses.

2. **Recovery never runs out of room** (should-fix, do it now). Repeated free `mail_prepare_send` on one unchanged
   composition grows the operation history past the admission reserve (`engine.py` around line 329); then
   `mail_operation_cancel`, `mail_notice_ack`, `mail_operation_repair` and the owner's `control_restore_confirm` all
   return `storage_limit`.
   - Give safety and recovery actions (cancel, acknowledge, repair, restore confirm, and anything else that only ends
     or repairs something) a reserved capacity that free work can't use. Free work hits its limit first, with a clear
     refusal; the reserved actions keep working.
   - Repeated preparation of the same unchanged composition must not grow history: reuse the existing pending
     operation for it (same approval, same id, while it is still `reserved` and unexpired), or cap pending
     preparations per composition. Say which you chose and why.
   - Provide a supported owner-only archive step (over `admin.sock`, `sudo aresos admin …`) that exports old finished
     history to an owner-readable file and compacts the store, keeping open operations, unacknowledged notices, the
     independent record's guarantees and restore detection intact. Test that the journal stays valid and a restart
     reports no corruption across it.
   - Regressions: the review's repeated-prepare case doesn't grow history (or stops at the cap); with free work at its
     limit, cancel, acknowledge, repair and restore confirm still succeed; the archive step leaves a valid journal.

3. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-9.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 17" section: each finding, what changed, the files changed and why, the policy-source list
   from point 1, the tests by name. Add one owner-section line for the archive step if the owner will use it (what it
   does and when he'd run it), saying it follows the safety rule. Run IDs as before: in `REPORT.md`, the runs of the
   last commit that changes code or tests (both workflows, both passes) and the statement that any later commit
   changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and decision 22's vetted additions. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`. Change brief 18b's
`control/boundary/` only as far as point 1 needs (for example making its launcher or checks aware of the drop-in
directory), and name each change. Brief 18's tests under `control/tests/` change only by additions or where the new
rules force it; name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `9278b000` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. A managed policy source that isn't absent or exactly as generated refuses asking tools; free work stops before
recovery would.

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
  test_ingress_bounds test_journal_closed`, plus your new plain-Python tests. Aim for one push with the code and tests
  and one with the report. For the second pass on the final head, rerun the same run with `gh run rerun <id>`; never
  push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (point 1, then point 2), so the branch is never left half-done if the run stops.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a boundary completeness fix and storage reservation, on code it wrote.
