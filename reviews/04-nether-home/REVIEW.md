Reviewed commit `47a6dd1`. Two findings:

1. **blocking — Missing home data silently rebuilds an existing hub.**  
   **Where:** [NetherHome.java:95](/C:/Users/pab/AresOS-04-nether-home/mod/src/main/java/dev/aresos/world/NetherHome.java:95).  
   If an established save retains its manifest but loses `data/aresos/nether_home.dat`—for example during an incomplete restore—the startup handler calls `initialize()` again. It replaces the entire hub volume, destroys player edits, reapplies gamerules, and re-enables a disabled desktop marker. The corruption guard catches an unreadable file only when that file still exists. The current reload test keeps it intact, so it misses this failure.  
   **Fix:** Persist a completed provisioning state and refuse automatic construction when a completed save lacks home data. Permit construction only for an explicitly new creation. Add a regression that edits the hub, removes its home-data file, and verifies reopening refuses recovery without changing blocks.

2. **should-fix — Saved vehicle restoration overrides hub arrival.**  
   **Where:** [PlayerListHomeMixin.java:15](/C:/Users/pab/AresOS-04-nether-home/mod/src/main/java/dev/aresos/mixin/PlayerListHomeMixin.java:15), calling [NetherHome.java:157](/C:/Users/pab/AresOS-04-nether-home/mod/src/main/java/dev/aresos/world/NetherHome.java:157).  
   In the generated 26.2 source, `PrepareSpawnTask.Ready.spawn()` calls `placeNewPlayer()`, then `loadAndSpawnParentVehicle()`. Consequently, quitting while riding a minecart or strider away from home initially places the player at the hub, then remounts them at the vehicle’s saved position. If the vehicle was saved in the Overworld, restoration now creates it in the Nether at those coordinates. The current rejoin test saves an unmounted player.  
   **Fix:** Handle saved vehicle restoration explicitly for home arrivals, preserving the vehicle in its original dimension without remounting the arriving player. Keep the early login-dimension hook. Test mounted rejoins from both dimensions and assert the player remains at the hub after subsequent ticks.

Static review included the generated vanilla sources and recorded verification output. `git diff --check main...HEAD` passed; game tests were not rerun in this read-only review.

CHANGES-NEEDED