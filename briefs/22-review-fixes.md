# 22: review fixes

Follow-up on branch `pkg/22-update-route` (PR #32). Brief 22 still applies. Read `reviews/22-update-route/REVIEW.md` (CHANGES-NEEDED at `ab5850ec`, gpt-6-astra high).

**Owner answers to the report's judgment calls** (board #154, 2026-11-09, "Yes to both"):
- **Call 1, accepted:** the current and previous AresOS plus the pinned stock are kept, and older AresOS versions drop off.
- **Call 4, accepted:** after the first update, `rollback`, `keep-stock` and layout trials refuse until follow-up 22c extends them. That follow-up comes before the second update.

Don't change either behaviour here.

Fix all four review points as the review proposes:

1. **Blocker: false update confirmation.**
   - `update` and `previous` record their expected outcome: target digest, expected deployment order, nothing pending.
   - After the reboot, `check`, `title` and `records` PASS only when that exact outcome is booted. An older booted release, a still-staged update or a still-queued rollback must STOP with a clear message and a route (Help, or `previous`).
   - Tests: failed finalization (the target never booted) and an unsuccessful `previous`.
2. **Blocker: concurrent owner commands.**
   - One exclusive lock, shared by the bootstrap and every installed owner command, held for the whole operation, so two owner commands can never interleave.
   - Recheck the safety predicates immediately before staging: idle, no layout trial, deployment shape, nothing staged or queued.
   - Test: an interleaving test, e.g. a layout trial attempted during update verification.
3. **Should-fix: a resumed tools update skips the system preflight.** Rerun the relevant safety checks before resuming the copy or swap. Extend the interruption tests so host state changes between attempts.
4. **Should-fix: legacy migration.** Migrate the known 15f fingerprint (`3ef85c4a…`) with `daily_wheel=False`, never a wildcard. Test that a rewritten legacy rule is rejected.

Keep `os/manifest/ci/16/pending-rebind.json` exact. If the payload changes, regenerate the bundle and its fingerprint everywhere it is pinned. Rerun the focused owner suites and the full WSL suite (plain and `-B`, one full suite at a time, with at least 4 GB free RAM). Add a "Review fixes" section to the REPORT, then push.
