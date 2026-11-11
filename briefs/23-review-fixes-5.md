# 23: review fixes, round 5 (conservative by default)

Follow-up to `briefs/23-review-fixes-4.md`. Review: `reviews/23-minecraft-starts/REVIEW-5.md` (gpt-6-astra high on `d6aab7ab`, CHANGES-NEEDED: 1 blocking, 3 should-fix). **Builder: a new Claude agent on Fable 5.2.** Five reviews in a row found hand-off races, so this resists normal attempts (CLAUDE.md). Read REVIEW-2 to REVIEW-5 and the REPORT's review-fix sections first. Starts after the Claude weekly reset (Thu 11-12 00:00). Next review: a fresh Codex context.

## The rule that ends the races

Restart automatically only when the end is **certain** to be an ordinary crash. Anything uncertain (an ambiguous signal, a lost report, a reboot in between, an end not seen directly) latches recovery and waits for the owner's `retry`.

The owner already chose this direction: board #170, an unexplained death latches, and he accepted that a crash taking the wrapper down needs his `retry`. Wider latching costs at most an occasional extra `retry`; it never risks a restart loop. Record it as an updated JUDGMENT-CALL 10; the integrator decides whether it goes back to the owner.

## Fix

1. **Confirmed sends only** (REVIEW-5 #1). The wrapper counts a signal as sent only when the kernel accepted it (`os.kill`/`pidfd_send_signal` on a still-running child, with no early return). A skipped or failed send never counts. When in doubt, the end is uncertain and latches.
2. **Exit 0 is the owner's quit whenever the wrapper didn't stop Java** (#2), before or after acceptance, refusal or lost hand-off. Test all three; no failure counted, no restart.
3. **Facts survive a reboot** (#3). Keep the terminal facts (launch, session, status, confirmed signals) durably until the reconciliation that uses them is committed. After a reboot, reconcile the accounting, but never carry the old session's quit into the new session. Test a reboot between writing the explanation and consuming it.
4. **A model that can't agree with the code by accident** (#4).
   - Split the wrapper's stop, timeout escalation, record write and report into separately schedulable events. Model a reboot as clearing the whole runtime directory.
   - Derive the expected outcome from an independent ledger of what really happened, not from the supervisor's return values or the wrapper's rule.
   - Keep the invariants from round 4 (brief 4). Add one: an uncertain end never restarts.
5. **Simplify where you can.** If a smaller protocol (for example, the supervisor reading Java's end from systemd's scope result and cgroup events instead of from the wrapper's report) removes whole classes of races, propose it in the report first, with what it costs. Don't add another layer of patches.

## Proof and rules

- Revert proof per fix, as before. Run the full WSL suite (plain and `-B`) from a fresh clone, one suite at a time: `pgrep` first, ≥ 4.5 GB available, `setsid`, `pkg23-` names, remove the clone after.
- The `d6aab7ab` full suite never ran (the disk was full, then the round was parked).
- No CI unless the image build or a VM check changes.
- Write a "Review fixes 5" section first in `REPORT.md`. Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. `AGENTS.md` applies.
