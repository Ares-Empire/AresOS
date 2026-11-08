# 15f REPORT: Lenovo's own Fedora firmware entry

Built by Claude. Brief: `briefs/15f-lenovo-firmware-entry.md`. Reviews are in `REVIEW*.md` next to this file.

## Done

- `firmware_entry` (in `os/owner-tools/owner.py` and the payload copy):
  - Sets aside at most one target-ESP entry whose loader is `\EFI\fedora\shim.efi`. That's the entry Lenovo's firmware recreates at every start.
  - Beside that alias, exactly one other target-ESP entry must remain, and it must be the installer's `\EFI\fedora\shimx64.efi`.
  - Without an alias, the old rule is unchanged: exactly one target-ESP entry.
  - Labels and optional data still decide nothing.
- Tests in `os/tests/test_owner_firmware.py`:
  - Accepted: the alias in either order, with optional data, and in upper case.
  - Refused: the alias alone, two aliases, and the alias beside any other loader (`grubx64.efi`, `\EFI\BOOT\BOOTX64.EFI`, `shim.efi.bak`, `\EFI\other\shim.efi`), with or without the installer entry.
- Review 1 (CHANGES-NEEDED) raised two points, both fixed:
  - **Blocking:** the alias let an unexpected loader stand alone. Fixed by requiring the shimx64 entry beside an alias.
  - **Should-fix:** the equality test treated the package 14 and 15 reports as current. This report is now the current one; those reports stay as history.
- The payload was regenerated with `python os/owner-tools/bundle.py --refresh`.
- Current tools manifest fingerprint: `3ef85c4adab3c8a5daf5bf26c2a40805d24bcb0c17b9327cfc55e7e96aeebefc`. It appears in `docs/INSTALL.md` (the copy check and bootstrap line 8) and in `os/owner-tools/commands.json`.
- INSTALL step 8 now names the Bazzite entry and explains Lenovo's Fedora entry.

## Not changed

- The VM harness's one-entry assertion: OVMF does not make this alias.
- Historical fingerprints in older briefs, reports and fixtures.
- The other install-night guide fixes (board #99, #100, #114, #122). They're a separate package.
