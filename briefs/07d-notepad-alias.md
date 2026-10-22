# 07d: Narrow the Notepad alias

Follow-up on branch `pkg/07-real-apps` (PR #6). Read `reviews/07-real-apps/REVIEW-07c.md`.

**Goal:** fix the one regression 07c introduced. The Notepad alias matches any path ending in `notepad.exe`, so an unrelated `C:\Tools\notepad.exe` gets swallowed into the `notepad` entry.

**In scope:** only the known Windows Notepad identities count as aliases:
- `%WINDIR%\notepad.exe`
- `%WINDIR%\System32\notepad.exe`
- `%WINDIR%\SysWOW64\notepad.exe`
- the `Microsoft.WindowsNotepad_*` Store identity

Resolve environment variables and compare normalized full paths. Regression test: configured default Notepad + its Store record + a `C:\Tools\notepad.exe` shortcut → two entries, owner fields unchanged, ids stable after rediscovery. All earlier 07/07b/07c tests stay green.

**Acceptance:** the new test fails before the fix (show it) and passes after. Run the full `build runClientGameTest` twice, green. Add a "07d" section to `REPORT.md`, and stop your Gradle daemons.

**Model:** gpt-6.1-sol, xhigh.
