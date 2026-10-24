# 11m: Let the budget guard read the whole run history, then finish 11l's probe and Part B

Follow-up on branch `pkg/11-two-disk-rehearsal` (PR #11, draft). Read the "11l" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11l still apply, plus the changes below.

## What stopped 11l

The four review fixes, the GRUB selector and the BootNext rule are done, with 103 local tests and all 32 replays passing. Then `rehearsal_guard.py probe 186` refused with "Budget history requires pagination". The branch now has 123 workflow runs, and the guard reads only the first page of 100, whose oldest run (2026-10-23T16:43:29Z) is newer than the allowance start (16:21:00Z). Refusing was correct: an incomplete ledger must never authorize a dispatch.

## Integrator decision

1. **Read the whole run history, and fail closed.**
   - Page through the same run listing the guard already uses (same filters and ledger definition) until the history is complete. Use each read through the 11k bounded retry.
   - Completeness has to be proven, not assumed. Use the API's own `total_count` and require the collected unique run ids to match it. Inconsistent counts, a duplicate or missing id (for example, a new run shifting the pages mid-read), an empty page before the end, or a page error after the retries all fail. At most one complete fresh re-read is allowed after a detected shift. Then fail.
   - Set a hard page limit (for example 20 pages) that fails closed instead of reading forever.
   - Nothing else in the ledger changes: same start, cap 900, five historical fulls, and the one-B allowance from 11l.
2. **Regressions:**
   - Two pages (100 + 23) give exactly the union, including a run at the page boundary near the allowance start.
   - The 11l stop case (oldest run on page 1 newer than the start) now passes, but only because page 2 is read.
   - A `total_count` mismatch, a duplicate id across pages and a missing id each fail with no authorization.
   - A 502 on page 2 recovers through the 11k retry; five 502s fail closed; a 404 fails at once.
   - Hitting the page limit fails closed.
   - The existing budget, time, full-count and B-count tests pass unchanged.
3. **Same guard in CI.** The probe and B jobs run the guard too, so the fix covers them. Show it in the probe's own guard receipt (pages read, ids counted, `total_count`).

## Then

Continue 11l's plan unchanged from where it stopped:
1. Push the fix (fast-forward), let source privacy pass, and run a fresh guard.
2. One fresh probe on that head.
3. One Part B qualification run on the same head, in the protected-second order, exactly as 11l's walk-through describes.

All stop rules hold. No second probe, no second B run, no ordinary full run.

## Acceptance

11l's acceptance, plus an "11m" REPORT section with:
- the pagination change, its regressions, and the pages/ids/`total_count` from every real guard read this round
- the probe and B results as 11l requires (rendered menu frames, OCR, selection, promotion, the new Windows-first timing in protected-second, BootNext write and consumption receipts)
- Part B green, or a clearly stated blocker
- the budget table

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
