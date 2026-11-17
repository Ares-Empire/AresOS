Reviewed **79c9b1a5**, comparing both branches against `origin/main`. No builds, Gradle, tests, or game runs. The approved JUDGMENT-CALLs are not findings.

1. **Blocking — Failed restoration can reopen the replacement instead of the preserved home.**  
   [HomeSwitch.java:188](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeSwitch.java:188), [HomeSwap.java:103](/var/home/ares/AresOS-48-home-menu/mod/src/main/java/dev/aresos/world/HomeSwap.java:103).

   After promotion succeeds but opening the new home fails, restoration first moves the replacement back to staging. If that move fails, AresHub still contains the replacement and the old home remains archived. `restoreAndOpen` nevertheless opens **AresHub**: it selects the archive only when AresHub is absent. If this succeeds, the chat falsely says “Your home is as it was.” If reopening fails, `fail()` abandons recovery; title screens become permitted, and a recovery timeout can leave the non-dismissible working screen behind.

   **Fix:** track the old home’s actual location and reopen that location whenever restoration fails, regardless of whether another AresHub exists. Keep recovery state and an actionable recovery screen until recovery succeeds. Add failure-injection coverage for both restoration renames and failed reopening, checking the actual world identity and chat.

2. **Should-fix — New home assumes the open world is AresHub, although its menu gate permits every desktop world.**  
   [AresOsMenuScreen.java:40](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java:40), [HomeSwitch.java:97](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeSwitch.java:97).

   The switch never records the current save folder. From an archived desktop world, it closes that world but archives/replaces the unrelated canonical AresHub. On failure it also reopens AresHub instead of the world the owner left. This is reachable through this package’s own archive-opening recovery fallback: another New home attempt then fails because AresHub is missing and tries to recover by opening that missing path.

   **Fix:** capture and validate the current world before closing it. Either safely reject New home outside canonical AresHub while leaving the current world open, or explicitly support those worlds with correct source and recovery paths. Test the archive fallback followed by another New home attempt.

3. **Should-fix — Cancelling confirmation leaves Create disabled.**  
   [HomeCreateScreen.java:49](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeCreateScreen.java:49), [AresOsMenuScreen.java:70](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java:70).

   Create disables itself before opening confirmation. Cancel returns the same chooser instance. Minecraft 26.2 does not rerun protected `init()` when that initialized screen returns, so Create remains disabled—even after editing the seed. The existing cancellation test immediately cancels the chooser too, missing this.

   **Fix:** re-enable Create when confirmation is cancelled, preserving the choices. Test Create → Cancel → Create again without toggling the home type or reopening the chooser.

4. **Nit — The key hint becomes stale after changing controls.**  
   [AresOsMenuScreen.java:54](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java:54).

   The hint is constructed only during initial initialization. Settings returns to the same menu instance, so rebinding G or inventory leaves the old keys displayed. The Build-mode Apps tooltip also hardcodes G.

   **Fix:** refresh the hint when returning to the menu and use the actual mode binding in the tooltip.

The principal staging order is sound on static inspection: creation leaves the old AresHub in place; a process kill between the forward renames leaves the old archive and staging folder; after promotion, the checked replacement occupies AresHub and the archive remains. A failed second rename attempts the correct undo. The defects above concern subsequent recovery and world selection.

First start correctly excludes existing paths, including dangling symlinks, and makes its decision once. The menu gate preserves Minecraft’s menu in normal worlds and outside sessions. During a switch, readiness is suppressed; after `ready:false`, the supervisor’s startup timeout is excluded by `ever_ready`, and its heartbeat timeout is excluded by `launch.ready == false`. I found no timer defect in that transition.

The **second merge of packages 46 and 48 must**:

- Make `save_world` return `no_world` throughout `HomeSwitch.busy()`. Cover admission, queued/coalesced requests, and execution so staging never produces a successful acknowledgement. Test success and recovery paths.
- Keep one session-plus-desktop-world predicate, shared by `HomeScreen.home` and the menu gate, independent of helper connectivity.
- Preserve both 46’s HUD saving-text suppression and 48’s working-screen replacements. Test that New home shows no “Saving world” text.
- Update 46’s `SaveNowClientGameTest` around lines 126–138: it currently requires a paused `PauseScreen` in a session desktop world. Assert the non-pausing AresOS menu there; retain paused-save coverage through Settings or a separate vanilla-menu case, plus covered-world coverage.
- Combine `ShellFocusClient.readyWorld` changes: retain 48’s busy guard and use 46’s `DesktopWorld.saveName(server)` for shared wire identity.
- Preserve both packages’ initialization, production/test mixin registrations, client-test entries, and Gradle properties. Keep existing screenshot numbering and update stale test-order comments.

Those integration items are not counted as findings against this PR.

CHANGES-NEEDED