# 18-review-fixes: fix the package review's findings on the control base

**Goal:** fix the four findings in `reviews/18-control-base/REVIEW.md` (fresh `gpt-6.1-sol` review of head
`a684496`) on the same branch, each with a test that fails before the fix and passes after it. Nothing else changes.

## Background (read first)

- `briefs/18-control-base.md` (the package brief; its scope, out-of-scope list and rules still hold).
- `reviews/18-control-base/REVIEW.md` (the findings, with locations and suggested fixes).
- `reviews/18-control-base/REPORT.md` and `control/README.md` (what was built).
- The design: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`, rules 4.1, 4.3, 4.4
  and 4.10.

## What to fix

1. **Finding 1 (blocking), failed-save cleanup** (`control/aresos_control/files.py`, `save`). Cleanup must never
   act on a pathname whose identity was checked earlier: a replacement made between the check and the unlink must
   survive. A refused save must not leave the exported bytes behind under any name, including a hard-link alias
   made during the transfer (rollback works on the pinned inode we created, for example by emptying it through
   its descriptor, and only then deals with the name). If some residue can't be avoided on Linux, the result must
   say exactly what is left and where, never "refused" while the bytes stay readable. Tests: a replacement during
   cleanup survives untouched; an alias made during the transfer no longer holds the bytes after a refusal (or is
   reported precisely).
2. **Finding 2 (blocking), expiry after the adapter checks** (`control/aresos_control/engine.py`, `submit`).
   Check expiry again after `revalidate()` and `has_submission_evidence()`, immediately before recording
   `submitting`. On expiry: record `failed` (nothing submitted), call the adapter's `drop`, submit nothing. Tests:
   the deadline crossed during each of the two adapter checks gives `failed`, no receiver arrival, and the same
   result when the approval is sent again.
3. **Finding 3 (should-fix), positive far-side evidence** (`engine.py`, `submit`). When the adapter finds
   submission evidence before submitting, durably move the operation to `unknown` with the evidence and an
   explanation, so it can no longer be cancelled or expire as "nothing submitted". Tests: extend the existing
   pre-flight evidence test to cover a following cancel and a following expiry; both must leave `unknown`.
4. **Finding 4 (should-fix), large hook input** (`control/aresos_control/hooks.py`, `main`). Read the complete
   hook input and parse it inside the error handling. Valid input of any size Claude Code documents (a long pasted
   prompt, Stop's last assistant message) must still produce the reminder. If you set an input limit, it must be
   far above normal use and a refusal must give Claude Code explicit, event-appropriate feedback, never a silent
   crash. Tests: subprocess tests for both hooks with an input over 64 KiB while work is pending.

Then update `reviews/18-control-base/REPORT.md`: a short "Review fixes" section that maps each finding to the
change and its test, with the workflow run IDs. Don't rewrite the rest of the report.

## Out of scope

Everything outside these four findings. Ideas or further findings go in the report as **PLAN-GAP** or
**JUDGMENT-CALL**, not into the code. Same out-of-scope list as `briefs/18-control-base.md` (`os/`, `mod/`,
`docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`,
`docs/control/FEATURES.md`). Don't edit `reviews/18-control-base/REVIEW.md`.

## Acceptance

- Each finding has a test that fails on `a684496` and passes after the fix; say in the report that you saw it fail.
- All existing tests still pass; none weakened, skipped or deleted.
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
- Keep it to about 8 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: small, careful fixes with tests.
