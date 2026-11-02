# 14g: Make the PR #12 binding git-only, then a third probe

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14f: Actual fresh gates, final probe and PR-read PLAN-GAP" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14f still apply, with the change below.

## Integrator decision

Stopping was right, and so was not guessing at a permission. The fault is in my 14e design: it put a GitHub API read into a CI path, and the job token can't make that read. Adding a permission without proof could cost another probe.

**The fix: drop the API read from CI and use the precedent instead.** In the same file, the `rewritten` path binds the earlier history rewrite with a pinned commit and git checks only. Do the same here.

The facts the API read was meant to check, I verified with the owner's login on 2026-10-25 (recorded in brief 14e). They become pinned constants:
- PR 12, merged
- merge commit `775be05b7f0d6971cbdc8a3bd1aea617fc008c4d`
- head `pkg/13-keyboard-layout`
- base `main`

## Changes

1. **In the org path of `os/ci/verify_release.py`**, remove the `gh api repos/Ares-Empire/AresOS/pulls/12` read and its four asserts. Keep the pinned constants, with a short comment saying where they were verified.
2. **Keep these git checks** (they need only `contents: read`):
   - fetch `refs/pull/12/head`; the source must be an ancestor of it
   - fetch `775be05`; it must be an ancestor of HEAD
   - `git diff --exit-code` over the payload from the source to HEAD (as now) and from the source to `775be05`
3. **Shallow clones:**
   - The `rehearsal` job checks out with `fetch-depth: 0`. The `switch` job uses the default depth, so its ancestry checks would fail for the wrong reason.
   - Give every job that runs `verify_release.py` the history it needs (for example `fetch-depth: 0` on `switch`).
   - Make the verifier fail closed with a clear message if the repo is shallow.
4. **No new workflow permissions.** Add a test that every `gh api` call left in a job's CI path uses only endpoints that job's declared permissions already cover. Use the existing calls and the package 13 record as the reference. The local login can't prove the job token's access, so this test is the guard.
5. **Tests:**
   - Update the refusal tests: each git link and each pinned constant fails closed when wrong.
   - Add a test for the shallow-clone refusal.
   - Drop the API-mock cases that no longer apply.
6. **Budget:**
   - One more probe allowance (3 in total; 2 are spent, about 11 minutes).
   - One qualification is planned, as in your planning snapshot. The second stays optional, behind its own fresh guard.
   - Cap 350. Org reserve 150.
   - Recheck the ledger, billing and privacy CI right before dispatch.

## Then

Pinned local gitleaks before every push. Local replay as in 14e/14f. Then the third probe, then the qualification, per briefs 14 to 14f. The final package review covers this change. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
