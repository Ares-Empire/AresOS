# 23: review fixes, round 4 (settle the hand-off for good)

Follow-up to `briefs/23-review-fixes-3.md`. Review: `reviews/23-minecraft-starts/REVIEW-4.md` (gpt-6.1-sol high on `8420eba2`, CHANGES-NEEDED: 1 blocking, 2 should-fix). Builder: the same Claude agent (Opus). Next review: a fresh Codex context.

## Why this round is different

Rounds 2, 3 and 4 each found a new race at the same place: the hand-off between the supervisor and the Java wrapper (lost answers, kills and slow stops in different orders). Patching one order per round isn't converging. This round fixes the hand-off by construction, and proves it over every order of events at the race points.

## Fix

1. **Classify each end from facts, never from where the code happened to be.**
   - The wrapper records each signal it actually sends, before sending it. After reaping Java, "stopped by the wrapper" holds only when the wrapper sent a signal and Java's real end matches it: died of that signal, exited after the wrapper's SIGTERM with Java's SIGTERM status, or the wrapper's own SIGKILL after its window.
   - Otherwise Java's real status decides: a SIGKILL the wrapper didn't send means `killed` and latches; exit 0 is his quit; anything else is a crash.
   - This fixes REVIEW-4 finding 1 (a kill or exit between `poll()` and `stop()`), and any similar gap.
2. **Persist what is unresolved.**
   - When the supervisor latches an unexplained end, store the launch's identity (launch ID, PID, start time) and an `unresolved` mark with the accounting.
   - A restarted supervisor restores it and reconciles a matching late report or exit record exactly once: an explained failed start replaces the latch with one counted failure, and a kill stays latched. This fixes finding 2.
3. **One deadline rule.**
   - Once a lost hand-off is observed, the supervisor waits the full stop-and-report window, measured from that moment, even past the 30 s authorization limit.
   - Without an observed loss, the 30 s limit stands. Keep the wrapper's and supervisor's constants tied by a test. This fixes finding 3.

## Proof

- **Every order at the race points.** Write a model-based test that enumerates the protocol's events: authorize, `jvm_started` sent, answer received or lost, Java exits (0, crash or SIGKILL), wrapper SIGTERM, wrapper SIGKILL, wrapper dies, supervisor restarts, late report arrives. Drive the real supervisor state machine through every order up to a small bound, with a fake clock.
- Assert these invariants for every order:
  - a kill the wrapper didn't send never restarts and counts nothing;
  - his quit never restarts;
  - a crash counts exactly once;
  - no launch is accounted twice;
  - nothing latches forever when a full explanation exists;
  - after a normal reboot the hub starts.
- Keep the real-wrapper and real-loop tests for the three REVIEW-4 cases, with a deterministic hook for the race (no sleeps for ordering).
- **Revert proof:** each of the three fixes reverted alone makes the model test and its own test fail. Record which assertion fails, as before.

## Rules

- WSL: the desktop and helper modules, then one full suite (plain and `-B`) from a fresh clone. Check `pgrep` first and run at ≥ 4.5 GB available (WSL's page cache explains the gap to 5 GB; accepted). Use `setsid … < /dev/null`, `pkg23-` names, and remove clones right after. Package 27's rehearsal runs on GitHub, so WSL should be free, but still check.
- **Disk:** C: has about 2 GB free; keep it lean.
- **CI:** none unless the image build or a VM check changes.
- **Claude allowance:** the integrator pauses all work at a clean point on Wed 11-11 between 09:00 and 12:00 (local). If the round won't finish by then, push a clean intermediate state with REPORT notes by 09:00, and say where you stopped.
- Update `REPORT.md` with a "Review fixes 4" section first. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `AGENTS.md` applies.
