# 14k: Owner decision: run probe 6 and the second qualification now

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14j: Ledger and both next-resume options" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14j still apply, with the change below.

## Decision

The owner chose to run now in October (2026-10-26), with a smaller reserve for the other repos.

**Why the new numbers:** the bound uses each job's hard timeout (probe 40, qualification 130), plus 12 for closing privacy, so 184 minutes in total. The org has 274 free, which leaves about 90 for the other repos for the rest of October in the worst case. Over October they used about 240 minutes in 25 days. The package cap of 350 is my own number from brief 14, and it's too small for the fixes since then.

Set these in `os/ci/rehearsal-packages.json` for package `14` only, and refresh any bindings or hashes that cover that file:
1. `minute_cap`: **400** (212 consumed + 184 bound = 396).
2. `dispatch_caps.probe`: **6**. `owner-tools` stays **2** (1 is used).
3. `organization_budget.other_repos_reserve`: **80** for this package's remaining October dispatches. Leave package 13's settings unchanged.

Then:
- Pinned local gitleaks before every push. The 14e/14f replay plus the 14i strict composed-command checks.
- Fresh exact-head privacy, the complete ledger and billing.
- **Probe 6** on the pushed head. Only if it passes, the **second qualification on the same head**.
- If the guard refuses because other repos used minutes meanwhile, stop and report; don't lower anything further.
- If either run stops on anything, stop and report, with no rerun. No allowance is left after this.
- When acceptance is met, put the reserve back to **150** in a final commit and mark PR #13 ready for review. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
