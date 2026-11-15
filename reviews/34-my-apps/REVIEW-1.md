Reviewed `dad1442b` against `ad2bcb6b`, excluding `mod/dev`. I read the requested documents, implementation, tests, protocol fixtures, and all seven screenshots. I also inspected relevant Minecraft bytecode. No Gradle, tests, or game were run; no files changed.

I found these issues:

1. **Blocking — deferred removals can be forgotten across login.**  
   [MyAppsGame.java:62](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/MyAppsGame.java:62) marks both inventories current whenever `restoredForLogin()` is false. But the subsequent login `populate()` only reconciles the active Live inventory; it never sweeps saved Build, and does nothing in Build mode.

   For example, remove an app while reconciliation is deferred, then disconnect before a safe tick. On an ordinary Live login, its saved Build item survives; switching to Build does not trigger another reconciliation. Schema migration can produce the same stale items.

   **Fix:** start every login with removal reconciliation pending for both inventories. Mark addition work complete only after it actually runs in Live.

2. **Blocking — app items can still duplicate and reach the world through containers.**  
   [AppInventory.java:158](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:158) checks the cursor but not the crafting grid. Put an app item in the 2×2 grid, open Apps, and pick that app: `take()` cannot find the existing stack and creates another. Switching screens does not clear the server’s crafting grid.

   External storage is another route: put an app in a chest, then trigger reconciliation. `populate()` creates a replacement because it searches only the player inventory. Breaking the chest can put the original into the world; [AppDropMixin.java:22](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/mixin/AppDropMixin.java:22) intercepts player drops, not block-container drops. Some of this predates package 34, but its claimed uniqueness/world guarantees remain false.

   **Fix:** reject pickup while crafting is occupied, and enforce where app items may be stored, including external containers and nested storage. Otherwise reconciliation must account for those locations. `/aresos give` also still creates copies unconditionally.

3. **Blocking — the helper icon check does not secure the file actually opened.**  
   [AppIcons.java:59](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/icon/AppIcons.java:59) checks `isRegularFile(path)` and subsequently opens that path separately. The file or a symlink target can change between those operations. Replacing it with a FIFO can block `newInputStream()` indefinitely; the byte limit never gets a chance to help.

   This can block startup because [AresOs.java:131](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/AresOs.java:131) generates icons synchronously. During play it can strand the sole icon worker.

   **Fix:** validate the safely opened file handle, close the symlink/special-file replacement race, retain bounded reads, and move initial helper-icon I/O off the initialization thread with a bounded fallback. The existing tests cover static invalid files, not replacement races or blocking reads.

4. **Should-fix — a fresh installation with the current 1.0 helper loses two starter items.**  
   [AppsConfig.java:218](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/config/AppsConfig.java:218) creates every discovered entry with `mine=false`. The starter rule then runs only during detailed day one. With a new config and a 1.0 helper, Notepad comes from defaults, but newly discovered Browser and Terminal remain outside My apps.

   **Fix:** initialize newly discovered starter IDs as mine independently of protocol details, without setting the baseline or re-adding starters the owner explicitly removed. Test a genuinely fresh config with 1.0; the existing migration test already contains all three starters and misses this.

5. **Should-fix — reconciliation moves an unrelated pinned app.**  
   [AppInventory.java:42](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:42) calls `placePinned()` on every reconciliation, including an unrelated add/remove or icon refresh.

   A pinned app can legitimately be in slot 9 because the hotbar was full. Free a hotbar slot, then add another app: reconciliation moves the existing app into the hotbar. The restored-Live login path also now performs this repositioning on its first safe tick.

   **Fix:** separate initial pin placement from reconciliation. Reconciliation should preserve existing stack positions, remove only unwanted apps, update presentation, and insert missing items into slots 9–35.

