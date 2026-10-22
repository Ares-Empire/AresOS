# 10: Install guide for AresOS on its own SSD

**Owner decision (2026-10-22):** AresOS gets its **own internal SSD**, a Crucial P310 500 GB NVMe (CT500P310SSD801), in the laptop's free M.2 2280 slot. This replaces same-drive dual boot as the main route, because the owner wants to use AresOS regularly and keep Windows' space. The Windows SSD (Micron 512 GB) is never touched. The same-drive guide stays as a documented fallback.

**Goal:** rewrite `docs/INSTALL.md` (and the matching parts of `docs/design/OS-BASE.md` §8 and Appendix C) for the own-SSD route. The guide must be **much simpler** than the same-drive one while staying safe. The owner is a student, not a Linux expert, on German Windows 11 Home.

**Read first:** the current `docs/INSTALL.md`, `INSTALL-RECORD.md`, `docs/install-tools/`, OS-BASE §3, §8 and Appendix C, `reviews/councils/2026-10-21-dual-boot/` (lessons that still apply: two USB sticks, German UI names, stop conditions, undo), and `CLAUDE.md` hard rule 1.

**Laptop facts:**
- Lenovo LOQ 15IRH8 (82XV), UEFI, Secure Boot OFF, device encryption believed off.
- One Micron MTFDKCD512TFK (2242) in one slot. The 2280 slot is believed empty, because Windows sees only one disk.
- F12 is the boot menu.

**In scope:**
1. **Fitting the SSD** (owner, physical), in plain steps based on Lenovo's own hardware maintenance manual for this model (cite it):
   - shut down fully, unplug, and use the battery precaution Lenovo prescribes
   - bottom cover screws and clips, ESD care, where the 2280 slot is, the screw or standoff, any thermal pad or shield
   - closing up
   - checking in the BIOS/UEFI setup that both drives are listed
   - stop conditions (for example the slot is occupied, missing parts, a damaged clip)
2. **Installing:** official Bazzite installer from the installer USB, targeting **only the new Crucial disk**.
   - Use whole-disk automatic partitioning if the current installer supports it safely for a chosen disk. Prefer that over manual partitioning, and only use the legacy ISO if it's required.
   - Exact disk identification on screen (model "Crucial"/"CT500P310SSD8", about 465 GiB, empty) versus the Windows disk (Micron, about 477 GiB, with partitions).
   - The new disk gets its own EFI partition. Nothing is written to the Windows disk or its EFI partition.
   - The Windows recovery stick is still made first and kept. The installer stick gets erased.
3. **Switching to AresOS:** keep the rebase/account steps as a clearly marked placeholder pointing to brief 06 (image release). That part isn't released yet, so physical installation stays gated.
4. **Choosing the OS at startup:** F12, and/or setting the boot order in the Lenovo firmware, with Windows Boot Manager kept intact. What to do if Windows updates change the order.
5. **Undo:** remove AresOS by wiping only the Crucial disk, or simply removing it. Windows was never changed.
6. **Read-only helper:** adapt `docs/install-tools/` if needed, so the owner can confirm before and after installing that the Windows disk is unchanged (same partitions and GUIDs).
7. **Keep the same-drive guide** as an appendix or separate file, marked as the fallback.

**Out of scope:** doing any of it, touching disks, installing anything, and OS code. Web research and docs only.

**Acceptance:**
- The updated docs are committed with a PR open.
- Every external fact has a dated source.
- `reviews/10-own-ssd-install/REPORT.md` exists.
- A design council (safety + followability) reviews it next, so write it to be challenged.

**If unsure:** pick the option that never writes to the Windows disk and is easiest for a novice to follow.

**Model:** gpt-6-astra, xhigh.
