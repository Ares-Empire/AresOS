# 15f: Accept Lenovo's own Fedora firmware entry beside Bazzite

Built by Claude (small fix, found during the owner's real install). A fresh Codex context reviews it.

## What happened (2026-11-08, owner's laptop, Lenovo LOQ 15IRH8)

- Step 4: the bootstrap passed (SHA256SUMS and every file OK). Then `at install` stopped before any write with "Linux firmware entry does not uniquely map to target EFI". `/var/lib/ares` held only diagnostics, no intent.
- Read-only checks passed: /boot/efi, /boot and /sysroot are on Crucial, Micron is unmounted, and the Windows entry matches record A.
- Two firmware entries point at Crucial's new ESP:
  - "Bazzite" → `\EFI\fedora\shimx64.efi`, made by the installer (BootCurrent).
  - "Fedora" → `\EFI\fedora\shim.efi`. Its optional data reads "RC", like every entry the firmware makes itself (USB, DVD, network, PXE).
- With the owner's OK, the "Fedora" entry was deleted with efibootmgr. At the next start the firmware had recreated it. Deleting it can't fix this.
- `disk_record` runs `firmware_entry`, and install, prepare, records, before_switch and others call it. So every tools step would stop on this laptop.

## Fix

- `firmware_entry` still decodes every entry from its device-path bytes. It still ignores labels and optional data, which neither authorize nor refuse.
- Of the entries on the target ESP, it sets aside **at most one** whose loader is `\EFI\fedora\shim.efi` (case-insensitive, since FAT ignores case). It still requires **exactly one** other entry on the target ESP and returns that one.
- So these still stop:
  - the alias alone
  - two aliases
  - two installer entries
  - any other loader path on the target ESP (for example `grubx64.efi`, `\EFI\BOOT\BOOTX64.EFI`, or `shim.efi` outside `\EFI\fedora\`)
- Why it's safe: the alias starts Fedora's shim from the same target ESP. It can't reach the Micron or Windows' boot files. The Windows entry and Micron checks are unchanged.
- The payload is regenerated with `bundle.py --refresh`. The new fingerprint is in INSTALL.md (copy check and bootstrap line 8) and in `os/owner-tools/commands.json`.
- INSTALL step 8 now names the Bazzite entry and explains the Fedora one.

## Out of scope

- Historical briefs, reviews and fixtures that record the old fingerprint.
- The VM harness's own one-entry assertion (`os/ci/two_disk_vm.py`), because OVMF does not make this alias.
- The other install-night guide fixes (board #99, #100, #114, #122). They're a separate package.

**Review model:** gpt-6-astra, high. The diff is small and the change sits on the real install path; the weekly allowance is about 88% used.
