# 05: Same-drive dual boot plan and install guide

**Goal:** switch the OS design from "AresOS on its own drive" to **dual boot on the existing Windows SSD** (owner decision 2026-10-21: free, and not very risky if done carefully). Write the owner's step-by-step install guide, including an **early first boot** of the plain AresOS image (labwc and a terminal, no Minecraft yet) right after the image package.

**Read first:**
- `docs/design/OS-BASE.md` §3, §8, §10, Appendix C and Appendix E
- `README.md` phases and safety rules, and `CLAUDE.md` hard rule 1
- Bazzite's dual boot and install guides (docs.bazzite.gg)
- Branch `origin/pkg/03-os-image`, if present, for how the image is built and which deployment backend it uses

**Facts about the laptop (msinfo32 and Windows, 2026-10-21):**
- Lenovo LOQ 15IRH8, Windows 11 Home in German, UEFI mode.
- **Secure Boot OFF.** Device encryption almost certainly off.
- One NVMe SSD (Micron 512 GB) with 168 GB free on C:. F12 opens the boot menu.

**In scope:**
1. **Revise the design** (§3, §8, Appendix C, Appendix E) for same-drive dual boot:
   - **Install route:** the official Bazzite installer from a USB stick, with manual partitioning into the free space only. Then switch the installed system to the AresOS image (rebase).
   - **AresOS's own EFI partition:** decide with evidence whether it gets one (Bazzite recommends it), or what the safest alternative is. Windows' boot files are never modified.
   - **Where the rebase image comes from.** GitHub Free private package storage is 500 MB and the image is several GB. Compare a public registry, a local build inside the installed Bazzite with podman from this repo, and release assets. Recommend one and mark it as an owner decision.
   - **Windows prerequisites:** Fast Startup / hibernation off before shrinking, confirm encryption is off, backup first.
   - **Secure Boot stays off,** so no MOK is needed. Turning it on later is a separate owner decision.
   - **Partition size for AresOS:** recommend one with reasoning (deployments, Minecraft, apps, backups) while leaving Windows healthy free space.
   - **Boot selection:** firmware F12 menu and/or GRUB, and what to do if a Windows update changes the boot order.
   - **Appendix C becomes a same-drive safety spec:**
     - never delete, format, move or resize existing Windows partitions
     - how to identify the free space exactly, with what the owner should see on screen
     - abort conditions
     - a safe **undo** path that removes AresOS completely and gives the space back to Windows
2. **Appendix E:** add an **early hardware first boot** right after the image package. Install, rebase, and boot into the plain labwc session. Check the NVIDIA driver (`nvidia-smi`), screen, Wi-Fi, sound, keyboard and touchpad. Then boot Windows and confirm it's fine. After that come the Minecraft milestone (P2) and the full trial (P3).
3. **Write `docs/INSTALL.md`**, a step-by-step guide for the owner. Plain language, with German Windows UI names in parentheses (for example Datenträgerverwaltung, Schnellstart). It covers:
   - backup
   - prerequisite checks
   - making the Bazzite USB stick (which tool and which ISO, per Bazzite's docs)
   - shrinking C:, booting the USB with F12, and the exact installer choices
   - first boot and the rebase to AresOS (put in a clearly marked placeholder if the image distribution isn't decided yet)
   - getting back to Windows
   - undo: removing AresOS completely

   Every risky step says what to check before clicking, and when to stop and ask.
4. **Mark facts:** verified from docs, or assumed for this laptop.

**Out of scope:** doing any of it, touching disks, installing anything, and OS code.

**Acceptance:**
- The revised design and `docs/INSTALL.md` are committed on the branch, with a PR open.
- New external facts have dated source links.
- A short `reviews/05-dual-boot/REPORT.md` exists.

**If unsure:** pick the option that leaves Windows' partitions and boot files untouched and is easiest to undo.

**Model:** gpt-6-astra, xhigh.
