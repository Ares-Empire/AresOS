# 14w: Owner raised the Actions budget to $3; push 14v, probe 11 and qualification 3

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14v still apply, with the change below.

## Owner decision (2026-10-27, about 01:00 local)

The Actions budget is now **$3**, with prevent_further_usage still true. Paid use can never go past $3. October's free minutes are spent (about $0.08 has been charged so far).

**Guard:**
- Budget amount **3**. Deduct the net Actions spend already charged, as in 14t.
- Settings for package `14` only:
  - `minute_cap`: **700**
  - `dispatch_caps.probe`: **11**
  - `dispatch_caps.owner-tools`: **3**
- Reserve 0 and closing reservation 0 for October stay as they are.

## Then

1. Pinned local gitleaks, the replay and strict checks. Exactly **one** push, carrying 14s, 14t's bookkeeping and the 14v fix.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 11**. Only if it passes, **qualification 3 on the same head**.
4. **Artifact scan:**
   - Use the 14v whole-line kernel X.509 class plus the 14s ISO listing.
   - Anything else is a STOP. But if the only open item is an artifact finding and the probe passed, stop before the qualification and report the exact lines, as in 14t.
5. Any stop: report it, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, and mark PR #13 ready for review. Then say the run is over, so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
