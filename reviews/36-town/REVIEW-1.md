Reviewed commit `a0ae24bbf749fb359ef6138527b6581c586d8b1e` — read-only review; no files changed and no builds, tests or game runs performed.

| Point | Status | Reason |
|---|---|---|
| 1. Ownership and world safety | OPEN | Downgrades, foreign or overlapping records, edited lights and reused identifiers can cause removal of the owner’s property. |
| 2. Complete list and flat-home restriction | OK | The keeper requires a complete session list and `flat-1`; wanted apps require `mine && !absent`. The helper publishes complete lists only. |
| 3. Loaded ground only | OK | Gate preflight checks chunks and entity availability before world inspection. Road extension checks each row before paving. Unloaded work remains pending. |
| 4. Refusals, reassignment and duplicates | OPEN | Normal passes have bounded rounds and guards against building while an old logo remains. Rejecting an existing town file as though no town existed can nevertheless create duplicate logos. |
| 5. Threads and shutdown | OPEN | The town picture worker uses immutable inputs and a future handover, without accessing the world. The hand-built gate command still waits for picture reading and converts pictures on the server thread. |
| 6. Host-only rebuild | OK | `hub` uses `requires(AppCommands::allowed)` at parsing and checks the host again during execution. |
| 7. Saved data and older mods | OPEN | Package 35 preserves the optional JSON fields through its normal edits; packages 32–34 refuse schema 4 without rewriting it. Preserving `town.dat` does not establish safe ownership after a downgrade. |
| 8. Step-4 tuning | OK | The display mixin only exposes a setter; its production caller targets recorded group names. News suppression is restricted to a flat home with a complete session list. The accepted scale and first-build summary decisions are not findings. |
| 9. Tests and suite safety | OPEN | Coverage includes placement, assignment, refusals, roads and rebuild. New client tests are last, and server tests use plot-relative locations and their own tickets. Persistence, ownership and actual refresh-trigger regressions are missing below. |

Findings are derived from source inspection, not executed reproductions.

1. **FIX — A downgrade can make the town reclaim and delete the owner’s replacement blocks.**

   **Where:** `mod/src/main/java/dev/aresos/hub/HubData.java:168`, `mod/src/main/java/dev/aresos/zone/GateBuilder.java:285`.

   **Scenario:** Package 36 builds a town logo containing red concrete at position P. The owner opens that world with package 35, removes that block and builds his own red-concrete structure through P, then returns to package 36. The older mod never updates `town.dat`, so the old ownership entry survives. Package 36 adopts it and removal or renewal deletes P because its current block ID matches.

   The accepted limitation that older mods do not protect town blocks does not justify deleting the owner’s subsequent edits. This breaches rule 1 for the new town ledger; it is distinct from the accepted hand-built-gate limitation.

   Establish ownership continuity across older writers, or conservatively suspend destructive reconciliation when continuity cannot be established. The existing downgrade tests only rewrite `hub.dat` without editing town blocks.

2. **FIX — The town file is not bound to a particular world, and a mismatched file is silently replaced.**

   **Where:** `mod/src/main/java/dev/aresos/hub/HubData.java:109`, `mod/src/main/java/dev/aresos/hub/HubData.java:166`.

   **Scenario A:** Restore or copy `town.dat` from another flat home into this world. Both normally have the same `GlobalPos`: Overworld, `(0,64,0)`. `attach` accepts the foreign ledger. Any owner block matching a recorded material at a recorded position can subsequently be removed as part of that foreign logo.

   **Scenario B:** An existing town file has a different home from `hub.dat`, while its old logos remain in the world. `attach` installs an empty town instead of refusing reconciliation. The keeper then treats the old logos as obstacles, builds the wanted apps elsewhere and dirties the replacement file. The old records are lost and two logos can remain for one app.

   These meet the ownership, data-loss and duplicate-logo bars. Bind the records to persistent world/hub identity, preserve legitimate whole-world copies and renames, and refuse automatic replacement of an existing mismatched or unreadable ledger. The unit test exercises `adopt`’s exception, not `attach`’s replacement branch.

3. **FIX — Loading overlapping logo records bypasses the uniqueness checks and breaks permanent relinquishment.**

   **Where:** `mod/src/main/java/dev/aresos/hub/HubData.java:177`, `mod/src/main/java/dev/aresos/hub/HubData.java:273`, `mod/src/main/java/dev/aresos/hub/HubData.java:300`.

   **Scenario:** A decoded `town.dat` contains logos A and B both recording red concrete at P. Loading calls `index`, bypassing `add`’s checks; `logoBlocks` remembers only B. The owner replaces P with diamond: `forget` removes P from B but leaves A’s entry. He then places red concrete at P. Removing A deletes his replacement.

   This breaches rule 1. Validate decoded records before adopting any of them, including duplicate apps, block ownership, places and identifiers. Conflicting ownership must stop destructive reconciliation. Testing rejection through `hub.add` does not cover loading.

