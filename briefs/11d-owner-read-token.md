# 11d: Reach the signed release with the owner's read-only token, then finish 11c

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11c" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Everything in brief 11c still applies, except the change below.

## What blocked 11c, and the owner's decision

**Cause:** the repo moved to the `Ares-Empire` org. The signed release `ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402` still exists, as a private package owned by the user account. A user-owned package can grant Actions access only to the user's own repos (the integrator checked the package settings on 2026-10-24), so the org repo's ephemeral job token can't read it. GitHub can't transfer the package.

**Owner decision (2026-10-24):** for this rehearsal, CI may read the release with an owner token stored as the Actions secret **`GHCR_READ_TOKEN`**. It is a classic token with only `read:packages`, and it expires in 30 days. This replaces brief 11's "no owner token" rule **only** within these limits:

1. **Read only, one image.** Use it only to read `ghcr.io/carlsenares/aresos` at the pinned digest: the manifest preflight, the pull, and any signature or attestation reads of that same digest. Use username `carlsenares`.
   - no push, tag, delete or visibility change
   - no other package or registry
   - no `gh api` calls with it unless a step can't work without one; record any you make
2. **Only in `workflow_dispatch` rehearsal jobs** (probe and full). Never in `push` or `pull_request` jobs, and never in the publish or build path, which stays disabled.
3. **Never exposed:**
   - Pass it through `env` to the steps that need it.
   - Write the registry auth file under `$RUNNER_TEMP` with mode 600, outside the workspace and outside every artifact path.
   - Delete it in an `if: always()` cleanup.
   - Never echo it and never trace (`set -x`) around it.
   - Never put it in logs, evidence, artifacts or committed files. Don't rely on GitHub's log masking.
   - Evidence names only the secret and its scope, never the value.
4. **Fail closed.** If the secret is missing, expired or rejected, stop and report. Don't fall back to anything else.
5. **Same proof as before:**
   - The digest must resolve to exactly the pinned digest.
   - The existing signature, identity and runtime-equivalence checks stay unchanged.
   - Any step that read package metadata through `users/carlsenares/packages` with the job token must not silently pass. Use the secret within these limits, or record the check as not possible from the org.
6. **Add regressions:**
   - The workflow references the secret only in dispatch rehearsal jobs.
   - The auth file path is outside the workspace and artifacts.
   - Cleanup always runs.
   - The privacy check stays green.

## Then

Fix this in the harness, run a fresh probe on the new commit, then do the full runs exactly as brief 11c says:
- **Part A** in both drive orders
- the Windows-like boot without the Linux disk, after install and again after undo
- offline protected-disk audits and NVRAM diffs at every stage, using the firmware-owned rule from 11c
- **Part B**

All of 11c's stop rules still hold. In particular, a firmware behaviour the 11c contract doesn't cover means stop and report it as a PLAN-GAP.

## Budget

These minutes come from **11c's existing allowance**: **330 rounded minutes and 3 full runs** in total for 11c and 11d together. 11c's ledger already counts what it used. About 420 account minutes are left in October. If the cap is reached, stop and report what's left.

## Acceptance

11c's acceptance, plus an "11d" REPORT section covering:
- how the token was used
- the gate → evidence table
- the minute ledger

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
