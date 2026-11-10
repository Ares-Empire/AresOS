# 22: review fixes, round 2

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-2.md` (CHANGES-NEEDED; the retry guards, repeated preflight, resumed checks and R13 migration are confirmed). Fix both High findings as the review proposes:

1. **Record the outcome before the change.**
   - `update` and `previous` durably journal their intent (the expected outcome) **before** they stage or queue anything.
   - An intent without a completed outcome counts as unresolved: `check`, `title` and `records` STOP on it with the failed-update route and never PASS on the old release.
   - Test an interruption, or an observation or write failure, at every point between the change and the final record, for both commands.
2. **Upgrading from the installed 15f tools must exclude them.**
   - The 15f commands never take the new lock, and `idle()` doesn't see their Python processes.
   - Before the copy or swap, refuse while any legacy owner command is running, detected through the actual 15f entry point and its process, not by name guessing. Also prevent new legacy invocations during the replacement.
   - Test against the real legacy entry point.
3. **The review notes retries aren't actually limited to one.** Either enforce once-per-failure in code or make the guide and REPORT say what is true ("Help decides each repeat"). Don't leave the claim and the code disagreeing.

Keep the fingerprint, the pins and `pending-rebind.json` exact after any payload change. Rerun the focused owner suites and one full WSL suite, plain and `-B` (at least 4 GB free, one suite at a time). Add a "Review fixes 2" section to the REPORT, then push.
