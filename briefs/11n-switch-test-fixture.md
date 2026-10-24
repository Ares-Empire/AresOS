# 11n: Give the switch-block test its prerequisites, then run the probe and Part B

Follow-up on branch `pkg/11-two-disk-rehearsal` (PR #11, draft). Read the "11m" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11m still apply, plus the changes below.

## What stopped 11m

The paginated guard works: the local gate and the probe's own CI guard read both pages, and the ids matched `total_count` (129 and 130). The probe then stopped in its native suite, 199/200:

`test_install_transactions_stop_on_failure_and_never_include_the_reboot` (`os/tests/test_shell_assertions.py`) runs the owner's exact fenced switch block with only `bootc` stubbed to return 42. Since 11l, that block is exactly `switch.sh`, which first requires `ares-recovery` at UID 1000, no `ares`, UID 1001 free, a readable `/etc/ostree/auth.json` and no pending deployment. The clean runner has no `ares-recovery`, so the block stops at `id -u ares-recovery` before reaching `bootc`. This is a gap in the test's setup, exposed by the 11l fix. It is not a product failure. Stopping was correct.

Codex's local run (112 tests) didn't include `test_shell_assertions.py`, so the gap reached CI.

## Integrator decision

1. **Fix the test setup, never the block.**
   - The test keeps executing the exact fenced owner block. Give it safe stand-ins for every prerequisite: the recovery account at UID 1000, no `ares`, UID 1001 free, a readable auth file, and `bootc status --json` showing nothing staged or queued. It still requires the injected 42 and no later transaction or reboot.
   - The stand-ins must only use temporary files, PATH shims or shell functions. They never read or change the real system's accounts or `/etc`.
   - Add negative cases. Each one must stop before `bootc switch` is called: `ares` already exists, UID 1001 is taken, the auth file is unreadable, a deployment is staged, and a rollback is queued.
   - `switch.sh`, the INSTALL block and their equality test stay unchanged.
2. **Run the whole suite before any dispatch.**
   - Run the complete native discovery locally in a Linux-like environment if one is available (for example WSL, or Git Bash for tests that support it).
   - If some tests still can't run locally, list them and say why. Every test that 11l–11n touched or whose inputs they changed must have run somewhere before the probe.
3. **Budget:** same ledger, cap 900. 11m's failed probe stays counted. It qualified nothing, so allow **one more fresh probe**, plus the one Part B run from 11l. Plan: 637 + 42 + 130 + 14 = 823, at most 900. If the guard can't fit it, stop and report.

## Then

1. Push (fast-forward), let source privacy pass, and run a fresh guard.
2. One fresh probe on that head.
3. One Part B qualification run on the same head, in the protected-second order, exactly as 11l's walk-through describes.

All stop rules hold. No other probe, no second B run, no ordinary full run.

## Acceptance

11l's and 11m's acceptance, plus an "11n" REPORT section with:
- the fixture fix and its negative cases
- which tests ran locally, and where the rest ran
- the probe and Part B results (rendered menu frames, OCR, selection, promotion, the new Windows-first timing, BootNext receipts, guard pages/ids/`total_count`)
- Part B green, or a clearly stated blocker
- the budget table

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
