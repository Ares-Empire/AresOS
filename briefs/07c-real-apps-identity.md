# 07c: Real apps, two identity regressions from 07b

Follow-up on branch `pkg/07-real-apps` (PR #6). Read `reviews/07-real-apps/REVIEW-07b.md` (findings 1 and 2; 3–5 are resolved).

**Goal:** fix the two regressions 07b introduced, without undoing the 07b fixes.

**In scope:**
1. **Notepad reconciliation.** Restore deliberate reconciliation of the known Notepad aliases (including the `Microsoft.WindowsNotepad_*` Store record) to the existing `notepad` id, but only while the owner hasn't repurposed that entry. Regression test: migration plus discovery with the configured default Notepad and its Store record → exactly one entry, owner fields unchanged.
2. **Raw-argument identity.** Launch equivalence keeps the **raw** shortcut argument string. Collapse only when equivalence is certain, and diagnose ambiguous configured matches instead of guessing. Native shortcut fixtures: `cmd.exe /d /c echo "one&ver"` vs `cmd.exe /d /c echo one&ver` → two apps survive.
- Keep every 07b regression test passing (aliases, argv commands, working directories, container pins, overflow, icon fallback).

**Acceptance:** both new tests fail before the fix (show it) and pass after. Run the full `build runClientGameTest` twice, green. Add a "07c" section to `REPORT.md`, and stop your Gradle daemons.

**If unsure:** keep two entries rather than merge, and never drop or re-id an entry.

**Model:** gpt-6.1-sol, xhigh.
