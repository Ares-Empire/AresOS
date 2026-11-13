Reviewed `a2ba13bd..0ad8b5fb` and the affected paths only; ignored the later merge. Read-only review, including relevant local Minecraft bytecode. I did not run Gradle or the game.

1. **CLOSED — Damaged flat-home data.**  
   [NetherHome.java:94](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/world/NetherHome.java:94) removes partial codec results; `get()` rejects a missing exact home when the manifest identifies the save as flat. Rejection neither dirties nor replaces the saved data. Arrival, respawn override, and `home set` respect that rejection. Healthy exact homes pass unchanged, and legacy Nether homes retain their anchor fallback. The added save-opening regressions cover missing, malformed, and partial nested data, unchanged position/respawn/world state, the warning, and byte-identical home files after shutdown.

2. **CLOSED — Permanent relinquishment of ownership.**  
   [HubBlockChangeMixin.java:15](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/mixin/HubBlockChangeMixin.java:15) observes completed block-kind changes. [HubData.java:86](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/hub/HubData.java:86) removes entries from both representations and marks the record dirty; observed mismatches do likewise. Same-material replacement cannot reclaim ownership, including after restart. Failed/no-op writes, same-kind state changes, wrong-dimension checks, and refused Live-mode breaks do not relinquish unchanged fixed blocks. The client regression checks both relinquished and still-owned blocks after reopening.

3. **CLOSED — Guest-controlled explosion protection.**  
   [HubData.java:115](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/hub/HubData.java:115) selects only the singleplayer host. Unknown host and Live protect; host Build permits destruction. Guest mode cannot change that policy. Coverage includes the policy function, an unidentified-host/creative-guest case, and actual explosions with the real client host.

4. **ACCEPTED-AS-DECIDED — Group names.**  
   Version 1 names remain the mod’s and change with the look. The report now states the exception and retains name-survival assertions. This follows the explicit design decision; no code fix remains.

5. **CLOSED — Continuous no-mob observation.**  
   [MobAdditions.java:16](/var/home/ares/AresOS-32-flat-home/mod/src/gametest/java/dev/aresos/test/MobAdditions.java:16) retains entity-addition counts throughout the observation interval, so subsequent death, removal, or departure cannot erase evidence. A dedicated regression covers addition and removal within one tick. The quiet interval checks the cumulative count, retains the positive control, and restores every changed rule, including `SPAWN_MONSTERS` last. Omitting the actual-home client sprint follows the fix brief’s explicit allowance and the report’s measured timeout.

**No remaining or newly introduced blocking, should-fix, or nit findings within this scope.**

Known limits, not another fix round:

- Ownership tracking is not an authorization boundary for deliberate world alterations. Owner-arranged piston changes or a guest explicitly granted creative editing can change blocks and therefore relinquish them. Ordinary Live attacks and guest-triggered explosions cannot strip protection from unchanged blocks. These require the unusual owner-enabled circumstances you excluded.
- The continuous 12,000-tick check uses the server flat fixture under production rules. The actual initialized home is checked separately; a continuous client-home interval remains unverified. Reported test passes were not independently rerun here.

SAFE