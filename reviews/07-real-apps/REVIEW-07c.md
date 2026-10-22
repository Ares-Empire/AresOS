Reviewed `c158fb5..42d750b` for 07c only.

1. **blocking — Notepad grouping can silently drop a distinct executable.**  
   **Where:** [WindowsAppCatalogue.java:113](/C:/Users/pab/AresOS-07-real-apps/mod/src/main/java/dev/aresos/catalogue/WindowsAppCatalogue.java:113), using `notepadAlias` at line 198.  
   **Why:** The predicate accepts any path ending in `/notepad.exe`. With the default configured Notepad, discovery of both its Store record and an unrelated `C:\Tools\notepad.exe` shortcut puts both into the `"notepad"` group. That entire group reconciles to the existing entry, so the distinct Tools application never reaches the config. Before 07c, these launches had separate identity groups. The new repurposing test checks the **configured** command, but does not cover an unrelated discovered executable.  
   **Fix:** Restrict executable aliases to known Windows Notepad paths, alongside the known Store identity. Add a regression with configured default Notepad, its Store record, and `C:\Tools\notepad.exe`; require two entries, unchanged owner fields, and stable IDs after rediscovery.

The two original regressions are fixed for their tested scenarios. Archived pre-fix XML records both expected failures; both full-pass logs show the new tests and existing 07b alias/argv, working-directory, container-pin, overflow, and icon-fallback checks passing. Existing tests were unchanged. Gradle was not rerun in this read-only review.

CHANGES-NEEDED