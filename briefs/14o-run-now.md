# 14o: Owner decision: run probe 7 and the qualification now, not on 1 November

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14n still apply, with the change below.

## Decision (owner, 2026-10-26)

Run now. I checked the other Ares-Empire repos: none has a scheduled workflow. They only run privacy checks (and Arestoteles' CI) on push and pull request. If October's minutes run out, the only effect is that their checks pause until 1 November. So the 150-minute reserve wasn't protecting anything operational.

The billing API reported 1,786.19 of 2,000 used at about 20:50Z, so about 214 are free.

Set these in `os/ci/rehearsal-packages.json` for package `14` only, and refresh any bindings that cover the file:
- `minute_cap`: **440**. That is 249 consumed plus 6 for this push, plus the 184 bound (probe 42, qualification 130, closing privacy 12), which comes to 439.
- `dispatch_caps.probe`: **7**. `owner-tools` stays **2** (1 is used).
- `organization_budget.other_repos_reserve`: **20**. That is about 208 free after this push, minus the 184 bound, which leaves about 24.

## Then

1. Commit together with your local 14m/14n work. Run the pinned local gitleaks, the local replay and the strict checks. Make exactly **one push** (fast-forward).
2. Get fresh exact-head privacy, the ledger and billing.
3. Run **probe 7**. It includes 14n's native loop-image test. Only if it passes, run the **second qualification on the same head**.
4. If the guard refuses, or any run stops, stop and report. No rerun, and don't lower anything.
5. Avoid any other push until the qualification has finished.
6. When acceptance is met, put the reserve back to **150** in a final commit and mark PR #13 ready for review. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
