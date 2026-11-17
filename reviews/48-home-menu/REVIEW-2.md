Reviewed **e904c0c5** against **877753ea**, excluding changes brought by the main merge and REVIEW-1’s 46/48 integration items. **No remaining findings within this scope.**

1. **Blocking — recovery identity and retry: closed.** [HomeSwitch.java](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeSwitch.java:213) now reopens the tracked old-home location even when AresHub holds the replacement. Tracking updates after successful renames, including undo and restoration. Chat distinguishes the actual outcomes. Failed reopening or timeout retains recovery state and presents Try again; the title-screen guard remains active. Completion requires the expected folder and level name with loading finished.

2. **Should-fix — New home from an archive: closed.** [HomeSwitch.java](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeSwitch.java:103) records and validates the current save before closing it. [HomeSwap.java](/var/home/ares/AresOS-48-home-menu/mod/src/main/java/dev/aresos/world/HomeSwap.java:77) handles an existing or absent AresHub independently, leaving the source archive’s name intact. Failure returns to that source.

3. **Should-fix — Create disabled after cancellation: closed.** [HomeCreateScreen.java](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/HomeCreateScreen.java:85) explicitly re-enables Create when confirmation is cancelled. The same chooser retains its choices; the regression test clicks Create again without changing type or reopening it.

4. **Nit — stale key hint: closed.** [AresOsMenuScreen.java](/var/home/ares/AresOS-48-home-menu/mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java:93) refreshes the hint when the menu returns, and the Apps tooltip uses the actual mode binding. Tests check both after rebinding through Settings.

The [recovery tests](/var/home/ares/AresOS-48-home-menu/mod/src/gametest/java/dev/aresos/test/HomeMenuClientGameTest.java:461) cover both restoration failures, archive switches with and without AresHub, damaged-save reopening, timeout and retry. They assert world folder, distinct level names, exact recovery chat and absence of title screens.

The package’s own changes stay within the brief’s allowed paths. Documentation and verification results are recorded. This was static review only; I ran no build, Gradle, tests or game and changed no files.

SAFE