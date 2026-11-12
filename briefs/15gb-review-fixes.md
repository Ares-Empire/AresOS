# 15gb: Review fixes for 15g

Follow-up on branch `pkg/15g-install-night-guide-fixes` (PR #23). Brief 15g still applies. Read `reviews/15g-install-night-guide-fixes/REVIEW.md` (CHANGES-NEEDED at `c20510e6`).

All four points are accepted. Fix them as the review proposes:

1. **Reinstall return.**
   - The failure route keeps its return to step 4 box 1.
   - Once record C passes on the retry, INSTALL-RECORD's reinstall checkpoint returns straight to the installer boxes in the **current** live session, the keyboard/destination box. It must not go back to box 1 again.
2. **Windows serial reading.**
   - Give the Windows printed-serial reading in INSTALL-RECORD its own checkpoint.
   - It ends with an explicit "PASS → Return to step 4, box 1" link, placed before the Linux identification text.
3. **Idle live-session shutdown.**
   - State the idle-live-session exception identically in EMERGENCY.md and INSTALL-REFERENCE.md.
   - Keep the ten-minute wait, the exclusions, the Windows return and the mandatory Help.
4. **Layout procedures.**
   - INSTALL-PROCEDURES lines 9 and 41 assume an umlaut password. The new alphabet rules that out.
   - Explain that the password stays typeable, and that the public `yz-/!ü` proof exercises the layout difference.
   - Keep the supervised negative test and its recovery protections.

Extend the owner-path tests to pin each fix. Keep `os/manifest/ci/16/pending-rebind.json` exact for any bound file you change. Same sandbox rules as before: edit only in this worktree; do not commit, push or run WSL. Then add a "15gb" section to the REPORT.

**Model:** gpt-6-astra, xhigh.
