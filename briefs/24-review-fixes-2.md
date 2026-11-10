# 24: review fixes, round 2

Follow-up on `pkg/24-interface-v1` (PR #33). Read `reviews/24-interface-v1/REVIEW-2.md` (CHANGES-NEEDED; points 1, 2 and 5 of round 1 are fixed). Fix all four findings as the review proposes:

1. **A late failure cancels the wrong launch.**
   - Carry the original request ID and focus token through the failure callback, and match on those, never on `appId` alone.
   - Test: two launches of the same app, with a delayed failure of the first.
2. **Degraded tracking fills the journal.**
   - Mark a per-process launch terminal when its process exits cleanly.
   - Keep replay retention separate from window lifetimes that can't be observed.
   - Test: capacity recovers after many successful exits, more than the journal size.
3. **Late failures are lost across reconnects.**
   - Reconcile watched request IDs on reconnect, and route their replies through the late-failure handling.
   - Test: a failure that happens while the client is disconnected still reaches the player once.
4. **The 0.5 s focus hand-off.** Test both sides of the threshold explicitly, and record the rule as a JUDGMENT-CALL in the REPORT: what the player sees in each case, the alternatives, and why.

Same rules and resource gates as before:
- Never start a Minecraft client while Lunar runs.
- Gradle needs at least 6 GB free RAM; a full WSL suite needs at least 4 GB, one suite at a time.

Add a "Review fixes 2" section to the REPORT, then push.
