Reviewed commit `4c88529`. Static review against the brief and vanilla/Fabric sources; I did not rerun Gradle or the client in this read-only sandbox.

1. **blocking — Item-use state does not guarantee one launch per click.**  
   [AppItem.java:27](C:/Users/pab/AresOS-01-first-app/mod/src/main/java/dev/aresos/item/AppItem.java:27)  
   Holding right-click, switching to an empty hotbar slot, then switching back ends vanilla’s use state and permits another launch without another click. Conversely, releasing and pressing again between client ticks leaves `isUsingItem()` true; vanilla drains the queued second click without calling `use()`. The existing test leaves four ticks between clicks, so it misses this.  
   **Fix:** Track actual client press/release events independently of item-use state. Add fake-launcher tests for held-click slot changes and release/repress between ticks.

2. **should-fix — Interactive targets can swallow app launches.**  
   [AppItem.java:22](C:/Users/pab/AresOS-01-first-app/mod/src/main/java/dev/aresos/item/AppItem.java:22)  
   Launching is hooked only through `Item.use()`. Vanilla handles block and entity interactions first: right-clicking while holding Notepad and targeting a chest, door, or villager can perform that interaction and return before the launcher runs. The client test aims into empty space, masking this dependency on where the player looks.  
   **Fix:** Handle app activation before target interactions and consume the click once. Add client tests targeting an interactive block and entity, asserting one launch and no unintended interaction.

3. **should-fix — An earlier launch failure can cancel a newer launch’s focus return.**  
   [AresOsClient.java:60](C:/Users/pab/AresOS-01-first-app/mod/src/client/java/dev/aresos/client/AresOsClient.java:60)  
   Every failed future unconditionally resets the shared `FOCUS_RETURN`. If launch A is slow, launch B succeeds and creates its focus-loss pause screen, then A fails, A’s callback erases B’s ownership record. Returning from B leaves the pause menu open. Slow executable paths make this possible with the real asynchronous launcher.  
   **Fix:** Associate focus tracking with a launch generation/token; only let a failure cancel its own tracking. Test two controlled futures where the earlier request fails after the newer request captures a pause screen.

CHANGES-NEEDED