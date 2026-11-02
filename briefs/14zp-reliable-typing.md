# 14zp: Reliable physical typing (short holds, counter-verified hidden input); probe 23 and qualification 12

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zo still apply, with the change below.

## What qualification 11 proved

- **Owner-length hidden token path works:** the 40-character dummy went through the VT, both sudo relays and getpass. All 110 of 110 key events arrived, with 0 repeats and 0 SYN_DROPPED, and the tool returned its normal refusal. Record this as owner-path evidence.
- **Then the next visible command was typed as `/var/lib/ares/aatt`:** every key doubled. That is guest **autorepeat**: a key seen as held longer than the 250 ms repeat delay, because the release arrived late with QMP `send-key` at a 100 ms hold on a busy guest. The visible-text check stopped it correctly, before the real token. The same effect can silently corrupt a long hidden token. That fits qualifications 9 and 10, but stays unproven for them.

## Fix (harness only)

1. **Shorter key holds:** send each chord with a short hold (for example `send-key` `hold-time` 30 ms, or explicit `input-send-event` down/up pairs) and keep a gap of at least 120 ms between chords. Record the timing.
2. **Visible input** keeps its existing echo check before Enter, which is what caught this.
3. **Hidden input:** run the 14zo guest event counter for the whole typing window. **Before pressing Enter**, require exactly the expected press and release counts, 0 repeats and 0 SYN_DROPPED.
   - If that fails: send the line-kill key (Ctrl-U, VKILL; the reader's terminal is canonical) and retype the same value **once**, with the counter again.
   - If it fails again, or if Ctrl-U can't be proven to have cleared the line (the counter still sees the reader waiting with no Enter sent), STOP. Never press Enter on an unverified hidden value.
   - This replaces 14zi's "never retype" only for this pre-Enter, counter-proven case.
4. **The 377-character CI token:** chunked as in 14zo, under the counter, verified before Enter.
5. **Don't change the guest's keyboard settings.** No `kbdrate` or console changes: the fix is in how we press keys.
6. **Local tests:**
   - the hold and gap schedule
   - the pre-Enter verification logic: pass; extra repeats lead to Ctrl-U plus one retry; a second failure STOPs; a drop STOPs
   - Enter is never sent unverified

## Budget (owner's $10 cap; about $6.23 billed)

One push, plus probe 23, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1600** (1306 + 238 = 1544)
- `dispatch_caps.probe`: **24**
- `owner-tools`: **13**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 23**. Only if it passes, **qualification 12 on the same head**.
4. Any CI stop: report it with counts and diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
