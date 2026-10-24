Reviewed commit `d7f0ac4`. Four findings:

1. **Should-fix — The harness restores Windows-first earlier than the owner guide does.**  
   [two_disk_vm.py:831](../../os/ci/two_disk_vm.py#L831), [INSTALL.md:351](../../docs/INSTALL.md#L351), [EMERGENCY.md:36](../../docs/EMERGENCY.md#L36).  
   Immediately after installation, the harness calls `restore_windows_order()`. The owner instead gets an F12 Windows selection in §5; persistent Windows-first restoration appears only in §8, after switching and recovery checks. F12 selects one boot, so following the guide can leave Linux as the firmware default while the emergency card promises Windows will start unattended. The rehearsal therefore includes a safety step missing from the owner’s sequence.  
   **Fix:** after successful first-login pause/pin, explicitly restore Windows-first and verify an unattended Windows boot before switching. Align the harness with that documented sequence.

2. **Should-fix — Stock identification and GRUB position are incorrectly coupled to BLS filename digits.**  
   [two_disk_vm.py:359](../../os/ci/two_disk_vm.py#L359), [two_disk_vm.py:563](../../os/ci/two_disk_vm.py#L563).  
   The retained installed entries contain **one** checksum-matching stock deployment, but the suffix-required regex accepts **zero** candidates. Also, `menu_index=int(match[1])` is invalid: actual `ostree-2` is titled `Bazzite (ostree:0)`. Allowing bare IDs alone would leave the position bug. The synthetic selector test encodes the same assumption.  
   **Fix:** identify stock by resolving each actual BLS `ostree=` target and matching the exact recorded deployment checksum. Independently obtain its position from the installed GRUB menu inventory—or reproduce that pinned `blscfg` implementation’s ordering and configuration—then confirm the rendered menu before sending keys. Fedora documents filename comparison rules, not an ID-digit-to-position mapping. Add regressions using the retained bare-ID entries and mismatched ID/title numbers. [Fedora BLS ordering](https://fedoraproject.org/wiki/Changes/BootLoaderSpecByDefault)  
   **Owner steps:** INSTALL/EMERGENCY do **not** share the filename-digit assumption; they request a recorded entry, and `default-stock.sh` resolves the deployment index from status. However, INSTALL’s instruction to “record … current GRUB entry” provides no checksum-to-menu mapping procedure. Add one, including the observed fact that both entries can be labelled **Bazzite**. Keep Part B explicitly unqualified until rehearsed.

3. **Should-fix — Firmware auditing accepts arbitrary `BootNext` changes.**  
   [disk_audit.py:316](../../os/ci/disk_audit.py#L316).  
   `compare_nvram()` skips every `BootNext` change without validating its length, destination, authorization or consumption. Windows can remain byte-identical and first in `BootOrder` while an unexpected `BootNext` redirects the next unattended boot. Subsequent installed boots overwrite it in the harness constructor, potentially hiding that regression. The retained full-run captures have no pending `BootNext`; this is a checker gap, not evidence that this run redirected Windows.  
   **Fix:** record and validate each harness-authorized one-time selection before boot, require its consumption afterward, and reject unexpected or malformed values. Add negative tests for an unknown destination and a retained override at a Windows-default checkpoint.

4. **Should-fix — The owner’s switch command omits the newly rehearsed pending-deployment guard.**  
   [switch.sh:10](../../os/release/switch.sh#L10), [INSTALL.md:425](../../docs/INSTALL.md#L425).  
   CI executes a fresh check rejecting `staged` or `rollbackQueued` immediately before `bootc switch`. The owner’s block directly switches after the intervening authentication/signature steps. Earlier pinning does not enforce the required state at the switch boundary.  
   **Fix:** include the same guard in the owner block and test that both switch paths retain equivalent preconditions.

The four owner-facing scripts passed Bash syntax checks; the owner pin block matches the script. Python/VM tests were not rerun because no Python runtime is installed locally. No exposed credential was found in the inspected changes.

CHANGES-NEEDED
