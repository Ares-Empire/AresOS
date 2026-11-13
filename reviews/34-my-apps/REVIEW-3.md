The REVIEW-2 finding is **CLOSED**. `/aresos give` chooses a destination before changing ownership or touching the existing stack. With no destination, it reports failure and preserves both inventories. Successful transfers reuse the same stack; occupied-cursor and pending-switch guards reject the command before mutation.

**One remaining should-fix in the touched pickup path:**

[AppInventory.java:227](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:227) — **Picking up an offhand app with a full Live inventory, then closing the inventory, loses the original stack.**

1. Slots 0–35 are full; the app is in the offhand.
2. Apps pickup puts that stack on the cursor and empties the offhand.
3. Pressing Escape invokes vanilla cursor return, which cannot insert into the empty offhand.
4. The drop interceptor calls `giveBack`, which also searches only slots 0–35. With no room, it retains no stack; closing clears the cursor.

Membership survives and reconciliation can eventually create a replacement, but the original stack and its components are not retained. I confirmed the vanilla return behavior from cached Minecraft bytecode. Ordinary offhand use followed by cancelling a pickup does not require the owner to act against himself. This behavior predates this round, but remains in the pickup path explicitly included in this review.

**Fix:** retain the pickup’s source and restore the exact stack there on cancellation when available, without overwriting anything. Alternatively, refuse offhand pickup when no main-inventory return destination exists. Add a full-Live/offhand pickup-and-close regression asserting exact stack preservation and unchanged saved Build inventory.

The three new tests provide good coverage of the **give** fix:

- Exact full-Build/offhand failure, including saved Live and the failure message.
- Ten successful/repeated moves across Live and Build, preserving customized stacks and unrelated items.
- Missing-item failure without ownership changes, followed by successful insertion.

They do **not** exercise pickup cancellation, occupied-cursor rejection, or pending-switch rejection. Inspection supports those rejection guards: pickup refuses Build, an occupied cursor, and a pending switch; a held cursor also prevents a mode switch. The remaining loss occurs on subsequent ordinary menu closure.

Container copies remain an accepted known limit, not another finding.

Read-only review of `d6635144..da90757e`; no files changed, Gradle or game run. Reported test passes were not independently rerun.

CHANGES-NEEDED