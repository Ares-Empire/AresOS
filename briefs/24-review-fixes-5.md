# 24: review fixes, round 5

Follow-up on `pkg/24-interface-v1` (PR #33). Read `reviews/24-interface-v1/REVIEW-5.md` (CHANGES-NEEDED; the restructure itself holds). Fix all three as the review proposes:

1. **P2: an unrecognized state means `unknown`, never `gone`.**
   - `gone` only for explicit terminal states (inactive, failed, dead and the like, listed explicitly) and for absence from a valid, complete listing.
   - Any unrecognized active-state value is `unknown`.
   - Test malformed and unrecognized states.
2. **P2: confirmed activity clears uncertainty.**
   - A positive scope result (`active`) or a window confirmation clears a launch's `uncertain` mark and persists that, during reconciliation too.
   - Test: `unknown`, then `active`, then `gone`, ending in a normal close, not `launch_uncertain`.
3. **P3: the wake-up test must prove the wake-up.** Assert that the selector returns the `scopes` event before its timeout and that the event applies the result without `tick()` polling. The test must fail if the socket notification is removed.

Same rules and resource gates. Add a "Review fixes 5" section to the REPORT, then push.
