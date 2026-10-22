Reviewed `34d248b`. Static review only; no tests rerun. Binary screenshots and golden images excluded.

1. **blocking — Discovery can permanently duplicate existing apps.**  
   Where: [WindowsAppCatalogue.java:89](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:89), [AppsConfig.java:117](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/config/AppsConfig.java:117).  
   Discover `B.lnk`, then add an earlier-sorted `A.lnk` targeting the same executable and arguments. Discovery now keeps A and suppresses B. A receives a different ID and Explorer argv, so merge appends it while retaining B forever. Existing configured commands with arguments also fail matching because direct-target reconciliation accepts only single-element argv.  
   **Fix:** reconcile complete launch identities against existing entries before choosing shortcut representatives or wrapping launches in Explorer. Prefer existing IDs, preserve owner argv, and diagnose ambiguous matches. Test alias additions and configured commands with arguments.

2. **blocking — Distinct shortcuts are silently dropped.**  
   Where: [windows-discovery.ps1:48](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/resources/aresos/windows-discovery.ps1:48), [WindowsAppCatalogue.java:89](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:89).  
   Shortcut deduplication compares only executable and arguments; discovery never records working directory. Two shortcuts running the same interpreter with `app.py` from different project directories represent different apps, but only one reaches the catalogue.  
   **Fix:** include working directory in launch equivalence, and collapse shortcuts only when their launch behavior is equivalent. Add a fixture containing identical targets/arguments with different working directories.

3. **should-fix — Hotbar moves through chest menus never persist pins.**  
   Where: [AppInventoryMixin.java:20](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/mixin/AppInventoryMixin.java:20).  
   Tracking starts only for `InventoryMenu`. Moving an app between the player inventory and hotbar while a chest is open changes hotbar membership without updating `apps.json`. Opening the ordinary inventory afterward cannot recover the change: its baseline already contains the new hotbar.  
   **Fix:** track hotbar changes across applicable container menus, retaining the Live/desktop/host guards. Test pinning and unpinning through a chest.

4. **should-fix — Overflow pins never enter subsequently freed hotbar slots.**  
   Where: [AppInventory.java:37](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/item/AppInventory.java:37), [AppItems.java:59](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/item/AppItems.java:59).  
   With a full hotbar, population places a configured pinned app in the main inventory. After freeing a hotbar slot and rejoining, `placePinned` finds that existing item and skips it. The app remains outside the hotbar indefinitely despite `pinned: true`.  
   **Fix:** move an existing pinned item into an available hotbar slot during population, without duplication or overwriting ordinary items. Test full-hotbar overflow followed by freeing a slot and rejoining.

5. **should-fix — Failed configured-icon refreshes retain stale artwork.**  
   Where: [WindowsAppCatalogue.java:69](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:69).  
   When extraction for a configured command returns `icon: null`, the decoder ignores the record. Its previous generated source PNG and configured cache path survive, so `IconPack` continues displaying the old icon instead of falling back to `look`.  
   **Fix:** explicitly invalidate owned source files and merge an empty icon result when extraction fails. Preserve custom icon paths. Test successful extraction followed by an unreadable or missing source.

CHANGES-NEEDED