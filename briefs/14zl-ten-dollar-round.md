# 14zl: Owner raised the Actions budget to $10; push 14zk, probe 20 and qualification 9

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zk still apply, with the change below.

**Owner decision (2026-10-28, about 10:45 local):** the Actions budget is **$10**, with prevent_further_usage still true. About $4.46 had been billed before this round.

**Guard:** budget amount **10**; deduct the net spend already charged. Settings for package `14` only:
- `minute_cap`: **1500**
- `dispatch_caps.probe`: **22**
- `dispatch_caps.owner-tools`: **11**

That leaves room for up to two more rounds after this one, each behind its own fresh guard. Reserve 0 and closing 0 for October stay as they are.

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push, carrying 14zk.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 20**. Only if it passes, **qualification 9 on the same head**.
4. The artifact rules from 14v apply.
5. Any CI stop: report it with the exported diagnostics, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
