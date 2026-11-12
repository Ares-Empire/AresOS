- **Medium — [test_owner_update.py:1087](C:/Users/pab/AresOS-22-update-route/os/tests/test_owner_update.py:1087): the regression still passes with the original faulty retry condition.** Every invocation repeats the same hang or truncated output, so an improper retry also fails and satisfies `assertRaises`. **Fix:** supply a bad first result followed by a valid successful result, and assert that `works()` fails after exactly one invocation. Retain a complete-bounce case that permits two.

The current `works()` and `refused()` guards correctly reject hangs and partial refusals; all three former partial assertions are fixed. No additional whole-PR recovery blocker found.

Payload, `e765ae29…` fingerprint, both bootstrap blocks and all 17 pending bindings are unchanged and match. REPORT records both round-8 WSL suites with only known failures. Review was static plus hash checks; Python unavailable, WSL access denied. No files edited.

CHANGES-NEEDED