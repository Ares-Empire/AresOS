# 14zt: Explain the post-records prompt stop; fix locally; no dispatch until November

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zs still apply, with the change below.

**Qualification 15:**
- Both bounded logins passed, in 8.9 s each (14zs confirmed).
- Nine owner records passed, and `corrected-stock records` printed `PASS records`.
- The completion wait never found a cursor-line prompt:
  - Two authorized Enter resyncs, with the observer proving the idle bash behind `sudo -i`, didn't restore one.
  - All three VCSA samples show the cursor at (0,49) on an empty line, root-prefixed rows at 23/33/45, and no row ending in the accepted delimiter.

**Do (zero cost, local only):**
1. **Explain the screen.** From the private raw VCSA and receipts, and only there (no secret is involved at this stage; keep the raw data private anyway):
   - What exactly are rows 23, 33, 45 and 46–49?
   - Did each Enter produce a new line or prompt?
   - Is the prompt string different here (PS1, color codes stripped, a trailing character)?
   - Does `records` print something after PASS (for example a trailing blank line, or a pager or column effect)?
   - Did the bash prompt render somewhere other than the cursor line?

   State what's proven and what's only likely.
2. **Fix the readiness predicate or the resync on the real evidence, without loosening it:**
   - The prompt must still be a real idle-shell prompt, proven by the observer plus a prompt on screen.
   - If the actual prompt form differs (for example a prompt after a blank line, or a scrolled screen), match that exact form.
   - Add a regression from this exact VCSA, and keep the old fixtures passing.
3. **Walk every remaining stage** with this new fixture shape: layout proof with US International, back to German, rollback, keep-stock, and the final Windows checks.
4. Commit locally, with the pinned local gitleaks. **No push and no dispatch:** October's paid budget is nearly used up. The next CI round runs on **1 November** with fresh free minutes, unless the owner decides otherwise.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
