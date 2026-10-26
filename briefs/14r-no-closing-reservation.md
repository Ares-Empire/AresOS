# 14r: Don't reserve closing privacy for this October dispatch

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14q still apply, with the change below.

**Stop:** 187 free against a 190 plan: 6 for the push, 42 for the probe bound, 130 for the qualification, and 12 for closing privacy.

**Integrator decision (within the owner's "use October's minutes now"):**
- **Drop the closing-privacy reservation for this dispatch only** (12 → 0). The tests themselves still fit even in the worst case: 6 + 42 + 130 = 178 ≤ 187.
- **The closing privacy checks** run after the qualification. If October's minutes are gone by then, they run, or are re-run, on 1 November.
- **Merge rule:** PR #13 can't merge before its privacy checks pass. That rule is unchanged.

**Keep the guard honest:** apply this as an explicit, recorded setting for package 14's October dispatch. Don't change the probe or qualification bounds. Then:
1. Pinned local gitleaks. Exactly **one** push.
2. Fresh exact-head privacy, the ledger and billing.
3. **Probe 9**. Only if it passes, the **second qualification on the same head**.
4. A guard refusal or any stop: report it, no rerun.
5. When acceptance is met, put the closing reservation back to 12 and the reserve back to 150 in a final commit, and mark PR #13 ready for review. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
