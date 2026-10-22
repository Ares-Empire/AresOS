# Council: own-SSD install guide (2026-10-22)

**Under review:** `docs/INSTALL.md` (rewritten for AresOS on its own SSD), `docs/INSTALL-RECORD.md`, `docs/install-tools/`, and the matching changes to `docs/design/OS-BASE.md` §8 and Appendix C. PR #9, branch `pkg/10-own-ssd-install`, diff `git diff main...HEAD`. Also read `briefs/10-own-ssd-install.md`, `reviews/10-own-ssd-install/REPORT.md` and `CLAUDE.md` hard rule 1.

**Context:**
- The owner is a student, not a Linux expert, using German Windows 11 Home on a Lenovo LOQ 15IRH8 (82XV).
- They will fit a Crucial P310 500 GB NVMe into the free M.2 2280 slot themselves (opening the bottom cover), then install AresOS onto that whole drive. The Windows SSD (Micron 512 GB, 2242) must never be touched.
- Secure Boot is off, and encryption is believed off.
- The earlier same-drive guide went through a council (`reviews/councils/2026-10-21-dual-boot/`). Its lessons should still hold where relevant.

**Questions:**
1. **Safety:** can following this guide as written damage Windows, its partitions, its boot files or personal data, or physically damage the laptop (opening the case, ESD, battery, screws, clips)? Are disk identification and stop conditions sufficient so the installer can't target the Windows drive? Is undo safe?
2. **Followability:** where would a non-expert most likely make a mistake (opening the laptop, picking the wrong slot or disk, the installer's disk selection, German UI names, the BIOS/boot menu)? Does each risky step say what they should see before acting?
3. **Proportionality:** with a separate drive, which ceremony from the same-drive guide is no longer needed? What is the minimal safe version?

**Output:** follow `docs/REVIEW.md` (councils). For every finding give the gap in one line, a concrete scenario, the impact, the fix, and the check. Most severe first.
