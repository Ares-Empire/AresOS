# 14e: Bind the package 13 release to its squash merge, then a fresh probe

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14d: Actual continuation and PLAN-GAP" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14d still apply, with the change below.

## Integrator decision

The gate was right to stop, and right not to remove the check or rerun the probe.

**Why it failed:** our workflow merges every PR with `gh pr merge --squash` (docs/WORKFLOW.md step 6). The package 13 image was built and signed on its branch at `2abc12e`. Main got one squash commit, `775be05`, instead of that history, so "is the source an ancestor of HEAD" can never pass on main.

**What I verified** (read-only):
- PR #12 is merged, its merge commit is `775be05b7f0d6971cbdc8a3bd1aea617fc008c4d`, and its head branch is `pkg/13-keyboard-layout`.
- `2abc12e` is an ancestor of PR #12's head, fetched from `refs/pull/12/head`. GitHub keeps that ref after the branch is deleted.
- `775be05` is an ancestor of this branch's HEAD.
- The eight-path runtime payload is identical from `2abc12e` to `775be05` and to HEAD.

The ancestry check's purpose is "the signed source is code we reviewed and merged". With squash merges, that purpose is met by binding the source to its merged PR. The file `verify_release.py` already does the same for the earlier history rewrite (the pinned `rewritten` commit).

So:
1. **In the org path of `os/ci/verify_release.py`**, replace only the `merge-base --is-ancestor source HEAD` step with this binding, pinned in code like the existing `rewritten` path:
   - PR `12` of `Ares-Empire/AresOS`, read through the API:
     - it is merged
     - its `merge_commit_sha` is exactly `775be05b7f0d6971cbdc8a3bd1aea617fc008c4d`
     - its head ref is `pkg/13-keyboard-layout`
     - its base is `main`
   - Fetch `refs/pull/12/head`. The source must be an ancestor of it.
   - `775be05` must be an ancestor of HEAD.
   - Keep every other check exactly as it is: the run identity and branch, the job success, the signature identity, the release fields, the job-token read, the image diff, and the payload `git diff --exit-code source HEAD`.
2. **Refusal tests** for each broken link, each failing closed:
   - PR not merged
   - a different merge commit
   - a different head branch or base
   - the source not in the PR head's history
   - the merge commit not an ancestor of HEAD
   - any payload difference

   Use local fixture repos or stubs. Spend no CI minutes on these.
3. **Zero-cost replay before every dispatch:** before any workflow dispatch, run locally every step of that job that needs only git, files or read-only `gh api` (this verifier included). Dispatch only if all of them pass. This stop cost a probe that a local replay would have caught.
4. **Budget:**
   - One fresh probe allowance (2 probes in total for package 14; the first one is spent).
   - Qualifications stay at 2. Cap 350 minutes. Org reserve 150 minutes.
   - Recheck the ledger and billing right before the dispatch, as before.

## Then

Continue exactly where 14d stopped:
- local replay
- the fresh probe gate
- the qualification, per briefs 14, 14b, 14c and 14d

The final package review covers this verifier change. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
