# 22: review fixes, round 9

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-9.md` (CHANGES-NEEDED: one Medium, in a regression test only). The review confirms that `works()` and `refused()` now reject hangs and partial output, that the three former partial-text assertions are fixed, and that the payload, fingerprint, bootstrap blocks and 17 bindings are unchanged.

1. **Make the regression catch the old bug** (`os/tests/test_owner_update.py` around line 1087).
   - Today every invocation in the test repeats the same hang or truncated output, so a faulty retry also fails and the test passes anyway.
   - Feed `works()` a bad first result (a hang after the bounce line, or a truncated bounce), followed by a valid successful result. Assert that `works()` fails after exactly one invocation.
   - Keep a case with a complete, terminated bounce that permits exactly two invocations and passes.
   - Check the test by temporarily restoring round 7's retry condition: the test must fail. Report that you did this; don't commit it.

Tests only: the payload, fingerprint, pins and `pending-rebind.json` stay unchanged. Run `test_owner_update` in WSL, plain and `-B`. The full suites already ran on round 8's code, so rerun them only if something outside this test file changes. Add a "Review fixes 9" section to the REPORT, then push.
