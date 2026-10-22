Reviewed 09c through `79220ae`. One blocking regression remains.

1. **Blocking — timeout rollback can permanently lose picked-up items.**  
   **Where:** [ModeInventories.java:80](C:/Users/pab/AresOS-09-mode-inventories/mod/src/main/java/dev/aresos/mode/ModeInventories.java:80), invoked by timeout recovery at line 122.  
   **Why:** while acknowledgement is pending, the guards block item-action packets but leave automatic item pickup running. With a lost acknowledgement, a player can collect a dropped item during the 200-tick window: vanilla removes the item entity and adds its stack to the destination inventory. Rollback then overwrites that inventory and restores the earlier snapshots, erasing the collected item everywhere. The timeout tests leave the destination inventory unchanged, so they miss this loss.  
   **Fix:** prevent automatic pickups while pending, or preserve those transfers transactionally through rollback. Add a regression with inventory space, a dropped item and a withheld acknowledgement; assert that timeout/reconnect preserves the total item count across both inventories and the world.

The original unsupported-client finding is fixed before transaction mutation. The regression commit and local red log demonstrate both new tests failing before the fix. Local logs corroborate two complete green runs on unchanged final sources; the diff checks also passed. I did not rerun Gradle in this read-only review.

CHANGES-NEEDED