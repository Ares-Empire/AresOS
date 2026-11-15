# 23: review fixes, round 3

Follow-up to `briefs/23-review-fixes-2.md`. Review: `reviews/23-minecraft-starts/REVIEW-3.md` (gpt-6-astra high on `e69b16a0`, CHANGES-NEEDED: 1 blocking, 2 should-fix). All 9 REVIEW-2 findings are fixed; these three are at the hand-off's edges. Builder: the same Claude agent (Opus). Next review: a fresh Codex context (narrow round).

## Fix

Numbered as in REVIEW-3.

1. **Blocking: a SIGKILL after PID acceptance must latch, never restart.**
   - The case: the supervisor accepts `jvm_started` and its answer is lost. Java then gets SIGKILL before the wrapper acts on that loss. The wrapper reports `status=-9`, `stopped=False`, but `on_jvm_failed()` ignores the status once `launch.reported` is set. Its `stopped_reason` then wins over SIGKILL in `finish_jvm()`, so the exit restarts as a plain crash.
   - Carry an explicit "the wrapper stopped Java" indicator through the protocol and the exit record. Use the real termination status whenever the wrapper did not stop Java.
   - Regression test: accepted PID, lost answer, SIGKILL. It must latch `RECOVERY/killed`, count no failure and never restart.
2. **The supervisor's deadline must cover the wrapper's stop.**
   - On a connection loss before acceptance, the supervisor waits 2 s, but the wrapper allows Java up to 10 s to stop before it reports. A slow stop becomes a false kill latch, and the late report is dropped.
   - Align the two: the supervisor waits at least the wrapper's stop window plus the reporting margin, and a matching late report still counts. A really unexplained death stays conservative.
   - Test with a child that delays SIGTERM and one that ignores it. Require termination in the end and exactly one failed start.
3. **A gap in pressure sampling resets the clear minute.**
   - Reset the interval when the gap between samples exceeds the cadence (5 s) plus a stated tolerance.
   - Test: advance the clock past 60 s without sampling ticks, then Retry must stay refused.

For each, show the test fails with only that fix reverted (interfaces kept), as in round 2.

## Rules

- WSL: run the desktop and helper modules, then one full suite (plain and `-B`) from a fresh clone. Check `pgrep` and ≥ 5 GB free first, use `setsid … < /dev/null`, `pkg23-` names. Package 27's agent also runs suites tonight; never in parallel.
- **CI:** none needed unless you change the image build or a VM check. If you do, report first.
- Update `REPORT.md` with a "Review fixes 3" section first. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `AGENTS.md` applies.
