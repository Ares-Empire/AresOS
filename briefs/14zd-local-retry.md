# 14zd: A Windows rename denial in the local replay is retryable; then the $6 round

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zc still apply, with the change below.

**Clarification:** the "no rerun" rule covers **Actions dispatches**, which cost money. It doesn't cover zero-cost local checks.

`installer_inspect.py` `checkpoint()` → `Path.replace` failed with `PermissionError [WinError 5]` during the **local** ISO replay. On Windows that usually means another process briefly holds the target or the temp file, for example Defender scanning a freshly written file, or an overlapping reader.

**Do:**
1. Make sure no other replay or reader of that checkpoint is running.
2. Rerun the local replay. If the denial comes back, retry it up to **3 times**, waiting 10, 20, then 30 seconds.
3. If it still fails, find out what holds the file. Don't change `installer_inspect.py`'s Linux CI behaviour just for Windows. If needed, the local replay may write its checkpoint to a fresh path in `.work/` (local tooling only).
4. Record what happened.

Then continue exactly as 14zc says:
- pinned local gitleaks, then exactly **one** push carrying 14zb and 14zc
- fresh exact-head privacy, the ledger, billing and the budget ($6, prevent true)
- **probe 15**; only if it passes, **qualification 5 on the same head**

Any **CI** stop: report it with the exported diagnostics, no rerun. When acceptance is met, follow 14zc's closing steps. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
