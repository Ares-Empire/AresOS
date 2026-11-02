# 14zv: November round: free minutes only, reserve 150, closing 12; one push, probe 27, qualification 16

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zu still apply, with the changes below.

## Integrator decision: November settings

The October paid overflow is over. The owner's Actions budget is now **$0 with "stop usage" on** (read 2026-11-01), so November runs use the organization's free 2,000 minutes only. Other private repos now use almost none: the companions website check runs only by hand since 2026-10-29, and no org repo has scheduled workflows.

1. **Guard: free minutes only from November.**
   - Keep the October paid-overflow path for October only, as historical behaviour with its tests on a fixed October `now`.
   - For any later month, read no budget amount, count no paid minutes, and use `included_minutes - used`.
   - STOP if the current month's summary shows any non-zero `netQuantity` or `netAmount` for Actions minutes, since that means the organization is already past its free minutes.
   - At the start of a month, a well-formed, current-period summary may have no Actions rows yet. Treat that as 0 used. A stale, malformed or wrong-organization response still STOPs.
2. **`os/ci/rehearsal-packages.json`, package 14:**
   - `organization_budget.other_repos_reserve`: 0 → **150**.
   - `closing_privacy_reservation.minutes`: 0 → **12**. The guard already refuses 0 outside October.
   - `minute_cap`: raise to the **package ledger at the start of November + 1000**, then round up to the next 50, and record the ledger figure. One round's bound is 6 + 72 + 160 = 238, so four rounds plus closing fit in 964. If the ledger is above 1800, STOP and report rather than raising further.
   - `dispatch_caps`: **four more of each** than the counts the guard sees now (probe and owner-tools). Record the counts.
3. **Local checks:**
   - the guard tests for October versus November, the empty-month summary and the paid-usage STOP
   - the affected regressions
   - the pinned local gitleaks
   - commit
4. **One push** with everything since `65edb11` (14zs/14zt/14zu and this). Wait for the push and PR privacy checks to pass.
5. **Probe, then qualification, on that same pushed head**, under the same rules as before. Watch them through to the end.
6. **Then STOP and report, pass or fail.** Append the round to `reviews/14-owner-tools/REPORT.md`, newest first, and commit it locally; it goes out with the next round's push.
   - **On a stop:** diagnose it from retained output, never from a mock, and say whether it's an owner-tool bug or the test's console emulation.
   - **If it's console emulation again,** add a short plan for running the remaining non-typing stages (rollback, keep-stock, final Windows checks) as serial-run commands. Physical typing stays only where the stage tests typing itself: the US International login and back to German. Don't build the plan until I've answered.
   - **If everything passes,** list the acceptance evidence for each remaining stage: US International success, back to German, rollback, keep-stock, final Windows checks.

Unchanged: the GHCR_READ_TOKEN rules (11d), and no secret in evidence, artifacts or logs. No merge, no push to `main`, no image publication, no visibility change.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
