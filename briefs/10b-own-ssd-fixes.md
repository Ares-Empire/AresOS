# 10b: Own-SSD install guide, council fixes

Follow-up on branch `pkg/10-own-ssd-install` (PR #9). Read `reviews/councils/2026-10-22-own-ssd/VERDICT.md` and both member files first.

**Goal:** resolve all 6 findings (3 blocking, 3 non-blocking), keeping the guide as short as safety allows.

**In scope:**
1. **Battery damage stop (blocking).** Before opening, check for external bulging. Right after lifting the cover, check for visible battery damage (swelling, cracks, leakage, heat, smell). Any damage → stop, don't press or handle it, keep power disconnected, and contact Lenovo or a qualified repairer. Apply the same check to removal. Cite Lenovo's safety guidance.
2. **Physical SSD → installer destination mapping (blocking).**
   - Keep the complete records, and add a simple annotated disk tree.
   - Add a same-session mapping: **model + serial (from the drive label and the live system) → whole-disk device path → the exact installer destination entry**.
   - Turn detailed comparisons into clear PASS/FAIL results the owner can read: Crucial identified after renumbering, no unexpected partitions on Crucial, any proposed write to the Micron or its EFI rejected.
3. **SSD seating before the screw (blocking).** A model-specific sequence: insert at an angle (about 20–30°) without force, fully engaged with the gold contacts barely visible, the notch aligned with the standoff, lower gently, then secure gently without overtightening. **Never use the screw to pull the drive into place.** Include what fully seated vs partly inserted looks like. Cite Lenovo's manual and an SSD maker's installation guidance.
4. **Default undo = "stop using AresOS, leave the Crucial installed".** Verify direct Windows boot and its original boot target, restore Windows as the default, check an unattended restart, done. Removal and erasing become optional extras.
5. **German keyboard first.** In the live session, set and test the German layout (`y z / - " $`) before opening Konsole. Distinguish it from the installer's target keyboard setting.
6. **Admin terminal after reboot.** In record B, repeat "right-click Start → Terminal (Administrator) → Windows PowerShell", and add an elevation pre-check with a clear message.

Keep the existing release gate (physical installation is still not released) and the same-drive fallback file.

**Acceptance:**
- Updated docs plus `reviews/councils/2026-10-22-own-ssd/CHANGES.md` mapping each finding to its fix.
- Dated sources for new facts.
- Helper tests still pass in both PowerShell versions.
- **Don't run the mod's Gradle suite**: this package changes no mod code, and client tests must not overlap with other runs (`CLAUDE.md`).
- Pushed on the branch.

**Model:** gpt-6-astra, xhigh.
