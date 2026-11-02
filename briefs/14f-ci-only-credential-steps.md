# 14f: Steps that need the CI job's package access are CI-only in the local replay

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14e: Actual zero-cost job replay" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14e still apply, with the change below.

## Integrator decision

Stopping was right, and so was not touching any credential.

**The rule's purpose:** brief 14e's replay rule is meant to catch deterministic mismatches for free: code, history, files and frozen records. That was the kind of thing that cost the first probe. It was never meant to grant the laptop new access.

**Why this step is different:**
- `gh api orgs/Ares-Empire/packages/container/aresos` (in `registry_auth.preflight`), the registry digest inspect, the pull and the signature checks against the registry are live checks with the job's own `GITHUB_TOKEN` (`packages: read`). The laptop's `gh` login doesn't have that scope.
- Package 13 already passed this same path in CI (`job_token_read.status == passed` in the frozen release record).

So:
1. **Classify** every replay step that needs credentials or access only the CI job has (package metadata, registry inspect, pull, registry signature checks) as **CI-only**.
   - Record each one in the replay result, with its reason and the CI step that checks it.
   - Every other replay step must still pass locally before dispatch, as 14e says.
2. **Don't change any credential or scope:**
   - Don't refresh or add scopes to the local `gh` login.
   - Never read, use or substitute any owner secret.
   - The CI-only steps stay fail-closed in CI, exactly as they are.
3. **If a CI-only step fails** in the probe, stop and report it. That would mean the live package state has changed, which is a real stop. Don't rerun.

## Then

Recheck the ledger, billing and privacy CI right before the dispatch, then send the fresh probe (2/2), then the qualification, per briefs 14 to 14e. The final package review covers this. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
