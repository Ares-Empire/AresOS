1. **FIXED — SSD removal.** [Line 55](/C:/Users/pab/AresOS/docs/EMERGENCY.md:55) requires §9’s full procedure, including verified backups and Windows checks. That procedure explicitly verifies the original Micron EFI target. Failed checks mean leave the SSD installed; remaining firmware changes are acknowledged.

2. **FIXED — Reaching GRUB.** The card distinguishes F12 from GRUB and explicitly routes recovery through F12 → Linux entry → GRUB. It distinguishes the Linux deployment default from Windows’s firmware default.

3. **PARTIAL — Deployment identity and untested promotion.** [Line 32](/C:/Users/pab/AresOS/docs/EMERGENCY.md:32) correctly requires the recorded stock entry, rejects selection by position, and provides a stop condition. However, “not tested yet, so if anything looks different … stop” still suggests proceeding when screens match. INSTALL §6 explicitly calls this an **UNTESTED, open release gate**. Preserve that wording and make clear that matching screens do not close the gate.

4. **FIXED — Forced shutdown.** A brief press and approximately one-minute wait precede holding until off. The card warns about lost work, excludes firmware/BIOS update screens, and removes the unsupported ten-second timing.

5. **FIXED — Windows availability.** Windows is described as the intended return route, explicitly without a guarantee. Missing entries or failed startup require stopping and getting help.

6. **FIXED — Terminal safety and availability.** The card states that the terminal lacks administrator rights but can change/delete personal files, defines Super, and directs failed shortcut attempts to the Ctrl+Alt+F3 row.

All four unique INSTALL anchor links resolve to their intended headings; the relative file target also exists.

**New problems:** None identified within the requested scope. The remaining **should-fix** issue is finding 3 above.

CHANGES-NEEDED