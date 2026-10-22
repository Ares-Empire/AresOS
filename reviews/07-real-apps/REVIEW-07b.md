Reviewed `cf62b88..5ea4cfc`, excluding binary images. Inspected source, recorded pre-fix failures, JUnit results, and both successful full-pass logs. Gradle was not rerun in this read-only review.

1. **blocking — Finding 1’s alias/argv tests pass, but Notepad reconciliation regressed.**  
   **Where:** [WindowsAppCatalogue.java:134](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:134).  
   **Why:** With the default `notepad` command configured, a `Microsoft.WindowsNotepad_*` UWP record cannot match its executable identity. The replacement alias condition explicitly requires `notepad` to be absent, so discovery appends a hashed entry. Previously, the explicit Notepad alias retained the existing ID. Current fixtures never combine configured Notepad with its Store record.  
   **Fix:** Restore deliberate reconciliation of the known Notepad aliases, checking that the owner has not repurposed the entry. Add a migration-plus-discovery regression asserting one entry and unchanged owner fields.

2. **blocking — Finding 2’s directory case is fixed, but argument normalization can silently drop distinct shortcuts.**  
   **Where:** [WindowsAppCatalogue.java:150](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:150), grouped at line 111.  
   **Why:** Identity retains parsed `argv` and discards raw shortcut arguments. For `cmd.exe`, `/d /c echo "one&ver"` and `/d /c echo one&ver` produce identical `CommandLineToArgvW` arrays but different behavior: quoting protects `&` from command separation. Discovery therefore collapses distinct launches. The previous raw-argument comparison kept them separate. [Microsoft documents cmd’s quoting rules](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd).  
   **Fix:** Preserve raw arguments when equivalence cannot be established safely; diagnose ambiguous configured matches. Add native shortcut fixtures for these two command lines and assert two apps survive.

3. **should-fix — Finding 3 resolved.**  
   **Where:** [AppInventoryMixin.java:20](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/mixin/AppInventoryMixin.java:20).  
   Container tracking now includes chest menus, retains Live/desktop/host guards, and saves completed moves. The client regression demonstrates actual mouse-driven pin/unpin and recorded failures before the fix. No further fix identified.

4. **should-fix — Finding 4 resolved.**  
   **Where:** [AppItems.java:66](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/item/AppItems.java:66).  
   Population moves the existing stack into a free hotbar slot and clears its former slot. The previously failing overflow/rejoin test checks exactly one app and preservation of ordinary stacks. No further fix identified.

5. **should-fix — Finding 5 resolved.**  
   **Where:** [WindowsAppCatalogue.java:84](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:84).  
   Failed extraction now deletes the owned source and merges an empty icon result; custom paths survive. Decoder/native regressions failed before and pass afterward, including generated-artifact cleanup. No further fix identified.

Both full-pass logs also retain the existing normal-world/Build guards and one-launch-per-click checks. Launch handling itself is unchanged.

CHANGES-NEEDED