6. **Should-fix — full-inventory recovery stops before a slot becomes available.**  
   [MyAppsGame.java:185](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/MyAppsGame.java:185) marks additions complete even when `populate()` returns missing apps. Freeing a slot does not increment `CHANGES`, so the item remains absent until an unrelated change or login.

   This also affects [giveBack()](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:122): a cursor app discarded because the inventory is full is not reliably restored “when there is room.” The server test conceals this by explicitly calling `MyAppsGame.changed()` after freeing a slot.

   **Fix:** retain pending addition work for missing items, retry at safe inventory changes or throttled safe ticks, and keep the existing warning suppression.

7. **Should-fix — a double-click can add the wrong program.**  
   [AppsScreen.java:251](/var/home/ares/AresOS-34-my-apps/mod/src/client/java/dev/aresos/client/AppsScreen.java:251) cannot preserve the hovered row when the list is too short to scroll; [Row.mouseClicked()](/var/home/ares/AresOS-34-my-apps/mod/src/client/java/dev/aresos/client/AppsScreen.java:358) ignores `doubleClick`.

   Concrete example: search `pdf` with none of its three matches mine, then double-click Xournal++. After the first click adds it, the new My apps heading and row push All programs downward. The original pointer position now contains Okular. The second click adds Okular.

   **Fix:** bind a double-click sequence to the original app ID, or suppress its second action when reflow changed the target. Test a lower result in a short, non-scrollable list.

8. **Should-fix — malformed revisions can turn mixed pages into a “complete” list.**  
   [ShellClient.java:699](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/shell/ShellClient.java:699) reads `revision` through `text()`. Missing, null, numeric, and object revisions all become `null`; successive invalid revisions therefore compare equal. Their pages can be merged and published, setting the baseline and changing My apps.

   **Fix:** require a valid revision string on every 1.1 page before accepting any entries. Reject the entire listing when it is absent or malformed. Add malformed-revision cases that assert the previously published list and apps file remain unchanged.

9. **Should-fix — startup can miss the only catalogue update.**  
   [AresOs.java:113](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/AresOs.java:113) starts the shell and consumes its initial list before registering the listener at line 127. A completed refresh between those steps never reaches the config or inventory, and there is no periodic reconciliation to repair it.

   **Fix:** subscribe before starting discovery, with initialization arranged so an older startup snapshot cannot overwrite a newer callback. Carry list details/version with the list rather than reading `shell.detailed()` separately. The client test registers its listener before `start()`, so it does not exercise production’s ordering.

10. **Should-fix — schema-1 migration on Linux still removes Windows commands.**  
    [AppsConfig.java:51](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/config/AppsConfig.java:51) deletes `command`. The original survives in the backup, but the migrated working file does not preserve it as B1 explicitly requires. This behavior is inherited; it still contradicts this package’s “nothing lost” claim.

    **Fix:** preserve the command data during migration. Linux already launches exclusively through the helper, regardless of saved commands. Update the inherited `linuxMigrationImportsAppearanceOnlyAndKeepsCommandsInBackup` expectation to the new preservation requirement.

11. **Should-fix, pre-existing — the duplicate-open publication race is confirmed.**  
    [ShellClient.java:352](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/shell/ShellClient.java:352) publishes `connection`, invokes callbacks, and completes readiness before iterating `opens`. An `open()` in that interval enqueues its own send and also enters the replay iteration. Both sends use the same request ID.

    **Impact:** duplicate protocol traffic and replies, not a second launch when the helper’s journal works.

    **Smallest robust fix:** add a writer-owned “last connection sent on” field to each `PendingOpen`, and route normal sends and replay sends through one send-once-per-connection method. Reconnection still permits replay. Merely moving readiness later leaves status/listener callbacks and direct `open()` callers exposed. Add a deterministic callback/barrier test asserting one received request per ID on that connection.

12. **Should-fix — announcements discard the names after the fifth new app.**  
    [MyAppsGame.java:195](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/MyAppsGame.java:195) drains the remaining queue into an anonymous count. B2 requires a line naming each newly joined program.

    **Fix:** rate-limit delivery while retaining the remaining named messages, instead of discarding them.

