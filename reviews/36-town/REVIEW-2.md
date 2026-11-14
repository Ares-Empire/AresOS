Reviewed commit `e9995dee3303f10ee259d7bfba2cfc79d6a9f501` — read-only review of `e98d4191..HEAD`; no files changed and no builds, tests or game runs performed.

| Point | Status | Reason |
|---|---|---|
| 1. Seal and freeze | OPEN | Recorded frozen logos are guarded against removal and renewal; trust is host-only at parsing and execution, and permits the next save to seal. However, a restored ledger can omit standing logos, and an empty restored ledger bypasses the seal check entirely. Finding 1. |
| 2. Refused files and load checks | CLOSED | Normal loading refuses unreadable files, mismatched homes and the specified overlaps before adoption. Loading and `add` share `check`. Refusal blocks reconciliation, rebuild and trust without dirtying or replacing the refused town file. A5’s empty-file exception is confined to `store`’s new-home path. |
| 3. Light-state edits | CLOSED | The chunk hook relinquishes a light on any successful state change. Returning to the original state cannot restore ownership. Mushroom-face changes retain the accepted exception. |
| 4. Sign and zone ownership | OPEN | Town cleanup checks display type, position and text, and zone ID, app, dimension, box and absence of a gate. B1 leaves an unsafe exception for hand-built signs. Finding 2. |
| 5. Picture work and shutdown | OK | Production picture reads and conversion run on the worker. Futures transfer results; world access stays on the server thread. Orders require a later tick, the same player/world, position block and facing. Stop hooks cancel pending reads and remove orders; an already-running read can finish its current app without touching the world. |
| 6. Names, doorway recovery and reopening | CLOSED | Name changes request passes. Doorway recovery preserves conflicting zones and reports the obstruction. Server tests reload records between passes; the client test actually leaves and reopens the world. |
| 7. Existing behavior | OK | Complete-list, `flat-1`, host and loaded-ground restrictions remain. No apps.json or hub.dat format regression found. First-build aggregation implements B5; later passes retain the more-than-five rule. Hand-built sign safety is covered by point 4. |
| 8. Tests and suite safety | OPEN | The new regressions substantially exercise the fixes, with plot-relative ground, their own tickets and unchanged client-test ordering. Missing restored-ledger reconciliation coverage hides finding 1; hand-built edited signs lack coverage. One new unit assertion also races completion cleanup. Finding 3. |

1. **FIX — Restoring a ledger that omits a standing logo can build that app twice.**

   **Where:** [HubData.java:240](../../mod/src/main/java/dev/aresos/hub/HubData.java:240), [HubData.java:265](../../mod/src/main/java/dev/aresos/hub/HubData.java:265), [TownKeeper.java:399](../../mod/src/main/java/dev/aresos/hub/TownKeeper.java:399).

   **Scenario:** Save a town containing Chrome, then later build Discord and save again. With the game closed, restore only the earlier `town.dat`. The world and `zones.dat` still contain Discord’s logo and doorway.

   The fingerprint mismatch freezes Chrome, but Discord has no entry to freeze. During reconciliation its existing position is treated as an obstruction, and Discord receives another logo on free ground. Its original logo and zone remain. There are now two logos for one app.

   Restoring an earlier **empty** ledger is worse: `join` skips the fingerprint check, reports no freeze, and `sealable()` allows the replacement ledger to receive a fresh seal without trust.

   This meets the explicit duplicate-logo bar and, for the empty case, trusts records despite contrary seal evidence. No concurrent external writer is required.

   Preserve enough continuity information to distinguish omitted standing apps from newcomers, or conservatively suspend affected building when a ledger fingerprint mismatch prevents that distinction. An empty restored file must not automatically count as a world that never had logos. Add regressions that restore both a subset and an empty ledger, then run reconciliation. The current backup test stops after checking the loaded freeze state.

2. **FIX — B1 still deletes an edited hand-built sign without establishing ownership.**

   **Where:** [GateBuilder.java:245](../../mod/src/main/java/dev/aresos/zone/GateBuilder.java:245), [GateBuilder.java:282](../../mod/src/main/java/dev/aresos/zone/GateBuilder.java:282).

   **Scenario:** Build a gate with `/aresos logo terminal`, edit its text display into a personal notice using `/data`, then remove the gate. The hand-built path passes `null` for the expected sign. `made` accepts any text display with the UUID, and cleanup discards the edited notice. A relocated display or replacement text display with that UUID is likewise deleted.

   This loses an entity the ownership rule treats as his. B1 therefore breaches the requested bar. The town-specific path is fixed, but the shared cleanup function deliberately retains this exception. The established package-33 downgrade and grass limitations do not establish ownership of an edited sign.

   Save expected position and text for newly built hand-built gates. For older records lacking that evidence, preserve the display and explain the retained sign. Add an edited hand-built-sign regression through the real removal path.

3. **SHOULD — The new picture-reader test can fail after a correct read.**

   **Where:** [PictureReaderTest.java:27](../../mod/src/test/java/dev/aresos/zone/PictureReaderTest.java:27), [PictureReader.java:61](../../mod/src/main/java/dev/aresos/zone/PictureReader.java:61).

   **Scenario:** The worker completes `result`, waking the test’s `get()`, and the test checks `waiting()` before the worker executes the `whenComplete` removal. It observes one pending entry and fails despite successful reading.

   Waiting for the original future does not guarantee completion of its dependent cleanup callback. Use an executor barrier, as the shutdown test already does, or explicitly await cleanup. This is a suite reliability issue, below the FIX bar.

The report’s principal “from reading” regression claims hold: removing strict decoding permits partial records; removing shared validation permits the tested overlaps; removing the light hook retains the changed-back lights; reverting cleanup deletes the tested edited/reused entities and zone; removing doorway recovery fails the restoration assertion; removing first-build aggregation fails the new line assertions. The settled-world `name` test exercises the actual scheduler trigger. The post-reopen `unname` check is weaker as an isolated trigger regression because the join-triggered pass may still be pending.

The picture tests establish worker execution and deferred placement, but do not directly demonstrate responsiveness with a deliberately slow icon. Shutdown cancellation is tested on `PictureReader`; actual server-stop wiring is supported by inspection. Further important gaps are saving and reopening **while still frozen**, real-command trust permission tests, failed-save handling, and persisted refusal checks for overlapping files. Walking through a town doorway and real-client unloaded-ground retries remain explicitly unverified. The builder’s reported successful runs were not reproduced in this review.

Normal save/reopen, whole-world copy and trust renewal have meaningful coverage. The mixin’s `RETURN` hook itself does not establish that the underlying file write succeeded; the literal “every write, and only then” claim is stronger than the supplied tests establish. A seal-write gap remains an accepted conservative false alarm. Another program replacing world files while the game is running remains a known limit: ownership is loaded and checked once, then maintained in memory. Neither FIX above requires that concurrent-write case.

VERDICT: CHANGES-NEEDED