4. **FIX — Light-state edits are not permanently relinquished.**

   **Where:** `mod/src/main/java/dev/aresos/mixin/HubBlockChangeMixin.java:20`, `mod/src/main/java/dev/aresos/hub/HubData.java:283`, `mod/src/main/java/dev/aresos/zone/GateBuilder.java:286`.

   **Scenario:** In Build mode the owner changes a town light from level 15 to another level, then back to 15 before anything calls `holds` on it. Both changes retain the same block kind, so the mixin never removes ownership. Removing or rebuilding the logo then deletes the light.

   The same issue applies to waterlogging and subsequently drying a light. This breaches the town’s explicit permanent-ownership rule. Observe the relevant light-state changes when they happen, while retaining the accepted treatment of automatic mushroom-face changes.

   `TownGameTests.java:467` explicitly calls `holds` after changing the light, which conceals the missing automatic relinquishment.

5. **FIX — Destructive sign and zone cleanup trusts identifiers without checking what they identify now.**

   **Where:** `mod/src/main/java/dev/aresos/zone/GateBuilder.java:297`, `mod/src/main/java/dev/aresos/hub/Town.java:90`, `mod/src/main/java/dev/aresos/hub/HubData.java:223`.

   **Scenario:** A stale or restored town record’s sign UUID now identifies an owner entity. Taking down the logo discards that entity unconditionally—even if it is not a text display. Likewise, if the recorded zone ID now belongs to an owner-created zone, removal deletes that zone by ID alone, without checking its app, dimension or geometry.

   A changed town sign also has no ownership check before deletion. The group-name exception does not establish unrestricted ownership of every entity named by a gate record.

   This breaches rule 1 and can lose owner data. Record and validate enough identity and expected state to establish that the entity or zone still belongs to this logo; preserve mismatches. Include reused-ID and changed-sign regressions.

6. **FIX — The hand-built gate path still blocks the server on picture work.**

   **Where:** `mod/src/main/java/dev/aresos/zone/ZoneCommands.java:118`, `mod/src/main/java/dev/aresos/zone/GateBuilder.java:80`.

   **Scenario:** The owner runs `/aresos logo <app>` for an app whose helper-provided icon is slow to read. The server calls `planInFrontOf → picture → AppIcons.read`; although file access uses a worker, `AppIcons.java:69` waits synchronously for up to three seconds. Decoding and conversion then run on the calling server thread.

   The new helper-picture path therefore introduces a noticeable server stall for apps that previously immediately received a plain front. It also violates rule 5. Read and convert asynchronously, then schedule fresh world preflight and placement on the server thread, checking that the original server and world remain active.

7. **SHOULD — Changing a short name does not schedule a town refresh.**

   **Where:** `mod/src/main/java/dev/aresos/AresOs.java:80`, `mod/src/main/java/dev/aresos/hub/TownKeeper.java:166`.

   **Scenario:** With a settled town and no pending work, run `/aresos app name browser web`, or remove an app’s current main name. The command changes the catalogue and refreshes slash commands, but never calls `TownKeeper.ask`. The sign retains its old command until another unrelated trigger occurs.

   This misses step 3’s requirement that signs follow the main name, but does not meet the FIX bar. Request reconciliation after successful name changes, including automatic reassignment. Test the actual command and scheduler; the current server test changes a fake app and explicitly invokes a pass.

8. **SHOULD — Surviving town records do not repair missing trigger zones after a downgrade.**

   **Where:** `mod/src/main/java/dev/aresos/hub/TownKeeper.java:351`, `docs/design/HUB.md:22`.

   **Scenario:** Open the town with package 35 and remove one of its now-plain zones using `/aresos zone remove`. Return to package 36. The logo record survives, and its picture/version/name are unchanged, so reconciliation skips it. Its doorway remains dead until something forces a rebuild.

   The statement that the files “cannot disagree” is therefore incorrect. Check the corresponding zone during reconciliation and restore a missing zone only after validating ownership and conflicts. Document mismatches that require manual recovery. This is a functional gap, below the FIX bar.

9. **SHOULD — Add persistence and lifecycle regressions rather than relying on in-memory passes.**

   **Where:** `mod/src/test/java/dev/aresos/hub/HubDataTest.java:74`, `mod/src/gametest/java/dev/aresos/test/TownGameTests.java:394`, `mod/src/gametest/java/dev/aresos/test/TownClientGameTest.java:94`.

   **Scenario:** The existing rollback checks round-trip an unchanged hub record; the client test builds, removes an app and rebuilds without reopening the resulting town. They can all pass while the ownership and recovery failures above remain.

   Add regressions for downgrade edits, a mismatched or damaged town file, overlapping decoded ownership, reused sign/zone IDs, light edits changed back, reopening a town, and closing the server while pictures are pending. Also retain the report’s explicit gaps for walking through a town doorway and real-client unloaded-place retries. No existing test result establishes those paths.

VERDICT: CHANGES-NEEDED