13. **Nit — command completion is not host/world restricted.**  
    [AppCommands.java:34](/var/home/ares/AresOS-34-my-apps/mod/src/main/java/dev/aresos/item/AppCommands.java:34) suggests the owner’s app IDs without checking the source. Execution and the new payload handler correctly check host and desktop status, but LAN guests and normal-world command completion can still query the catalogue.

    **Fix:** apply the same source checks to suggestions.

The remaining checks support these conclusions:

- **Config writes:** schema-2 migration preserves the parsed document, validates before backup/replacement, and uses atomic replacement without a non-atomic fallback. Pin/mine edits validate the current schema before writing. I found no in-process path that writes a partially migrated JSON document. The schema-1 command exception is finding 10.
- **Older mod:** the report is correct: it rejects schema 3, leaves the file intact, starts without configured apps, and reports the error on join.
- **Protocol fixtures:** I found no §3.8 mismatch in the committed JSON examples. Negotiation, capabilities, request IDs, matching cursor/revision, ordered pages, final-page termination, optional-field shapes, all five sources, and the event envelope agree. No command, arguments, environment, or extra path is present.
- **Protocol bounds:** paging and restarts are bounded; incomplete attempts are not published. Optional metadata has useful type/length/count limits. The `apps_changed` scheduler coalesces events. The revision validation hole remains.
- **Icons:** byte/dimension/PNG-decoder limits are sensible once bytes are obtained safely. Normal refreshes use fingerprints and a five-second reload interval. The unsafe open and synchronous startup path defeat the stronger safety claim.
- **UI:** search, Enter, Escape, and scrolling are structurally suitable for 200 programs. The **release-time pickup change is correct**: Minecraft dispatches that release to the captured Apps screen, so changing screens inside it does not dispatch the same release to the inventory.

The tests are useful, but do not establish all the report’s guarantees. Missing cases include fresh-config 1.0 membership, saved-inventory reconciliation after reconnect, crafting-grid pickup, external storage, real slot-freeing recovery, malformed revisions, startup listener ordering, and the short-list double-click. The pending-removal test does check both inventories and preserves ordinary stacks, but does not cover `giveBack()` during a pending switch.

I found **no unjustified weakening of the edited existing assertions**:

- Package 07 changes pagination navigation to search/Enter while retaining pickup and pin assertions; `.withMine(true)` correctly updates its fixtures.
- Windows icon assertions merely unwrap the new `IconPack.Result`.
- The Windows Notepad preservation test adds only the expected `mine` field before its whole-entry comparison.
- Protocol version assertions appropriately distinguish the offered 1.1 hello from negotiated 1.0 traffic.

For every decision in [REPORT.md](/var/home/ares/AresOS-34-my-apps/reviews/34-my-apps/REPORT.md):

| # | JUDGMENT-CALL assessment | PLAN-GAP assessment |
|---|---|---|
| 1 | Conservative handling of unknown origin is reasonable, but should be identified as an explicit exception to the brief’s wording. | Deferring baseline until 1.1 is sensible. It does not justify missing fresh 1.0 starters. |
| 2 | Making `/give` imply mine is reasonable; unconditional duplicate creation remains unresolved. | Agree: places and short commands belong to later packages. |
| 3 | Refusing Q is sensible. Disagree with “nothing can double”; other item paths remain open. | Agree: logo icon integration is outside this package’s permitted area. |
| 4 | Agree that All programs includes mine. That does not prevent reflow-related wrong clicks. | Disagree with deferring the startup gap: `apps_changed` is introduced here, and its only notification can be lost. |
| 5 | Agree with scrolling. The screenshots show a usable layout; automated coverage reaches 150, not 200. | Repeating status in the screen is a useful, contained addition. |
| 6 | Disagree: the second click can target another program, not reliably pick up the first. | Agree: short names are package 35. |
| 7 | Agree with returning to inventory. | Agree with adapting package 07; its substantive pickup/pin checks remain. |
| 8 | Agree with the temporary wording until packages 35/36. The five-name truncation needs fixing separately. | Agree that the existing HUD overlap is outside this package; the screenshot confirms it. |

CHANGES-NEEDED