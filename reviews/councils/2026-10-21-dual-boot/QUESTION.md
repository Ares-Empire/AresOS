# Council: same-drive dual boot plan and install guide (2026-10-21)

**Under review:** `docs/INSTALL.md` and the dual-boot changes to `docs/design/OS-BASE.md` (PR #5, branch `pkg/05-dual-boot`, diff `git diff main...HEAD`). Also read `briefs/05-dual-boot.md`, `reviews/05-dual-boot/REPORT.md`, and `README.md` / `CLAUDE.md` hard rule 1.

**Context:**
- The owner is a student, not a Linux expert, using German Windows 11 Home on a Lenovo LOQ 15IRH8. One 512 GB NVMe SSD with about 168 GB free, Secure Boot off, encryption believed off.
- They chose same-drive dual boot to avoid buying a second SSD. They will perform every disk step themselves by following `docs/INSTALL.md`. Agents never touch the laptop's disks.

**Decision that depends on this:** whether the owner can follow this guide on their only laptop once the image handoff exists.

**Questions:**
1. **Safety:** is there any step where following the guide as written could damage or erase Windows partitions, Windows boot files or personal data, or leave the laptop unable to boot Windows? Is the undo path really safe? Are the stop conditions complete?
2. **Followability:** where would a non-expert most likely make a mistake (wrong partition selected, wrong installer option, wrong ISO, wrong German UI name, an ambiguous instruction)? Does each risky step say what they should see on screen before clicking?
3. **Proportionality:** is anything in the guide unnecessary ceremony for a hobby dual boot that would make the owner skip steps? What is the minimal safe version?

**Output:** follow `docs/REVIEW.md` (councils). For every finding give the gap in one line, a concrete scenario, the impact, the fix, and the check. Most severe first.
