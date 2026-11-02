# 14zc: Owner raised the Actions budget to $6; push 14zb, probe 15 and qualification 5

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zb still apply, with the change below.

## Owner decision (2026-10-27, about 21:50 local)

The Actions budget is now **$6**, with prevent_further_usage still true, so paid use can never go past $6.

**Guard:** budget amount **6**; deduct the net spend already charged, as in 14t. Settings for package `14` only:
- `minute_cap`: **1100**
- `dispatch_caps.probe`: **16**
- `dispatch_caps.owner-tools`: **6**

That allows one more round after this one if needed, each with a fresh guard. Reserve 0 and closing 0 for October stay as they are.

## Then

1. Pinned local gitleaks, the replay and strict checks. Exactly **one** push, carrying 14zb.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 15**. Only if it passes, **qualification 5 on the same head**, using the fixed watcher.
4. The artifact rules from 14v apply.
5. Any stop: report it with the exported diagnostics, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
