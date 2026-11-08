Reviewed `f8e8cdf9`. Two findings:

1. **Blocking — the exception accepts an unexpected primary loader.**  
   [owner.py:602](C:/Users/pab/AresOS-15f-lenovo-firmware-entry/os/owner-tools/owner.py:602), also shipped in `payload/owner.py`.

   With exactly two target-ESP entries—`\EFI\fedora\shim.efi` and `\EFI\fedora\grubx64.efi`—the function removes the alias and accepts GRUB. The same happens with `\EFI\BOOT\BOOTX64.EFI` or `\EFI\other\shim.efi`. These configurations previously stopped and contradict the brief’s explicit refusals.

   Matching the target ESP is necessary, but does not establish that the remaining entry is the reviewed installer boot path. `disk_record` consequently lets install, prepare, switch, recovery and reboot proceed with this unexpected setup.

   **Fix:** allow the alias exception only beside exactly one reviewed `\EFI\fedora\shimx64.efi` entry, comparing case-insensitively. In [test_owner_firmware.py:76](C:/Users/pab/AresOS-15f-lenovo-firmware-entry/os/tests/test_owner_firmware.py:76), add **alias + unexpected loader, without the normal entry** refusal cases. The existing tests always include the normal entry, so they only demonstrate rejection of three-entry configurations.

2. **Should-fix — the fingerprint equality test still treats historical reports as current.**  
   [test_owner_equality.py:21](C:/Users/pab/AresOS-15f-lenovo-firmware-entry/os/tests/test_owner_equality.py:21).

   Its report slices include the old `3e2c78…` fingerprint at `reviews/14-owner-tools/REPORT.md:47` and `reviews/15-owner-path/REPORT.md:27`. Neither slice is excluded as historical by the existing boundaries. With the new payload, `check_fingerprints` will raise “Stale tools fingerprint or unbound hash.”

   **Fix:** update the test’s current-versus-historical report selection for package 15f, preserving historical receipts and strict checking of current installation documents. Do not globally allow the retired fingerprint.

The exact alias-path comparison and existing device-path validation are appropriately narrow **once finding 1 is fixed**. Protected-disk mount refusal and target-only EFI/boot/system mount checks remain unchanged. I found no additional single-firmware-entry dependency in records, title, reboot, switch, rollback/keep-stock, step 9, optional removal, or EMERGENCY. Stock-title uniqueness concerns BLS deployment entries. The OVMF-only assertions remain unchanged as scoped.

PowerShell verification passed for all **12 payload files**, source equality, both manifests, the exact file list, and the INSTALL.md/commands.json bootstrap match. The resulting fingerprint is `57f2a5c48045fa0d8e0a2b506c473d2bc208b99b04e0c8d2261f3686162ad73a`. `git diff --check main...HEAD` passed.

I did **not** run Python tests: `py -0p` reported no installed Python. Linux Bash/bootstrap, POSIX install/resume/export, native loop-device and two-disk VM tests were not run. Findings above are from source tracing and read-only checks; no laptop disk or firmware operations were performed.

CHANGES-NEEDED