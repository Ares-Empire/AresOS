# 14t: Owner allows up to $1 of paid Actions overflow; probe 10 and the qualification now

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14s still apply, with the change below.

## Owner decision (2026-10-26)

The owner raised the org's Actions budget from $0 to **$1**, with "stop usage when budget is reached" still on. Paid minutes can never exceed $1.

**Guard:**
- Count the available minutes as the included minutes left, plus `floor(budget / price per minute)`.
- Read the budget read-only from `organizations/Ares-Empire/settings/billing/budgets`. Require `budget_product_sku == actions`, the amount you use, and `prevent_further_usage == true`. If prevent is off, or the amount differs, STOP.
- Read the price per minute for the runner SKU from the billing usage API's `pricePerUnit`, not from a hard-coded value.
- Record both in the ledger.

**Settings for package `14` only:**
- `minute_cap`: **520**
- `dispatch_caps.probe`: **10**; `owner-tools` stays **2**
- reserve **0**; closing reservation stays **0** for this October dispatch, as in 14r

## Then

1. Pinned local gitleaks, the replay and strict checks, then exactly **one** push (it carries 14s's race fix).
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 10**. Only if it passes, the **second qualification on the same head**.
4. A guard refusal or any stop: report it, no rerun.
5. When acceptance is met, put the closing reservation back to 12 and the reserve back to 150 in a final commit, and mark PR #13 ready for review. Tell me when the run is over: the owner sets the budget back to $0 afterwards. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
