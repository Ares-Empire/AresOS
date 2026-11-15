Reviewed `9d26842b..f57e83a8`, limited to the fixes and their affected paths. No Gradle, tests, or game were run; no files changed.

| Original finding | Verdict | Assessment |
|---|---|---|
| 1. Deferred removals across login | CLOSED | Both inventories start with removal work pending; initial population credits only completed Live additions. |
| 2. Crafting, `/give`, containers | ACCEPTED-AS-DECIDED | Crafting blocks pickup and `/give` reuses existing items. Containers are explicitly documented as outside uniqueness guarantees. New `/give` regression below. |
| 3. Blocking icon reads | CLOSED | Startup queues background generation. Reads have deadlines and disposable workers; a stuck worker does not prevent later reads. This meets the agreed broken-file threat model. |
| 4. Fresh-file 1.0 starters | CLOSED | Newly discovered starters become mine without a baseline. Existing removed starters remain removed, including on upgrade to 1.1. |
| 5. Reconciliation moves pins | CLOSED | Later reconciliation preserves positions; initial pin placement remains separate. |
| 6. Recovery after full inventory | CLOSED | Missing additions remain pending. Full inventories get a bounded free-slot check, without repeating reconciliation or warnings every tick. |
| 7. Double-click adds neighbour | CLOSED | The second action is suppressed; the regression fixture explicitly places Okular under the original pointer after reflow. |
| 8. Malformed revisions | CLOSED | Every detailed page requires a nonempty string revision before entries are accepted. Invalid attempts leave the published list and file unchanged. |
| 9. Startup catalogue ordering | CLOSED | Subscription precedes connection; snapshots carry their details flag; readiness never reapplies an older snapshot. |
| 10. Linux schema-1 commands | ACCEPTED-AS-DECIDED | Commands remain in the original backup only, as OS-BASE B1 specifies. |
| 11. Duplicate open publication | CLOSED | Normal sends and replays share writer-owned connection tracking. A new connection permits replay. The deterministic test keeps the request pending through the post-replay writer barrier. |
| 12. Truncated announcements | CLOSED | Undelivered names remain queued after the five-message batch. |
| 13. Command completion scope | CLOSED | Suggestions now require the host in an AresOS world. |

**New finding — should-fix: `/aresos give` can delete the existing offhand app in Build mode.**

At [AppInventory.java:184](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:184), the command removes the existing stack before calling `inventory.add(stack)`.

With slots 0–35 full and that app in the offhand, removing it creates no destination that vanilla insertion searches. Minecraft’s creative-mode overflow behavior then clears the supplied stack and returns `true`, so the restoration branch is skipped. The command reports success while the existing Build item disappears. Membership remains saved, but the stack is lost.

I confirmed the insertion behavior by inspecting the cached Minecraft 26.2 bytecode. This requires ordinary offhand use, a full building inventory, and the documented command—not hostile manipulation or deliberately destroying his own data.

**Fix:** select a valid destination before removing the existing stack and move it directly. If none exists, preserve the original and report failure. Add a regression covering a full Build inventory with the app in the offhand, asserting exact preservation of both inventories.

No other new problems were found in the reviewed paths. Pending switches defer reconciliation; saved-inventory removals preserve unrelated stacks. Icon publication waits for an attached client’s reload, and refreshes remain request-driven and fingerprint-gated. The apps-file fixes retain the validated atomic replacement path.

The inventory screenshot shows the Apps button above the panel, clear of the hearts. `git diff --exit-code 9d26842b..f57e83a8 -- mod/src/test/resources/shell-1.1` produced no output and exited 0: the contract fixtures are unchanged.

Container copies and adversarial same-user file replacement remain accepted limits, not grounds for another round.

CHANGES-NEEDED