# 23: review fixes, round 2

Follow-up to `briefs/23-review-fixes-1.md`. Review: `reviews/23-minecraft-starts/REVIEW-2.md` (gpt-6-astra high on `7ec26b84`, CHANGES-NEEDED: 1 blocking, 8 should-fix). Builder: the same Claude agent (Opus). Next review: a fresh Codex context.

The owner accepted the updated JUDGMENT-CALL 10 (board #170, 2026-11-10: "Yes"), and REVIEW-2 agrees with it. These fixes complete it; they don't change it.

## Fix

Fix each finding at its cause, numbered as in REVIEW-2.

1. **Blocking: kills before the PID handoff must latch, not restart.**
   - A SIGKILL of Java, or the wrapper's death, between authorization and the accepted `jvm_started` reports `jvm_failed` or "wrapper gone". Both count as a plain crash and restart.
   - Keep the termination status and the scope's result for pre-handoff deaths. Latch recovery for a kill or any unexplained death, exactly as after the handoff.
   - Test: SIGKILL Java and the wrapper right after authorization, before the PID is accepted.
2. **Retry needs 60 s of continuously cleared pressure.**
   - Track a clear interval that resets on any pressure above the limit and on any unreadable value. A supervisor restart must not skip it.
   - Fix the test that drops pressure from 42 to 3 without advancing time and expects success.
3. **A lost handoff must not leave an untracked JVM.**
   - If the connection breaks during `jvm_started`, either make the launch and PID identity recoverable (reconnect and reconcile), or abort the unaccepted start safely.
   - Test a real connection closure between authorization and acceptance, with Java still alive.
4. **Persist the decision, not only the accounting.**
   - After a reconciled exit, store the session's disposition (stopped after his quit, recovery latch, or a pending crash backoff with its deadline) next to `accounted`. Restore it after a supervisor restart without counting the exit again.
   - Test: his quit stays stopped across two supervisor restarts, and a pending backoff keeps its deadline.
5. **Exact-home data must be valid, not only present.**
   - Validate `home.dimension` as a resource identifier, by the mod's codec rules.
   - Require finite exact-home yaw and pitch.
   - Fixtures for a malformed dimension and non-finite angles, rejected by both preflight and readiness.
6. **Read Java's modified UTF-8.**
   - NBT strings use `writeUTF`/`readUTF`: NUL and characters outside the BMP are encoded differently.
   - Decode them compatibly. Add fixtures with bytes as Java writes them (a world name with an emoji, and a NUL).
7. **Corrupt compressed data is damage, not a crash.**
   - Turn `zlib.error` (and `EOFError`/`OSError` from `gzip`) into `NbtError`.
   - Test corrupt DEFLATE separately from a bad header and truncated NBT, including the fallback to a valid `level.dat_old`.
8. **Focus hand-back survives late identification.**
   - Keep the previous foreground target when a newly appearing window is identified only later.
   - Test activation followed by a later app-ID event, including split socket reads.
9. **The VM pressure check must prove pressure.**
   - Require the scope to be entered and the allocation to have started. Tie the termination to that scope's OOM evidence (kernel or oomd log), and check that recovery stays responsive during the pressure.
   - Add a negative test: a launcher failure must fail the check.

## Regression proof

REVIEW-2 notes that several new tests failed on old code only in shared setup. For each finding, show that its test fails when only that fix is reverted and the interfaces stay compatible. Record per finding which assertion fails.

## Also

- Add release run 42834907206 (the mirror timeout) to "Checks of this round" in `REPORT.md`, as you drafted.
- **CI:** Ubuntu's snapshot mirror is down (500/504 since about 14:30 UTC). The integrator is watching it and will give the go for one `check_build=build`. Dispatch nothing before that. The round's VM checks (`desktop_jvm`, `memory_protection`, `memory_pressure` with finding 9's fix) run in that build.
- **Memory:** package 27's WSL suite is running. Check `pgrep -f "python3.*unittest"` is empty and ≥ 5 GB is free before your suites; run them with `setsid -w … < /dev/null`, one at a time.
- Update `REPORT.md` with a "Review fixes 2" section first. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `AGENTS.md` applies: never merge, never push to `main`, never `--no-verify`.
