# 24: review fixes, round 3

Follow-up on `pkg/24-interface-v1` (PR #33). Read `reviews/24-interface-v1/REVIEW-3.md` (CHANGES-NEEDED; review 2's other findings are fixed). Fix both points as the review proposes:

1. **P2: adopted scopes after a restart.**
   - Keep monitoring scopes that are still running when the helper restarts, and close or settle their journal entries when they end.
   - Test the full chain: restart while the app runs, the app exits, the replay ID is still retained, capacity recovers.
2. **P3: the two-launch game test bypasses the focus token.**
   - Drive the real path: focus loss, the first launch's delayed failure, then `regainedFocus()`.
   - Assert that the second launch still returns the player in front of its logo. The test must fail against code that cancels the second launch's token.

Same rules and resource gates as before. Add a "Review fixes 3" section to the REPORT, then push.
