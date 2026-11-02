# 14p: Pass REHEARSAL_MODE to the native loop test; probe 8 and the qualification now

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14o still apply, with the change below.

**Stop:** probe 7 passed all 329 native tests. Then `os/ci/owner_devices.py` asserted `REHEARSAL_MODE in ('probe','owner-tools')`. The "Qualify tools, regressions, rewritten release identity and private access" step doesn't set `REHEARSAL_MODE` in its `env`, unlike the capability step before it. A wiring bug.

## Fix

1. Add `REHEARSAL_MODE: ${{ inputs.rehearsal }}` to that step's `env`. Keep `sudo -E env -u GH_TOKEN` as it is, so the variable reaches the script.
2. Add a static test: every workflow step that runs a script reading `REHEARSAL_MODE` (`owner_devices.py`, `owner_capabilities.py`, and any other) declares it in that step's `env`. The test parses `os-image.yml` and fails if it's missing.
3. Commit your local probe 7 STOP report together with the fix.

## Budget (owner decision, 2026-10-26: use October's remaining minutes now)

The other org repos have no scheduled workflows, and unused October minutes expire anyway. Billing showed 1,795.19 used at about 21:40Z. Set for package `14` only:
- `minute_cap`: **460** (265 consumed + 6 for this push + the 184 bound = 455).
- `dispatch_caps.probe`: **8**. `owner-tools` stays **2** (1 is used).
- `organization_budget.other_repos_reserve`: **0**.

## Then

1. Pinned local gitleaks, the replay and the strict checks. Exactly **one** push.
2. Fresh exact-head privacy, the ledger and billing.
3. **Probe 8**. Only if it passes, the **second qualification on the same head**.
4. If the org runs out of minutes mid-run, GitHub stops the job. Record it as a STOP; the rest waits for November.
5. Any other stop: report it, no rerun.
6. No other push until the qualification finishes.
7. When acceptance is met, put the reserve back to **150** in a final commit and mark PR #13 ready for review. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
