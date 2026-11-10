# 22: review fixes, round 8

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-8.md` (CHANGES-NEEDED: one Medium finding in the test helpers, nothing in the owner tools). The confirming `task/` snapshot, `reached()`'s markers, the separate sleepers, the payload hashes, the fingerprint pins, both bootstrap blocks and the 17 pending bindings all hold. Fix the finding as the review proposes:

1. **A hung bounce must not pass.**
   - `works()` (around `os/tests/test_owner_update.py:1042`) retries on `not the installed entry` only when the first run terminated by itself (`timed_out` false) and printed the complete expected bounce text. A timeout fails the test, whatever the output says.
   - The refusal assertions (around lines 1185, 1219 and 1228) also require termination and the complete expected refusal, not partial text.
   - Add regressions: an entry that prints the bounce or refusal text and then hangs must fail each helper.

This round touches tests only. If the payload changes after all, keep the fingerprint, the pins and `pending-rebind.json` exact. Run the focused owner suites. Then run the full WSL suites (plain and `-B`), one at a time, only with at least 5 GB free and nothing heavy running; the owner allows restarting a run that Claude Code stops for low memory once memory is free again (board #160). If memory never allows it, report them as pending. Add a "Review fixes 8" section to the REPORT, then push.
