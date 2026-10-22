# 09b: Build/Live inventories, review fixes

Follow-up on branch `pkg/09-mode-inventories` (PR #8). Read `reviews/09-mode-inventories/REVIEW.md` and `REPORT.md` first.

**Goal:** fix both blocking findings. The rule: **no path loses or duplicates items.**

**In scope:**
1. **External mode changes (blocking).** Track which inventory is active **independently** of vanilla game mode. Route survival/creative changes from any source (`/gamemode`, F3+F4, the game-mode switcher, other mods) through the same inventory transaction in marked AresOS worlds. If a change can't be routed safely, refuse it with a message. Regression: G to Build → collect blocks → `/gamemode survival` → G → the original Live inventory is intact, plus a rejoin variant.
2. **Acknowledged switching state (blocking).** While a switch is pending, block item interactions on the client and server: drop, use, attack, hand swap, menu clicks, hotbar moves, creative-inventory edits, and further toggles. Unblock only when the complete destination state, or a failure, has been received. Ignore stale packets sent before the acknowledgement. Client test with artificially delayed sync: attempt drop, click, hand swap and a second G during the transition → nothing happens to either inventory.

**Acceptance:**
- Each new test fails before its fix (show it) and passes after.
- Full `build runClientGameTest` twice, green.
- A "09b" section in `REPORT.md`. Stop your Gradle daemons.

**If unsure:** block the action and keep items safe.

**Model:** gpt-6.1-sol, xhigh.
