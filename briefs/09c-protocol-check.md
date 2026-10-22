# 09c: Never lock a client that can't acknowledge

Follow-up on branch `pkg/09-mode-inventories` (PR #8). Read `reviews/09-mode-inventories/REVIEW-09b.md`.

**Goal:** fix the one blocking regression. External mode changes for a connected player whose client doesn't support `ModeSwitchStatePayload` (for example an older AresOS or a vanilla client on LAN) must **not** begin a switch.

**In scope:**
- Check protocol support (the receiver for the state channel) **before** beginning or mutating anything.
- If unsupported, refuse the mode change for that player with a message. The inventory, mode and `pending` stay unchanged.
- The acknowledgement requirement for supported clients stays.
- Also guarantee a bounded escape: if an acknowledgement never arrives for a supported client, the server times out the pending switch and rolls back to the original consistent state, with a visible message.
- Regressions:
  - an unregistered state channel leaves inventory and mode unchanged and `pending == false`
  - a lost acknowledgement leads to rollback after the timeout
  - all 09/09b tests stay green

**Acceptance:** the new tests fail before the fix (show it) and pass after. Full `build runClientGameTest` twice, green. A "09c" section in `REPORT.md`. Stop your Gradle daemons.

**Model:** gpt-6.1-sol, xhigh.
