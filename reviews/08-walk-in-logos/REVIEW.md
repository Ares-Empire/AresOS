Reviewed commit `8c3d87b`. This was a static review; I did not rerun game tests.

1. **blocking — Adjacent zones can relaunch an app without the player leaving its zone.**  
   [WalkInZones.java:70](/C:/Users/pab/AresOS-08-walk-in-logos/mod/src/main/java/dev/aresos/zone/WalkInZones.java:70) uses `findFirst()` and remembers only that zone. Two boxes sharing a boundary are accepted, but the player’s body can intersect both. Moving beside that boundary can select B → A → B while continuously intersecting B, launching B twice.  
   **Fix:** retain membership and launch state per zone until the player actually leaves it, or reject spacing that permits ambiguous body intersections. Add an adjacent-zone regression test.

2. **blocking — Construction can silently destroy neighboring blocks.**  
   [LogoBuilder.java:76](/C:/Users/pab/AresOS-08-walk-in-logos/mod/src/main/java/dev/aresos/zone/LogoBuilder.java:76) checks air inside the placement area, then calls `setBlockAndUpdate`. A valid cactus immediately behind the proposed wall lies outside that area. Placing a solid logo pixel beside it invalidates the cactus, causing vanilla to break it without confirmation.  
   **Fix:** check whether planned placement invalidates existing neighboring blocks and refuse before writing. Add a game test proving an adjacent cactus remains unchanged.

3. **should-fix — A new logo can obstruct another zone’s saved exit.**  
   [ZoneData.java:23](/C:/Users/pab/AresOS-08-walk-in-logos/mod/src/main/java/dev/aresos/zone/ZoneData.java:23) checks trigger boxes against exits, but excludes the logo’s solid blocks. A wall at `z=4`, with its trigger occupying `z=[2,4)`, can place a block around an existing exit at `z=4.5` without triggering any conflict. Subsequent returns from that existing zone are refused.  
   **Fix:** reject proposed blocks intersecting any saved exit’s standing body. Test disjoint trigger boxes whose wall would obstruct an existing exit.

4. **should-fix — Opening a screen before the app takes focus loses the return teleport.**  
   [FocusReturn.java:49](/C:/Users/pab/AresOS-08-walk-in-logos/mod/src/main/java/dev/aresos/focus/FocusReturn.java:49) emits a return token only when `eligible`, which requires no screen at focus loss. Enter a zone, then open inventory while the program starts: launching succeeds, but returning produces no zone-return notification.  
   **Fix:** separate return-token ownership from permission to close a pause screen. Preserve the existing screen while still notifying the server. Add this delayed-focus case to the client tests.

5. **should-fix — Live protection covers mining only.**  
   [WalkInZones.java:52](/C:/Users/pab/AresOS-08-walk-in-logos/mod/src/main/java/dev/aresos/zone/WalkInZones.java:52) protects through `PlayerBlockBreakEvents.BEFORE`. TNT or a Nether bed explosion bypasses that event and can destroy logo blocks in Live mode; disabling mob griefing does not prevent those explosions.  
   **Fix:** also exclude protected logo positions from explosion destruction in Live mode, while allowing Build-mode editing. Test actual explosion damage against both modes.

CHANGES-NEEDED