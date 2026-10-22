# 09d: No item loss through pickups during a pending switch

Follow-up on branch `pkg/09-mode-inventories` (PR #8). Read `reviews/09-mode-inventories/REVIEW-09c.md`.

**Goal:** fix the one blocking regression. During the pending-acknowledgement window, automatic item pickup (and anything else that changes the inventory outside the blocked packets: experience-orb mending, hopper or minecart transfers into the player, commands) must not lead to loss on timeout rollback.

**In scope:**
- Simplest safe option first: **block automatic pickups and other inventory insertions while a switch is pending.** Items stay in the world.
- If something can't be blocked, preserve it transactionally through rollback.
- Regression: inventory space, a dropped item next to the player, acknowledgement withheld → after timeout and rollback (and reconnect), the total item count across both inventories **and the world** is unchanged.
- All 09–09c tests stay green.

**Acceptance:** the new test fails before the fix (show it) and passes after. Full `build runClientGameTest` twice, green. A "09d" section in `REPORT.md`. Stop your Gradle daemons.

**Model:** gpt-6.1-sol, xhigh.
