# 14za: The probe 14 watcher stop was bookkeeping; dispatch qualification 4

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14z still apply, with the change below.

**Integrator verification** (read-only `gh run view 40560134727`):
- `workflow_dispatch` on `pkg/14-owner-tools`, head `2fb695cdb419d67b51a76d91727668b33df82ecd`, attempt 1
- "Two-disk rehearsal (probe)", completed **success**

So the dispatch identity is confirmed. Your local watcher's history-list match failed, not the run. Under your stop rule, holding back was right.

**Do:**
1. Find out why the watcher's bounded list reads missed the run (filter, paging or timing), fix it locally and add a test. That tool isn't part of the workflow, so don't push for this.
2. Refresh the ledger, billing and the budget ($3, prevent true; about $0.84 net used). Then dispatch **qualification 4** on the same pushed head `2fb695c`, with probe run **40560134727**, using the fixed watcher. **No push.**
3. Any stop: report it, no rerun.
4. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
